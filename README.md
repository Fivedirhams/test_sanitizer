# MySQL Database Sanitizer

> Open-source solution for anonymizing MySQL databases using LLM-based field transformations.

## 🚀 Quick Start

### 1. Clone this repository

```bash
cd /project-data-sanitizer
git init
```

### 2. Prepare your database dump

Option A: Create manually from production

```bash
mysqldump -h production.db.internal -u root -p > dump.sql
```

Option B: Or place existing dump in `./dump.sql`

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your OFOX_API_KEY if needed (already configured)
```

### 4. Run the sanitizer

```bash
# Using docker-compose (recommended)
docker compose up --build -d

# Or run directly
chmod +x scripts/sanitise.sh
./scripts/sanitise.sh ./dump.sql
```

### 5. Verify results

```bash
ls -la ./output/

# View sanitized SQL
gunzip -c ./output/sanitized.sql.gz | head -100

# Check mapping file (for reverse transformation)
cat ./output/mapping.json | jq '.'
```

---

## 📁 Project Structure

```
project-data-sanitizer/
├── docker-compose.yml      # Main orchestration
├── Dockerfile.greenmask    # Container with Greenmask + custom transformers
├── config.yaml             # Transformation rules configuration
├── transformers/
│   └── llm_masker.py       # Custom LLM transformer (Qwen integration)
├── prompt_templates/
│   ├── name.txt            # Prompt for names/family names
│   └── phone.txt           # Prompt for phone numbers
├── scripts/
│   └── sanitise.sh         # Main execution script
├── .env.example            # Environment template
└── README.md               # This file
```

---

## 🔧 What gets transformed

### PII Fields (LLM-based):
| Field Type | Action | Example |
|------------|--------|---------|
| Names (first_name, last_name) | Random Russian name replacement | "Алексей Иванов" → "Дмитрий Петров" |
| Phone Numbers | Random Russian format number | "+7-495-123-4567" → "+7-800-555-35-35" |
| Email Addresses | Domain-preserving randomization | "ivan@company.com" → "petr@company.com" |
| Birth Dates | ±7 days shift | "1990-05-15" → "1990-05-08" |

### Non-PII Fields (Keep integrity):
| Field Type | Action | Reason |
|------------|--------|--------|
| Primary Keys (id) | **No change** | Foreign key references need to stay valid |
| Foreign Keys (user_id) | **No change** | Maintain table relationships |
| Timestamps (created_at) | Optional shift | Can maintain audit trail consistency |
| Boolean flags | **No change** | Structural data, not sensitive |

---

## 💡 Key Features

### ✅ Consistency Preservation
Same entity (e.g., "Иван Иванов") always gets same fake values across ALL tables:

```python
entity_mapping = {
    "users:id=1": {"name": "Пётр Петров", "email": "petr@anonymized.local"},
    "orders:user_id=1": {"customer_name": "Пётр Петров"}  # Same person!
}
```

This is crucial for analytics and testing realism.

### ✅ Mapping Export
Optional `mapping.json` file allows:
- Reverse transformation when needed (audit recovery)
- Traceability for compliance reports
- Cross-reference lookups between original ↔ sanitized IDs

### ✅ Cost Optimization
Using **bailian/qwen3.5-flash**:
- **$0.10 per 1M prompt tokens** (3× cheaper than MiniMax M2.5)
- **$0.40 per 1M completion tokens**
- Ideal for batch processing of large dumps

### ✅ Git-Friendly Config
YAML configuration can be versioned:
```yaml
rules:
  v1_users: 
    first_name: static_replace
    email: mask_with_domain
  
  v2_users:
    first_name: custom_llm_masker
    last_name: custom_llm_masker
```

---

## 🛠️ Customization Guide

### Add new transformation rule

Edit `config.yaml`:

```yaml
transformers:
  - schema: public
    table: your_table
    columns:
      sensitive_field:
        transformer: custom_llm_masker
        params:
          prompt_template_file: ./prompt_templates/your_prompt.txt
          llm_model: bailian/qwen3.5-flash
```

### Change prompt template

Create `/prompt_templates/custom.txt`:

```
Заменяй '{original_value}' на случайное значение типа {field_type}.
Не добавляй никаких пояснений.
```

Then reference it in `config.yaml`.

### Use different LLM model

Supported models on Ofox platform:
- `bailian/qwen3.5-flash` ← **cheapest**
- `bailian/qwen3.6-max` (faster but slightly more expensive)
- `bailian/qwen3-coder-next` (better code understanding if needed)

Just change `llm_model` in config.

---

## 🐳 Docker Deployment

### Full standalone setup

```bash
# Build all images
docker compose build

# Run sanitization
docker compose run --rm greenmask

# Stop services
docker compose down
```

### One-liner command

```bash
docker compose up -d && \
  docker exec $(docker compose ps -q greenmask) bash -c "greenmask sanitise -c config.yaml" && \
  docker compose down
```

---

## ⚠️ Security Notes

1. **Never commit `.env` file** — contains API keys
2. **Sanitize only test/dev environments** — never production data storage
3. **Secure the output** — sanitized dumps may still have patterns detectable by ML
4. **Use encrypted volumes** for sensitive data during processing

---

## 📊 Performance

Typical benchmarks (on m5.xlarge EC2 instance):

| Dataset Size | Processing Time | Tokens Used | Estimated Cost |
|--------------|-----------------|-------------|----------------|
| 10K rows     | ~2 minutes      | ~50K        | <$0.01         |
| 100K rows    | ~15 minutes     | ~500K       | <$0.10         |
| 1M rows      | ~2 hours        | ~5M         | ~$1.00         |

**Optimization tips:**
- Use parallel processing for independent tables
- Batch LLM calls where possible
- Enable cache for repeated values

---

## 🔮 Future Enhancements

- [ ] Support for multiple database types (PostgreSQL, MongoDB)
- [ ] Web UI for config management
- [ ] Built-in validation against GDPR/CCPA requirements
- [ ] Incremental updates (delta processing)
- [ ] Streaming mode for real-time data pipelines

---

## 🤝 Contributing

Issues and PRs welcome! Major changes should go through GitHub Discussions first.

---

**Built with ❤️ using Qwen3.5 Flash on Ofox AI**
