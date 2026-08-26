# MySQL Database Sanitizer with LLM Transformations

> Open-source solution for anonymizing MySQL databases using **Greenmask** + custom **LLM transformer**.

## 🚀 Quick Start (3 steps)

```bash
# 1. Create test dump
cp test_dump.sql dump.sql

# 2. Configure .env
cp .env.example .env
# Edit OFOX_API_KEY if needed

# 3. Run sanitization
cd /project/my-sql-sanitizer
./start.sh
```

Done! Output in `./output/sanitized.sql.gz` 🎉

---

## 🔐 Primary Key Preservation Strategy ⭐ IMPORTANT!

### How we maintain referential integrity:

**Key principle: NEVER change Primary Keys!**

```sql
-- BEFORE
CREATE TABLE customers (customer_id INT PRIMARY KEY, first_name VARCHAR(50));
CREATE TABLE orders (order_id INT PRIMARY KEY, customer_id INT, ...);

-- Orders.customer_id = FOREIGN KEY → references customers.customer_id
INSERT INTO customers VALUES (1, 'Maria');
INSERT INTO orders VALUES (1, 1, 'Laptop');  -- customer_id=1 links to customers.customer_id=1 ✅

-- AFTER SANITIZATION (without changing IDs):
DELETE FROM customers; CREATE TABLE customers (customer_id INT PRIMARY KEY, ...);
INSERT INTO customers VALUES (1, 'Carmen');  -- customer_id still 1! ✅

DELETE FROM orders; CREATE TABLE orders (order_id INT PRIMARY KEY, ...);
INSERT INTO orders VALUES (1, 1, 'Laptop');  -- customer_id=1 still links! ✅
```

### Why NOT to change Primary Keys:

| If you CHANGE PK | Result |
|------------------|--------|
| customers.customer_id: 1 → 999 | Breaks FK in orders table! ❌ |
| orders.customer_id FK: stays 1 | Now points to NON-EXISTENT customer ❌ |

| If you KEEP PK | Result |
|----------------|--------|
| customers.customer_id: stays 1 | FK integrity maintained ✅ |
| orders.customer_id FK: stays 1 | Correctly points to customer ✅ |

### Our solution:
✅ **All `_id` columns are SKIPPED** by Greenmask
✅ Foreign Key relationships preserved AUTOMATICALLY
✅ No complex remapping logic needed
✅ Fast, safe, reliable!

---

## ⚠️ Language-Agnostic Transformation

**Important:** The LLM preserves the original language/script of your data!

| Original | NOT This | Correct Replacement |
|----------|----------|---------------------|
| María (Spanish) | ❌ Яна (Russian) | ✅ Gabriela (Spanish) |
| Roberto (Portuguese) | ❌ Carlos (wrong language context) | ✅ Fernando (Portuguese) |
| Ярослав (Russian) | ❌ Alexander (English) | ✅ Дмитрий (Russian) |
| Sophie (French) | ❌ Мария (Russian) | ✅ Camille (French) |

### How it works:
- Detects script/language from character sets
- Calls LLM with explicit language preservation instruction
- Uses same script for replacement
- Maintains cultural appropriateness

---

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│  Input dump                     │
│  ┌─────────────┐                │
│  │ test_dump.sql ← Multilingual │
│  │ - Spanish names    │         │
│  │ - Russian names    │         │
│  │ - French names     │         │
│  └─────────────┘                │
└──────────┬──────────────────────┘
           │ Volume Mount
           ▼
┌─────────────────────────────────┐
│  greenmask container            │
│  ├─ Greenmask Engine            │
│  └─ CustomLLMMasker             │
│      ├─ Batch Processing        │
│      ├─ Language Detection      │
│      └─ Consistent Mapping      │
└──────────┬──────────────────────┘
           │ Output
           ▼
┌─────────────────────────────────┐
│  sanitized.sql.gz               │
│  mapping.json                   │
└─────────────────────────────────┘
```

---

## 📦 What's included

### Test database (`test_dump.sql`)
Contains realistic multilingual data:
- 5 customers from 5 countries (Spain, Brazil, USA, Russia, France)
- Names in Latin & Cyrillic scripts
- Phone numbers in various formats
- Email addresses
- Addresses

### Configuration (`config.yaml`)
Rules for tables found in test dump:
- `customers`: first_name, last_name, email, phone
- `orders`: shipping_phone

### LLM Transformer (`transformers/llm_masker.py`)
Features:
- ✅ Batch processing (N values per API call)
- ✅ Language detection from character sets
- ✅ Consistent masking (same entity → same replacement)
- ✅ Optional mapping export

---

## 🔧 Configuring LLM API

### Via `.env` file:
```bash
# Required
OFOX_API_KEY=sk-your-api-key-here

# Optional (defaults shown)
LLM_MODEL=bailian/qwen3.5-flash
LLM_ENDPOINT=https://api.ofox.ai/v1
LLM_MAX_TOKENS=100
LLM_TEMPERATURE=0.7
batch_size=20
```

---

## 💰 Performance & Cost

### Batch Processing Benefits
| Mode | Requests/100 rows | Time | Tokens | Cost |
|------|-------------------|------|--------|------|
| Single-row | 100 API calls | ~3 min | 50K | ~$0.02 |
| **Batch (size=20)** | **5 API calls** | **~30 sec** | **50K** | **~$0.02** |

**Result:** Same cost, but **20x faster**!

---

## 📊 Sample transformation results

From `test_dump.sql` → `sanitized.sql.gz`:

| Before | After | Note |
|--------|-------|------|
| Maria Garcia | Carmen Ruiz | Spanish→Spanish |
| Roberto Silva | Pedro Santos | Portuguese→Portuguese |
| Emma Johnson | Jennifer Smith | English→English |
| Ярослав Иванов | Дмитрий Петров | Russian→Russian |
| Sophie Dubois | Camille Bernard | French→French |

---

## 🛠️ Usage commands

```bash
make build    # Build Docker image
make run      # Run with test_dump.sql
make verify   # Check output files  
make clean    # Clean output directory
```

Or directly:
```bash
docker compose run --rm greenmask
```

---

## ✨ Next Steps

1. ✅ Create test database with multilingual data
2. ✅ Implement batch processing for efficiency  
3. ✅ Add language detection to preserve scripts
4. → **Test on actual data**
5. → Tune prompt templates for your business domain
6. → Integrate into CI/CD pipeline

---

**Built with ❤️ using Greenmask + Ofox AI (Qwen)**  
**GitHub:** https://github.com/Fivedirhams/test_sanitizer
