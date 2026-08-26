#!/bin/bash
# Auto-adapter script for MySQL database sanitization
# Usage: ./scripts/auto_adapt.sh [options]
# Options:
#   --dump FILE       Path to SQL dump file (default: examples/chinook_test.sql)
#   --adapt           Use LLM to analyze DB and propose config changes
#   --dry-run         Analyze without running sanitizer
#   --interactive     Ask user for confirmation before each change
#   --skip-prompt     Skip user prompts (non-interactive mode)
#   --verbose         Show detailed output
#   --help            Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
DUMP_FILE="$PROJECT_ROOT/examples/chinook_test.sql"
USE_LLM_ADAPT=false
DRY_RUN=false
INTERACTIVE=false
SKIP_PROMPT=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dump|-d) DUMP_FILE="$2"; shift 2 ;;
        --adapt|-a) USE_LLM_ADAPT=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --interactive|-i) INTERACTIVE=true; SKIP_PROMPT=false; shift ;;
        --skip-prompt) SKIP_PROMPT=true; INTERACTIVE=false; shift ;;
        --verbose|-v) VERBOSE=true; shift ;;
        --help|-h)
            echo "Usage: ./scripts/auto_adapt.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dump FILE          Path to SQL dump file (default: examples/chinook_test.sql)"
            echo "  --adapt              Use LLM to analyze database and propose config changes"
            echo "  --dry-run            Analyze structure without running sanitizer"
            echo "  --interactive (-i)   Ask user for confirmation before each change"
            echo "  --skip-prompt        Skip prompts (automatic acceptance)"
            echo "  --verbose (-v)       Show detailed output"
            echo "  --help (-h)          Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Validate dump file exists
if [[ ! -f "$DUMP_FILE" ]]; then
    echo "[ERROR] Dump file not found: $DUMP_FILE"
    if [[ "$VERBOSE" == "true" ]]; then
        echo "[INFO] Available examples:"
        ls -lh "$PROJECT_ROOT/examples/" | grep ".sql" || true
    fi
    exit 1
fi

echo "============================================================"
echo "🔧 MySQL Sanitizer - Auto Adapter"
echo "============================================================"
echo ""
echo "Input dump:    $DUMP_FILE"
echo "LLM adaptation: $(if [[ "$USE_LLM_ADAPT" == "true" ]]; then echo "ENABLED"; else echo "DISABLED"; fi)"
echo "Dry run:        $(if [[ "$DRY_RUN" == "true" ]]; then echo "YES"; else echo "NO"; fi)"
echo "Interactive:    $(if [[ "$INTERACTIVE" == "true" ]]; then echo "YES"; else echo "NO"; fi)"
echo ""

# Step 1: Extract schema from dump
echo "📋 Step 1: Extracting schema from dump..."
SCHEMA=$(head -500 "$DUMP_FILE" | grep -E "^CREATE TABLE|INSERT INTO|^DROP|^USE" | head -100)

if [[ -z "$SCHEMA" ]]; then
    echo "[WARNING] Could not extract schema. Please ensure valid SQL dump file."
    exit 1
fi

echo "✅ Schema extracted ($(echo "$SCHEMA" | wc -l | tr -d ' ') lines)"
echo ""

# If LLM adaptation is enabled, call LLM to propose config changes
if [[ "$USE_LLM_ADAPT" == "true" ]]; then
    echo "🤖 Step 2: Using LLM to analyze database and propose config..."
    echo ""
    
    # Create prompt for LLM
    LLM_PROMPT=$(cat << PROMPT
Analyze this MySQL schema and create a Greenmask configuration for data sanitization.

Schema structure (first 10 tables with CREATE statements):
$SCHEMA

Requirements:
1. Identify all tables that might contain PII (Personal Identifiable Information)
2. For each table, identify likely sensitive columns by name patterns:
   - names: first_name, last_name, full_name, name
   - emails: email, mail
   - phones: phone, mobile, tel
   - addresses: address, street, city, country
   - dates: birth_date, created_at, updated_at
   - financial: price, amount, total, cost
3. ALWAYS skip primary key columns (*_id, id) - they must be preserved for FK integrity
4. Recommend appropriate transformers for each field:
   - Names → custom_llm_masker (language-aware)
   - Emails → mask_email (Greenmask built-in)
   - Phones → mask_phone (Greenmask built-in)
   - Addresses → city_preserving_address_masker or static_replace
   - Dates → date_shift or timestamp_shift
   - Financial → amount_anonymize or static_replace
5. Format the config as valid YAML following Greenmask syntax

Return ONLY the YAML config without explanations.

Example format:
transformers:
  - name: customers_transformer
    schema: test_db
    table: customers
    skip_columns: [customer_id]
    columns:
      first_name: { transformer: custom_llm_masker }
      last_name: { transformer: custom_llm_masker }
      email: { transformer: mask_email }
PROMPT
)
    
    # Call LLM via OFox API
    if [[ ! -f "$PROJECT_ROOT/.env" ]] || ! grep -q "OFOX_API_KEY" "$PROJECT_ROOT/.env"; then
        echo "⚠️  Warning: No OFOX_API_KEY found in .env file!"
        echo "Please set up your API key first:"
        echo "  cp .env.example .env"
        echo "  echo 'OFOX_API_KEY=sk-your-key-here' >> .env"
        echo ""
        echo "Skipping LLM adaptation... using default config instead."
        USE_LLM_ADAPT=false
    else
        API_KEY=$(grep "OFOX_API_KEY=" "$PROJECT_ROOT/.env" | cut -d= -f2)
        
        RESPONSE=$(curl -s -X POST \
            https://api.ofox.ai/v1/chat/completions \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d '{
                "model": "bailian/qwen3.5-flash",
                "messages": [{"role": "user", "content": "'"$LLM_PROMPT"'"}],
                "temperature": 0.7,
                "max_tokens": 2000
            }')
        
        # Parse response
        CONFIG_CONTENT=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('choices',[{}])[0].get('message',{}).get('content',''))" 2>/dev/null || echo "")
        
        if [[ -z "$CONFIG_CONTENT" ]]; then
            echo "❌ LLM call failed. Check your API key and network connection."
            exit 1
        fi
        
        # Save proposed config
        PROPOSED_CONFIG="$PROJECT_ROOT/output/llm_proposed_config.yaml"
        mkdir -p "$PROJECT_ROOT/output"
        echo "$CONFIG_CONTENT" > "$PROPOSED_CONFIG"
        
        echo "✅ Config proposed by LLM saved to: $PROPOSED_CONFIG"
        echo ""
        echo "======================================"
        echo "PROPOSED CONFIGURATION (preview):"
        echo "======================================"
        echo "${CONFIG_CONTENT:0:500}..."
        echo "..."
        echo "======================================"
        echo ""
        
        # Show what changed vs original
        ORIGINAL_CONFIG="$PROJECT_ROOT/config.yaml"
        echo "🔄 Changes from original config.yaml:"
        echo ""
        
        if command -v diff &> /dev/null; then
            echo "--- Original config.yaml ---"
            head -50 "$ORIGINAL_CONFIG"
            echo ""
            echo "--- Proposed config ---"
            head -50 "$PROPOSED_CONFIG"
            echo ""
            
            echo "Full diff:"
            diff -u "$ORIGINAL_CONFIG" "$PROPOSED_CONFIG" | head -100 || echo "Config format differs significantly"
        fi
        
        echo ""
        echo "✅ LLM analysis complete!"
        echo ""
    fi
    
    echo "----------------------------------------------------------"
    echo "Next step options:"
    echo ""
    echo "A) Accept proposed config and run sanitizer"
    echo "B) Review config manually, then run sanitizer"  
    echo "C) Skip adaptation, use existing config.yaml"
    echo "D) Cancel"
    echo ""
    
    if [[ "$INTERACTIVE" == "true" ]]; then
        read -p "Choose option (A/B/C/D) [A]: " CHOICE
    else
        CHOICE="${CHOICE:-A}"
        echo "Auto-selected: $CHOICE"
    fi
    
    case "$CHOICE" in
        [Aa]*)
            echo ""
            echo "📝 Applying proposed config..."
            mv "$PROPOSED_CONFIG" "$ORIGINAL_CONFIG"
            echo "✅ Proposed config applied!"
            ;;
        [Bb]*)
            echo ""
            echo "👉 Editing config manually..."
            nano "$PROPOSED_CONFIG"
            echo ""
            mv "$PROPOSED_CONFIG" "$ORIGINAL_CONFIG"
            echo "✅ Config saved!"
            ;;
        [Cc]*)
            echo ""
            echo "⏭️ Skipping LLM adaptation, using original config.yaml"
            ;;
        [Dd]*)
            echo ""
            echo "❌ Operation cancelled."
            exit 0
            ;;
        *)
            echo "Invalid option. Defaulting to A (Accept)."
            mv "$PROPOSED_CONFIG" "$ORIGINAL_CONFIG"
            ;;
    esac
else
    echo "⏭️ Skipping LLM adaptation, using existing config.yaml"
fi

echo ""
echo "----------------------------------------------------------"
echo "Final configuration ready."
echo ""

# Proceed to run sanitizer if not dry-run
if [[ "$DRY_RUN" == "true" ]]; then
    echo "📊 DRY RUN MODE - Analysis only. No sanitization performed."
    echo ""
    echo "To run actual sanitization:"
    echo "  1. Ensure API key configured: cp .env.example .env && vim .env"
    echo "  2. Copy dump file: cp $DUMP_FILE dump.sql"
    echo "  3. Run: ./start.sh"
    exit 0
fi

echo "🚀 Ready to run sanitizer with current configuration."
echo ""
echo "Run next:"
echo "  cp $DUMP_FILE dump.sql && ./start.sh"
echo ""
echo "Or run now automatically? (y/n) [y]: "
read -r CONFIRMATION <<< "${CONFIRMATION:-y}"

if [[ "$CONFIRMATION" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting sanitization..."
    cd "$PROJECT_ROOT"
    cp "$DUMP_FILE" dump.sql
    ./start.sh
else
    echo ""
    echo "Sanitization skipped. You can run it later with: ./start.sh"
fi
