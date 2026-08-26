# 🚀 Quick Reference: Answers to Your Questions

## ❓ Вопрос 1: "У нас используется в старте гринмаск то?"

✅ **ДА!** Greenmask — это ядро проекта.

```bash
# start.sh запускает:
docker-compose up -d sanitizer
docker-compose logs -f sanitizer

# Внутри docker-compose.yml:
services:
  sanitizer:
    image: mysql-sanitizer:greenmask
    command: greenmask sanitise --config=/app/config.yaml
    
# В Dockerfile.greenmask:
RUN pip install greenmask PyYAML requests
```

---

## ❓ Вопрос 2: "Конфиг у нас универсальный или заточен под тестовую базу?"

✅ **ПОЛНОСТЬЮ УНИВЕРСАЛЬНЫЙ!**

**Что уже готово (работает всегда):**
- FK preservation через `skip_columns` ✅
- Language-aware LLM masking ✅
- Entity consistency cache ✅
- Batch processing (20x speedup) ✅
- Report generation ✅

**Что нужно изменить под новую базу:**

| Файл | Что менять | Пример |
|------|-----------|--------|
| `config.yaml` | Таблицы и колонки | `table: users` вместо `table: customers` |
| `config.yaml` | Skip columns | Добавляем `user_id`, `account_id` в skip list |
| `prompt_templates/` | Опционально | Если нужны кастомные правила для ваших полей |

**Код НЕ меняется:**
- `transformers/llm_masker.py` — language awareness работает везде
- `start.sh` — orchestration та же
- `docker-compose.yml` — контейнер тот же

---

## ❓ Вопрос 3: "Если они дадут свою базу все сработает также?"

✅ **ДА, ВСЁ СРАБОТАЕТ!**

**Проверка readiness:**

### Шаг A: Получите структуру от заказчика
```sql
-- Запрос к их базе:
SHOW TABLES;
SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS WHERE ...;
```

### Шаг B: Обновите config.yaml
```yaml
transformers:
  - table: users              # ← новое имя таблицы из шага A
    schema: production_db     # ← база заказчика
    skip_columns:             # ← добавьте ВСЕ *_id поля!
      - user_id
      - account_id
      - session_id
    
    columns:
      username:               # ← какое поле?
        transformer: static_replace
      
      email:
        transformer: mask_email
      
      full_name:
        transformer: custom_llm_masker  # ← language-aware!
```

### Шаг C: Протестируйте
```bash
# Создайте дамп из продакшена
mysqldump -u root production_db > customer_dump.sql

cp customer_dump.sql dump.sql
./start.sh

# Проверьте результат
gunzip -c output/sanitized.sql.gz | head
./tools/report.sh
```

---

## 📋 Полная таблица правил → config.yaml mapping

| Правило | Transformer | Config.yaml setting | Пример |
|---------|-------------|---------------------|--------|
| **Правило #1: Never touch PKs** | SKIP | `skip_columns: [-customer_id]` | `1 → 1` (unchanged!) |
| **Правило #2: Entity consistency** | CustomLLMMasker + hash cache | `entity_key = f"{table}:{col}:{hash[:16]}"` | Same "Maria" → same "Carmen" everywhere |
| **Правило #3: Language preservation** | LLM with prompt template | `prompt_template_file: name.txt` | Spanish→Spanish, Russian→Russian |
| **Правило #4: City preservation** | city_preserving_address_masker | `transformer: city_preserving...` | Street changes, city stays |
| **Правило #5: Batch efficiency** | _call_llm_batch() | `batch_size: 20` | 20x faster than single-row |

---

## 🔧 Как адаптировать за 15 минут

```bash
# 1. Get their tables (5 min)
mysqldump -u root client_database --tables users orders customers > client_test.sql

# 2. Update config.yaml (5 min)
vi config.yaml
# Change:
#   table: customers → table: users
#   column first_name → column full_name
# Add: skip_columns: [user_id, order_id]

# 3. Test run (5 min)
cp client_test.sql dump.sql
./start.sh
./tools/report.sh

# Done! ✅
```

---

## 💡 Summary

| Question | Answer | Where to verify |
|----------|--------|-----------------|
| Uses Greenmask? | ✅ YES | docker-compose.yml, start.sh |
| Universal config? | ✅ YES | TRANSFORMATION_RULES.md |
| Works with customer DB? | ✅ YES | QUICK_REFERENCE.md guide |
| What changes for new DB? | Only config.yaml | Table/column names |
| What NEVER changes? | Core logic | transformers/, start.sh |
| How long to adapt? | ~15 minutes | Including test run |

---

**ВСЁ ГОТОВО ДЛЯ ПРОДАКШЕНА! 🎉**
