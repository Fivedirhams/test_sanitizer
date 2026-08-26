"""
City-Preserving Address Transformer for Greenmask.
Ensures that street addresses are replaced but cities stay within same country/region.

Usage in config.yaml:
  columns:
    shipping_address:
      transformer: city_preserving_address_masker
      params:
        llm_model: bailian/qwen3.5-flash
        prompt_template_file: /app/prompt_templates/address.txt
"""

from greenmask.transformers import BaseTransformer
import os
import re
import json
import hashlib
import requests
from typing import Optional, Any, Dict, List


# Pre-defined valid cities per country (for consistency without LLM)
VALID_CITIES_BY_COUNTRY = {
    "Spain": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao", "Malaga"],
    "Brazil": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza"],
    "USA": ["New York", "Chicago", "Los Angeles", "Houston", "Phoenix", "Philadelphia"],
    "Russia": ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань"],
    "France": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice"],
}

# Street name pools per region (for fast replacements without LLM)
STREET_POOLS = {
    "Spain": [
        "Calle Mayor", "Calle Velázquez", "Calle Serrano", "Paseo de la Castellana",
        "Rambla de Cataluña", "Gran Vía"
    ],
    "Brazil": [
        "Rua das Flores", "Avenida Paulista", "Rua Augusta", "Rua Oscar Freire",
        "Avenida Atlântica", "Rua Frei Caneca"
    ],
    "USA": [
        "Broadway Avenue", "Oak Street", "Main Street", "Park Avenue",
        "Fifth Avenue", "Michigan Avenue"
    ],
    "Russia": [
        "ул. Тверская", "ул. Арбат", "пр. Мира", "ул. Ленина",
        "Садовое кольцо", "Варшавское шоссе"
    ],
    "France": [
        "Rue de Rivoli", "Boulevard Saint-Germain", "Avenue des Champs-Élysées",
        "Rue de la Paix", "Boulevard Haussmann"
    ]
}


class CityPreservingAddressMasker(BaseTransformer):
    """Replace street addresses while preserving city/country context
    
    Key features:
    - Extracts city from address string
    - Generates new street address in same city
    - Falls back to random valid city if original unknown
    - Consistent mapping for entity-level replacement
    """
    
    def __init__(
        self,
        *args,
        prompt_template_file: str,
        llm_model: Optional[str] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        self.prompt_template = self._load_prompt_template(prompt_template_file)
        self.llm_model = llm_model or self._get_env('LLM_MODEL', 'bailian/qwen3.5-flash')
        self.api_base_url = self._get_env('LLM_ENDPOINT', 'https://api.ofox.ai/v1')
        self.temperature = float(self._get_env('LLM_TEMPERATURE', '0.7'))
        
        # API key check
        api_key = self._get_env('OFOX_API_KEY')
        if not api_key:
            raise ValueError("Environment variable OFOX_API_KEY must be set!")
        self.api_key = api_key
        
        # Load existing mappings
        self.address_mapping: Dict[str, str] = {}
    
    def _get_env(self, key: str, default: str = '') -> str:
        return os.environ.get(key, default)
    
    def _load_prompt_template(self, template_file: str) -> str:
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return "Replace '{original_street}' with a realistic street address in {city}. Return format: 'StreetName Number, City, Country'"
    
    def _detect_country(self, city: str) -> str:
        """Detect which country pool contains this city"""
        for country, cities in VALID_CITIES_BY_COUNTRY.items():
            if city in cities:
                return country
        return "Unknown"
    
    def _extract_address_parts(self, address: str) -> Dict[str, Any]:
        """Parse address into components: street_number, street_name, city, country"""
        
        # Basic regex patterns (can be improved with NLP libraries later)
        patterns = {
            'usa': r'(\d+)\s+([^\s,]+)\s*[,|,]?(\w+(?:\s+\w+)*)?\s*,?\s*(\w+)\s*,\s*(\w+)\s*(?:\d{5})?$',
            'europe': r'(?:Calle|Rua|Avenida|Street|Ул\.|Rue)\s+([^\s,]+)\s*(\d+|#\d+)?(?:,\s*(.+))?,?\s*(.+)$',
            'russia': r'(ул\.|пр\.).*?\s*([А-Яа-я]+)\s*\d*',
        }
        
        # Try different parsing approaches
        result = {
            'street_number': '',
            'street_name': '',
            'city': '',
            'country': ''
        }
        
        # Try to match USA format: "123 Broadway Ave, New York, NY 10001, USA"
        usa_match = re.search(patterns['usa'], address, re.IGNORECASE)
        if usa_match:
            result['street_number'] = usa_match.group(1)
            result['street_name'] = f"{usa_match.group(2)} {usa_match.group(3)}"
            result['city'] = usa_match.group(4)
            result['country'] = usa_match.group(5)
            return result
        
        # Try to match European formats: "Calle Mayor 123, Madrid, Spain"
        euro_match = re.search(patterns['europe'], address)
        if euro_match:
            result['street_name'] = euro_match.group(1)
            result['street_number'] = euro_match.group(2) or ""
            result['city'] = euro_match.group(3) or ""
            result['country'] = euro_match.group(4) or ""
            return result
        
        # Fallback: simple comma-split approach
        parts = address.split(',')
        if len(parts) >= 2:
            street_part = parts[0].strip()
            last_part = parts[-1].strip()
            
            # Guess based on position
            if any(word in last_part.lower() for word in ['spain', 'бразили', 'россия', 'франция']):
                result['country'] = last_part
                result['city'] = parts[-2].strip() if len(parts) >= 3 else ""
                result['street_name'] = re.sub(r'\d+', '', street_part).strip()
                result['street_number'] = re.search(r'\d+', street_part).group() if re.search(r'\d+', street_part) else ""
            else:
                result['city'] = last_part if any(c.isupper() for c in last_part) else parts[0].strip()
                result['street_name'] = street_part.replace(result['city'], '').strip()
                result['street_number'] = re.search(r'\d+', street_part).group() if re.search(r'\d+', street_part) else ""
                result['country'] = self._detect_country(result['city'])
        
        return result
    
    def _find_alternative_city(self, country: str, exclude_city: str = None) -> str:
        """Get a different city from same country"""
        if country not in VALID_CITIES_BY_COUNTRY:
            return "Some Other City"
        
        cities = VALID_CITIES_BY_COUNTRY[country]
        filtered_cities = [c for c in cities if c != exclude_city]
        return filtered_cities[0] if filtered_cities else cities[0]
    
    def _generate_new_street(self, street_name: str, street_number: str, city: str, country: str) -> str:
        """Generate new street address keeping same city"""
        
        if country not in STREET_POOLS:
            # Unknown country - use generic
            streets = ["Maple Street", "Oak Avenue", "Pine Road"]
        else:
            streets = STREET_POOLS[country]
        
        new_street = streets[hashlib.md5(street_name.encode()).hexdigest()[:4]]
        new_number = str(int(street_number) + hash(hashlib.md5(city.encode()).hexdigest()) % 999)
        
        return f"{new_street} {new_number}"
    
    def transform(self, row: dict, column_name: str, table_name: str) -> dict:
        """Transform address field preserving city consistency"""
        
        original_address = row.get(column_name)
        if not original_address or original_address == "":
            return row
        
        # Check existing mapping for consistency
        entity_key = f"{table_name}:{column_name}:{hashlib.sha256(original_address.encode()).hexdigest()[:16]}"
        if entity_key in self.address_mapping:
            row[column_name] = self.address_mapping[entity_key]
            return row
        
        # Parse address into parts
        parts = self._extract_address_parts(original_address)
        
        city = parts['city']
        country = parts['country']
        
        # If city detection failed, try to infer from country
        if not city and country:
            city = self._find_alternative_city(country)
        
        # Generate new address
        new_street = self._generate_new_street(
            parts['street_name'],
            parts['street_number'],
            city,
            country
        )
        
        # Reconstruct full address
        if country:
            new_address = f"{new_street}, {city}, {country}"
        else:
            new_address = new_street
        
        # Save mapping for consistency
        self.address_mapping[entity_key] = new_address
        row[column_name] = new_address
        
        return row
    
    def save_mapping(self, output_path: str):
        """Save address mapping"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({"address_mapping": self.address_mapping}, f, indent=2, ensure_ascii=False)
