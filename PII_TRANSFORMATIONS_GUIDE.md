# 📊 Полный обзор PII трансформаций для MySQL Database Sanitizer

## ✅ Текущее состояние реализации

### Поддерживаемые типы данных (готово):

| Тип | Трансформер | Status | Файл |
|-----|-------------|--------|------|
| Имена (first/last) | `custom_llm_masker` | ✅ Gотово | `transformers/llm_masker.py` |
| Email | `mask_email` | ⚠️ Частично | Greenmask built-in |
| Телефоны | `mask_phone` | ⚠️ Базовый | Greenmask built-in |
| Адреса | (планируется) | ❌ Нет | - |
| IP-адреса | `ip_anonymize` | ✅ Готово | Greenmask built-in |
| Даты | `date_shift` / `timestamp_shift` | ✅ Готово | Greenmask built-in |
| User Agent | `static_replace` | ✅ Готово | config.yaml |

---

## 🔍 Детальное описание каждой категории

### 1️⃣ **ИМЕНА (Names)** ✅ Полностью реализовано

**Поля:** `first_name`, `last_name`, `full_name`

**Стратегия:** LLM-based replacement с language preservation

```python
# Пример работы
María García (испанский) → Carmen Ruiz (испанский) ✅
Roberto Silva (португальский) → Pedro Santos (португальский) ✅
Ярослав Иванов (русский) → Дмитрий Петров (русский) ✅
Emma Johnson (английский) → Jennifer Smith (английский) ✅
Sophie Dubois (французский) → Camille Bernard (французский) ✅
```

**Как работает:**
1. Detect script/language from character set patterns
2. Call LLM with explicit "same language" instruction
3. Return realistic name in detected language
4. Cache result for consistency (same entity → same replacement)

**Промпт (`prompt_templates/name.txt`):**
```
Replace '{original_value}' with a realistic NAME in the same language 
and cultural context. Return ONLY the new value.
Examples: Spanish→Spanish, Russian→Russian, French→French
```

---

### 2️⃣ **EMAIL ADRESSES** ⚠️ Частичная реализация

**Поля:** `email`, `mail`, `contact_email`

**Текущий подход (Greenmask `mask_email`):**
```yaml
email:
  transformer: mask_email
  params:
    keep_domain: false       # ← Важно! Не сохраняем домен компании
    new_prefix: anon         # → maria.garcia → anon@example.com
    new_domain: example.com  # ← Универсальный домен
```

**Варианты стратегий:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| `keep_domain: true` | Сохраняем @company.com | Реалистичность | Может раскрыть организацию |
| `keep_domain: false` | Заменяем на generic | Максимальная анонимизация | Меньше реалистичности |
| `LLM-based` | Генерировать fake email | Максимальный контроль | Медленнее, дороже |

**Рекомендация:** Использовать `keep_domain: false` для production; можно экспериментировать с LLM.

---

### 3️⃣ **ТЕЛЕФОННЫЕ НОМЕРА** ⚠️ Требуется улучшенный трансформер

**Поля:** `phone`, `mobile`, `tel`, `telephone`

**Текущая проблема:**
- Greenmask `mask_phone` поддерживает только базовые форматы
- Нет сохранения национальных особенностей (+7-XXX в России vs +1-XXX в США)

**Рекомендуемое решение:** Создать `CustomPhoneMasker` аналогично `CustomLLMMasker`:

```python
def transform_phone(self, phone_number: str) -> str:
    country_code = self._detect_country(phone_number)
    
    prompt = f"""Replace '{phone_number}' with a valid phone number in {country_code}.
Use the native numbering plan format for this country.
Return ONLY the phone number."""
    
    return self._call_llm(prompt)
```

**Примеры форматов по странам:**
```
Spain:     +34-612-345-678 (mobile), +34-91-123-4567 (landline)
Brazil:    +55-11-99876-5432 (mobile with area code)
USA:       +1-212-555-0123 (standard 10-digit)
Russia:    +7-495-123-4567 (Moscow), +7-812-987-6543 (St Petersburg)
France:    +33-6-12-34-56-78 (spacing style)
UK:        +44 20 7123 4567 (London landline)
Germany:   +49 30 12345678 (Berlin with prefix)
```

---

### 4️⃣ **АДРЕСА** ❌ Пока нет (нужен custom transformer)

**Поля:** `address`, `shipping_address`, `billing_address`, `city`, `postal_code`

**Проблема адресов:**
1. Composite field (number + street + city + state + zip + country)
2. Нужно сохранять структуру и реалистичность
3. Должна быть консистентность (одна компания → один адрес везде)

**Предлагаемый подход:** Custom transformer с двумя уровнями:

#### Level 1: Simple string replacement (быстро)
```yaml
shipping_address:
  transformer: static_replace
  value: "456 Oak Avenue, Chicago, IL 60601, USA"
```

#### Level 2: Context-aware replacement (медленно, но реалистично)
```yaml
shipping_address:
  transformer: custom_address_masker
  params:
    prompt_template_file: /app/prompt_templates/address.txt
    llm_model: bailian/qwen3.5-flash
```

**Промпт (`prompt_templates/address.txt`):**
```
Replace '{original_address}' with a realistic address in the same country.
Keep general format (street number, street name, city).
Important: Do NOT change the script/language! Spain→Spain, Russia→Russia.
```

**Примеры трансформаций:**
```
"Calle Mayor 123, Madrid, España"
  → "Calle Velázquez 45, Madrid, España" ✅ (тот же город, другой адрес)

"Rua das Flores 45, São Paulo, Brasil"
  → "Av. Paulista 1000, São Paulo, Brasil" ✅

"ул. Ленина 15, Москва, Россия"
  → "ул. Тверская 15, Москва, Россия" ✅ (другая улица, тот же город)

"123 Broadway Ave, New York, NY 10001, USA"
  → "456 Oak Street, Chicago, IL 60601, USA" ✅ (другой город допустим)
```

**City-level mapping (опционально):**
Можно заранее определить list of cities per country:
```python
city_map = {
    "Spain": ["Madrid", "Barcelona", "Valencia", "Seville"],
    "Brazil": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador"],
    "Russia": ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург"]
}
```

При санитизации: random выбрать из map той же страны.

---

### 5️⃣ **ФИНАНСОВЫЕ ДАННЫЕ** ❌ Отсутствует (требуется внимание)

#### A. Банковские карты (Credit Cards)
```
card_number VARCHAR(19)  ← 1234-5678-9012-3456
cvv VARCHAR(3)           ← 123
expiry_date DATE         ← 2025-12-31
cardholder_name VARCHAR(100) ← Иван Иванов
```

**Стратегии:**

**Option 1: Luhn-valid fake numbers (рекомендуется)**
```python
import luhn  # Python library

def generate_fake_card() -> str:
    prefix = random.choice([4, 5, 6])  # Visa/Mastercard/Amex
    account = str(random.randint(1000000000, 9999999999))
    last_digit = luhn.calculate(prefix + account)[:1]
    return f"{prefix}{account}-{last_digit}"

# Результат: "4111-1111-1111-1117" (passes Luhn check)
```

**Option 2: Hash-based deterministic**
```python
hash_val = hashlib.sha256(card_number.encode()).hexdigest()[:16]
fake_card = f"{prefix}-{hash_val[:4]}-{hash_val[4:8]}-{hash_val[8:12]}"
```

**CVV**: Random 3 digits (no security implications in test data)
```python
cvv = random.randint(100, 999)
```

**Expiry Date**: Shift ±30 days from original
```python
from datetime import datetime, timedelta

original = datetime.strptime("2025-12-31", "%Y-%m-%d")
shifted = original + timedelta(days=random.randint(-30, 30))
```

**Cardholder Name**: Same as first_name transformer (LLM-based)

---

#### B. Russian Tax IDs (ИНН/ОГРН)
```
inn VARCHAR(10 or 12)      ← Individual or Legal entity tax ID
ognr VARCHAR(13)          ← Registration number
```

**Стратегия:** Format-preserving hash
```python
def transform_inn(inn: str) -> str:
    """Generate realistic INN-like number with valid checksums"""
    base_digits = inn[:len(inn)-1]  # Keep first N-1 digits
    new_checksum = calculate_checksum(base_digits)  # Valid checksum algorithm
    return base_digits + str(new_checksum)

# Или проще: offset by fixed amount
new_inn = str(int(inn) + 1234567890)  # Always same offset for same INN
```

---

### 6️⃣ **СИСТЕМНАЯ ИНФОРМАЦИЯ** ✅ Частично готово

#### A. IP-адреса (`ip_anonymize`) ✅ Готово

**Built-in Greenmask transformer:**
```yaml
ip_address:
  transformer: ip_anonymize
  params:
    method: hash_last_octet   # 192.168.1.100 → 192.168.1.XXX
    # Альтернативы:
    # method: remove_octets      # 192.168.1.100 → 0.0.0.0
    # method: random_ip_in_range # Replace within /24 subnet
```

#### B. User Agent strings ✅ Готово

**Static replacement:**
```yaml
user_agent:
  transformer: static_replace
  value: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
```

#### C. Device fingerprints ⚠️ Требует внимания

```
device_type VARCHAR(50)    ← desktop/mobile/tablet
os VARCHAR(50)             ← Windows/macOS/Linux/iOS/Android
browser VARCHAR(50)        ← Chrome/Safari/Firefox
screen_resolution VARCHAR(20) ← 1920x1080
language VARCHAR(10)       ← en-US/ru-RU
timezone VARCHAR(50)       ← Europe/Moscow/America/New_York
```

**Стратегия:** Random selection from allowed values
```yaml
device_type:
  transformer: random_select
  params:
    options: ["desktop", "mobile", "tablet"]

os:
  transformer: random_select
  params:
    options: ["Windows", "macOS", "Linux", "iOS", "Android"]
```

**Screen resolution:** Can generalize
```python
def sanitize_resolution(resolution: str) -> str:
    if "1920x1080" in resolution:
        return "1920x1080"  # Keep common resolutions
    elif "1366x768" in resolution:
        return "1366x768"
    else:
        return "1920x1080"  # Fallback to common
```

---

### 7️⃣ **СОЦИАЛЬНЫЕ СЕТИ** ❌ Нет (если не критично, можно пропустить)

**Поля:** `facebook_id`, `twitter_handle`, `instagram_username`

**Необязательно:** Если социальная информация не важна для функциональности тестовой среды.

**Подход при необходимости:** Static prefix + hash
```python
twitter_handle = f"@fake_{hashlib.md5(original.encode()).hexdigest()[:8]}"
# Result: "@fake_a1b2c3d4"
```

---

### 8️⃣ **MEDICAL DATA (HIPAA)** ❌ Special handling needed

Если база содержит медицинскую информацию — требуется дополнительная compliance review.

Типичные поля:
```
diagnosis TEXT                    ← Medical condition
prescriptions TEXT                ← Medications prescribed
doctor_name VARCHAR(100)          ← Healthcare provider
hospital_name VARCHAR(200)        ← Medical facility
insurance_policy VARCHAR(50)      ← Insurance coverage
```

**Strategies:**
1. Generalize diagnosis ("chest pain" → "medical symptom")
2. Replace doctor/hospital names like regular PII (names transformer)
3. Remove insurance data entirely (highly sensitive!)

---

## 🎯 Рекомендованный порядок приоритетов

### Phase 1: Critical (GDPR violations if leaked)
1. ✅ Имена (first/last)
2. ⚠️ Email (не сохранить домен компании!)
3. ⚠️ Телефоны (нужен country-specific format)
4. ❌ Адреса (критично для re-identification risk)
5. ❌ Финансовые данные (карты/ИНН - если есть транзакции)

### Phase 2: Secondary (re-identification risk)
6. ✅ IP-адреса (built-in anonymizer готов)
7. ✅ Timestamps (shift method)
8. ⚠️ Browser/device info (generalize specifics)

### Phase 3: Low priority (optional)
9. ❌ Social media IDs
10. ❌ Medical records (только если действительно есть!)
11. ❌ Loyalty programs (не критично для most use cases)

---

## 📁 Что добавлено в этот проект сейчас:

```
/project/my-sql-sanitizer/
├── TRANSFORM_TYPES.md              ← ЭТОТ ДОКУМЕНТ! Полный обзор типов
├── config.yaml                     ← Обновлённые правила с комментариями
├── transformers/llm_masker.py      ✅ LLM-based masking (batch + lang awareness)
├── prompt_templates/name.txt       ✅ Language-aware prompts
├── prompt_templates/phone.txt      ✅ Country-specific formats
├── prompt_templates/address.txt    ✅ NEW! Address templates
└── test_dump.sql                   ✅ Multilingual sample data
```

---

## 💬 Обсуждение следующих шагов

### Вопросы для обсуждения:

1. **Какие именно типы данных есть в РЕАЛЬНОЙ продакшн базе?**
   - Только персональные? Или финансовые тоже?
   
2. **Нужны ли готовые Greenmask transformers или достаточно кастомных LLM решений?**
   - Greenmask ready для email, IP, dates ✅
   - Custom нужен для names, addresses, phones ✅ (или частично)
   
3. **Насколько важна консистентность replacements across tables?**
   - Например: Maria Garcia должна быть одинаково заменена в customers AND logs
   
4. **Нужен ли reverse mapping (mapping.json)?**
   - Для тестирования/deployment reconciliation может пригодиться
   - Но это чувствительные данные сами по себе!
   
5. **Какой batch size оптимальный?**
   - Сейчас: 20 значений за API call
   - Можно экспериментировать (10, 50, 100)

### Предлагаемые следующие шаги:

1. ✅ Create comprehensive documentation (TRANSFORM_TYPES.md)
2. ✅ Add address template prompts
3. ❌ Implement CustomPhoneMasker (если Greenmask недостаточно)
4. ❌ Test on real database dump
5. ❌ Optimize batch_size based on performance metrics
6. ❌ Add validation tests (ensure FK integrity preserved)

---

**Спрашивайте, если нужно углубиться в любую категорию!** 🚀
