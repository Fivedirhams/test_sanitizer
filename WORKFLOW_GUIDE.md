# 🚀 Workflow Guide: From SQL Dump to Sanitized Output

## Quick Decision Tree

```
┌─────────────────────────────────────┐
│  START: Got a MySQL dump?          │
└─────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ↓                   ↓
┌───────────────┐   ┌───────────────┐
│ Use test data │   │  Customer DB? │
│ (Chinook)     │   │  New schema?  │
└───────────────┘   └───────┬───────┘
                            │
            ┌───────────────┴───────────────┐
            ↓                               ↓
    Manual Config Mode              LLM Auto-Adapter
    (edit config.yaml manually)     (scripts/auto_adapt.sh --adapt)
```

---

## Option A: Test with Sample Data (No Setup Required)

**Use case:** Testing the tool for first time or quick validation

```bash
# 1. Copy sample dump
cp examples/chinook_test.sql dump.sql

# 2. Configure API key
cp .env.example .env
echo 'OFOX_API_KEY=sk-of-HYzanedLejZVMehnpTieLfyRZRurIkQzNeNWfSIXnFiLOXDGMPENIVFnXXEkAOCd' >> .env

# 3. Run sanitizer (uses default config.yaml)
./start.sh

# 4. Check results
gunzip -c output/sanitized.sql.gz | head -50
cat output/report.txt
```

✅ **Done in 3 commands!**

---

## Option B: Adapt to Customer Database (Interactive Mode)

**Use case:** Working with real production database, need PII detection

```bash
# Step 1: Get customer's SQL dump
# (ask customer to run: mysqldump -u root production_db > customer_dump.sql)

# Step 2: Use auto-adapter with interactive review
./scripts/auto_adapt.sh --dump customer_dump.sql --interactive

# This will:
# ✅ Extract CREATE TABLE statements from dump
# ✅ Call LLM to propose transformation config
# ✅ Show preview of proposed changes
# ✅ Ask you to confirm/modify before applying
```

**User choices shown by script:**
| Choice | Action |
|--------|--------|
| `A` | Accept proposed config → applies automatically |
| `B` | Open editor to modify config manually |
| `C` | Skip adaptation, keep original config.yaml |
| `D` | Cancel entirely |

**Recommendation:** Always use `--interactive` first time!

---

## Option C: Batch Processing (CI/CD Pipeline)

**Use case:** Automated sanitization without user intervention

```bash
# Non-interactive mode for scripts
./scripts/auto_adapt.sh \
  --dump $CUSTOMER_DUMP \
  --skip-prompt \
  --dry-run  # First time, check analysis only

# After confirming works, remove --dry-run:
./scripts/auto_adapt.sh \
  --dump $CUSTOMER_DUMP \
  --skip-prompt

# Then run sanitizer automatically
./start.sh
```

**Alternative: Python CLI**
```python
# tools/analyze_config.py also supports Python integration
from analyze_config import ConfigAnalyzer

analyzer = ConfigAnalyzer(api_key="your-key")
result = analyzer.analyze_and_propose("customer.sql", "proposed.yaml")

# result contains:
# {success, config, output_file, schema_tables}
```

---

## Option D: Full Control (Manual Mode)

**Use case:** Custom requirements not covered by auto-detection

### Step 1: Analyze your database structure

```sql
-- Get all tables
SHOW TABLES;

-- Get column names for specific table
DESC customers;
SELECT column_name FROM information_schema.COLUMNS 
WHERE table_name = 'customers';
```

### Step 2: Edit config.yaml directly

```yaml
transformers:
  - name: custom_transformer
    schema: my_production_db
    table: employees
    
    skip_columns: [employee_id, department_id]  # ← ALWAYS preserve PKs!
    
    columns:
      # Name fields → LLM masking (language-aware)
      employee_name:
        transformer: custom_llm_masker
        params:
          prompt_template_file: /app/prompt_templates/name.txt
      
      # Email → built-in masker
      work_email:
        transformer: mask_email
        params:
          new_prefix: anon
          new_domain: example.com
      
      # Phone → built-in masker  
      mobile_number:
        transformer: mask_phone
        params:
          country_code: "+1"
      
      # Address → city-preserving
      office_address:
        transformer: city_preserving_address_masker
      
      # Salary → static replacement (financial sensitivity)
      annual_salary:
        transformer: static_replace
        value: "[REDACTED]"
```

### Step 3: Test on small dataset

```bash
# Create minimal dump (first 10 rows)
mysqldump --where="id <= 10" production_db employees > test_small.sql
cp test_small.sql dump.sql
./start.sh

# Validate results
gunzip -c output/sanitized.sql.gz
```

---

## Workflow Comparison Table

| Method | Time to Setup | Best For | Risk Level |
|--------|---------------|----------|------------|
| **Test (Option A)** | 3 min | Learning/Testing | Zero |
| **Interactive (B)** | 15 min | First customer project | Low |
| **Batch (C)** | 10 min | CI/CD automation | Medium |
| **Manual (D)** | 30+ min | Complex/custom needs | Low-Medium |

---

## Common Scenarios & Recommended Workflows

### Scenario 1: Small Business Customer (~10 tables)

```bash
# Recommended: Interactive mode
./scripts/auto_adapt.sh --dump customer_db.sql --interactive
# Review the proposed changes, accept if looks correct
# Run sanitizer
./start.sh
```

### Scenario 2: Large Enterprise Database (100+ tables)

```bash
# Recommended: Dry-run first
./scripts/auto_adapt.sh --dump enterprise_db.sql --dry-run --verbose

# Review full schema analysis in logs
grep "Schema extracted successfully" output/auto_analysis.log

# If OK, proceed with actual adaptation
./scripts/auto_adapt.sh --dump enterprise_db.sql --skip-prompt

# Run sanitizer
./start.sh
```

### Scenario 3: Sensitive Industry (Finance/Healthcare)

```bash
# Recommended: Manual mode + extra validation
# 1. Identify compliance requirements (HIPAA, PCI-DSS, etc.)
# 2. Define stricter masking rules:
#    - All names → static replace (not LLM)
#    - Addresses → generic placeholder only
# 3. Edit config.yaml accordingly
# 4. Test thoroughly before production use
```

### Scenario 4: Development/Sandbox Environment

```bash
# Recommended: Automated workflow
# Add to CI pipeline (.github/workflows/sanitize.yml):
- name: Sanitize Database
  run: |
    ./scripts/auto_adapt.sh --dump prod_backup.sql --skip-prompt
    ./start.sh
    # Upload sanitized dump to artifact storage
    aws s3 cp output/sanitized.sql.gz s3://my-bucket/test-db.sql.gz
```

---

## Post-Sanitization Checklist

After running `./start.sh`, always verify:

- [ ] `output/sanitized.sql.gz` exists and is non-empty
- [ ] FK relationships preserved (check `mapping.json`)
- [ ] Language consistency maintained (María stays María-style, not Russian)
- [ ] No real PII leaked in `sanitized.sql.gz`
- [ ] Report generated: `output/report.txt` shows all transformations
- [ ] Optional: `output/mapping.json` deleted (contains sensitive mapping!)

---

## Troubleshooting

### Issue: "LLM call failed" error

**Cause:** API key missing or invalid

**Fix:**
```bash
# Check .env file exists and has API key
cat .env

# Should contain:
OFOX_API_KEY=sk-...

# If not:
cp .env.example .env
vim .env  # Add your API key here
```

### Issue: "Invalid YAML detected" in auto-adapt

**Cause:** LLM returned malformed YAML

**Fix:**
1. Manually review: `cat output/llm_proposed_config.yaml`
2. Fix syntax errors (indentation, quotes)
3. Or fall back to manual config editing

### Issue: FK integrity broken

**Cause:** Accidentally transformed primary key column

**Fix:**
- ALWAYS add to `skip_columns`:
```yaml
skip_columns:
  - customer_id
  - order_id
  - any*_id field
```

---

## Next Steps

1. Start with **Option A** (test data) to learn the basics
2. Try **Option B** (interactive) with a small customer database
3. Once comfortable, use **Option C** (batch) for automation
4. For special cases, **Option D** (manual) gives full control

**Questions?** Check these docs:
- `TRANSFORMATION_RULES.md` - Understanding transformers
- `QUICK_REFERENCE.md` - Answers to common questions
- `docs/ARCHITECTURE.md` - Technical deep dive
