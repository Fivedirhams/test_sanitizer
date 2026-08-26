# Architecture Overview

## Processing Pipeline

```
dump.sql → Parse SQL → Extract Rows → Transform Fields → Rebuild SQL → sanitized.sql.gz
```

### Key Components

1. **Greenmask Engine** - Core transformation pipeline
2. **CustomLLMMasker** - Language-aware name replacement via LLM API
3. **CityPreservingAddressMasker** - Street change with city preservation
4. **EntityMapper** - Consistency cache (same value → same replacement)

### FK Integrity Guarantee

- Primary Keys (`*_id`, `id`) are NEVER transformed
- Config.yaml defines `skip_columns` for automatic protection
- Foreign keys reference unchanged parent PKs → integrity maintained

### Batch Processing Mode

For large datasets (>1K rows), process entire columns in batches:
- 20 values per LLM call (vs single-row mode)
- ~20x speedup on production-scale dumps

---

See [`../README.md`](../README.md) for Quick Start.
