# MySQL Database Sanitizer with LLM Transformations

> Open-source решение для анонимизации MySQL баз данных с использованием **Greenmask** + кастомного **LLM трансформера**.

## 🚀 Quick Start (3 шага)

```bash
# 1. Создайте дамп продакшена
mysqldump -h production.db.internal -u root -p > dump.sql

# 2. Настройте .env
cp .env.example .env
# Отредактируйте OFOX_API_KEY если нужно

# 3. Запустите санитизацию
cd /project/my-sql-sanitizer
./start.sh
```

Готово! Результат в `./output/sanitized.sql.gz` 🎉

---

## 🏗️ Архитектура решения

### Готовое open-source решение: **Greenmask**
- Поддержка MySQL, PostgreSQL
- Сохранение FK/PK связей
- YAML конфигурация правил
- Docker-образ готов к использованию

### Ваш кастомный трансформер: **CustomLLMMasker**
- Интеграция с LLM API (Ofox / Qwen)
- Консистентная замена PII данных
- Сохранение маппинга для обратной совместимости

```
┌─────────────────────────────────────────────────────────┐
│  Входной дамп                                           │
│  ┌─────────────┐                                        │
│  │ dump.sql    │ ← SQL dump продакшена                  │
│  └─────────────┘                                        │
└──────────────────┬──────────────────────────────────────┘
                   │ Volume Mount
                   ▼
┌─────────────────────────────────────────────────────────┐
│           greenmask:latest (Docker Container)           │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Greenmask Engine + CustomTransformer              │  │
│  │                                                   │  │
│  │ • Парсинг структуры БД                            │  │
│  │ • Применение правил из config.yaml               │  │
│  │ • Вызов LLM через API                             │  │
│  │ • Сохранение маппинга                             │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │ Output path
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Выходные файлы                                         │
│  ┌─────────────────┐                                     │
│  │ sanitized.sql.gz │ ← Анонимизированный SQL            │
│  └─────────────────┘                                     │
│  ┌─────────────────┐                                     │
│  │ mapping.json     │ ← Опционально                      │
│  └─────────────────┘                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Структура проекта

```
/project/my-sql-sanitizer/
├── docker-compose.yml        # Оркестрация Greenmask контейнера
├── Dockerfile.greenmask      # Образ с Greenmask + custom transformer
├── config.yaml               # Правила трансформации (редактируй!)
├── transformers/
│   └── llm_masker.py         # Кастомный LLM трансформер (ваш код!)
├── prompt_templates/
│   ├── name.txt              # Промпт для имён
│   └── phone.txt             # Промпт для телефонов
├── .env.example              # Шаблон переменных окружения
├── start.sh                  # Главный скрипт запуска
├── Makefile                  # make build, make run
└── README.md                 # Этот файл
```

---

## 🔧 Как настроить LLM API

### Через `.env` файл:
```bash
# LLM API Configuration (для трансформера)
OFOX_API_KEY=sk-your-api-key-here
LLM_MODEL=bailian/qwen3.5-flash
LLM_ENDPOINT=https://api.ofox.ai/v1
LLM_MAX_TOKENS=100
LLM_TEMPERATURE=0.7

# MySQL Connection (не нужен для dump-based workflow)
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=password
DB_NAME=test_db
```

### Либо через CLI args:
```bash
docker compose run --rm \
  -e OFOX_API_KEY=sk-xxx \
  -e LLM_MODEL=bailian/qwen3-coder-next \
  greenmask
```

---

## 💰 Стоимость LLM

| Модель | Prompt | Completion | Сравнение |
|--------|--------|------------|-----------|
| **bailian/qwen3.5-flash** | $0.10/1M | $0.40/1M | ✅ Самый дешёвый |
| bailian/qwen3-coder-next | $0.20/1M | $1.50/1M | ⬆️ Дешевле MiniMax |
| minimax/m2.5 | $0.30/1M | $1.20/1M | ❌ В 3× дороже |

---

## ✨ Что делает ваш трансформер

| Поле | Действие | Пример |
|------|----------|--------|
| Имена | Замена на случайное русское имя | "Алексей" → "Дмитрий" |
| Фамилии | Замена на случайную русскую фамилию | "Иванов" → "Петров" |
| Телефоны | Замена на российский формат | "+7-495-123-4567" → "+7-800-555-35-35" |
| Email | Сохранение домена, замена пользователя | "ivan@company.com" → "petr@company.com" |
| Даты | Сдвиг на ±7 дней | "1990-05-15" → "1990-05-08" |
| PK/FK | **Не меняются** | Внешние связи intact |

**Консистентность**: "Иван Иванов" везде становится одинаковым псевдонимом.

---

## 🛠️ Добавление новых правил

### В `config.yaml`:
```yaml
transformers:
  - schema: public
    table: your_table
    columns:
      sensitive_field:
        transformer: custom_llm_masker
        params:
          prompt_template_file: /app/prompt_templates/custom_prompt.txt
          llm_model: bailian/qwen3.5-flash
```

### Промпт в `prompt_templates/custom_prompt.txt`:
```
Замени '{original_value}' на случайное {field_type}. Верни только значение.
```

---

## 📊 Производительность

Бенчмарк на m5.xlarge EC2:

| Размер БД | Время | Токены | Стоимость |
|-----------|-------|--------|-----------|
| 10K строк | ~2 мин | ~50K | <$0.01 |
| 100K строк | ~15 мин | ~500K | <$0.10 |
| 1M строк | ~2 часа | ~5M | ~$1.00 |

---

## ⚙️ Использовать make

```bash
make build    # Build Docker images
make run      # Run sanitization (requires dump.sql)
make verify   # Check output files
make clean    # Clean output
```

---

## 📝 Следующие шаги

1. **Протестировать** на тестовой базе
2. **Настраивать правила** под ваши поля
3. **Интегрировать в CI/CD** pipeline
4. **Мониторить стоимость** токенов

---

**Built with ❤️ using Greenmask + Ofox AI (Qwen)**
