# 🏗️ Архитектура обработки данных в Greenmask

## 🔍 Как происходит трансформация: ряд за рядом, поле за полем

### Основной цикл Greenmask:

```python
# Псевдокод внутреннего цикла Greenmask (упрощённо)
for row in source_table.rows():           # ← Цикл ПО СТРОКАМ
    for column_name, value in row.items():  #   внутри каждого столбец
    
        transformer = get_transformer(column_name)  # Какой трансформатор?
        
        if transformer is None:
            continue  # Нет правил - пропускаем
        
        # Вызываем transform() для этого конкретного поля
        new_value = transformer.transform(row=row, column_name=column_name, table_name=table_name)
        
        row[column_name] = new_value  # Заменяем значение
    
    output_row = finalize_row(row)     # Финализация (например маппинг)
    write_row_to_output(output_row)    # Записываем в output
```

### Ключевые выводы:

| Аспект | Значение | Что это значит для нас |
|--------|----------|------------------------|
| **Обработка по строкам** | Row-level iteration | Мы видим ВСЕ поля текущей строки сразу |
| **Поле за полем** | Column-level transformation | Каждый transformer получает доступ ко всей текущей строке |
| **Sequential by default** | Последовательная обработка | Порядок колонок важен при наличии зависимостей |
| **Batch size per column** | Greenmask batch по каждому столбцу независимо | Не междустолбцовый батчинг автоматически |

---

## 💡 **Где мы можем добавить кастомную логику?**

### Вариант 1: Cross-field awareness через `transform()` signature ✅

**Технически возможно:** Greenmask передаёт в трансформер ВСЮ строку!

```python
class CustomLLMMasker(BaseTransformer):
    def transform(self, row: dict, column_name: str, table_name: str) -> dict:
        """row содержит ВСЕ поля текущей записи!"""
        
        original_value = row.get(column_name)
        
        # ← Можем читать другие поля из этой же строки!
        customer_id = row.get('customer_id')          # Primary key
        first_name = row.get('first_name')             # Другое поле
        phone = row.get('phone')                       # И так далее
        
        # Создаём уникальный ключ на основе комбинированных полей
        entity_key = f"{customer_id}:{table_name}:{hashlib.md5(str(original_value).encode()).hexdigest()[:8]}"
        
        # LLM-трансформация с контекстом других полей
        context_prompt = f"""
        Replace '{original_value}' with a realistic {field_type}.
        IMPORTANT: This belongs to customer_id={customer_id}.
        Other fields: first_name={first_name}, phone={phone}
        
        If this is an address field, use the same city as in another field (if present).
        Return ONLY the new value."""
        
        masked_value = self._call_llm(context_prompt)
        
        return masked_value
```

**Возможности:**
- ✅ Чтение PK (primary key) для консистентного маппинга
- ✅ Чтение соседних полей того же record для context-aware replacement
- ✅ Создание entity-level mapping across ALL tables

---

### Вариант 2: Custom preprocessing после встроенных трансформеров ⚠️

**Problem:** Greenmask сначала применяет built-in transformers (`mask_email`, `ip_anonymize`), потом наши custom.

**Solution:** Добавить post-processing layer!

```yaml
transformers:
  - name: customers_transformer
    schema: test_db
    table: customers
    
    columns:
      email:
        transformer: mask_email       # ← Сначала встроенный
        params:
          keep_domain: false
      
      # ← Но можно добавить "wrapper" transformer который видит результат первого
      # НЕТ! В Greenmask каждый transformer независим :(
      
# Проблема: мы НЕ МОЖЕМ напрямую видеть результат работы другого трансформера
# Решение: использовать single transformer для всех sensitive fields в таблице
```

---

### Вариант 3: Single transformer для группы полей (Рекомендуется!) ⭐⭐⭐

**Лучший подход:** Один custom transformer обрабатывает всё поле целиком с контекстом

```yaml
# Вместо нескольких separate columns → один composite transformer
- name: full_custom_transformation
  schema: test_db
  table: customers
  
  columns:
    # ← Объявляем все PII-поля одним transformer
    _all_pii_fields_:           # Special marker for multi-column transformer
      transformer: custom_multi_field_masker
      params:
        llm_model: bailian/qwen3.5-flash
        preserve_city_from_address: true
        generate_consistent_ids: true
```

---

## 🎯 **City/preserving strategies**

### Подход 1: Extract + Transform (наиболее гибкий)

```python
def transform(self, row: dict, column_name: str, table_name: str) -> dict:
    # ← Если колонка - address (composite field)
    if 'address' in column_name:
        address = row[column_name]
        
        # Parse address manually or use library
        parts = parse_address(address)
        # parts = {"street": "Calle Mayor 123", "city": "Madrid", "country": "Spain"}
        
        city = parts['city']
        country = parts['country']
        street_num = parts['street_number']
        street_name = parts['street_name']
        
        # ← Генерируем новую улицу ТОЛЬКО того же города
        prompt = f"""Replace street number/name for {street_num} {street_name} in {city}, Spain.
Return format: "StreetName StreetNumber".
Do NOT change city or country."""
        
        new_street = self._call_llm(prompt)
        
        new_address = f"{new_street}, {city}, {country}"
        row[column_name] = new_address
        return row
    
    # Для отдельных адресных полей
    elif 'shipping_address' in column_name:
        # Аналогично сохраняем city consistency
```

### Подход 2: Mapping-based approach (consistency guaranteed!)

```python
class AddressTransformer:
    def __init__(self):
        self.city_mapping = {}  # city_name → new_city_in_same_region
    
    def _load_city_list(self, country: str):
        """Pre-load list of valid cities per country"""
        self.cities_by_country = {
            "Spain": ["Madrid", "Barcelona", "Valencia", "Seville"],
            "Brazil": ["São Paulo", "Rio de Janeiro", "Brasília"],
            "Russia": ["Москва", "Санкт-Петербург", "Новосибирск"]
        }
    
    def transform(self, city: str, country: str) -> str:
        """Ensure new city stays within same country/region"""
        
        if country not in self.cities_by_country:
            return city  # No mapping available
        
        current_cities = self.cities_by_country[country]
        
        if city not in current_cities:
            # Unknown city → replace with random from list
            return random.choice(current_cities)
        
        # Known city → consistent replacement
        other_cities = [c for c in current_cities if c != city]
        return random.choice(other_cities)
```

**Преимущества:**
- ✅ City всегда остаётся в рамках страны
- ✅ Консистентность: Madrid → Barcelona везде одинаково
- ✅ Fast lookup (no LLM calls needed!)

---

## 🔄 **Consistent ID generation across related tables**

### Problem: Foreign Key Integrity

```sql
-- BEFORE
customers.customer_id = 1 → orders.customer_id = 1

-- BAD (если менять ID случайно в каждой таблице)
customers.customer_id = 999 → orders.customer_id = 847  ← BROKEN FK!

-- GOOD (консистентное изменение с сохранением связи)
customers.customer_id = 999 → orders.customer_id = 999  ← PRESERVED!
```

### Solution 1: PK-preserving approach (Recommended) ✅

**Не трогать Primary Keys вообще!**

```yaml
transformers:
  - name: preserve_pks
    schema: test_db
    table: customers
    columns:
      customer_id:
        transformer: nullifier_or_skip   # ← Просто НЕ маскируем PK!
    
    # Альтернатива: skip rule
    skip_columns:
      - customer_id
      - order_id
      - log_id
```

**Почему лучше не трогать PK:**
- ✅ FK relationships automatically preserved
- ✅ Database integrity maintained without extra work
- ✅ Easier debugging/testing
- ✅ PKs are rarely PII (just numbers/UUIDs)

### Solution 2: Consistent remapping via PK hash

Если очень нужно изменить PK:

```python
class ConsistentPKRemapper:
    def __init__(self):
        self.pk_mapping = {}
    
    def _create_pk_hash(self, old_pk: int) -> int:
        """Generate consistent new PK based on old one"""
        
        # Check existing mapping
        if old_pk in self.pk_mapping:
            return self.pk_mapping[old_pk]
        
        # Generate deterministic replacement
        import hashlib
        hash_val = int(hashlib.sha256(str(old_pk).encode()).hexdigest()[:8], 16)
        new_pk = 100000 + (hash_val % 900000)  # Range: 100000-999999
        
        # Save mapping for consistency
        self.pk_mapping[old_pk] = new_pk
        
        return new_pk
    
    def transform(self, pk_value: int) -> int:
        return self._create_pk_hash(pk_value)
```

**Usage:**
```python
# In customers table
new_customer_id = remapper.transform(old_customer_id)

# In orders table (same remapper instance!)
new_order_customer_id = remapper.transform(existing_fk_reference_to_customer)
```

**Результат:**
```
customers.customer_id: 1 → 456789
orders.customer_id FK: 1 → 456789  ← SAME! ✅
```

---

## 📋 **Recommendation: Hybrid approach**

### Best practice for your project:

```yaml
transformers:
  # ====================================================================
  # CUSTOMERS TABLE
  # ====================================================================
  - name: customers_full_transform
    schema: test_db
    table: customers
    columns:
      # Primary Key - KEEP AS IS (preserve FK references!)
      customer_id:
        transformer: static_replace
        value: "{{ customer_id }}"   # ← Keep original value
      
      # Names (LLM with language detection)
      first_name:
        transformer: custom_llm_masker
        params:
          prompt_template_file: /app/prompt_templates/name.txt
          llm_model: bailian/qwen3.5-flash
      
      last_name:
        transformer: custom_llm_masker
        params:
          prompt_template_file: /app/prompt_templates/name.txt
      
      # Contact info (built-in Greenmask fast & reliable)
      email:
        transformer: mask_email
        params:
          keep_domain: false
          new_prefix: anon
      
      phone:
        transformer: mask_phone
        params:
          country_code: "+1"
          format: international
      
      # Dates (shift but maintain relative ordering)
      birth_date:
        transformer: date_shift
        params:
          shift_days: -7
      
      # Addresses (city-preservation!)
      address:
        transformer: custom_city_preserving_masker
        params:
          extract_city_from_other_field: true
          replace_street_only: true
      
      # System logs will reference these IDs - they're now consistent!
  
  # ====================================================================
  # ORDERS TABLE - FK relationships auto-preserved via unchanged customer_id
  # ====================================================================
  - name: orders_transformer
    schema: test_db
    table: orders
    columns:
      # Foreign Key - AUTO-PRESERVED (points to same customer_id in customers)
      customer_id:
        transformer: static_replace
        value: "{{ customer_id }}"   # ← Reference from customers!
      
      shipping_address:
        transformer: static_replace
        value: "456 Oak Avenue, Chicago, IL 60601, USA"
      
      status:
        transformer: random_select
        params:
          options:
            - completed
            - pending
            - shipped
            - cancelled
  
  # ====================================================================
  # SYSTEM LOGS - Technical data anonymization
  # ====================================================================
  - name: system_logs_transformer
    schema: test_db
    table: system_logs
    columns:
      # User reference (FK - preserved)
      user_id:
        transformer: static_replace
        value: "{{ user_id }}"
      
      ip_address:
        transformer: ip_anonymize
        params:
          method: hash_last_octet
      
      timestamp:
        transformer: timestamp_shift
        params:
          shift_days: -7
```

---

## 🎯 **Summary: Your requirements mapped**

| Your requirement | Our solution | File location |
|------------------|--------------|---------------|
| Flexibility beyond single field | Multi-column awareness via full `row` object | `llm_masker.py::transform()` |
| Post-builtins processing | Hybrid: built-ins first, then LLM if needed | `config.yaml` order matters |
| System prompts for text/JSON | Add instructions in `_system_context_` parameter | `llm_masker.py::_call_llm()` |
| Preserve linkages (FK integrity) | Don't touch Primary Keys! | All tables |
| Random names but realistic | LLM with language script preservation | `prompt_templates/name.txt` |
| Random addresses from same cities | Extract city, regenerate street only | `config.yaml` + custom transformer |
| Consistent ID changes across tables | Hash-based PK mapping OR just don't change them | `ConsistentPKRemapper` class |

---

## 💬 **My answer to your concerns:**

### Do I agree/disagree?

✅ **AGREE:** 
- Don't touch Primary Keys (preserve FK integrity)
- Use LLM only for complex text fields (names, addresses)
- Let Greenmask built-ins handle simple replacements (email, IP)
- Maintain city/country boundaries in address masking

⚠️ **Clarify:**
- "System prompts for JSON fields" → You can add ANY instruction in your LLM prompt!
- "Processing row-by-row vs field-by-field" → Both happen; row gives access to all fields at once

🔧 **Enhance:**
- Create `CustomAddressTransformer` that extracts+preserves city
- Make sure FK references don't need changing at all

---

## 🚀 **Next concrete steps:**

1. ✅ Add skip_rule for primary keys in config.yaml
2. ✅ Create `custom_city_preserving_masker` class
3. ✅ Test with test_dump.sql to verify FK integrity preserved
4. ✅ Document best practices in README.md

Хочешь, чтобы я создал реальный код для `CustomAddressTransformer` прямо сейчас? Или сначала протестируешь current setup?
