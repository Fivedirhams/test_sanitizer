# 📋 Правила Трансформации Данных и Их Отражение в config.yaml

## 🔑 Ключевые Принципы (Всегда Работают!)

### ✅ ПРАВИЛО #1: NEVER Transform Primary Keys!

**Почему:** Foreign Keys ссылуются на PK → если поменять PK, FK станут невалидными.

**Как реализовано:**
```yaml
skip_columns:
  - customer_id       # ← Везде пропускается!
  - order_id
  - user_id
  - log_id
```

**Пример:**
```sql
-- ДО:
customers(1, "María García")         -- customer_id = 1
orders(100, 1, "Laptop")              -- orders.customer_id = 1 → ссылки на customers.customer_id = 1 ✅

-- ГРИНМАСК НЕ ТРОГАЕТ customer_id:
-- ПОСЛЕ:
customers(1, "Carmen Silva")         -- STILL 1! ✅
orders(100, 1, "Desktop")             -- STILL 1! ✅
-- REFERENTIAL INTEGRITY PRESERVED! 🎉
```

---

### ✅ ПРАВИЛО #2: Entity Consistency

**Почему:** Одно и то же значение должно заменяться одинаково везде.

**Пример проблемы БЕЗ консистентности:**
```sql
-- БЕЗ cache:
customers.first_name: "Maria Garcia" → "Anonymous Person"
orders.first_name: "Maria Garcia"   → "Someone Else" ❌ (разные замены!)
```

**Решение WITH entity_key hashing:**
```python
# transformers/llm_masker.py::CustomLLMMasker.transform()
entity_key = f"{table}:{column}:{hash(value)[:16]}"

if entity_key in global_mapping:
    return global_mapping[entity_key]  # ← Та же самая замена!
else:
    new_value = call_llm(...)
    global_mapping[entity_key] = new_value
```

**Итог:**
```sql
-- С cache:
customers.first_name: "Maria Garcia" → "Carmen Lopez" ✅
orders.first_name: "Maria Garcia"   → "Carmen Lopez" ✅ (Одинаково!)
```

---

### ✅ ПРАВИЛО #3: Language Preservation

**Почему:** Spanish names должны оставаться Spanish, Russian — Russian.

**Реализация через prompt_template:**
```python
# prompt_templates/name.txt
Do NOT change script or language. 
For example: María→Gabriela (not Яна), Roberto→Carlos (not Ярослав).
```

**Примеры трансформаций:**
| Original | Transformed | Preserved? |
|----------|-------------|------------|
| María García | Carmen López | ✅ Испанский |
| Ярослав Петров | Дмитрий Соколов | ✅ Русский |
| Luís Gonçalves | Pedro Silva | ✅ Португальский |
| François Tremblay | Marie Dubois | ✅ Французский |
| Maria Garcia (English) | Anonymous Name | ⚠️ Если нет шаблона языка |

---

### ✅ ПРАВИЛО #4: City/Country Preservation in Addresses

**Почему:** Улица меняется, но город остаётся тем же для локализации.

**Реализация:**
```yaml
address:
  transformer: city_preserving_address_masker
  
shipping_address:
  transformer: static_replace
  value: "New street, [same_city], same_country"
```

**Пример:**
```sql
-- DO:
Av. Brigadeiro Faria Lima, São Paulo, Brazil

-- AFTER:
Rua Augusta, São Paulo, Brazil  ← Street changed, city preserved! ✅
```

---

### ✅ ПРАВИЛО #5: Batch Processing for Efficiency

**Оптимизация для больших баз (>1K rows):**

```python
# transformers/llm_masker.py
batch_size = 20  # Configurable

def transform(self, row, column_name, table_name):
    # Collect batch first
    batch_values = collect_column_values(column_name)
    
    # Single API call for entire batch
    masked_batch = _call_llm_batch(batch_values)  # 1 call vs N calls
    
    # Distribute back to original rows
    return zip(batch_values, masked_batch)
```

**Эффект:**
| Dataset Size | Single-Row Calls | Batch (20x) Calls | Speedup |
|--------------|------------------|-------------------|---------|
| 100 rows | 100 | 5 | **20x faster** |
| 1,000 rows | 1,000 | 50 | **20x faster** |
| 10,000 rows | 10,000 | 500 | **20x faster** |

---

## 📊 Таблица всех трансформаций (config.yaml ↔ Rule)

| Поле | Transformer | Правило | config.yaml | Пример до/после |
|------|-------------|---------|-------------|-----------------|
| `*_id` | SKIP | Never change PK/FK | `skip_columns: [-customer_id]` | `1 → 1` (unchanged!) |
| `first_name` | LLM Masker | Language-aware replacement | `transformer: custom_llm_masker` | `"María" → "Carmen"` |
| `last_name` | LLM Masker | Language-aware replacement | `transformer: custom_llm_masker` | `"García" → "López"` |
| `email` | Greenmask `mask_email` | New prefix + domain | `transformer: mask_email` | `"maria@g.com" → "anon@example.com"` |
| `phone` | Greenmask `mask_phone` | Country code format | `transformer: mask_phone` | `"+7-495..." → "+1-(XXX)"` |
| `address` | Custom masker | City+country preserved | `city_preserving_address_masker` | `"Street A, City B" → "Street C, City B"` |
| `shipping_address` | Static replace | Placeholder string | `static_replace` | Full text → `"456 Oak Ave, Chicago"` |
| `ip_address` | Greenmask `ip_anonymize` | Hash last octet | `ip_anonymize` | `192.168.1.100 → 192.168.1.XXX` |
| `user_agent` | Static replace | Generic browser | `static_replace` | `"Chrome/120.0..." → generic string` |
| `birth_date` | Date shift | Shift -7 days | `date_shift` | `"1990-05-15" → "1990-05-08"` |
| `order_timestamp` | Timestamp shift | Shift chronology | `timestamp_shift` | Relative order maintained |
| `total`, `price` | Amount anonymize | Preserve distribution | `amount_anonymize` | Numeric range kept |
| `status` | Random select | Uniform distribution | `random_select` | Uniform mix of statuses |

---

## 🔧 Как адаптировать под БАЗУ ОТ ЗАКАЗЧИКА?

### Шаг 1: Определите таблицы с PII

```sql
-- Запрос к базе заказчика:
SHOW TABLES;
SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS 
WHERE TABLE_NAME IN ('users', 'customers', 'employees')
AND (COLUMN_NAME LIKE '%name%' OR COLUMN_NAME LIKE '%email%' OR COLUMN_NAME LIKE '%phone%');
```

### Шаг 2: Обновите config.yaml

```yaml
transformers:
  
  # NEW: users table from your database
  - name: users_transformer
    schema: production_db          # ← ИЗ МЕНЮ
    table: users                   # ← ИЗ МЕНЮ
    
    skip_columns:
      - user_id                    # ← ВСЕГДА сохраняйте PK
    
    columns:
      username:
        transformer: static_replace
        value: "anonymous_user_[hash]"
      
      email:
        transformer: mask_email
        params:
          new_prefix: anon
          new_domain: example.com
      
      full_name:
        transformer: custom_llm_masker
        params:
          field_type: "name"
          prompt_template_file: /app/prompt_templates/name.txt
      
      phone:
        transformer: mask_phone
        params:
          country_code: "+1"
          format: international
      
      address:
        transformer: city_preserving_address_masker
  
  # ... Add more tables as needed
```

### Шаг 3: Для каждого типа поля выберите transformer

| Тип поля | Какой transformer | config.yaml настройка |
|----------|-------------------|------------------------|
| Имена людей | `custom_llm_masker` | `transformer: custom_llm_masker` + `prompt_template_file` |
| Email | `mask_email` | `transformer: mask_email` + `new_prefix/new_domain` |
| Телефоны | `mask_phone` | `transformer: mask_phone` + `country_code` |
| Адреса | `city_preserving_address_masker` | Или `static_replace` для простого |
| IP адреса | `ip_anonymize` | `transformer: ip_anonymize` |
| Даты | `date_shift` или `timestamp_shift` | `params.shift_days: -7` |
| Статусы | `random_select` | `params.options: ["A", "B", "C"]` |
| Любые другие | `static_replace` | `value: "[MASKED]"` |

### Шаг 4: Добавьте в skip_columns все *_id поля

```yaml
skip_columns:
  - user_id
  - account_id
  - order_id
  - session_id
  # ← ВСЕ первичные ключи!
```

---

## 🎯 Summary: Универсальный подход

✅ **Конфиг универсален** — работает с любой MySQL базой

**Что нужно изменить для новой базы:**

| Что | Где изменить | Сколько файлов |
|-----|-------------|----------------|
| Список таблиц с PII | `config.yaml` — `transformers[].table` | 1 файл |
| Columns для каждой таблицы | `config.yaml` — `columns.*` | 1 файл |
| Skip columns (PKs) | `config.yaml` — `skip_columns[]` | 1 файл |
| Prompt templates (опционально) | `prompt_templates/*.txt` | Если нужны кастомные правила |
| Логика трансформации (advanced) | `transformers/*.py` | Только при необходимости кастомной логики |

**Что НЕ меняется:**
- `start.sh` — запускает то же самое
- `docker-compose.yml` — контейнер тот же
- `llm_masker.py` — language awareness та же
- Entity consistency logic — та же
- FK preservation mechanism — тот же

---

## 💡 Проверка перед продакшеном

```bash
# 1. Создайте тестовый дамп из production базы
mysqldump -u root production_db > test_production.sql

# 2. Обновите config.yaml под структуру этой базы
# (добавьте правильные table/column имена)

# 3. Протестируйте на маленьком дампе
cp test_production.sql dump.sql
./start.sh

# 4. Проверьте результаты
gunzip -c output/sanitized.sql.gz | head -100

# 5. Проверьте статистику
./tools/report.sh

# 6. Если всё ок → готово для продакшен!
```

---

## 🚨 Чего НЕ делать:

❌ **NEVER** менять первичные ключи (`*_id`) без полной перемаппинга FK
❌ **DON'T** использовать статические значения для sensitive данных (лучше LLM masking)
❌ **DON'T** сохранять mapping.json в продакшене (это sensitive data!)
❌ **DON'T** запускать без .env с правильным API key
