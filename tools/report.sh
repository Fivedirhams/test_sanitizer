#!/bin/bash
# Generate sanitization statistics report
# Usage: ./tools/report.sh [mapping_file]
# Default: output/mapping.json

MAPPING_FILE="${1:-$(pwd)/output/mapping.json}"

if [[ ! -f "$MAPPING_FILE" ]]; then
    echo "❌ Mapping file not found: $MAPPING_FILE"
    echo "Usage: ./tools/report.sh [path/to/mapping.json]"
    exit 1
fi

echo "📊 Generating sanitization report..."
echo ""

python3 << PYTHON
import sys
sys.path.insert(0, '/project/my-sql-sanitizer/transformers')
from report_generator import SanitizationReportGenerator

reporter = SanitizationReportGenerator("$MAPPING_FILE")
print(reporter.generate_summary_report())
PYTHON
