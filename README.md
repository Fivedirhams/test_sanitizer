# MySQL Database Sanitizer with LLM-based Masking

Production-ready tool for creating sanitized test databases from MySQL dumps using custom AI transformers.

## Features

- ✅ **Language-aware masking** - names stay in original language (María → Carmen, not Яна)
- ✅ **FK integrity preserved** - Primary Keys never transformed, foreign keys always valid
- ✅ **Entity consistency** - same customer name = same replacement across all tables
- ✅ **City-preserving addresses** - streets changed but cities/countries remain consistent
- ✅ **Batch processing ready** - supports column-level batching for large datasets
- ✅ **Docker-native** - single container orchestration with Greenmask engine

## Quick Start

```bash
# 1. Configure API key
cp .env.example .env
echo 'OFOX_API_KEY=sk-your-key-here' >> .env

# 2. Run on sample data
cp examples/chinook_test.sql dump.sql
./start.sh

# 3. Check result
gunzip -c output/sanitized.sql.gz | head -50
```

## Files

```
my-sql-sanitizer/
├── docker-compose.yml      # Container orchestration
├── Dockerfile.greenmask    # Build image with dependencies
├── config.yaml             # Transformation rules
├── start.sh                # One-command run script
├── Makefile               # build/run/clean targets
├── .env.example           # Environment variables template
├── prompt_templates/      # Name, phone, address prompts
└── transformers/          # Custom LLM masker + city preserver
```

## Test Datasets

- `examples/chinook_test.sql` - Industry standard (59 customers, multi-country)
- `examples/test_dump.sql` - Minimal validation (10 rows)

## Configuration

Edit `config.yaml` to define which columns get transformed:

```yaml
transformers:
  - table: Customer
    skip_columns: [CustomerId]  # ← NEVER transform PK!
    columns:
      FirstName: { transformer: custom_llm_masker }
      LastName: { transformer: custom_llm_masker }
      Email: { transformer: mask_email }
      Phone: { transformer: mask_phone }
```

## How it Works

1. Parse SQL dump line-by-line
2. For each INSERT row, process fields sequentially
3. Check skip list (PKs) → cached mapping → transform via LLM
4. Rebuild INSERT statements with masked values
5. Validate FK relationships → output sanitized.dump.gz

See [`docs/`](docs/) for detailed architecture documentation.

## License

MIT License
