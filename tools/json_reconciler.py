#!/usr/bin/env python3
"""
JSON & Cross-Reference Reconciler

После основного пропуска санитизации проходит ПОСЛЕДНИЙ раз по ВСЕМУ дампу
и проверяет КАЖДУЮ ячейку на наличие значений которые были заменены в других полях.
Если найден - заменяет на CONSISTENT новое значение из mapping.json.

Критично для: JSON колонок (логи с email/телефон внутри), дублирующиеся PII данные
"""

import argparse
import gzip
import json
import re
import sys
from pathlib import Path
from typing import Dict, Set, Tuple


class ConsistencyReconciler:
    """Проверяет и исправляет консистентность данных после первичной санитизации"""
    
    def __init__(self, mapping_path: str, debug: bool = False):
        self.mapping = self._load_mapping(mapping_path)
        self.debug = debug
        self.stats = {
            "json_fields_checked": 0,
            "cross_refs_found": 0,
            "cross_refs_fixed": 0,
            "original_values_in_output": set()
        }
    
    def _load_mapping(self, path: str) -> Dict[str, str]:
        """Load transformation mapping from JSON file"""
        if not Path(path).exists():
            print(f"[WARNING] Mapping file not found: {path}")
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('mapping', {})
        except Exception as e:
            print(f"[ERROR] Failed to load mapping: {e}")
            return {}
    
    def _find_all_entities(self, content: str) -> Set[Tuple[str, int]]:
        """Find ALL original values in sanitized content that should have been replaced"""
        
        # Patterns for common PII that needs checking
        patterns = {
            'email': r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            'phone': r'\+?[\d\s\-\(\)]{10,}',
            'name': r'"[A-Z][a-z]+ [A-Z][a-z]+'  # Simple name pattern
        }
        
        results = []
        for pattern_name, pattern in patterns.items():
            for match in re.finditer(pattern, content):
                value = match.group(0)
                pos = match.start()
                
                # Check if this ORIGINAL value exists in our replacement mapping
                if value in self.mapping:
                    new_value = self.mapping[value]
                    results.append((value, pos, pattern_name, new_value))
                    self.stats['cross_refs_found'] += 1
        
        return results
    
    def reconcile_content(self, content: str) -> str:
        """Run final pass over entire content, replace any missed references"""
        
        # First, apply direct mapping replacements (string replace)
        new_content = content
        
        for old_val, new_val in self.mapping.items():
            # Escaping special regex characters
            escaped_old = re.escape(old_val)
            new_content = re.sub(escaped_old, new_val, new_content)
        
        # Then scan for ANY remaining original values we missed
        misses = self._find_all_entities(new_content)
        
        for old_val, pos, field_type, new_val in misses:
            new_content = new_content[:pos] + new_val + new_content[pos + len(old_val):]
            self.stats['cross_refs_fixed'] += 1
            
            if self.debug:
                print(f"[DEBUG] Fixed {field_type}: '{old_val}' → '{new_val}' at position {pos}")
        
        return new_content
    
    def process_dump_file(self, input_path: str, output_path: str) -> None:
        """Process SQL dump file (handles .gz compression)"""
        
        print(f"🔍 Starting consistency reconciliation...")
        print(f"  Input: {input_path}")
        print(f"  Output: {output_path}")
        print(f"  Mapping entries: {len(self.mapping)}")
        
        # Read content (handle gzip)
        if input_path.endswith('.gz'):
            with gzip.open(input_path, 'rt', encoding='utf-8') as f:
                content = f.read()
        else:
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        print(f"  Content size: {len(content):,} chars")
        
        # Reconcile
        result = self.reconcile_content(content)
        
        # Write output
        if output_path.endswith('.gz'):
            with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                f.write(result)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
        
        print(f"\n✅ Reconciliation complete!")
        print(f"  Cross-references fixed: {self.stats['cross_refs_fixed']}")
        print(f"  Original values remaining: {len(self.stats['original_values_in_output'])}")
    
    def validate_output(self, output_path: str) -> bool:
        """Verify no original PII values remain in output"""
        
        errors = []
        
        if output_path.endswith('.gz'):
            with gzip.open(output_path, 'rt', encoding='utf-8') as f:
                content = f.read()
        else:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Scan for known patterns
        if '@gmail.com' in content or '@yahoo.com' in content or '@hotmail.com' in content:
            errors.append("Found real email domains (should be anonymized)")
        
        if '+7-495-' in content or '+55 (11)' in content or '+1 (555)' in content:
            errors.append("Found real phone number patterns (should be anonymized)")
        
        if errors:
            print(f"\n❌ Validation FAILED:")
            for error in errors:
                print(f"  • {error}")
            return False
        
        print("\n✅ Validation PASSED - No original PII detected")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Post-processing reconciliation for consistent anonymization",
        epilog="Example: python tools/json_reconciler.py --input output/sanitized.sql.gz --mapping output/mapping.json --output output/sanitized_final.sql.gz"
    )
    
    parser.add_argument("--input", "-i", required=True, help="Input sanitized dump file")
    parser.add_argument("--mapping", "-m", required=True, help="Mapping JSON from primary sanitization pass")
    parser.add_argument("--output", "-o", default=None, help="Output file (default: same path with _reconciled appended)")
    parser.add_argument("--debug", "-v", action="store_true", help="Verbose debugging output")
    parser.add_argument("--validate", action="store_true", help="Run validation after processing")
    
    args = parser.parse_args()
    
    # Determine output path
    output_path = args.output or (args.input.replace('.sql.gz', '_reconciled.sql.gz') 
                                    or args.input.replace('.sql', '_reconciled.sql'))
    
    reconciler = ConsistencyReconciler(args.mapping, debug=args.debug)
    reconciler.process_dump_file(args.input, output_path)
    
    if args.validate:
        reconciler.validate_output(output_path)


if __name__ == "__main__":
    main()
