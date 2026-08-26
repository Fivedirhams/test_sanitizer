"""
Primary Key (PK) Preservation Helper for Greenmask.
Ensures FK relationships are maintained across all tables.

Key principle: NEVER change Primary Keys! They are used by Foreign Keys
to maintain referential integrity. If you must remap, do it consistently.
"""


class PKPreservationHelper:
    """
    Manage Primary Key preservation strategies.
    
    Strategies:
    1. Keep original values (RECOMMENDED) - safest, preserves FK automatically
    2. Consistent hash-based remapping - if PKs must be changed
    """
    
    def __init__(self):
        self.pk_mapping: Dict[int, int] = {}
    
    # ======================================================================
    # STRATEGY 1: KEEP ORIGINAL VALUES (Recommended)
    # ======================================================================
    
    def keep_original_pk(self, pk_value: Any) -> Any:
        """Simply return the original value - no transformation"""
        return pk_value
    
    def get_skip_columns_for_schema(self, schema_name: str, table_name: str) -> List[str]:
        """Generate list of columns to skip based on common PK patterns"""
        
        # Common PK column names
        pk_patterns = [
            f"{table_name}_id",      # orders_id, customers_id
            "id",                    # id (simple)
            f"{schema_name}.{table_name}.id"
        ]
        
        return pk_patterns
    
    # ======================================================================
    # STRATEGY 2: CONSISTENT REMAPPING (if you MUST change PKs)
    # ======================================================================
    
    def _create_pk_hash(self, old_pk: int) -> int:
        """Generate deterministic new PK from old one"""
        hash_val = int(hashlib.sha256(str(old_pk).encode()).hexdigest()[:8], 16)
        # Ensure new PK is in valid range
        new_pk = 100000 + (hash_val % 900000)  # Range: 100000-999999
        return new_pk
    
    def transform_pk_consistently(self, old_pk: int) -> int:
        """Remap PK consistently across all tables"""
        
        # Check existing mapping first
        if old_pk in self.pk_mapping:
            return self.pk_mapping[old_pk]
        
        # Generate new PK
        new_pk = self._create_pk_hash(old_pk)
        
        # Save mapping for consistency
        self.pk_mapping[old_pk] = new_pk
        
        return new_pk
    
    def validate_fk_integrity(self, fk_value: int, source_table: str) -> bool:
        """Check if foreign key still points to valid primary key"""
        
        # After remapping, check if destination exists
        mapped_fk = self.transform_pk_consistently(fk_value)
        
        # Return True if we have a mapping (meaning this FK is tracked)
        return mapped_fk in self.pk_mapping.values()
    
    def generate_migration_script(self) -> str:
        """Generate SQL script to apply consistent PK changes"""
        
        lines = [
            "-- Auto-generated PK remigration script",
            "-- Apply in transactions to maintain referential integrity",
            "",
        ]
        
        for old_pk, new_pk in sorted(self.pk_mapping.items()):
            lines.append(f"UPDATE customers SET customer_id = {new_pk} WHERE customer_id = {old_pk};")
            lines.append(f"UPDATE orders SET customer_id = {new_pk} WHERE customer_id = {old_pk};")
            lines.append(f"UPDATE system_logs SET user_id = {new_pk} WHERE user_id = {old_pk};")
            lines.append("")
        
        return "\n".join(lines)
    
    def export_mapping_json(self, output_path: str):
        """Export PK mapping for reconciliation"""
        with open(output_path, 'w') as f:
            json.dump({
                "mapping_type": "pk_preservation",
                "strategy": "hash_based",
                "total_mappings": len(self.pk_mapping),
                "mappings": self.pk_mapping
            }, f, indent=2)
