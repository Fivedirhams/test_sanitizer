"""
Report generator for sanitization results.
Creates visual reports showing transformations applied.
"""

import json
from pathlib import Path
from datetime import datetime


class SanitizationReportGenerator:
    """Генератор отчётов о санитизации базы данных"""
    
    def __init__(self, mapping_file: str):
        self.mapping_data = self._load_mapping(mapping_file)
        
    def _load_mapping(self, filepath: str) -> dict:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('mapping', {})
        except FileNotFoundError:
            print(f"[WARNING] Mapping file not found: {filepath}")
            return {}
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in mapping file: {e}")
            return {}
    
    def generate_summary_report(self) -> str:
        """Generate summary statistics report"""
        
        if not self.mapping_data:
            return "No transformations recorded."
        
        # Group by source/target patterns
        stats = {
            'total_transformations': len(self.mapping_data),
            'unique_entities': len(set(k.split(':')[0] for k in self.mapping_data)),
            'transformed_values': 0,
            'by_field_type': {},
            'sample_changes': []
        }
        
        # Count and categorize
        for entity_key, new_value in self.mapping_data.items():
            table, field, _hash = entity_key.split(':')
            
            # Track sample changes (first 10 unique)
            if len(stats['sample_changes']) < 10:
                original_hash = self._extract_original_hash(entity_key)
                stats['sample_changes'].append({
                    'entity': entity_key,
                    'original_hash': original_hash,
                    'new_value': new_value
                })
            
            # Category tracking
            field_key = f"{table}.{field}"
            if field_key not in stats['by_field_type']:
                stats['by_field_type'][field_key] = {'count': 0, 'examples': set()}
            
            stats['by_field_type'][field_key]['count'] += 1
        
        # Build report
        lines = [
            "="*60,
            "📊 SANITIZATION REPORT",
            "="*60,
            "",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total transformations applied: {stats['total_transformations']",
            f"Unique entities processed: {stats['unique_entities']",
            "",
            "TRANSFORMATIONS BY FIELD:",
            "-"*40
        ]
        
        for field_name, data in sorted(stats['by_field_type'].items()):
            lines.append(f"  {field_name}: {data['count']} replacements")
        
        lines.extend([
            "",
            "SAMPLE CHANGES (original → transformed):",
            "-"*40
        ])
        
        for change in stats['sample_changes']:
            lines.append(f"  • {change['entity'].split(': ')[-1]} → {change['new_value']}")
        
        lines.extend([
            "",
            "="*60,
            "END OF REPORT",
            "="*60
        ])
        
        return "\n".join(lines)
    
    def _extract_original_hash(self, entity_key: str) -> str:
        """Extract the hash from entity key for display"""
        parts = entity_key.split(':')
        if len(parts) >= 3:
            return f"...{parts[2][:8]}"
        return "?"
    
    def save_report(self, output_path: str):
        """Save report to file"""
        report_text = self.generate_summary_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"\n📄 Report saved to: {output_path}")


# Alternative: Simple statistics export
def export_transformation_stats(mapping_file: str, output_csv: str = None):
    """Export transformation mappings to CSV for Excel/analysis"""
    
    import csv
    
    rows = []
    with open(mapping_file, 'r') as f:
        data = json.load(f).get('mapping', {})
    
    for entity_key, new_value in data.items():
        parts = entity_key.split(':')
        if len(parts) >= 2:
            rows.append({
                'Table': parts[0],
                'Field': parts[1],
                'ValueHash': f"...{parts[2][:8]}" if len(parts) > 2 else 'N/A',
                'NewValue': new_value
            })
    
    if output_csv:
        with open(output_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Table', 'Field', 'ValueHash', 'NewValue'])
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ Stats exported to CSV: {output_csv}")
    
    return rows

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <mapping.json>")
        sys.exit(1)
    
    reporter = SanitizationReportGenerator(sys.argv[1])
    print(reporter.generate_summary_report())
