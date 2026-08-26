# 📋 Полный обзор типов данных для санитизации

## 🎯 Категории PII (Personally Identifiable Information)

### 1️⃣ **Персональные имена** ✅ Уже есть
| Тип | Пример | Стратегия | Transformer |
|-----|--------|-----------|-------------|
| `first_name` | María García | LLM replacement (same language) | `custom_llm_masker` |
| `last_name` | Иванов | LLM replacement (same script) | `custom_llm_masker` |
| `full_name` | Роберто Silva | LLM → "Juan Pérez" / "Carlos Santos" | `custom_llm_masker` |

**Плюсы:**
- Сохраняет культурный контекст (испанское имя → испанское)
- Консистентная замена (одно имя = одна замена везде)

---

### 2️⃣ **Контактная информация** ⚠️ Частично
#### A. Email addresses ✅
```yaml
email:
  transformer: mask_email
  params:
    keep_domain: false       # ← Важно! НЕ сохраняем домен
    new_prefix: anon         # marcia.garcia → anon@example.com
    new_domain: example.com
```

#### B. Телефоны ⚠️ 
**Вопрос:** Готовые Greenmask transformers (`mask_phone`) работают?

Проверим что они умеют:
```yaml
phone:
  transformer: mask_phone
  params:
    country_code: "+7"        # ← Фиксируем код страны
    format: international     # +7-XXX-XXX-XX-XX
```

**Проблемы с готовыми transformers:**
1. Могут не поддерживать кастомные форматы
2. Нет сохранения исторических номеров
3. Не сохраняют консистентность

**Рекомендация:** Сделать свой `CustomPhoneMasker` аналогично `CustomLLMMasker`

---

### 3️⃣ **Адреса и локации** ❌ НЕТ ПРАВИЛ СЕЙЧАС

#### A. Уличные адреса
```
Текущие поля:
- address VARCHAR(200)          ← Calle Mayor 123
- city VARCHAR(50)              ← Москва / Madrid / São Paulo
- country VARCHAR(50)           ← Russia / Spain / Brazil
- shipping_address VARCHAR(200) ← Composite field
```

**Что делать:**

| Поле | Рекомендация | Transformer |
|------|--------------|-------------|
| `address` | Заменить на реальный адрес другого человека (консистентно!) | `custom_llm_masker` |
| `city` | Заменить на другой город той же страны | `custom_llm_masker` или `static_list` |
| `country` | Можно оставить как есть! (не персональный) | — |
| `postal_code` | Заменить на индекс другого города в стране | `custom_llm_masker` |
| `latitude`/`longitude` | Ошибка! Нельзя просто маскировать — сломается геолокация | — |

#### B. Географические координаты ⚠️
```sql
CREATE TABLE locations (
    location_id INT,
    latitude DECIMAL(10,8),      ← 48.8566° N (Paris)
    longitude DECIMAL(11,8),     ← 2.3522° E (Paris)
    altitude DECIMAL(8,4),       ← meters above sea level
);
```

**Неправильный подход:**
```python
# ❌ Просто заменять: 48.8566 → random_number
# Результат: координаты будут в Австралии 😱
```

**Правильный подход:**
1. Использовать смещение: `lat + (-0.5 to +0.5)` degrees
2. Или заменить на ближайший городской центр
3. Или удалить (если не критично)

---

### 4️⃣ **Финансовые идентификаторы** ❌ НЕТ

#### A. Инн/ОгРН/Russian Tax IDs
```
ИНН (Tax ID): 772312345678 (10 or 12 digits)
ОГРН (Registration ID): 1157700123456
```

**Стратегии:**
1. **LLM Replacement** → "123456789012" (сохранить формат)
2. **Deterministic hash** → SHA256(value)[:8] → всегда одинаковый для одного ИНН
3. **Shift method** → INN + 123456789 (всегда одинаково)

#### B. Банковские карты
```
card_number VARCHAR(19)  ← 1234-5678-9012-3456
cvv VARCHAR(3)           ← 123
expiry_date DATE         ← 2025-12-31
cardholder_name VARCHAR(100) ← Имя владельца (как first_name?)
```

**Стратегии:**
- `card_number`: `f"{prefix:04}-{hash[:4]}-{hash[:4]}-{hash[:4]}"`
- `cvv`: `random.random.randint(100,999)`
- `expiry_date`: сдвинуть на ±30 дней
- `cardholder_name`: тот же LLM что для first_name

#### C. Паспортные данные
```
passport_series INT      ← Серия (1234)
passport_number INT      ← Номер (567890)
issue_date DATE          ← Дата выдачи
issued_by VARCHAR(200)   ← Кем выдан
```

---

### 5️⃣ **Цифровые идентификаторы** ❌ НЕТ

#### A. Пользовательские ID (не PK)
```
user_id VARCHAR(50)      ← UUID: "550e8400-e29b-41d4-a716-446655440000"
session_id VARCHAR(100)  ← Random session token
api_key VARCHAR(100)     ← API secret key
auth_token VARCHAR(200)  ← JWT token
```

**Стратегии:**
- UUID: `uuid.uuid4()` (новые UUID)
- Session/API keys: regenerate with same length

#### B. Телефонные номера (уже обсудили выше) ✅

---

### 6️⃣ **Системная информация** ❌ НЕТ

#### A. IP-адреса ⚠️ 
```
ip_address VARCHAR(45)  ← IPv4: "192.168.1.100", IPv6: "::1"
```

**Готовое решение Greenmask:**
```yaml
ip_address:
  transformer: ip_anonymize
  params:
    method: hash_last_octet  # 192.168.1.100 → 192.168.1.XXXX
```

**Альтернативы:**
- `method: remove_octets` (полное удаление)
- `method: random_ip_in_range` (замена в пределах подсети)

#### B. User Agent strings
```
user_agent TEXT  ← "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/..."
```

**Стратегии:**
1. **Static replacement** → "Mozilla/5.0 (Browser)"
2. **LLM replacement** → Generate realistic but fake user agent
3. **Remove fields** → Set to NULL

#### C. Device fingerprints
```
device_type VARCHAR(50)    ← desktop/mobile/tablet
os VARCHAR(50)             ← Windows/MacOS/Linux/iOS/Android
browser VARCHAR(50)        ← Chrome/Safari/Firefox
screen_resolution VARCHAR(20) ← 1920x1080
language VARCHAR(10)       ← en-US, ru-RU
timezone VARCHAR(50)       ← Europe/Moscow, America/New_York
```

**Стратегии:**
- Keep generic categories ("desktop", "Windows")
- Remove specific identifiers ("Chrome/120.0.6099.109")

---

### 7️⃣ **Социальные сети и онлайн-аккаунты** ❌ НЕТ

#### A. Social Media IDs
```
facebook_id VARCHAR(50)     ← "john.doe.123"
twitter_handle VARCHAR(30)  ← "@janedoe"
instagram_username VARCHAR(30) ← "jane.doe_official"
linkedin_url VARCHAR(200)   ← "linkedin.com/in/johndoe"
```

**Стратегии:**
- LLM replacement with consistent pseudonyms
- Add prefix: "fake_john_doe_123"

#### B. Email aliases / Nicknames
```
nickname VARCHAR(50)       ← "johnnyboy"
display_name VARCHAR(100)  ← "John D."
username VARCHAR(50)       ← Unique login username
```

---

### 8️⃣ **Медицинская информация (HIPAA)** ⚠️ 

#### A. Diagnosis codes
```
icd10_code VARCHAR(10)     ← "E11.9" (Type 2 Diabetes)
diagnosis TEXT             ← "Patient reports chest pain"
prescriptions TEXT         ← "Amoxicillin 500mg"
doctor_name VARCHAR(100)   ← Dr. Johnson Smith
hospital_name VARCHAR(200) ← Memorial Hospital
```

**Стратегии:**
- Codes: Replace with other valid ICD10 codes
- Diagnoses: Generalize ("chest pain" → "medical symptom")
- Personal names: Same as customer names

#### B. Insurance information
```
insurance_policy VARCHAR(50)   ← Policy number
insurance_provider VARCHAR(100) ← Company name
member_id VARCHAR(50)          ← Member identification
```

---

### 9️⃣ **Транзакции и платежи** ⚠️

#### A. Transaction data
```
transaction_id VARCHAR(50)     ← UUID or sequential
amount DECIMAL(10,2)          ← $1,234.56 (敏感ный!)
currency_code VARCHAR(3)      ← USD/EUR/GBP
payment_method VARCHAR(50)    ← credit_card/bank_transfer/cash
merchant_id VARCHAR(50)       ← Merchant identification
receipt_url VARCHAR(200)      ← URL receipt PDF/image
```

**Стратегии:**
- transaction_id: regnerate UUID
- amount: preserve distribution statistics (mean/variance)
- currency_code: can stay same
- payment_method: static list of options
- merchant_id: hash-based replacement

#### B. Loyalty program data
```
loyalty_member VARCHAR(50)    ← Membership number
points_balance INT            ← Points earned/spent
tier_level VARCHAR(20)        ← Silver/Gold/Platinum
referral_code VARCHAR(30)     ← Referral code used
```

---

### 🔟 **Детская/образовательная информация (COPPA)** ⚠️

#### A. Student records
```
student_id VARCHAR(20)        ← Student identifier
grade_level VARCHAR(10)       ← "3rd grade", "Sophomore"
school_name VARCHAR(200)      ← School name
gpa DECIMAL(4,2)             ← 3.85 (grades are PII in some contexts!)
attendance_rate DECIMAL(5,2)  ← Percentage present
```

---

## 🛠️ Какие Greenmask transformers готовы?

| Transformer | Что делает | Когда использовать |
|-------------|------------|-------------------|
| `mask_email` | Замена email | Везде где есть email |
| `mask_phone` | Замена телефон | Если поддерживаются форматы вашей страны |
| `mask_credit_card` | Заменяет CC | Финансовые транзакции |
| `mask_bank_account` | IBAN/BIC | Банковские реквизиты |
| `ip_anonymize` | Анонимизация IP | Системные логи, аналитика |
| `date_shift` | Сдвиг даты | birth_date, created_at |
| `timestamp_shift` | Сдвиг timestamp | Все временные метки |
| `static_replace` | Жёсткая замена | Адреса с повторяющимися паттернами |
| `random_values` | Random из набора | City, Country lists |
| `nullifier` | Ставит NULL | Удаление sensitive data |

---

## 📊 Комбинированные стратегии

### 1. Composite fields (адрес целиком)
```sql
shipping_address = "123 Main St, New York, NY 10001, USA"
```

**Подход:**
1. Parse into parts: address + city + state + zip + country
2. Transform each part with appropriate transformer
3. Reconstruct string

**Или проще:**
- LLM replacement: "456 Oak Ave, Chicago, IL 60601, USA"

### 2. Referential integrity (PK/FK связи)
```sql
-- BEFORE
customers.customer_id: 1 → orders.customer_id: 1

-- AFTER (без маппинга)
customers.customer_id: 1 → orders.customer_id: 999  ← BROKEN FK!

-- AFTER (с маппингом)
customers.customer_id: 1 → customers.customer_id: 1  ← SAME!
                  ↓                               ↓
orders.customer_id: 1 → orders.customer_id: 1  ← PRESERVED!
```

---

## 🎯 Рекомендации по приоритетам

### Priority 1: Critical PII (GDPR/HIPAA violations if leaked)
- [ ] Имена (already done ✅)
- [ ] Email addresses (partially done ⚠️)
- [ ] Phone numbers (need improvement ⚠️)
- [ ] Addresses (NOT DONE ❌)
- [ ] Payment info (NOT DONE ❌)
- [ ] Medical records (NOT DONE ❌)

### Priority 2: Indirect identifiers (re-identification risk)
- [ ] IP addresses (Greenmask built-in ✅)
- [ ] Timestamps (Greenmask shift ✅)
- [ ] Browser/device fingerprint (NOT DONE ❌)

### Priority 3: Quasi-identifiers (de-anonymization risk)
- [ ] Postal codes (combination attack ⚠️)
- [ ] Birth dates (do not mask? too obvious ⚠️)
- [ ] Geographic coordinates (critical for privacy ⚠️)

---

## 💡 Заключение

**Текущий статус проекта:**

| Категория | Статус | Требуется доработка |
|-----------|--------|---------------------|
| Персональные имена | ✅ Реализовано | Нет |
| Email | ⚠️ Частично | Добавить новый домен |
| Телефоны | ⚠️ Частично | Custom transformer? |
| Адреса | ❌ Отсутствуют | Custom transformer |
| Геолокация | ❌ Отсутствует | Special handling needed |
| Финансы (карты/ИНН) | ❌ Отсутствуют | Need custom transformers |
| Цифровые ID (UUID/session) | ❌ Отсутствуют | Simple UUID regenerator |
| Системы/IP/UA | ⚠️ Часть есть | IP anonymize (greenmask) |
| Соцсети/онлайн | ❌ Отсутствуют | Optional |
| Медицина | ❌ Отсутствуют | Domain-specific |
| Транзакции | ❌ Отсутствуют | Financial masking |

**Следующие шаги:**
1. Определить какие данные есть в РЕАЛЬНОЙ базе
2. Создать transformers для недостающих типов
3. Настроить правила в config.yaml
4. Тестировать на тестовой базе
5. Production deploy
