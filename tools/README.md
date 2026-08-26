# Tools Directory

Utilities for working with sanitization reports and statistics.

## Report Generation

### Quick Report (recommended)

```bash
./tools/report.sh
# Reads: output/mapping.json
# Output: Statistics to stdout
```

### Custom mapping file

```bash
./tools/report.sh /path/to/custom/mapping.json
```

### Export to CSV

```bash
python3 transformers/report_generator.py \
  --csv output/stats.csv output/mapping.json
cat output/stats.csv
```

## Example Output

```
============================================================
📊 SANITIZATION REPORT
============================================================

Generated at: 2024-01-15 14:32:45
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
  • customers.first_name:...a1b2c3d4 → Carlos
  • customers.email:...e5f6g7h8 → anon@example.com
  • invoices.total:...i9j0k1l2 → [AMOUNT_MASKED]

============================================================
END OF REPORT
============================================================
```

## Integration

The report generator is automatically called by `start.sh` after successful sanitization.
