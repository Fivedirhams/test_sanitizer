#!/bin/bash
# MySQL Database Sanitizer - Main orchestration script
# Usage: ./start.sh [options]
# Options:
#   --no-report     Skip generating statistics report
#   --csv           Export stats to CSV format

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_FILE="${1:-dump.sql}"
OUTPUT_DIR="${SCRIPT_DIR}/output"
REPORT_ENABLED=true
CSV_EXPORT=false

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-report) REPORT_ENABLED=false; shift ;;
        --csv) CSV_EXPORT=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "=========================================="
echo "🔐 MySQL Database Sanitizer"
echo "=========================================="
echo ""
echo "Input:    $DUMP_FILE"
echo "Output:   ${OUTPUT_DIR}/sanitized.sql.gz"
echo ""

# Validate input file exists
if [[ ! -f "$DUMP_FILE" ]]; then
    echo "[ERROR] Input dump file not found: $DUMP_FILE"
    echo "Usage: cp examples/chinook_test.sql dump.sql && ./start.sh"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run Greenmask
echo "🚀 Running sanitization..."
docker-compose up -d sanitizer
docker-compose logs -f sanitizer | tee "$OUTPUT_DIR/greenmask.log" || true

# Check if mapping was created
MAPPING_FILE="${OUTPUT_DIR}/mapping.json"
if [[ -f "$MAPPING_FILE" ]]; then
    echo ""
    echo "✅ Sanitization complete!"
    echo ""
    
    # Generate summary report (always)
    python3 << PYTHON
import sys
sys.path.insert(0, '/project/my-sql-sanitizer/transformers')
from report_generator import SanitizationReportGenerator

reporter = SanitizationReportGenerator('$MAPPING_FILE')
print(reporter.generate_summary_report())
PYTHON
    
    echo ""
    
    # Optional: Export to CSV
    if [[ "$CSV_EXPORT" == "true" ]] || grep -q "csv" <<< "$@"; then
        python3 << PYTHON
import sys
sys.path.insert(0, '/project/my-sql-sanitizer/transformers')
from report_generator import export_transformation_stats

rows = export_transformation_stats('$MAPPING_FILE', '$OUTPUT_DIR/stats.csv')
print(f"\n📈 Statistics: {len(rows)} transformations exported")
PYTHON
        echo "✅ Stats CSV saved to: $OUTPUT_DIR/stats.csv"
    fi
    
else
    echo "⚠️  Warning: No mapping file generated (transformations may not be tracked)"
fi

echo ""
echo "=========================================="
echo "📁 Files created:"
echo "=========================================="
ls -lh "$OUTPUT_DIR"/
echo ""
echo "To view sanitized data:"
gunzip -c "$OUTPUT_DIR/sanitized.sql.gz" | head -50

