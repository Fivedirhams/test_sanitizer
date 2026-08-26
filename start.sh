#!/bin/bash
# MySQL Database Sanitizer - Single command execution
# Usage: ./start.sh [--reconcile] [--validate]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check API key
if [[ ! -f ".env" ]] || ! grep -q "OFOX_API_KEY=" .env; then
    echo "⚠️  ERROR: OFOX_API_KEY not configured!"
    echo "Run: cp .env.example .env && vim .env"
    exit 1
fi

INPUT_DUMP="${1:-dump.sql}"
if [[ ! -f "$INPUT_DUMP" ]]; then
    echo "❌ Input dump not found: $INPUT_DUMP"
    echo "Use: cp examples/chinook_test.sql dump.sql"
    exit 1
fi

echo "============================================================"
echo "🗄️  MySQL Database Sanitizer (Realistic Anonymization Only)"
echo "============================================================"
echo ""
echo "Input:   $INPUT_DUMP"
echo "Mode:    Realistic anonymization (NO obfuscation)"
echo "Output:  output/sanitized.sql.gz"
echo ""

mkdir -p output

# Step 1: Primary sanitization with Greenmask
echo "🔄 Step 1: Running primary sanitization pass..."
docker-compose run --rm sanitizer greenmask sanitise \
    --config=/app/config.yaml \
    --source-path=/data/${INPUT_DUMP} \
    --destination-path=/output/sanitized.sql

echo "✅ Primary sanitization complete"
echo ""

# Step 2: Post-processing JSON & cross-reference reconciliation
echo "🔧 Step 2: Running consistency reconciliation..."
python3 tools/json_reconciler.py \
    --input output/sanitized.sql \
    --mapping output/mapping.json \
    --output output/sanitized_final.sql

echo "✅ Consistency reconciliation complete"
echo ""

# Step 3: Compress final output
echo "💾 Step 3: Compressing output..."
gzip -9 output/sanitized_final.sql
mv output/sanitized_final.sql.gz output/sanitized.sql.gz

echo "✅ Compression complete"
echo ""

# Step 4: Generate statistics report
echo "📊 Step 4: Generating statistics report..."
python3 transformers/report_generator.py \
    --mapping output/mapping.json \
    --output output/report.txt

echo "✅ Report generated"
echo ""

echo "============================================================"
echo "🎉 SANITIZATION COMPLETE!"
echo "============================================================"
echo ""
cat output/report.txt
echo ""
echo "Output files:"
ls -lh output/

echo ""
echo "To validate consistency, run: python3 tools/json_reconciler.py --validate"
