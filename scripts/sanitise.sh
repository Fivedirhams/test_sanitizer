#!/bin/bash
set -e

echo "========================================"
echo "MySQL Database Sanitizer"
echo "========================================"

# Config
DUMP_PATH="${1:-./dump.sql}"
OUTPUT_DIR="./output"
CONFIG_PATH="./config.yaml"
TRANSFORMERS_DIR="./transformers"

if [ ! -f "$DUMP_PATH" ]; then
    echo "[ERROR] Dump file not found: $DUMP_PATH"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "[INFO] Starting sanitizer..."
echo "[INFO] Input dump: $DUMP_PATH"
echo "[INFO] Output directory: $OUTPUT_DIR"

# Run Greenmask
docker compose run --rm greenmask \
    -d "$DUMP_PATH" \
    -o "$OUTPUT_DIR/sanitized.sql.gz" \
    -c "$CONFIG_PATH"

echo "[SUCCESS] Sanitized dump created at: $OUTPUT_DIR/sanitized.sql.gz"
echo "[INFO] Check mapping file (if any): $OUTPUT_DIR/mapping.json"
