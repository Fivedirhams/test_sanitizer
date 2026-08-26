"""
Custom LLM-based transformer for Greenmask.
Поддерживает сохранение маппинга для обратной совместимости.
"""

from greenmask.transformers import BaseTransformer
import os
import json
import hashlib
import requests
from typing import Optional, Any


class CustomLLMMasker(BaseTransformer):
    """Кастомный трансформер на базе LLM для замены чувствительных данных
    
    Чтение переменных окружения:
        - OFOX_API_KEY: API key для ofox.ai (обязательно)
        - LLM_ENDPOINT: Endpoint API (по умолчанию https://api.ofox.ai/v1)
        - LLM_MODEL: Модель (по умолчанию bailian/qwen3.5-flash)
        - LLM_MAX_TOKENS: Max tokens in response (по умолчанию 100)
        - LLM_TEMPERATURE: Temperature parameter (по умолчанию 0.7)
        - MAPPING_PATH: Путь для сохранения маппинга (опционально)
    """
    
    def __init__(
        self,
        *args,
        prompt_template_file: str,
        llm_model: Optional[str] = None,
        mapping_path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        # --- Чтение из параметров config.yaml ---
        self.prompt_template = self._load_prompt_template(prompt_template_file)
        self.llm_model = llm_model or self._get_env('LLM_MODEL', 'bailian/qwen3.5-flash')
        self.api_base_url = self._get_env('LLM_ENDPOINT', 'https://api.ofox.ai/v1')
        self.max_tokens = int(self._get_env('LLM_MAX_TOKENS', '100'))
        self.temperature = float(self._get_env('LLM_TEMPERATURE', '0.7'))
        self.mapping_path = mapping_path
        
        # Поддержка через Greenmask parent class kwargs
        if not self.mapping_path and hasattr(self, '_parent_context'):
            context = getattr(self, '_parent_context', {})
            self.mapping_path = context.get('mapping', {}).get('output_path')
        
        # --- Чтение API ключа из env vars ---
        api_key = self._get_env('OFOX_API_KEY')
        if not api_key:
            raise ValueError(
                "Environment variable OFOX_API_KEY must be set!\n"
                "Add to .env file or pass via -e OFOX_API_KEY=your_key"
            )
        self.api_key = api_key
        
        # Загрузка существующего маппинга при инициализации
        self.entity_mapping: dict = {}
        if mapping_path and os.path.exists(mapping_path):
            with open(mapping_path, 'r') as f:
                data = json.load(f)
                self.entity_mapping = data.get('mapping', {})
    
    def _load_prompt_template(self, template_file: str) -> str:
        """Загрузить шаблон промпта из файла"""
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        else:
            # Дефолтные шаблоны
            return "Замени значение '{original_value}' на случайное русское {field_type}. Верни только новое значение."
    
    def _get_env(self, key: str, default: str = '') -> str:
        """Чтение переменной окружения с fallback к дефолту"""
        return os.environ.get(key, default)
    
    def _create_entity_key(self, table_name: str, column_name: str, value: Any) -> str:
        """Создать уникальный ключ для сущности (для консистентности замен)"""
        return f"{table_name}:{column_name}:{hashlib.sha256(str(value).encode()).hexdigest()}"
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Вызов LLM через ofox API с переменными окружения"""
        try:
            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            # Фоллбек на простую замену при ошибке
            import hashlib
            if original_value:
                return f"[MASKED_{hashlib.md5(str(original_value).encode()).hexdigest()[:8]}]"
            else:
                return "[MASKED]"
    
    def _is_sensitive(self, value: Any) -> bool:
        """Определить, является ли поле чувствительным"""
        if value is None or value == "" or isinstance(value, (int, float)):
            return False
        return True
    
    def transform(self, row: dict, column_name: str, table_name: str) -> dict:
        """Основная функция трансформации"""
        original_value = row.get(column_name)
        
        if not self._is_sensitive(original_value):
            return row
        
        entity_key = self._create_entity_key(table_name, column_name, original_value)
        
        # Проверяем, уже есть маппинг для этой сущности
        if entity_key in self.entity_mapping:
            masked_value = self.entity_mapping[entity_key]
            row[column_name] = masked_value
        else:
            # Формируем промпт
            field_type = self._detect_field_type(column_name)
            prompt = self.prompt_template.format(
                original_value=str(original_value),
                field_type=field_type
            )
            
            # Вызываем LLM
            masked_value = self._call_llm(prompt)
            
            # Сохраняем маппинг
            if masked_value and masked_value != "[ERROR]":
                self.entity_mapping[entity_key] = masked_value
                row[column_name] = masked_value
            else:
                # Если ошибка, используем детерминированную маскировку
                row[column_name] = f"[{field_type}_MASKED_{hashlib.md5(str(original_value).encode()).hexdigest()[:8]}]"
        
        return row
    
    def _detect_field_type(self, column_name: str) -> str:
        """Определяем тип поля для промпта"""
        patterns = {
            'name': ['name', 'first_name', 'last_name', 'full_name'],
            'email address': ['email'],
            'phone number': ['phone', 'mobile', 'tel'],
            'date': ['birth_date', 'dob', 'birthday'],
            'address': ['address', 'shipping_address', 'billing_address']
        }
        
        for field_type, keywords in patterns.items():
            if any(keyword in column_name.lower() for keyword in keywords):
                return field_type
        return "value"
    
    def save_mapping(self):
        """Сохранить маппинг в файл"""
        if self.mapping_path:
            os.makedirs(os.path.dirname(self.mapping_path), exist_ok=True)
            with open(self.mapping_path, 'w') as f:
                json.dump({"mapping": self.entity_mapping}, f, indent=2, ensure_ascii=False)
