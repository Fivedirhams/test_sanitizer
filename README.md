# MySQL Database Sanitizer with LLM-based Masking

Production-ready tool for creating sanitized test databases from MySQL dumps using custom AI transformers and Greenmask engine.

## Features

- ✅ **Language-aware masking** - names stay in original language (María → Carmen, not Яна)
- ✅ **FK integrity preserved** - Primary Keys never transformed, foreign keys always valid
- ✅ **Entity consistency** - same customer name = same replacement across all tables
- ✅ **City-preserving addresses** - streets changed but cities/countries remain consistent
- ✅ **Batch processing ready** - supports column-level batching for large datasets
- ✅ **Docker-native** - single container orchestration with Greenmask engine
- ✅ **Statistics report** - automatic generation of transformation summary

## Quick Start

```bash
# 1. Configure API key
cp .env.example .env
echo 'OFOX_API_KEY=sk-your-key-here' >> .env

# 2. Run on sample data
cp examples/chinook_test.sql dump.sql
./start.sh

# 3. Check results
gunzip -c output/sanitized.sql.gz | head -50

# 4. View statistics report (automatically generated)
cat output/report.txt
# Or run manually:
./tools/report.sh
```

## Files

```
my-sql-sanitizer/
├── docker-compose.yml      # Container orchestration (Greenmask-based)
├── Dockerfile.greenmask    # Build image with dependencies
├── config.yaml             # Transformation rules (universal!)
├── start.sh                # One-command run script (+report gen)
├── Makefile               # build/run/clean targets
├── .env.example           # Environment variables template
├── tools/                 # Utilities and reports
│   ├── report.sh         # Generate stats report
│   └── README.md         # Tool documentation
├── docs/                  # Architecture documentation
│   └── ARCHITECTURE.md   # Pipeline overview
├── examples/              # Test datasets
│   ├── chinook_test.sql  # Industry standard (59 customers!)
│   └── test_dump.sql     # Minimal validation (10 rows)
├── prompt_templates/      # Name, phone, address prompts
├── transformers/          # Custom LLM masker + city preserver
│   └── report_generator.py  # Statistics generator
└── output/                # Generated files (sanitized.sql.gz, mapping.json)
```

## Documentation

| Document | Description | Use Case |
|----------|-------------|----------|
| [README.md](README.md) | This file - quick start | Getting started |
| [TRANSFORMATION_RULES.md](TRANSFORMATION_RULES.md) | Complete rules ↔ config.yaml mapping | Understanding all transformer behaviors |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Answers to common questions | Adapting to new databases |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture | Deep dive |

## How it Works

1. Parse SQL dump line-by-line
2. For each INSERT row, process fields sequentially
3. Check skip list (PKs) → cached mapping → transform via LLM
4. Rebuild INSERT statements with masked values
5. Validate FK relationships → output sanitized.dump.gz
6. Generate statistics report showing all transformations

See [`TRANSFORMATION_RULES.md`](TRANSFORMATION_RULES.md) for complete rule documentation.

## Example Statistics Report

```
============================================================
📊 SANITIZATION REPORT
============================================================

Generated at: 2024-08-26 15:03:22
Total transformations applied: 847
Unique entities processed: 59

TRANSFORMATIONS BY FIELD:
----------------------------------------
  Customer.Address: 59 replacements
  Customer.Email: 59 replacements  
  Customer.FirstName: 59 replacements
  Customer.LastName: 59 replacements
  Customer.Phone: 59 replacements
  Invoice.Total: 412 replacements

SAMPLE CHANGES (original → transformed):
----------------------------------------
  • Luís Gonçalves → Carlos Santos
  • luisg@embraer.com.br → anon@example.com
  • +55 (12) 3923-5555 → +1 (XXX) XXX-XXXX
  • São Paulo address → New street, São Paulo

STATISTICS:
  - Languages detected: Brazilian Portuguese, German, French, Spanish
  - Countries preserved: Brazil, Germany, France, Canada
  - Cities preserved in addresses: YES
  - FK integrity: ALL LINKS VALID ✅
============================================================
```

## License

MIT License

## Auto-Adapter Mode (Experimental)

Automatically adapt the configuration file using LLM analysis of your SQL dump:

```bash
# 1. Analyze dump with LLM
./scripts/auto_adapt.sh --dump customer_database.sql --adapt

# 2. Interactive mode (review before accepting)
./scripts/auto_adapt.sh -d production_dump.sql --interactive

# 3. Non-interactive mode (auto-accept)
./scripts/auto_adapt.sh -d mydb.sql --skip-prompt

# 4. Dry run (analyze only)
./scripts/auto_adapt.sh --dry-run --verbose

# Or use Python CLI:
python tools/analyze_config.py --dump mydb.sql --interactive
```

**Available options:**
| Flag | Description |
|------|-------------|
| `--dump FILE` | Path to SQL dump (default: examples/chinook_test.sql) |
| `--adapt` | Enable LLM-based config generation |
| `--interactive` | Ask user confirmation before each change |
| `--skip-prompt` | Auto-accept (no prompts) |
| `--dry-run` | Analyze without running sanitizer |
| `--verbose` | Show detailed output |

See `./scripts/auto_adapt.sh --help` for full documentation.
