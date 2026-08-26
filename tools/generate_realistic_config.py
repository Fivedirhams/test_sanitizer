#!/usr/bin/env python3
"""
Realistic Anonymization Config Generator
Only mode - NO obfuscation. Generates config with realistic data preservation.
"""

import sys
import re
from pathlib import Path


def detect_email_format(local_part: str) -> str:
    """Detect email local part format pattern"""
    if '.' in local_part and '_' not in local_part:
        return "firstname.lastname"
    elif '_' in local_part and '.' not in local_part:
        return "firstname_lastname"
    elif len(local_part) <= 5:
        return "short_name"
    else:
        return "mixed"


def detect_phone_region(country_code: str) -> dict:
    """Get phone formatting rules for region"""
    return {
        "+7": {"format": "+{country}-{area}-{xxxx}", "description": "Russia mobile"},
        "+55": {"format": "+{country} ({area}) {prefix}-{suffix}", "description": "Brazil"},
        "+49": {"format": "+{country}-{area}-{number}", "description": "Germany"},
        "+1": {"format": "+{country} ({area}) xxx-xxxx", "description": "USA/Canada"},
    }.get(country_code, {"format": "+{country}-XXX-XXX-XXXX", "description": "Generic"})


def generate_llm_prompt_from_schema(schema_text: str) -> str:
    """Generate realistic anonymization prompt for LLM"""
    
    # Detect common tables
    tables = re.findall(r'CREATE TABLE `?(\w+)`?', schema_text, re.IGNORECASE)
    
    prompt = f"""You are a database sanitization expert creating configuration for REALISTIC ANONYMIZATION (NOT OBFUSCATION).

DATABASE SCHEMA:
{schema_text[:2000]}

REQUIREMENTS FOR REALISTIC ANONYMIZATION:
1. Names → Generate real names in same language/script as original
2. Email → Keep style (firstname.lastname OR firstinitiallastname), different name but similar format  
3. Phone → Keep country code + area code structure, change only subscriber number
4. Address → Change street but keep city/country
5. NEVER use placeholders like anon@example.com or +1-(XXX)-XXX-XXXX
6. ALWAYS produce data that looks valid and usable for testing

OUTPUT ONLY THE YAML CONFIG BELOW:

transformers:
"""
    
    return prompt


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/generate_realistic_config.py --dump file.sql")
        sys.exit(1)
    
    dump_file = sys.argv[1]
    if not Path(dump_file).exists():
        print(f"[ERROR] File not found: {dump_file}")
        sys.exit(1)
    
    # Read schema
    with open(dump_file, 'r', encoding='utf-8') as f:
        schema = ''.join(f.readlines()[:500])
    
    print("=" * 60)
    print("🔍 Analyzing schema for realistic anonymization...")
    print("=" * 60)
    
    # Detect tables and suggest PII fields
    create_tables = re.findall(r'CREATE TABLE `?(\w+)`?\s*\(([^;]+)\);', schema, re.IGNORECASE | re.DOTALL)
    
    print(f"\nFound {len(create_tables)} tables:")
    for table_name, columns in create_tables[:10]:
        print(f"\n  Table: {table_name}")
        cols = [c.strip().split()[0].replace('`', '') for c in columns.split(',') if ',' in columns or len(columns.split(',')) > 1]
        
        # Auto-detect likely PII fields
        pii_fields = []
        for col in cols:
            col_lower = col.lower()
            if any(kw in col_lower for kw in ['name', 'email', 'phone', 'address', 'mobile', 'tel']):
                pii_fields.append(col)
        
        if pii_fields:
            print(f"    Likely PII: {', '.join(pii_fields)}")


if __name__ == "__main__":
    main()
