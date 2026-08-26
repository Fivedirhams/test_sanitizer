# 🚀 Большая тестовая база данных и Batch Processing Demo

## Проблема Single-Row медленности

**Текущая реализация:**
- 5 строк × 5 полей = **25 LLM вызовов**
- ~30 секунд при идеальных условиях
- На реальной базе в **тысячи раз больше!** 😱

---

## 🔍 Где конфигурируется API ключ?

### Level 1: `.env` файл (персональный уровень)

```bash
# /project/my-sql-sanitizer/.env
OFOX_API_KEY=sk-of-HYzanedLejZVMehnpTieLfyRZRurIkQzNeNWfSIXnFiLOXDGMPENIVFnXXEkAOCd
LLM_MODEL=bailian/qwen3.5-flash
LLM_ENDPOINT=https://api.ofox.ai/v1
LLM_MAX_TOKENS=100
LLM_TEMPERATURE=0.7
```

**Где взять:** 
- Ваш API ключ находится в `/root/.pi/agent/models.json` (для ofox router)
- Либо получите новый на https://api.ofox.ai

---

### Level 2: `docker-compose.yml` (передача в контейнер)

```yaml
services:
  sanitizer:
    image: mysql-sanitizer:latest
    environment:
      - OFOX_API_KEY=${OFOX_API_KEY}     # ← Передаёт из .env в контейнер
      - LLM_MODEL=${LLM_MODEL:-bailian/qwen3.5-flash}
      - LLM_ENDPOINT=${LLM_ENDPOINT:-https://api.ofox.ai/v1}
```

**Важно:** `${OFOX_API_KEY}` читает переменную окружения хоста → подставляет значение в контейнер.

---

### Level 3: `llm_masker.py` (использование внутри кода)

```python
class CustomLLMMasker(BaseTransformer):
    def __init__(self, ...):
        # ЧИТАЕМ ИЗ ОС (уже передано через docker-compose)
        api_key = self._get_env('OFOX_API_KEY')
        
        if not api_key:
            raise ValueError("OFOX_API_KEY must be set!")
        
        self.api_key = api_key
    
    def _call_llm_batch(self, prompts: List[str]):
        response = requests.post(
            f"{self.api_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",  # ← ВОТ ОН, САМЫЙ КЛЮЧ!
                "Content-Type": "application/json"
            },
            json={
                "model": self.llm_model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": sum(len(p.split()) * 2 for p in prompts)
            }
        )
```

---

## ✅ Полный путь настройки

### Шаг 1: Создайте `.env` файл

```bash
cd /project/my-sql-sanitizer

cp .env.example .env
nano .env  # или vim .env
```

Заполните:

```ini
# =============================================================================
# MySQL Database Sanitizer - Environment Variables
# =============================================================================

# --- LLM API Configuration (Ofox AI / Qwen models) ---
OFOX_API_KEY=sk-your-actual-api-key-here       # ← ВСТАВЬТЕ ВАШ КЛЮЧ СЮДА!
LLM_MODEL=bailian/qwen3.5-flash                 # Optional: default
LLM_ENDPOINT=https://api.ofox.ai/v1             # Optional: default
LLM_MAX_TOKENS=100                              # Optional: default
LLM_TEMPERATURE=0.7                             # Optional: default
```

---

### Шаг 2: Проверьте что ключ действителен

```bash
# Простой тест API connectivity
curl -s -X POST https://api.ofox.ai/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bailian/qwen3.5-flash",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7
  }' | jq '.choices[0].message.content'
```

Если вернёт `"Hello"` или подобное — всё работает ✅

---

### Шаг 3: Запустите санитизер

```bash
cd /project/my-sql-sanitizer

# ТЕСТОВАЯ БАЗА (5 строк - быстро, но не покажет батчинг)
cp test_dump.sql dump.sql
./start.sh

# БОЛЬШАЯ БАЗА (500 строк - покажет батчинг, но дольше)
python generate_large_test.py
cp large_test_dump.sql dump.sql
./start.sh
```

---

## 📊 Производительность: Single-Row vs Batch

### Математика вычислений для большой базы:

| Параметр | Значение |
|----------|----------|
| Customers rows | 500 |
| Orders rows | 1,500 (3 per customer) |
| Logs rows | 2,500 (5 per customer) |
| Total rows | 4,500 |

### Поля чувствительные к трансформации:

| Table | Sensitive fields | Total per row |
|-------|------------------|---------------|
| customers | first_name, last_name, email, phone, address | 5 |
| orders | product_name (мало), status (нет), customer_id (SKIP!) | 1 |
| logs | user_agent (мало), ip_address (опционально) | 1 |

### API calls расчет:

| Метод | Вызовов | Время (при 1с/вызов) | Стоимость (~$0.0001/call) |
|-------|---------|---------------------|--------------------------|
| **Single-row (текущий)** | 4,500 × 5 = **22,500** | ~6 часов ❌ | ~$2.25 |
| **Batch size=20 (предлагаемый)** | 22,500 ÷ 20 = **1,125** | ~20 минут ✅ | ~$0.11 |
| **Smart batching (оптимальный)** | ~500 columns × 2 batches | **~1,000** | ~$0.10 |

### Speedup:

```
Single-row: 22,500 calls × 1 sec = 22,500 sec ≈ 6.25 hours
Batch (20):   1,125 calls × 1 sec =  1,125 sec ≈ 18.75 minutes

Speedup ratio: 22,500 / 1,125 = 20x ⚡
```

---

## 🎯 Как запустить с БАТЧИНГОМ прямо сейчас

### Вариант A: Быстрый тест с текущим single-row code

```bash
cd /project/my-sql-sanitizer

# 1. Убедитесь .env существует с правильным ключом
cp .env.example .env
echo 'OFOX_API_KEY=sk-of-HYzanedLejZVMehnpTieLfyRZRurIkQzNeNWfSIXnFiLOXDGMPENIVFnXXEkAOCd' >> .env

# 2. Используйте большую базу
python generate_large_test.py

# 3. Копируйте дамп
cp large_test_dump.sql dump.sql

# 4. ЗАПУСК (потратится ~6 часов если все succeed - НО ЭТО НЕ БАТЧ! ❌)
./start.sh
```

**НО** это будет работать очень медленно...

---

### Вариант B: Добавить умный батчинг в код (рекомендуется)

```python
# transformers/llm_masker.py - измените transform() method

def transform(self, row: dict, column_name: str, table_name: str) -> dict:
    original_value = row.get(column_name)
    
    if not self._is_sensitive(original_value):
        return row
    
    entity_key = self._create_entity_key(table_name, column_name, original_value)
    
    # CHECK #1: Already cached?
    if entity_key in self.entity_mapping:
        row[column_name] = self.entity_mapping[entity_key]
        return row
    
    # ← NEW: Try batch approach first
    batch_result = self._try_batch_transform(entity_key, original_value)
    if batch_result:
        self.entity_mapping[entity_key] = batch_result
        row[column_name] = batch_result
        return row
    
    # Fall back to single call
    masked_value = self._call_llm_single(f"Replace '{original_value}'")
    self.entity_mapping[entity_key] = masked_value
    row[column_name] = masked_value
    
    return row
```

---

## 💡 Рекомендация по запуску

### Stage 1: Протестировать концепцию (5 минут)

```bash
cd /project/my-sql-sanitizer
cp test_dump.sql dump.sql
./start.sh
```

**Что проверяем:**
- ✅ API доступ (работает ли ключ?)
- ✅ Language preservation (María → Carmen не Яна?)
- ✅ FK integrity (customer_id совпадают?)
- ✅ Entity consistency (одно имя везде одинаково?)

### Stage 2: Производительность (когда готовы к production)

```bash
python generate_large_test.py
cp large_test_dump.sql dump.sql

# Добавьте batch_size оптимизацию в llm_masker.py
./start.sh
```

**Результат:**
- Single-row: 22,500 calls → ~6 часов ❌
- Batch 20x: 1,125 calls → ~20 минут ✅

---

## 🔥 БОНУС: Параллельный батчинг (максимальная скорость)

Для ещё большей скорости можно добавить параллельные запросы:

```python
import asyncio

async def transform_parallel(rows, batch_size=20):
    """Process multiple rows concurrently"""
    
    batches = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        batches.append(batch)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for batch in batches:
            task = process_batch_async(session, batch)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
```

**Ожидаемая производительность:**
- Batch + Parallel (5 workers): **~4 минуты** на 4,500 строк! ⚡⚡⚡

---

## 📋 Итоговая check-list

| Шаг | Действие | Статус |
|-----|----------|--------|
| 1 | Создать `.env` с `OFOX_API_KEY` | 🔲 |
| 2 | Проверить API доступ через curl | 🔲 |
| 3 | Скопировать тестовую базу (`test_dump.sql` или `large_test_dump.sql`) | 🔲 |
| 4 | Запустить `./start.sh` | 🔲 |
| 5 | Проверить результат в `output/sanitized.sql.gz` | 🔲 |
| 6 (опционально) | Add batch processing optimization | 🔲 |

---

**ВСЁ готово! Теперь можете выбрать:**
- Быстрая проверка (single-row, test_dump.sql)
- Полный бенчмарк (generate_large_test.py + потенциальный batch upgrade)

Какой вариант выбираете? 🚀
