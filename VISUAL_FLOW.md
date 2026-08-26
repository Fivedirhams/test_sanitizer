# 🔄 Визуальная схема потока санитизации

```
┌──────────────────────────────────────────────────────────────────┐
│  START: dump.sql                                                  │
│  [SQL INSERTs with PII data]                                      │
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 1: PARSE SQL                                               │
│  ┌──────────────────────┐                                        │
│  │ Read dump.sql lines  │                                       │
│  └──────────┬───────────┘                                        │
│             │                                                    │
│             ├─→ Parse CREATE TABLE → Build schema                │
│             └─→ Parse INSERT INTO → Extract values              │
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 2: LOAD CONFIG.YAML                                        │
│  ┌──────────────────────┐                                        │
│  │ Read transformer     │                                       │
│  │ definitions          │                                       │
│  └──────────┬───────────┘                                        │
│             │                                                    │
│             ├─→ Initialize custom_llm_masker                     │
│             ├─→ Register mask_email (Greenmask)                  │
│             ├─→ Register ip_anonymize (Greenmask)                │
│             └─→ Build skip_columns list (PK protection!)         │
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 3: MAIN LOOP - ROW BY ROW                                  │
│                                                                  │
│  for each INSERT row in database:                                │
│      ┌─────────────────────────────────────────────────────────┐│
│      │ For each column value in row:                           ││
│      │                                                         ││
│      ├─→ CHECK #1: Is column_name in skip_columns?            ││
│      │    ┌─ YES → Keep ORIGINAL value                        ││
│      │    │   (customer_id, order_id, user_id stay unchanged) ││
│      │    │   ✅ FK INTEGRITY PRESERVED!                       ││
│      │    └─ NO → Continue                                    ││
│      │                                                         ││
│      ├─→ CHECK #2: Is entity_key in global_mapping_cache?     ││
│      │    ┌─ YES → Use CACHED replacement                     ││
│      │    │   (Same María → Same Carmen everywhere)           ││
│      │    │   ✅ CONSISTENCY MAINTAINED!                      ││
│      │    └─ NO → Continue                                    ││
│      │                                                         ││
│      └─→ TRANSFORM                                           ││
│           ┌─ Get transformer from config.yaml                 ││
│           ├─ Execute transform() with full row context        ││
│           └─ Cache result in mapping                          ││
│                                                                 ││
│  END LOOP                                                       ││
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 4: RECONSTRUCT SQL                                         │
│  ┌──────────────────────┐                                        │
│  │ Rebuild INSERT stmts │                                       │
│  │ with transformed val │                                       │
│  └──────────┬───────────┘                                        │
│             │                                                    │
│             └─→ Write to sanitized.sql.gz                       │
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 5: VALIDATION                                              │
│                                                                  │
│  Check FK integrity:                                             │
│  ├─ Load all customers IDs from output                         │
│  ├─ Load all orders.customer_ids (FK)                          │
│  ├─ Verify every FK points to existing customer                │
│  └─ If any violation → ERROR + abort                           │
│                                                                 ││
│ Result:                                                        │
│   ✅ FK relations intact (Maria ID=1 still linked to her orders)│
│   ✅ No duplicate PKs                                          │
│   ✅ Schema identical to original                               │
└─────────────────────┬────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 6: OUTPUT                                                  │
│                                                                  │
│  Files created:                                                 │
│  ├── sanitized.sql.gz  ← Anonymized SQL dump                    │
│  ├── mapping.json       ← Optional transformation cache         │
│  └── validation.log     ← Integrity check results               │
│                                                                 ││
│ SUCCESS MESSAGE:                                                │
│   "Sanitization complete! FK integrity validated."             │
└──────────────────────────────────────────────────────────────────┘
```

## Ключевые контрольные точки

### checkpoint_01: PK Skip Protection
Location: `config.yaml` skip_columns
```yaml
skip_columns:
  - customer_id      # PRIMARY KEY - NEVER TOUCHED
  - order_id         # PRIMARY KEY - NEVER TOUCHED
  - log_id           # PRIMARY KEY - NEVER TOUCHED
```

### checkpoint_02: Entity Consistency
Location: Global entity_mapping cache
```python
entity_mapping = {
    "customers:first_name:hash(maria)": "Carmen",
    "orders:first_name:hash(maria)": "Carmen"  # Same everywhere!
}
```

### checkpoint_03: FK Validation
Location: Post-processing step
```sql
-- Verify: Every orders.customer_id exists in customers.customer_id
SELECT COUNT(*) FROM orders o 
WHERE NOT EXISTS (
    SELECT 1 FROM customers c WHERE c.customer_id = o.customer_id
);
-- Must return 0 rows
```

## Порядок выполнения (последовательный vs параллельный)

| Шаг | Parallel? | Reason |
|-----|-----------|--------|
| Парсинг dump.sql | ❌ No | Line-by-line parsing |
| Инициализация конфиг | ❌ No | Single-threaded |
| Трансформация строк | ⚠️ Maybe | But entity_map needs sync |
| Вызовы LLM API | ✅ Async possible | Multiple HTTP requests ok |
| FK проверка | ❌ No | After all transformations |

## Почему не трогать Primary Keys критично

```
BEFORE:
customers(1, 'María')  ← customer_id = 1 (PK)
orders(1, 1, 'Laptop')  ← FIRST num = 1 (PK), SECOND = 1 (FK → customers)

AFTER (if we CHANGED customer_id):
customers(999, 'Carmen')  ← customer_id = 999 ❌
orders(1, 1, 'Laptop')    ← FK points to 1... but NO CUSTOMER with ID=1!
→ REFERENTIAL INTEGRITY BROKEN! 😱

AFTER (if we KEEP customer_id unchanged):
customers(1, 'Carmen')    ← customer_id = 1 ✅ (unchanged)
orders(1, 1, 'Laptop')    ← FK points to 1 → customer 1 EXISTS! ✅
→ REFERENTIAL INTEGRITY PRESERVED! 🎉
```
