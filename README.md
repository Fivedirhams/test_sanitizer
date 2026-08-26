# MySQL Database Sanitizer with Realistic Anonymization

Автоматическое создание анонимизированных тестовых баз данных из MySQL дампов с ИИ для замены чувствительных данных.

**ВАЖНО**: Только реалистичная анонимизация (no obfuscation). Не `anon@example.com`, а реальные данные вида `pedro.silva@gmail.com`.

## ⚡ Быстрый старт

```bash
# 1. API ключ
cp .env.example .env
echo "OFOX_API_KEY=sk-..." >> .env

# 2. Дамп для теста
cp examples/chinook_test.sql dump.sql

# 3. Запуск (автоматически + пост-процессинг)
./start.sh

# 4. Результат
cat output/report.txt
```

---

## 📋 Что делает инструмент

| Исходное значение | → | Анонимное значение | Сохранено? |
|-------------------|---|-------------------|------------|
| `María García` | → | `Carmen López` | ✅ Язык, стиль |
| `maria.garcia@gmail.com` | → | `pedro.silva@gmail.com` | ✅ Формат local_part |
| `+7-495-123-4567` | → | `+7-495-987-6543` | ✅ Country + area code |
| `customer_id: 1` | → | `customer_id: 1` | ✅ FK integrity |

### 🔑 Ключевые фичи

- ✅ **Реалистичные данные** — не заглушки, валидные значения для тестов
- ✅ **Языковая консистентность** — испанский остаётся испанским
- ✅ **Структурная консистентность** — тот же формат email/телефона
- ✅ **FK integrity preserved** — первичные ключи не трогаем
- ✅ **Cross-reference pass** — финальная проверка ВСЕЙ базы на консистентность

---

## 🔧 Как адаптировать под БАЗУ заказчика

### Шаг 1. Получите дамп от заказчика

```bash
mysqldump -u root production_db > customer_dump.sql
```

### Шаг 2. Измените config.yaml

Это НЕ меняет структуру базы! Это только правила маскирования.

```yaml
transformers:
  # ← ИЗМЕНИТЬ ИМЕНА ТАБЛИЦ/КОЛОНОК:
  - name: employees_transformer    # их таблица
    schema: production_db          # ← база заказчика
    table: employees               # ← их таблица
    
    skip_columns:                  # ← ВСЕ *_id добавляйте сюда!
      - employee_id
      - department_id
      
    columns:
      full_name:
        transformer: custom_llm_masker
      work_email:
        transformer: custom_email_generator
      mobile_number:
        transformer: custom_phone_generator
```

**Что менять:**
| config.yaml параметр | На что заменить |
|---------------------|-----------------|
| `table: customers` | → `table: employees` (их таблица) |
| `column first_name` | → `column full_name` (их колонка) |
| `skip_columns: [customer_id]` | → добавить все `*_id` поля |

**Не менять:** трансформеры работают универсально для любой базы.

### Шаг 3. Запуск

```bash
cp customer_dump.sql dump.sql
./start.sh
cat output/report.txt
```

---

## 🛠️ Трансформеры и как их настроить

| Поле | Transformer | Что делает | Конфиг пример |
|------|-------------|-----------|---------------|
| Имена | `custom_llm_masker` | LLM генерирует имена в том же языке | `prompt_template_file: name.txt` |
| Email | `custom_email_generator` | Генерирует email same style | `preserve_domain: false` |
| Телефон | `custom_phone_generator` | Генерирует номер той же страны | (country code auto-detected) |
| Адреса | `city_preserving_address_masker` | Меняет улицу, город остаётся | (авто) |
| JSON логи | `json_reconciler.py` (пост-процессинг) | Проверяет все ячейки на консистентность | `python tools/json_reconciler.py --mapping output/mapping.json` |

---

## 🗂️ Структура проекта

```
my-sql-sanitizer/
├── README.md                # Эта инструкция
├── config.yaml              # Правила маскирования (меняется под клиента)
├── start.sh                 # Команда запуска (+ реконциляция)
├── transformers/            # Трансформеры
│   ├── llm_masker.py        # ИИ-маскирование имен
│   ├── email_generator.py   # Генератор email (реалистичный)
│   ├── phone_generator.py   # Генератор телефона (регион сохраняется)
│   └── report_generator.py  # Статистика после запуска
├── tools/                   # Утилиты
│   ├── json_reconciler.py   # Финальный проход на консистентность
│   └── auto_adapt.sh        # Авто-генерация config (показать)
└── examples/
    └── chinook_test.sql     # Тестовый дамп (59 клиентов!)
```

---

## 📈 Пример отчёта

```
============================================================
📊 SANITIZATION REPORT
============================================================

Total transformations applied: 847
Unique entities processed: 59

EMAILS transformed: maria.garcia@gmail.com → pedro.silva@gmail.com
PHONES transformed: +7-495-123-4567 → +7-495-987-6543
NAMES transformed: María García → Carmen López

✅ All cross-references reconciled
```

---

## ❓ Вопросы

**Q: Config.yaml меняет структуру базы?**  
A: Нет! Только правила: *"это поле замаскируй так"*

**Q: Почему не обфускация типа anon@example.com?**  
A: Потому что это бесполезно для тестирования. Нужны реалистичные данные которые выглядят как настоящие.

**Q: FK relationships сохранятся?**  
A: Да! Все `*_id` автоматически пропускаются через `skip_columns`

**Q: JSON поля в логах тоже проверятся?**  
A: Да! `json_reconciler.py` — финальный шаг который проверяет ВЕСЬ дамп на наличие любых оставшихся оригинальных значений

---

## ⚙️ Команды

```bash
# Основной запуск (with reconciliation)
./start.sh

# Только первичный прогон (без reconciliation)
docker-compose run --rm sanitizer greenmask sanitise --config=config.yaml

# Проверить консистентность вручную
python3 tools/json_reconciler.py --input output/sanitized.sql.gz --mapping output/mapping.json --validate

# Посмотреть статистику
cat output/report.txt

# Очистка результата
make clean
```

---

**MIT License**
