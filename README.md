# MySQL Database Sanitizer with LLM

Автоматическое создание анонимизированных тестовых баз данных из MySQL дампов с использованием ИИ для замены чувствительных данных (имена, email, телефоны).

## ⚡ Быстрый старт

```bash
# 1. Укажите API ключ
cp .env.example .env
echo "OFOX_API_KEY=sk-..." >> .env

# 2. Запустите тест на примере
cp examples/chinook_test.sql dump.sql
./start.sh

# 3. Проверьте результат
cat output/report.txt
```

## 📋 Что это такое?

Это инструмент который берет **вашу SQL базу** и создаёт её **анонимную версию**:

| Исходная база | → | Анонимная версия |
|---------------|---|------------------|
| `María García` | → | `Carmen López` |
| `maria@gmail.com` | → | `anon@example.com` |
| `+7-495-123-4567` | → | `+1-(XXX)-XXX-XXXX` |
| `customer_id: 1` | → | `customer_id: 1` (НЕ меняется!) |

### 🔑 Ключевые особенности

- ✅ **FK integrity preserved** — первичные ключи не меняются (Foreign keys всегда работают)
- ✅ **Язык сохранён** — испанские имена остаются испанскими, русские русскими
- ✅ **Consistency** — одно имя заменяется одинаково во всех таблицах
- ✅ **Готов к Docker** — один контейнер, одна команда запуска

---

## 🔧 Как адаптировать под БАЗУ заказчика?

Вам НУЖНО только изменить `config.yaml`. Это НЕ меняет структуру базы!

### Шаг 1. Получите дамп от заказчика

```bash
mysqldump -u root production_db > customer_dump.sql
```

### Шаг 2. Откройте config.yaml

Он показывает **какие поля маскировать как**. Пример:

```yaml
transformers:
  # ← ИЗМЕНИТЬ ЭТО:
  - name: employees_transformer    # имя трансформера
    schema: production_db          # ← база заказчика
    table: employees               # ← их таблица
    
    skip_columns: [employee_id]    # ← ВСЕ *_id добавляйте сюда!
    
    columns:
      full_name:
        transformer: custom_llm_masker
      work_email:
        transformer: mask_email
      mobile_number:
        transformer: mask_phone
```

**Что изменять:**
| В config.yaml | На что заменить |
|--------------|-----------------|
| `table: customers` | → `table: employees` (их таблица) |
| `column first_name` | → `column full_name` (их колонки) |
| `skip_columns: [customer_id]` | → добавьте все `*_id` поля |

**Остальное НЕ МЕНЯТЬ!** Логика уже работает универсально.

### Шаг 3. Тест + запуск

```bash
cp customer_dump.sql dump.sql
./start.sh
cat output/report.txt  # Проверить статистику
```

---

## 📊 Таблица: Какие поля как маскировать

| Тип поля | Паттерн имени | Transformer в config.yaml |
|----------|--------------|---------------------------|
| Имена людей | `first_name`, `last_name`, `full_name` | `custom_llm_masker` |
| Email | `email`, `mail` | `mask_email` |
| Телефоны | `phone`, `mobile`, `tel` | `mask_phone` |
| Адреса | `address`, `street`, `city` | `city_preserving_address_masker` |
| Даты | `birth_date`, `created_at` | `date_shift` (-7 дней) |
| Любые другие | любое | `static_replace` |

---

## 🗂️ Структура проекта

```
my-sql-sanitizer/
├── README.md              # Эта инструкция
├── docker-compose.yml     # Контейнер с Greenmask
├── Dockerfile.greenmask   # Сборка образа
├── config.yaml            # Правила маскирования (меняется под клиентом)
├── start.sh               # Одна команда для запуска
├── .env.example           # Шаблон API ключа
├── transformers/          # Кастомные трансформеры (не меняются)
│   ├── llm_masker.py      # ИИ-маскирование имен
│   └── report_generator.py# Генерация статистики
├── prompt_templates/      # Промпты для ИИ (не меняются)
└── examples/              # Тестовые дамыпы
    └── chinook_test.sql   # Industry standard (59 клиентов!)
```

---

## 🚀 Команды

```bash
# Запустить санитайзер
./start.sh

# Смотреть логи
docker-compose logs -f sanitizer

# Проверить отчет
cat output/report.txt

# Очистка результата
make clean
```

---

## 📈 Пример отчёта после запуска

```
============================================================
📊 SANITIZATION REPORT
============================================================

Generated at: 2024-08-26 15:03:22
Total transformations applied: 847
Unique entities processed: 59

TRANSFORMATIONS BY FIELD:
  Customer.FirstName: 59 replacements
  Customer.Email: 59 replacements  
  Customer.Phone: 59 replacements
  Invoice.Total: 412 replacements

SAMPLE CHANGES:
  • María García → Carmen López
  • luisg@embraer.com.br → anon@example.com
  • +55 (12) 3923-5555 → +1 (XXX) XXX-XXXX
============================================================
```

---

## ❓ Частые вопросы

**Q: Config.yaml меняет структуру базы?**  
A: Нет! Это просто правила: *"это поле замаскируй так, а то — так"*

**Q: FK relationships сохранятся?**  
A: Да! Все `*_id` автоматически пропускаются через `skip_columns`

**Q: Работает с любой MySQL базой?**  
A: Да! Нужно только поменять имена таблиц/колонок в config.yaml

**Q: Сколько времени адаптация?**  
A: ~5 минут вручную или 20 минут через auto-адаптер (`./scripts/auto_adapt.sh --dump db.sql`)

---

**MIT License**
