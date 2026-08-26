"""
Email Generator - REALISTIC anonymization (not obfuscation)
Generates new email addresses that look real, not like "anon@example.com"
Preserves style: firstname.lastname OR firstinitiallastname
"""

from greenmask.transformers import BaseTransformer
import re
import os
import requests


class CustomEmailGenerator(BaseTransformer):
    """Генерирует реалистичные email адреса вместо заглушек
    
    Вместо анонсов типа anon@example.com создаёт:
      maria.garcia@gmail.com → pedro.silva@gmail.com
      luisg@empresa.com.br → carlos.santos@empresa.com.br
    
    Сохраняет формат имени части local_part (имя.фамилия vs ифамилия)
    """
    
    def __init__(self, *args, preserve_domain: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.preserve_domain = preserve_domain or False
        
        # Словари для генерации реалистичных значений
        FIRST_NAMES_ESP = ["Pedro", "Maria", "Carmen", "Jose", "Ana", "Luis", "Sofia", "Miguel"]
        LAST_NAMES_ESP = ["Garcia", "Martinez", "Lopez", "Sanchez", "Rodriguez", "Diaz", "Moreno"]
        
        FIRST_NAMES_RUS = ["Дмитрий", "Анна", "Сергей", "Елена", "Иван", "Мария", "Алексей", "Наталья"]
        LAST_NAMES_RUS = ["Соколов", "Новиков", "Фёдоров", "Морозов", "Волков", "Кузнецов"]
        
        self.name_pool = {
            "ES": {"first": FIRST_NAMES_ESP, "last": LAST_NAMES_ESP},
            "RU": {"first": FIRST_NAMES_RUS, "last": LAST_NAMES_RUS},
            "PT": {"first": ["Pedro", "Joao", "Maria", "Ana"], "last": ["Silva", "Santos", "Oliveira", "Ferreira"]},
        }
    
    def _detect_language_from_email(self, email: str) -> str:
        """Detect likely language from local part naming pattern"""
        if re.search(r'[áéíóúñçÁÉÍÓÚÑÇ]', email.lower()):
            return "ES"  # Spanish/Latin American
        elif any(ord(c) > 127 for c in email) and '://' not in email:
            return "RU"  # Cyrillic or other non-ASCII
        else:
            return "ES"  # Default to Spanish/Latin which is common
    
    def generate_new_email(self, original_email: str) -> str:
        """Generate realistic new email based on original format"""
        
        if '@' not in original_email:
            return f"user{os.getpid()}@example.com"  # Fallback
        
        local_part, domain = original_email.rsplit('@', 1)
        
        # Detect format: "maria.garcia" vs "luisg"
        has_dots = '.' in local_part and '_' not in local_part
        has_underscore = '_' in local_part
        
        lang = self._detect_language_from_email(original_email)
        
        names = self.name_pool.get(lang, self.name_pool["ES"])
        
        if has_dots:
            # Format: firstname.lastname
            new_first = self.random_choice(names["first"])
            new_last = self.random_choice(names["last"])
            new_local = f"{new_first}.{new_last}"
        elif has_underscore:
            # Format: firstname_lastname
            new_first = self.random_choice(names["first"]).lower().replace(' ', '_')
            new_last = self.random_choice(names["last"]).lower()
            new_local = f"{new_first}_{new_last}"
        else:
            # Short name or initial.lastname
            new_first = self.random_choice(names["first"])[:3]
            new_last = self.random_choice(names["last"]).lower()[:4]
            new_local = f"{new_first}{new_last}"
        
        if self.preserve_domain:
            return f"{new_local}@{domain}"
        else:
            # Keep similar domain but change TLD
            domain_parts = domain.rsplit('.', 1)
            new_domain = f"{domain_parts[0]}.{self.random_choice(['com', 'net', 'org'])}"
            return f"{new_local}@{new_domain}"
    
    def random_choice(self, pool: list) -> str:
        """Simple random selection"""
        import random
        return random.choice(pool)
    
    def transform(self, row, column_name: str, table_name: str) -> str:
        """Transform a single email field"""
        
        original = row[column_name]
        
        if not isinstance(original, str) or '@' not in original:
            return original  # Return as-is if not email format
        
        return self.generate_new_email(original)
