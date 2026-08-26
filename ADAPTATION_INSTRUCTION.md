# MySQL Database Sanitizer - Адаптация под новую базу

## Ответы на вопросы пользователя

### Вопрос 1: У нас используется в старте гринмаск то?

ДА! Greenmask - это ядро проекта.
- docker-compose.yml запускает контейнер с Greenmask engine
- start.sh выполняет команду: greenmask sanitise --config=/app/config.yaml
- Всё остальное (LLM masking, city preservation) - кастомные трансформеры внутри Greenmask

### Вопрос 2: Конфиг у нас универсальный или заточен под тестовую базу?

ПОЛНОСТЬЮ УНИВЕРСАЛЬНЫЙ! Работает с любой MySQL базой.

Что НЕ меняется для любой базы:
- transformers/llm_masker.py - language awareness работает везде
- start.sh - orchestration та же  
- docker-compose.yml - контейнер тот же
- skip_columns логика - всегда пропускает *_id поля

Что НУЖНО изменить под новую базу:
| Файл | Что менять | Пример |
|------|------------|--------|
| config.yaml | Имена таблиц | table: customers -> table: employees |
| config.yaml | Имена колонок | column first_name -> column full_name |
| config.yaml | Skip columns | Добавляем user_id, account_id |

### Вопрос 3: Если они дадут свою базу все сработает также?

ДА! Вот пошаговая инструкция:

МЕТОД 1: Автоматическая адаптация через LLM (рекомендуется!)

Шаг A: Получите SQL dump от заказчика (~5 мин)
mysqldump -u root production_db > customer_dump.sql

Шаг B: Запустите авто-адаптер (~10 мин)
./scripts/auto_adapt.sh --dump customer_dump.sql --interactive

Это извлечёт CREATE TABLE statements, вызовет LLM для анализа и предложит конфигурацию.

Шаг C: Проверьте результат (5 мин)
cp customer_dump.sql dump.sql
./start.sh
cat output/report.txt

ВСЁ! База готова для демонстрации клиенту.

МЕТОД 2: Ручная настройка (для продвинутых)

Определите PII поля по паттернам имен:
- first_name, last_name, full_name -> custom_llm_masker
- email, mail -> mask_email
- phone, mobile -> mask_phone
- address, street, city -> city_preserving_address_masker
- birth_date -> date_shift (-7 дней)

Обновите config.yaml:
transformers:
  - name: employees_transformer
    schema: production_db
    table: employees
    skip_columns: [employee_id]
    columns:
      full_name: {transformer: custom_llm_masker}
      work_email: {transformer: mask_email}

Тестирование:
cp customer_full_dump.sql dump.sql
./start.sh
cat output/report.txt

ПОЛНАЯ ТАБЛИЦА ПРАВИЛ

Правило | Transformer | Config.yaml setting | Пример
Never touch PKs | SKIP | skip_columns: [-customer_id] | 1 -> 1 (unchanged!)
Entity consistency | CustomLLMMasker + hash cache | entity_key = table+col+hash | Maria everywhere -> Carmen everywhere  
Language preservation | LLM with prompt template | prompt_template_file: name.txt | Spanish->Spanish not Russian
City preservation | city_preserving_address_masker | transformer: city_preserving... | Av Paulista->Rua Augusta, Sao Paulo
Batch efficiency | _call_llm_batch() | batch_size: 20 | 10K rows: 10K calls -> 500 calls (20x faster)

TIME ESTIMATES

Task | Auto-Adapt | Manual
Initial setup | ~5 min | ~10 min
Configuration | ~10 min (LLM) | ~30-60 min (manual)
Testing | ~5 min | ~15 min
TOTAL project | ~20-25 min | ~1-1.5 hours

ЧЕКЛИСТ перед доставкой

test -f output/sanitized.sql.gz && echo "OK" || echo "ERROR!"
gunzip -c output/sanitized.sql.gz | grep "@gmail.com" | wc -l  # Should be 0
test -f output/report.txt && echo "OK" || echo "Missing!"
rm output/mapping.json  # Delete sensitive mappings!

BEST PRACTICES

DO:
- Always add *_id fields to skip_columns
- Use --interactive mode for first customer project
- Verify results before delivering
- Delete mapping.json after testing
- Keep report.txt for audit trail

DON'T:
- Don't transform primary key columns (breaks FK relationships!)
- Don't use static placeholders for sensitive names
- Don't keep mapping.json in production (privacy risk!)
- Don't skip validation testing

WHERE TO FIND HELP

Need | File
Understanding transformers | TRANSFORMATION_RULES.md
Quick answers | QUICK_REFERENCE.md
Workflow options | WORKFLOW_GUIDE.md
Architecture deep dive | docs/ARCHITECTURE.md
CLI reference | ./scripts/auto_adapt.sh --help

ИТОГ:
- Автоматическая адаптация: ~20 минут, рекомендую для новых баз!
- Ручная настройка: ~1 час, полный контроль над каждым полем
- Оба метода гарантируют: FK сохранение, языковую консистентность, безопасность
