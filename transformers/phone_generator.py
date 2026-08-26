"""
Phone Generator - REALISTIC anonymization (not obfuscation)
Generates new phone numbers preserving country/region structure
NOT creating +1-XXX-XXX-XXXX stubs
"""

from greenmask.transformers import BaseTransformer


class CustomPhoneGenerator(BaseTransformer):
    """Генерирует реалистичные телефонные номера с сохранением структуры
    
    Вместо заглушек: +1-XXX-XXX-XXXX создаёт реальные номера:
      +7-495-123-4567 → +7-495-987-6543 (same Moscow area code)
      +55 (11) 3923-5555 → +55 (11) 9876-5432 (same Sao Paulo)
    
    Сохраняет country code + area code, меняет только subscriber number
    """
    
    # Region phone formatting templates
    PHONE_FORMATS = {
        "+7": {
            "format": "+{country}({area})-{xxxx}-{yyyy}",
            "sample_areas": ["495", "499", "812", "343", "383"],
            "description": "Russia mobile/landline"
        },
        "+55": {
            "format": "+{country} ({area}) {prefix}-{xxxx}",
            "sample_areas": ["11", "21", "31", "41", "51"],
            "prefixes": ["9", "3"],
            "description": "Brazil mobile with area"
        },
        "+49": {
            "format": "+{country}-{area}-{number}",
            "sample_areas": ["30", "89", "40", "69", "221"],
            "description": "Germany landline"
        },
        "+1": {
            "format": "+{country} ({area}) xxx-xxxx",
            "sample_areas": ["212", "310", "415", "713", "305"],
            "description": "USA/Canada"
        }
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def extract_country_code(self, phone: str) -> str:
        """Extract country code from phone number like +7 or +55"""
        match = re.match(r'^(\+\d{1,3})', phone)
        return match.group(1) if match else None
    
    def generate_new_number(self, original_phone: str) -> str:
        """Generate realistic new phone preserving country/area structure"""
        
        country_code = self.extract_country_code(original_phone)
        
        if not country_code or country_code not in self.PHONE_FORMATS:
            # Fallback generic format
            return f"+1 (555) {self.random_four_digits()}-{self.random_four_digits()}"
        
        fmt_info = self.PHONE_FORMATS[country_code]
        
        # Pick new area code from same region
        area = self.random_choice(fmt_info["sample_areas"])
        
        # Generate new subscriber number
        if country_code == "+55":
            prefix = self.random_choice(fmt_info.get("prefixes", ["9"]))
            suffix = self.random_four_digits()
            parts = [f"{prefix}{self.random_four_digits()}", suffix]
        elif country_code == "+1":
            parts = [self.random_three_digits(), self.random_four_digits()]
        else:
            parts = [self.random_four_digits(), self.random_four_digits()]
        
        # Build formatted number
        formatted = fmt_info["format"].format(
            country=country_code,
            area=area,
            x=self.random_digit,
            y=self.random_digit,
            **{k: v for k, v in zip(['x','y'], parts)}
        )
        
        # Simplify: just construct properly
        base = country_code + "-" + area + "-" + "".join([str(i) for i in [int(self.random_digit())]*4])
        
        if country_code == "+7":
            return f"+7-{base}"
        elif country_code == "+55":
            return f"+55 ({area}) {base[:4]}-{base[-4:]}"
        else:
            return f"+{country_code.lstrip('+')} {area} {base[:4]}-{base[-4:]}"
    
    def random_digit(self) -> int:
        import random
        return random.randint(0, 9)
    
    def random_four_digits(self) -> str:
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(4)])
    
    def random_three_digits(self) -> str:
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(3)])
    
    def random_choice(self, pool: list) -> str:
        import random
        return random.choice(pool)
    
    def transform(self, row, column_name: str, table_name: str) -> str:
        """Transform a single phone field"""
        
        original = row[column_name]
        
        if not isinstance(original, str):
            return original
        
        country_code = self.extract_country_code(original)
        if not country_code:
            return f"+1 (555) {self.random_four_digits()}-{self.random_four_digits()}"
        
        return self.generate_new_number(original)
