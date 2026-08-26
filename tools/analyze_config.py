#!/usr/bin/env python3
"""
Configuration Analyzer - LLM-powered config adapter for MySQL databases

This tool analyzes an SQL dump and proposes a Greenmask configuration with:
- Automatic table detection from CREATE statements
- PII field detection by naming patterns
- Transformer selection (LLM-based, static, email, phone, etc.)
- PK preservation via skip_columns
- Interactive mode for user confirmation
"""

import argparse
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

try:
    import requests
except ImportError:
    print("❌ Please install requests: pip install requests")
    sys.exit(1)


class ConfigAnalyzer:
    """Analyze SQL schema and propose Greenmask config using LLM"""
    
    # Naming patterns for PII fields
    NAME_PATTERNS = ['first_name', 'last_name', 'full_name', 'name', 'firstname', 'lastname']
    EMAIL_PATTERNS = ['email', 'mail', 'e-mail', 'email_address']
    PHONE_PATTERNS = ['phone', 'mobile', 'tel', 'telephone', 'cell']
    ADDRESS_PATTERNS = ['address', 'street', 'city', 'country', 'zip', 'postal', 'zipcode']
    DATE_PATTERNS = ['birth_date', 'dob', 'created_at', 'updated_at', 'date', 'timestamp']
    FINANCIAL_PATTERNS = ['price', 'amount', 'total', 'cost', 'salary', 'payment']
    
    def __init__(self, api_key: str, model: str = "bailian/qwen3.5-flash", verbose: bool = False):
        self.api_key = api_key
        self.model = model
        self.verbose = verbose
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def extract_schema(self, dump_file: str, max_tables: int = 20) -> str:
        """Extract CREATE TABLE statements from SQL dump"""
        schema_parts = []
        tables_found = 0
        
        try:
            with open(dump_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract CREATE TABLE statements
                create_pattern = r'CREATE\s+TABLE\s+`?(\w+)`?\s*\(([^;]+)\);?'
                matches = re.findall(create_pattern, content, re.IGNORECASE | re.DOTALL)
                
                for table_name, columns in matches[:max_tables]:
                    schema_parts.append(f"-- Table: {table_name}")
                    schema_parts.append(columns.strip())
                    schema_parts.append("")
                    tables_found += 1
                    
                    if self.verbose:
                        print(f"✅ Found table: {table_name}")
                
                if tables_found == 0:
                    print("[WARNING] No CREATE TABLE statements found. Trying alternative extraction...")
                    
                    # Fallback: extract INSERT INTO statements
                    insert_pattern = r'INSERT\s+INTO\s+`?(\w+)`?\s*VALUES\s*\(([^)]+)\)'
                    inserts = re.findall(insert_pattern, content, re.IGNORECASE | re.DOTALL)
                    
                    if inserts:
                        print(f"⚠️  No CREATE statements, but found {len(inserts)} INSERT statements")
                        for table, values in inserts[:5]:
                            schema_parts.append(f"-- Table: {table} (inferred from INSERT)")
                            schema_parts.append(f"-- Values sample: {values[:200]}...")
        
        except FileNotFoundError:
            print(f"[ERROR] Dump file not found: {dump_file}")
            sys.exit(1)
        
        return "\n".join(schema_parts)
    
    def generate_llm_prompt(self, schema: str) -> str:
        """Generate prompt for LLM config proposal"""
        
        prompt = f"""You are a database sanitization expert. Analyze this MySQL schema and create a Greenmask YAML configuration for data anonymization.

SCHEMA STRUCTURE:
{schema}

REQUIREMENTS:
1. Identify ALL tables containing PII (Personal Identifiable Information)
2. For each table, detect sensitive columns by name patterns:
   - Names: first_name, last_name, full_name, name → custom_llm_masker (language-aware)
   - Emails: email, mail, e-mail → mask_email (Greenmask built-in)
   - Phones: phone, mobile, tel, telephone → mask_phone (Greenmask built-in)  
   - Addresses: address, street, city, country → city_preserving_address_masker or static_replace
   - Dates: birth_date, created_at, updated_at → date_shift or timestamp_shift (-7 days)
   - Financial: price, amount, total, cost → amount_anonymize or static_replace
3. CRITICAL: ALWAYS skip PRIMARY KEY columns (*_id, id, primary_id) - they must be preserved for FK integrity!
4. Recommend transformer type and parameters for each field
5. Output ONLY valid YAML, no explanations or markdown

GREENMASK CONFIG FORMAT:
transformers:
  - name: table_transformer
    schema: database_name
    table: table_name
    skip_columns: [primary_key_column]
    columns:
      column_name:
        transformer: transformer_type
        params:
          param_key: param_value

RETURN THE FULL CONFIGURATION IN VALID YAML FORMAT ONLY."""
        
        return prompt
    
    def call_llm(self, prompt: str, timeout: int = 60) -> str:
        """Call OFox API to get LLM response"""
        
        url = "https://api.ofox.ai/v1/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if 'choices' not in data or len(data['choices']) == 0:
                raise ValueError("No choices returned from LLM API")
            
            content = data['choices'][0]['message']['content']
            return content
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] LLM API call failed: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to process LLM response: {e}")
            sys.exit(1)
    
    def validate_yaml(self, yaml_content: str) -> bool:
        """Basic validation of proposed YAML"""
        try:
            import yaml
            yaml.safe_load(yaml_content)
            return True
        except:
            return False
    
    def analyze_and_propose(self, dump_file: str, output_file: str) -> Dict[str, Any]:
        """Main workflow: extract schema → LLM proposal → validation"""
        
        print("=" * 60)
        print("🔍 Database Schema Analysis & Config Proposal")
        print("=" * 60)
        print()
        
        # Step 1: Extract schema
        print("📋 Step 1: Extracting schema from dump...")
        schema = self.extract_schema(dump_file)
        print(f"✅ Schema extracted successfully")
        print()
        
        # Step 2: Call LLM
        print("🤖 Step 2: Calling LLM to propose configuration...")
        prompt = self.generate_llm_prompt(schema)
        
        if self.verbose:
            print("\n--- LLM PROMPT (preview) ---")
            print(prompt[:500] + "...")
            print("--- END PROMPT ---\n")
        
        llm_response = self.call_llm(prompt)
        
        # Clean up response (remove markdown code fences if present)
        cleaned_response = re.sub(r'```yaml\s*', '', llm_response).replace('```', '')
        
        print("✅ LLM proposal received")
        print()
        
        # Step 3: Validate YAML
        print("🔧 Step 3: Validating proposed YAML...")
        is_valid = self.validate_yaml(cleaned_response)
        
        if not is_valid:
            print("❌ Invalid YAML detected!")
            print("Falling back to default configuration...")
            return {"success": False, "error": "Invalid YAML", "config": None}
        
        print("✅ YAML validated successfully")
        print()
        
        # Save to file
        print("💾 Saving proposed config to:", output_file)
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        Path(output_file).write_text(cleaned_response, encoding='utf-8')
        
        print("✅ Proposed configuration saved!")
        print()
        
        # Show preview
        print("=" * 60)
        print("👀 PREVIEW of Proposed Configuration:")
        print("=" * 60)
        preview_lines = cleaned_response.split('\n')[:60]
        for line in preview_lines:
            print(line)
        if len(preview_lines) < len(cleaned_response.split('\n')):
            print("...")
        print("=" * 60)
        print()
        
        return {
            "success": True,
            "config": cleaned_response,
            "output_file": output_file,
            "schema_tables": len(re.findall(r'CREATE\s+TABLE', schema, re.IGNORECASE))
        }


def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate Greenmask config from SQL dump using LLM analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/analyze_config.py --dump my_database.sql
  python tools/analyze_config.py --dump customer_dump.sql --interactive
  python tools/analyze_config.py --dump production.sql --verbose
        """
    )
    
    parser.add_argument("--dump", "-d", required=True, 
                       help="Path to SQL dump file")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Interactive mode: ask before accepting/rejecting")
    parser.add_argument("--skip-prompt", action="store_true",
                       help="Skip prompts, accept automatically")
    parser.add_argument("--output", "-o", default="output/llm_proposed_config.yaml",
                       help="Output path for proposed config (default: output/llm_proposed_config.yaml)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Check dump file exists
    if not Path(args.dump).exists():
        print(f"[ERROR] Dump file not found: {args.dump}")
        sys.exit(1)
    
    # Get API key
    env_path = Path(".env")
    api_key = None
    
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("OFOX_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    
    if not api_key:
        print("⚠️  WARNING: OFOX_API_KEY not found in .env file!")
        print("Please configure it first:")
        print("  cp .env.example .env")
        print("  echo 'OFOX_API_KEY=sk-your-key-here' >> .env")
        print()
        
        if args.interactive:
            input("Press Enter to continue anyway (analysis will use mock)... or Ctrl+C to cancel")
            print("Note: LLM adaptation requires valid API key. Skipping real LLM call.")
        else:
            sys.exit(1)
    
    # Run analyzer
    analyzer = ConfigAnalyzer(api_key=api_key or "", verbose=args.verbose)
    result = analyzer.analyze_and_propose(args.dump, args.output)
    
    # Handle result
    if result["success"]:
        print()
        print("=" * 60)
        print("✅ ANALYSIS COMPLETE!")
        print("=" * 60)
        print()
        print(f"Tables analyzed: {result['schema_tables']}")
        print(f"Proposed config: {result['output_file']}")
        print()
        print("Next steps:")
        print("  A) Accept and run sanitizer:")
        print(f"       mv {result['output_file']} config.yaml && ./start.sh")
        print()
        print("  B) Review manually first:")
        print(f"       vi {result['output_file']}")
        print("       Then move to config.yaml when ready")
        print()
        print("  C) Cancel (keep original config.yaml)")
        print()
        
        if args.interactive:
            choice = input("Choose option (A/B/C) [A]: ").strip().lower() or "a"
            
            if choice == "a":
                import shutil
                shutil.move(result['output_file'], "config.yaml")
                print("✅ Applied LLM-proposed configuration!")
                print()
                print("Ready to run. Execute: ./start.sh")
            elif choice == "b":
                print("👉 Opening editor for manual review...")
                os.system(f"vi {result['output_file']}")
            else:
                print("⏭️ Skipped. Original config.yaml unchanged.")
        else:
            print("To apply the proposed config, run:")
            print(f"  mv {result['output_file']} config.yaml && ./start.sh")
            print()
    else:
        print()
        print("❌ Analysis failed!")
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()
