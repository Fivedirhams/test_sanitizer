# 🧵 Алгоритм санитизации тестовой базы MySQL - Полная спецификация

## 📋 Обзор процесса

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: dump.sql                                            │
│  (SQL INSERT statements with original PII data)            │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: Parse SQL DUMP                                    │
│  ├─ Read dump.sql line by line                              │
│  ├─ Identify CREATE TABLE / INSERT statements               │
│  └─ Extract schema structure + row data                     │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: Load Transformers                                 │
│  ├─ Read config.yaml                                        │
│  ├─ Initialize Greenmask engine                             │
│  ├─ Register custom transformers (LLM masker, address)     │
│  └─ Skip columns based on PK preservation rules             │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: Transform Rows (MAIN LOOP)                        │
│                                                              │
│  for row in source_table.rows():                            │
│      for column_name, value in row.items():                │
│          if column_name in skip_columns:                    │
│              → PASS (no transformation)                     │
│              → FK integrity preserved ✅                    │
│          else:                                               │
│              transformer = get_transformer(column_name)     │
│              new_value = transformer.transform(row, ...)   │
│              → Save mapping for consistency                 │
│                                                              │
│  END LOOP                                                   │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 4: Post-Processing                                   │
│  ├─ Validate FK relationships                               │
│  ├─ Export mapping.json (optional)                          │
│  └─ Compress output to .sql.gz                              │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT: sanitized.sql.gz                                   │
│  (Identical schema, anonymized values, intact FK links)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Подробный разбор каждого этапа

### ⚡ PHASE 1: Парсинг SQL дампа

**Что происходит:**
```python
# Внутри Greenmask или кастомного парсера
with open('dump.sql', 'r', encoding='utf-8') as f:
    for line in f:
        # Распознаём типы строк
        if line.startswith('CREATE TABLE'):
            parse_schema(line)          # ← Строим структуру БД
        
        elif line.startswith('INSERT INTO'):
            table_name = extract_table(line)
            
            # Извлекаем все значения из INSERT statement
            values_list = extract_values(line)
            
            # Разбираем VALUES по колонкам
            for col_idx, value in enumerate(values_list):
                column_name = schema[table_name][col_idx]
                
                # ← Данные готовы к трансформации!
                row[column_name] = value
                
            process_row(row, table_name)  # ← Переход к PHASE 3
```

**Свойства:**
- **Sequntial processing**: читается ПО СТРОКАМ, одна за другой
- **No parallelism**: на уровне чтения файла нет асинхронности
- **Memory efficient**: построчное чтение без загрузки всего dump в RAM

---

### ⚡ PHASE 2: Инициализация трансформеров

**Что загружается из config.yaml:**

```yaml
transformers:
  - name: customers_transformer
    schema: test_db
    table: customers
    skip_columns: [customer_id]  # ← Ключевое правило
    columns:
      first_name: { transformer: custom_llm_masker, ... }
      last_name:  { transformer: custom_llm_masker, ... }
      email:      { transformer: mask_email, ... }
```

**Алгоритм инициализации:**
```python
class GreenmaskEngine:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        
        # 1. Parse all transformer definitions
        for table_def in self.config.transformers:
            for column_name, transformer_def in table_def.columns.items():
                
                # Create transformer instance
                transformer = create_transformer(
                    type=transformer_def.transformer,
                    params=transformer_def.params
                )
                
                # Register for this specific column
                self.column_transformers[f"{table_def.table}.{column_name}"] = transformer
        
        # 2. Build skip list for primary keys
        self.skip_columns = set()
        for table_def in self.config.transformers:
            if hasattr(table_def, 'skip_columns'):
                for col in table_def.skip_columns:
                    self.skip_columns.add(f"{table_def.table}.{col}")
    
    def transform(self, row, table_name, column_name, value):
        key = f"{table_name}.{column_name}"
        
        # ← КЛЮЧЕВАЯ ПРОВЕРКА №1: SKIP RULE
        if key in self.skip_columns:
            return value  # ← Возвращаем оригинал без изменений! ✅
        
        # ← Если не skip, применяем трансформер
        transformer = self.column_transformers[key]
        return transformer.transform(row=row, value=value)
```

**Важные свойства:**
- ❌ **НЕ параллельная** обработка на этапе инициализации
- ✅ Deterministic initialization (предсказуемый порядок)
- ✅ Single-threaded для надёжности маппинга

---

### ⚡ PHASE 3: Основная трансформация рядов (CRITICAL!)

#### Как работает цикл обработки:

```python
def transform_database(dump_path: str, config: Config):
    greenmask = GreenmaskEngine(config)
    
    # ← Открываем входной дамп
    input_f = gzip.open(dump_path, 'rt', encoding='utf-8')
    
    # ← Создаём выходной файл
    output_f = gzip.open('./output/sanitized.sql.gz', 'wt', encoding='utf-8')
    
    current_table = None
    
    for line in input_f:
        # Parse SQL line
        if line.strip().startswith('INSERT INTO'):
            match = re.search(r'INSERT INTO `?(\w+)`?', line)
            current_table = match.group(1) if match else None
            
            # Extract all field values from INSERT statement
            insert_match = re.search(r'VALUES\s*\(([^)]+)\)', line)
            raw_values = insert_match.group(1) if insert_match else ''
            
            # Parse comma-separated values into dict
            values_dict = parse_values(raw_values, schema[current_table])
            
            # ← КРИТИЧЕСКАЯ ЧАСТЬ: Transform each field
            transformed_values = {}
            for col_name, original_value in values_dict.items():
                
                entity_key = f"{current_table}:{col_name}:{hashlib.md5(str(original_value).encode()).hexdigest()[:16]}"
                
                # ← ПРОВЕРКА #1: Is this a skip column? (PK/FK field)
                if f"{current_table}.{col_name}" in greenmask.skip_columns:
                    transformed_values[col_name] = original_value
                    # ← ОРИГИНАЛЬНОЕ ЗНАЧЕНИЕ СОХРАНЯЕТСЯ ✅
                    continue
                
                # ← ПРОВЕРКА #2: Do we have cached mapping?
                if entity_key in global_entity_mapping:
                    transformed_values[col_name] = global_entity_mapping[entity_key]
                    continue
                
                # ← Вызываем трансформер
                transformer = greenmask.get_transformer(current_table, col_name)
                new_value = transformer.transform(
                    row=values_dict,         # ← Доступ ко ВСЕМ полям этой записи!
                    column_name=col_name,
                    table_name=current_table
                )
                
                # ← Сохраняем маппинг для консистентности
                global_entity_mapping[entity_key] = new_value
                transformed_values[col_name] = new_value
            
            # Rebuild INSERT statement
            new_line = rebuild_insert_line(current_table, transformed_values)
            output_f.write(new_line + '\n')
        
        else:
            # Non-INSERT lines pass through unchanged
            output_f.write(line)
    
    input_f.close()
    output_f.close()
```

---

### ⚡ ПРОВЕРКИ ЦЕЛОСТНОСТИ KEYs (Critical Section!)

#### PROBLEM: Что если LLM вернёт случайный новый ID?

```python
# ВНИМАНИЕ: Это НЕ произойдёт при правильной конфигурации!

class CustomLLMMasker(BaseTransformer):
    def transform(self, row, column_name, table_name):
        original_value = row.get(column_name)
        
        # ← ЭТОТ КОД БУДЕТ ИГНОРИРОВАТЬ _id COLUMNS благодаря skip_columns!
        # Но если бы мы случайно пропустили его:
        
        if column_name.endswith('_id'):  # Например, customer_id
            prompt = f"Replace '{original_value}' with random number..."
            random_id = self._call_llm(prompt)  # ← Опасно! Вернёт новое число
            
            # ← ЛЛМ может вернуть НОВЫЙ ID! Это нарушит FK связи!
            return random_id  
```

#### SOLUTION: Две уровня защиты!

**Level 1: CONFIG-SPECIFIC skip_columns**
```yaml
skip_columns:
  - customer_id
  - order_id
  - user_id
```

**Level 2: TRANSFORMER-INTERNAL validation**
```python
class CustomLLMMasker:
    def transform(self, row, column_name, table_name):
        # ← ЗАЩИТА №1: Проверка типа поля
        if column_name.endswith('_id') or column_name == 'id':
            raise ValueError(
                f"ERROR: Should not transform ID fields!\n"
                f"Check config.yaml skip_columns setting.\n"
                f"This error prevented FK breakage."
            )
        
        # ← Продолжаем только для безопасных полей
        masked_value = self._call_llm(...)
        return masked_value
```

**Level 3: VALIDATION AFTER TRANSFORMATION**
```python
def validate_fk_integrity(output_dump: str, original_schema: dict):
    """Post-processing check"""
    
    errors = []
    
    # Load both tables
    customers = load_data(output_dump, 'customers')
    orders = load_data(output_dump, 'orders')
    
    # Check every FK reference
    for order in orders:
        fk_customer_id = order['customer_id']
        
        # Find matching customer
        customer = next((c for c in customers if c['customer_id'] == fk_customer_id), None)
        
        if not customer:
            errors.append(
                f"FK violation: orders.customer_id={fk_customer_id} "
                f"has no matching customers.customer_id!"
            )
    
    if errors:
        print("❌ INTEGRITY CHECK FAILED!")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    
    print("✅ FK integrity validated successfully!")
```

---

## 🔄 Асинхронность и параллелизм

### Вопрос: **Parallel vs Sequential?**

| Этап | Parallel? | Reason |
|------|-----------|--------|
| Parсинг dump.sql | ❌ No | Line-by-line parsing required |
| Трансформация строк | ⚠️ Optional | Можно распараллелить BETWEEN rows |
| Transfomer calls | ❌ No | Entity mapping must be consistent |
| LLM API calls | ⚠️ Async possible | Multiple concurrent HTTP requests ok |
| FK validation | ❌ No | Must run after all transformations |

### Текущая реализация (Sequential):

```python
for row in rows:                  # ← SERIALLY processed one at a time
    for field in row.fields:      #       field by field
        result = transform(field)  #       synchronous call
    save_row(result)              # ← Write sequentially
```

### OPTIMIZATION: Batch+Async LLM calls

Если нужно ускорить:

```python
import asyncio

async def transform_batch(rows: List[dict], transformer):
    tasks = []
    
    for row in rows:
        task = asyncio.create_task(
            transformer.transform_async(row=row)  # ← Async version
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

**Ограничения:**
- Entity mapping всё равно требует синхронного доступа
- Консистентность важнее скорости

---

## 📊 Правила трансформации по типам данных

### Таблица: Какие transformers применяются к каким полям

| Поле | Transformer | Правило | Пример до/после |
|------|-------------|---------|-----------------|
| `customer_id` | **SKIP** | Не трогать Primary Key! | `1 → 1` ✅ |
| `order_id` | **SKIP** | Не трогать Primary Key! | `100 → 100` ✅ |
| `email` | `mask_email` | Новый домен, старый prefix | `maria@g.com → anon@example.com` |
| `phone` | `mask_phone` | Интернациональный формат | `+7-495-xxx → +1-XXX` |
| `first_name` | `custom_llm_masker` | Языко-сохранённая замена | `María → Carmen` (испанский) |
| `last_name` | `custom_llm_masker` | Языко-сохранённая замена | `Иванов → Петров` (русский) |
| `birth_date` | `date_shift` | Сдвиг -7 дней | `1990-05-15 → 1990-05-08` |
| `address` | city-preserving masker | Город остаётся | `Calle Mayor 123, Madrid → Calle Velázquez 45, Madrid` |
| `shipping_address` | static_replace | Полный текст | `→ "456 Oak Ave, Chicago"` |
| `ip_address` | `ip_anonymize` | Хеш последнего октета | `192.168.1.100 → 192.168.1.XXX` |
| `user_agent` | static_replace | Generic string | Mozilla...Chrome/120.0 → Mozilla...Chrome/120.0 |
| `timestamp` | timestamp_shift | Сдвиг хронологии | `2024-01-20 → 2024-01-13` |

---

## 🔐 Форматы и правила сохранения

### Для имен (Names):
```python
RULES:
1. Detect language/script from character set patterns
   - Latin Extended: María, Roberto (Spanish/Portuguese)
   - Cyrillic: Ярослав, Иванов (Russian)
   
2. Generate replacement in SAME language
   - Spanish names → Spanish names only
   - Russian names → Russian names only
   
3. Maintain cultural appropriateness
   - María → Gabriela (not Яна)
   - Ярослав → Дмитрий (not Alexander)
   
4. Consistent entity mapping across tables
   - "Maria Garcia" in customers AND orders → same replacement everywhere
```

### Для адресов (Addresses):
```python
RULES:
1. Parse address into components
   street_number, street_name, city, country
   
2. Preserve city/country boundary
   - Madrid stays in Spain
   - Москва stays in Russia
   
3. Regenerate street only
   - Old: Calle Mayor 123
   - New: Calle Velázquez 45 (same city)
   
4. Format preservation
   - European format: "StreetNumber, City, Country"
   - US format: "StreetName Number, City, ST ZIP, Country"
```

### Для телефонов (Phones):
```python
RULES:
1. Detect country from initial digits or existing pattern
   - +7 → Russia
   - +34 → Spain
   - +55 → Brazil
   
2. Preserve national numbering plan
   - Russia: +7-XXX-XXX-XX-XX
   - Spain: +34-XXX-XXX-XXX
   - USA: +1-XXX-XXX-XXXX
   
3. If unknown country → use default format (+1 international)
```

### Для первичных ключей (Primary Keys):
```python
RULES:
⚠️ NEVER CHANGE THEM!

Why:
- Foreign Keys reference these exact values
- Changing breaks referential integrity
- No valid reason to anonymize internal IDs

Rule: 
if column_name.endswith('_id') or column_name == 'id':
    → KEEP ORIGINAL VALUE UNCHANGED ✅
```

---

## ✅ Контрольные точки валидации

### Pre-transformation checks:
```python
def pre_validation(dump_path: str):
    # 1. Verify dump exists and is valid SQL
    if not os.path.exists(dump_path):
        raise FileNotFoundError("dump.sql not found")
    
    # 2. Verify config has valid transformers
    config = load_config('config.yaml')
    
    for table in config.tables:
        # Check all referenced transformers exist
        for transformer_type in table.transformers:
            assert transformer_exists(transformer_type), \
                f"Unknown transformer: {transformer_type}"
    
    # 3. Verify all tables have appropriate skip_columns
    for table in config.tables:
        assert any(col.endswith('_id') for col in table.columns), \
            "Table missing primary key detection"
    
    print("✅ Pre-validation passed")
```

### Post-transformation checks:
```python
def post_validation(output_path: str):
    with gzip.open(output_path, 'rt') as f:
        content = f.read()
    
    # Check FK references exist in both tables
    customers_ids = set(re.findall(r'INSERT INTO `customers`.*?\((\d+)\)', content))
    orders_cids = set(re.findall(r'INSERT INTO `orders`.*?\(\d+, (\d+)', content))
    
    invalid_refs = orders_cids - customers_ids
    if invalid_refs:
        raise ValueError(
            f"FK violations found! Invalid customer_id refs:\n{invalid_refs}"
        )
    
    # Verify some expected changes occurred
    assert 'anon@example.com' in content, "Email transformation failed"
    assert len(customers_ids) > 0, "No customers found"
    
    print("✅ Post-validation passed")
    print(f"   - Customers count: {len(customers_ids)}")
    print(f"   - FK integrity: Valid")
```

---

## 📁 Итоговая структура файлов и их роль

```
/project/my-sql-sanitizer/
├── dump.sql                   ← INPUT (или copy from test_dump.sql)
├── config.yaml                ← RULES definition (what transforms what)
│   ├── skip_columns           ← PK protection layer #1
│   ├── transformers           ← Field-to-transformer mapping
│   └── mapping                ← Output location config
│
├── transformers/
│   ├── llm_masker.py          ← Language-aware name replacement
│   ├── city_preserving_address_masker.py  ← City+country preservation
│   └── pk_preservation_helper.py          ← Validation helper (optional)
│
├── prompt_templates/
│   ├── name.txt               ← System prompt for name transformation
│   ├── phone.txt              ← Regional phone format instructions
│   └── address.txt            ← City-preservation rules
│
├── GREENMASK_ARCHITECTURE.md  ← Detailed architecture documentation
├── PII_TRANSFORMATIONS_GUIDE.md  ← Type-by-type transformation strategies
└── start.sh                   ← One-command orchestration script
```

---

## 🎯 Резюме: Полный алгоритм шаг за шагом

```
STEP 1: Read dump.sql line-by-line (sequential, memory-efficient)

STEP 2: Parse CREATE TABLE statements → build schema dictionary

STEP 3: For each INSERT statement:
        ├─ Extract table_name from INSERT INTO clause
        ├─ Extract values from VALUES (...) clause
        ├─ Split values by comma → associate with schema columns
        │
        STEP 4: For each (column_name, value) pair:
                ├─ Check if column in skip_columns (ends_with('_id')?)
                │   └─ YES → Keep original value (PK preserved!) ✅
                │   └─ NO → Continue
                │
                ├─ Check if entity_key in global_mapping_cache
                │   └─ YES → Use cached replacement ✅
                │   └─ NO → Continue
                │
                └─ Call transformer.transform(row, column_name, table_name)
                    ├─ Determine transformer type from config.yaml
                    ├─ Apply language-aware replacement if name field
                    ├─ Apply city-preserving logic if address field
                    ├─ Apply built-in mask_* transformers if applicable
                    └─ Cache result in global_mapping_cache

STEP 5: Reconstruct INSERT statement with transformed values

STEP 6: Write to output file (sanitized.sql.gz)

STEP 7: After all rows processed:
        ├─ Run FK integrity validation
        ├─ If validation fails → ERROR and stop
        └─ If validation passes → SUCCESS

STEP 8: Optionally export mapping.json for reconciliation
```

---

**Все вопросы закрыты! Готовы к запуску!** 🚀