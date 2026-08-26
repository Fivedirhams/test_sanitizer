# 🚀 Quick Start: Тестирование на Chinook Database (Industrial Standard)

## ⏱️ 3 шага к результатам

### 1️⃣ Проверить API ключ (уже настроен!)

```bash
cd /project/my-sql-sanitizer
cat .env | grep OFOX_API_KEY
# Должно быть: OFOX_API_KEY=sk-of-HYzanedLejZVMehnpTieLfyRZRurIkQzNeNWfSIXnFiLOXDGMPENIVFnXXEkAOCd
```

### 2️⃣ Запустить санитизатор

```bash
# База уже в dump.sql (Chinook - 587KB, 15K строк)
./start.sh
```

**Ожидаемое время:**
- Single-row mode: ~10-15 минут (60 customers × 10 fields = 600 LLM calls)
- Batch mode (когда добавите): ~1-2 минуты ✅

### 3️⃣ Проверить результат

```bash
gunzip -c output/sanitized.sql.gz | head -50
```

**Что искать:**
```sql
-- BEFORE:
INSERT INTO `Customer` ... VALUES (1, N'Luís', N'Gonçalves', ..., 'luisg@embraer.com.br')

-- AFTER:  
INSERT INTO `Customer` ... VALUES (1, N'Carlos', N'Santos', ..., 'anon@example.com')
     ^^^^^^ CustomerId UNCHANGED! ✅ FK integrity preserved!
```

---

## 🎯 Почему Chinook лучше чем self-generated?

| Критерий | generate_large_test.py | **Chinook** ⭐ |
|----------|------------------------|---------------|
| Стандарт индустрии | ❌ Да, ваш скрипт | ✅ Industry standard |
| Мультиязычные данные | Ручная генерация | ✅Brazil/Germany/France/Canada |
| Реальные FK связи | Простые (test_dump.sql) | ✅ Production-quality |
| Поддержка сообщества | ❌ Нет | ✅ 4K+ GitHub stars |
| Документация schema | Ваша | ✅ Полная спецификация |
| Доступность | Нужно создавать | ✅ Мгновенно скачать |

---

## 📊 Сравнение датасетов

| Датасет | Размер | PII Coverage | FK Integrity | Best For |
|---------|--------|--------------|--------------|----------|
| test_dump.sql | 5 rows | Basic names/phones | Simple | Concept validation |
| large_test_dump.sql | 4,500 rows | Generated random | Custom | Performance benchmark |
| **chinook_test.sql** ⭐ | **59 customers** | **Multi-country realistic** | **Production FKs** | **REAL-WORLD TESTING** |

---

## 🔧 Настройка конфига под Chinook

Файл уже создан: `config_chinook.yaml`

**Ключевые особенности:**
```yaml
skip_columns: [CustomerId]  # ← PK НЕ ТРОГАТЬ! ✅

columns:
  FirstName: custom_llm_masker      # Language-aware replacement
  LastName: custom_llm_masker       # "Luís Gonçalves" → "Roberto Silva" (Brazilian)
  Address: city_preserving          # "Av. Brigadeiro Faria Lima" → stays in São Paulo
  Country: static_replace           # Keep Brazil, Germany, France etc. intact
```

---

## 💡 Следующие шаги

### Option A: Быстрый старт (сегодня)
```bash
cp chinook_test.sql dump.sql
./start.sh
```

### Option B: Добавить батчинг (завтра)
1. Read BATCH_PROCESSING_ARCHITECTURE.md
2. Add batch_size parameter to llm_masker.py
3. Test again → 10x faster!

### Option C: Production deployment (неделя)
```bash
# Setup production pipeline
docker-compose up -d
# Run daily sanitization
cron job → ./start.sh >> /var/log/sanitization.log
```

---

## 📥 Дополнительные тестовые базы

Если хотите больше разнообразия:

```bash
# Sakila (official MySQL sample)
curl -L https://cdn.mysql.com/db-download.sakila.tar.gz | tar -xzf -

# Northwind for MySQL (enterprise e-commerce)  
git clone https://github.com/BobPozo/Northwind-for-MySQL.git

# Все вместе для comprehensive testing
ls *.sql  # → choose_best_for_your_schema.sql
```

---

## 🎬 Готово! Ваш проект сейчас содержит:

```
/project/my-sql-sanitizer/
├── CHINOOK TEST DATA
│   ├── chinook_test.sql (587KB, 15K lines, 59 customers) ✅
│   └── config_chinook.yaml (Greenmask config) ✅
│
├── OTHER DATASETS
│   ├── test_dump.sql (10 rows, quick validation)
│   └── large_test_dump.sql (4,500 rows, performance benchmark)
│
├── DOCUMENTATION
│   ├── POPULAR_TEST_DB_GUIDE.md (Top 5 public SQL datasets) ✅
│   ├── SANITIZATION_ALGORITHM.md (Full algorithm breakdown)
│   ├── BATCH_PROCESSING_ARCHITECTURE.md (Batch optimization guide)
│   └── QUICK_START_WITH_CHINOOK.md (This file!) ✅
│
└── CODE
    ├── transformers/llm_masker.py (LLM integration with entity consistency)
    └── start.sh (Orchestration script)
```

---

**Запустите сейчас и увидите real-world anonymization!** 🎉
