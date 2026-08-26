# 🔄 Batch Processing Architecture - Реальная реализация

## ⚠️ Проблема: Single-row vs Batch tension

### Текущее состояние:

```python
# В llm_masker.py
def transform(self, row, column_name, table_name):
    original_value = row.get(column_name)
    
    # ← ЭТО ОДИН ВЫЗОВ НА ОДНО ЗНАЧЕНИЕ
    masked_value = self.transform_single(original_value, field_type)
    
    return masked_value
```

**Problem:** Это НЕ batch processing! Это single-row calls → дорого и медленно.

---

## ✅ РЕАЛЬНЫЙ batch processing architecture

### Подход 1: Column-level batching (Recommended for your case!)

**Как работает:**

```python
class BatchProcessingGreenmask:
    def __init__(self, config_path: str):
        self.column_transformers = {}  # {table.column: transformer}
        self.global_mapping = {}       # {entity_key: masked_value}
    
    def process_database(self, dump_path: str):
        # STEP 1: Read ALL rows from dump first
        all_rows = self.load_rows_from_dump(dump_path)
        
        # STEP 2: Process by COLUMN TYPE (not by row)
        for column_name in unique_column_names(all_rows):
            
            # Extract all values of this column across ALL rows
            batch_values = [row[column_name] for row in all_rows 
                           if column_name in row and row[column_name]]
            
            # ← BATCH API CALL for entire column!
            masked_batch = self.batch_transform_column(
                column_name=column_name,
                values=batch_values,
                global_entity_mapping=self.global_mapping
            )
            
            # Map back to original rows
            for row, masked_value in zip(all_rows, masked_batch):
                row[column_name] = masked_value
        
        # STEP 3: Rebuild SQL with transformed values
        output_sql = self.rebuild_insert_statements(all_rows)
```

**Преимущества:**
- ✅ N значений → только N/BATCH_SIZE API вызовов
- ✅ Консистентность через shared `global_mapping`
- ✅ Memory efficient (один pass по всем данным)

**Недостатки:**
- ❌ Требует read-all-rows перед обработкой
- ❌ Не подходит для streaming/real-time

---

### Подход 2: Streaming batch queue (Best of both worlds!)

**Архитектура:**

```python
import asyncio
from queue import Queue
from threading import Thread

class StreamingBatchProcessor:
    def __init__(self, batch_size: int = 20, max_queue: int = 100):
        self.batch_size = batch_size
        self.queue = Queue(maxsize=max_queue)
        self.results = {}  # entity_key → masked_value
        self.mapping_lock = Lock()
        
        # Start worker threads for parallel processing
        self._start_workers()
    
    def _start_workers(self):
        """Start background workers that process batches"""
        for i in range(5):  # 5 parallel workers
            thread = Thread(target=self._worker_loop, daemon=True)
            thread.start()
    
    def _worker_loop(self):
        while True:
            batch = self.queue.get()
            
            if batch is None:  # Sentinel to stop
                break
            
            # ← PROCESS ENTIRE BATCH IN ONE API CALL
            responses = self._call_llm_batch(batch)
            
            # Map results back
            for i, response in enumerate(responses):
                entity_key = batch[i].entity_key
                masked_value = self._ensure_consistent(entity_key, response)
                
                with self.mapping_lock:
                    self.results[entity_key] = masked_value
    
    def _ensure_consistent(self, entity_key, new_response):
        """Check if already mapped, return consistent value"""
        with self.mapping_lock:
            if entity_key in self.results:
                return self.results[entity_key]  # Return cached value
            
            self.results[entity_key] = new_response
            return new_response
    
    def transform(self, row, column_name, table_name):
        """Called during main processing loop"""
        entity_key = f"{table_name}:{column_name}:{hash(row)}"
        
        # Submit to queue (non-blocking)
        item = {'entity_key': entity_key, 'value': row[column_name]}
        self.queue.put(item)
        
        # Wait for result (blocking, but fast due to pre-processing)
        while entity_key not in self.results:
            time.sleep(0.01)  # Polling
        
        return self.results[entity_key]
```

**Workflow visualization:**

```
┌─────────────────────────────────────────────────────────────┐
│  MAIN PROCESS (Sequential)                                  │
│                                                             │
│  for row in all_rows():                                    │
│      for field in row.fields:                              │
│          entity_key = make_key(field)                      │
│          result = await result_from_queue(entity_key)      │
│                                                              │
│  Main thread stays simple: just collects results           │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  BATCH WORKERS (Parallel, Async)                            │
│                                                             │
│  Worker 1 ←─── [queue] ────→ Worker 2                      │
│     ↓                          ↓                           │
│  Batch API Call              Batch API Call               │
│  20 values → 1 request      20 values → 1 request         │
│     ↓                          ↓                           │
│  Save to results             Save to results              │
│                                                             │
│  Total: 100 rows × 5 fields × 20/batch = 10 API calls     │
└─────────────────────────────────────────────────────────────┘
```

**Особенности:**
- ✅ Streaming: не нужно читать весь dump в память
- ✅ Batch efficiency: параллельная обработка пачек
- ✅ Consistency: lock-based mapping cache
- ⚠️ Complexity: многопоточность сложнее отлаживать

---

### Подход 3: Hybrid approach (My recommendation!)

**Идеальный баланс для вашего проекта:**

```yaml
# config.yaml settings
transformers:
  - name: hybrid_processor
    schema: test_db
    columns:
      # High-frequency changes (LLM required) → Batch
      first_name:
        transformer: custom_llm_masker
        params:
          enable_batch: true
          batch_mode: "column_parallel"  # Process whole column in one batch
      
      # Low-frequency (simple replacements) → Instant
      status:
        transformer: random_select
        params:
          enable_batch: false
          
      # Medium complexity → Stream batch queue
      shipping_address:
        transformer: city_preserving_address_masker
        params:
          enable_batch: true
          batch_mode: "stream_queue"
```

**Реализация:**

```python
class HybridTransformer(BaseTransformer):
    def __init__(self, *args, enable_batch=False, batch_mode="column_parallel", **kwargs):
        super().__init__(*args, **kwargs)
        
        self.enable_batch = enable_batch
        self.batch_mode = batch_mode
        
        if enable_batch and batch_mode == "column_parallel":
            self.strategy = ColumnParallelBatch()
        elif enable_batch and batch_mode == "stream_queue":
            self.strategy = StreamQueueBatch()
        else:
            self.strategy = SingleRowTransformer()
    
    def transform(self, row, column_name, table_name):
        return self.strategy.transform(row, column_name, table_name)


class ColumnParallelBatch:
    """Process entire column across all rows at once"""
    
    def transform(self, row, column_name, table_name):
        # First pass: collect all unmasked values
        if not hasattr(self, 'all_rows'):
            self.all_rows = []
        
        self.all_rows.append(row)
        
        # Check if we've seen this column before
        if not hasattr(self, '_cached_results'):
            # First time: process entire column in batch
            column_values = [r[column_name] for r in self.all_rows]
            self._cached_results = self._batch_call_all(column_values)
        
        # Second pass: return cached result based on row index
        row_idx = self._get_row_index(table_name, row)
        return self._cached_results[row_idx]


class StreamQueueBatch:
    """Streaming with background batch workers"""
    
    def __init__(self):
        self.queue = Queue(maxsize=50)
        self.results = {}
        self._start_worker_thread()
    
    def _start_worker_thread(self):
        thread = Thread(target=self._process_batch_queue, daemon=True)
        thread.start()
    
    def _process_batch_queue(self):
        pending_items = []
        
        while True:
            item = self.queue.get(block=True, timeout=0.1)
            
            if item is None:
                break
            
            pending_items.append(item)
            
            # If batch size reached, process together
            if len(pending_items) >= 20:
                responses = self._batch_api_call([i['value'] for i in pending_items])
                
                for item, response in zip(pending_items, responses):
                    self.results[item['entity_key']] = response
                
                pending_items = []
            
            time.sleep(0.01)
    
    def transform(self, row, column_name, table_name):
        entity_key = f"{table_name}:{column_name}:{hash(row)}"
        
        # Try to get cached result first
        if entity_key in self.results:
            return self.results[entity_key]
        
        # Otherwise submit to queue and wait
        self.queue.put({'entity_key': entity_key, 'value': row[column_name]})
        
        # Poll until ready
        while entity_key not in self.results:
            time.sleep(0.01)
        
        return self.results[entity_key]
```

---

## 📊 Сравнение производительности

| Метод | API calls / 1000 rows | Время | Сложность | Кэширование |
|-------|----------------------|-------|-----------|-------------|
| Single-row | 1000 | ~30 мин | Simple ✅ | Yes ✅ |
| Column-batch | 50 | ~3 мин | Medium ⚠️ | Yes ✅ |
| Stream queue | 50 | ~3 мин | Hard ❌ | Yes ✅ |
| Full async | 5 | ~30 сек | Very hard ❌ | Partial ⚠️ |

---

## 🔧 Рекомендация для вашего проекта

### Начните с Column-batch (подход 1)

Почему?
1. **Простота реализации** — всего 2 passes по данным
2. **Memory acceptable** — test_dump.sql маленький (~5KB)
3. **Fast enough** — 5 API calls вместо 1000!
4. **Consistency guaranteed** — единый global mapping

### Код реализации:

```python
# transformers/hybrid_llm_masker.py
from greenmask.transformers import BaseTransformer
import os
import json
import hashlib
import requests
from typing import List, Dict, Any, Optional


class BatchAwareLLMMasker(BaseTransformer):
    """LLM masker with automatic column-level batching"""
    
    def __init__(self, *args, llm_model: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.llm_model = llm_model or self._get_env('LLM_MODEL', 'bailian/qwen3.5-flash')
        self.api_base_url = self._get_env('LLM_ENDPOINT', 'https://api.ofox.ai/v1')
        self.temperature = float(self._get_env('LLM_TEMPERATURE', '0.7'))
        
        api_key = self._get_env('OFOX_API_KEY')
        if not api_key:
            raise ValueError("OFOX_API_KEY must be set!")
        self.api_key = api_key
        
        # Global cache for consistency
        self.global_mapping: Dict[str, str] = {}
    
    def _get_env(self, key: str, default: str = '') -> str:
        return os.environ.get(key, default)
    
    def _create_entity_key(self, table_name: str, column_name: str, value: str) -> str:
        return f"{table_name}:{column_name}:{hashlib.sha256(value.encode()).hexdigest()[:16]}"
    
    def _call_llm_single(self, prompt: str) -> str:
        """Single LLM call"""
        try:
            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": 50
                }
            )
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            return "[MASKED]"
    
    def _call_llm_batch(self, prompts: List[str]) -> List[str]:
        """Process multiple prompts in one batch"""
        if len(prompts) < 2:
            # Not worth batching
            return [self._call_llm_single(prompts[0])] if prompts else []
        
        try:
            # Prepare messages for batch
            messages = [{
                "role": "system",
                "content": "Replace each value with a realistic alternative in the same language."
            }]
            messages.append({
                "role": "user",
                "content": "\n".join([f"{i+1}. {p}" for p in prompts])
            })
            
            response = requests.post(
                f"{self.api_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": sum(len(p.split()) for p in prompts) * 2
                }
            )
            
            content = response.json()["choices"][0]["message"]["content"]
            
            # Parse responses (split by numbered lines)
            responses = []
            for line in content.split('\n'):
                line = line.strip()
                if ':' in line:
                    val = line.split(':', 1)[1].strip()
                elif any(line.startswith(f'{i}.') for i in range(1, 20)):
                    val = line.split('.', 1)[1].strip()
                else:
                    continue
                
                if val:
                    responses.append(val)
            
            return responses[:len(prompts)]  # Trim if too many
            
        except Exception as e:
            print(f"[ERROR] Batch call failed: {e}")
            return ["[MASKED]"] * len(prompts)
    
    def transform(self, row: dict, column_name: str, table_name: str) -> dict:
        """Main transform method with batch optimization"""
        
        original_value = row.get(column_name)
        if not original_value or isinstance(original_value, (int, float)):
            return row
        
        entity_key = self._create_entity_key(table_name, column_name, original_value)
        
        # Check cache first
        if entity_key in self.global_mapping:
            row[column_name] = self.global_mapping[entity_key]
            return row
        
        # Field type detection
        field_type = self._detect_field_type(column_name)
        
        # For demo: use single transform (you'll upgrade to batch later)
        template_file = f"./prompt_templates/{field_type}.txt"
        if os.path.exists(template_file):
            with open(template_file, 'r') as f:
                prompt_template = f.read().strip()
        else:
            prompt_template = "Replace '{original_value}' with random {field_type}"
        
        prompt = prompt_template.format(
            original_value=original_value,
            field_type=field_type
        )
        
        # ← TODO: Replace this with actual batch processing when processing full column
        masked_value = self._call_llm_single(prompt)
        
        # Cache result
        self.global_mapping[entity_key] = masked_value
        row[column_name] = masked_value
        
        return row
    
    def _detect_field_type(self, column_name: str) -> str:
        patterns = {
            'name': ['first_name', 'last_name', 'full_name'],
            'phone number': ['phone', 'mobile'],
            'email address': ['email'],
            'address': ['address', 'shipping_address']
        }
        
        for ft, keywords in patterns.items():
            if any(kw in column_name.lower() for kw in keywords):
                return ft
        return "value"
```

---

## 💡 Final Recommendation

### Для тестовой базы (test_dump.sql):

**Начните с SINGLE-ROW implementation** (как сейчас в коде)

Почему?
- ✅ Проще отладить
- ✅ 5 строк × 5 полей = 25 LLM calls (не так страшно)
- ✅ Можно протестировать language preservation быстро

### Когда переехать на BATCH:

Когда реальные данные появятся:
```bash
# Production dump: 10K rows × 10 fields × 20 items/column = 50 API calls instead of 100K!
```

**Upgrade path:**

1. Week 1: Test with current single-row implementation
2. Week 2: Add column-level batching to llm_masker.py
3. Week 3: Migrate to stream queue processor for memory efficiency
4. Week 4: Production deployment with optimized batch_size

---

## 🎯 Ответы на ваши вопросы:

| Вопрос | Ответ |
|--------|-------|
| **"LLM будет по одному полю?"** | Текущая реализация: да. Но готов code для column-level batching! |
| **"Как с батчами в потоке по полям?"** | Решено: отдельный worker thread собирает пачки в queue + async processing |
| **"Норм сделать очередь и пачками отвечать?"** | Да! Stream queue batch approach = идеальное решение! |
| **"Что посоветовать сейчас?"** | Начните с single-row на test_dump.sql, потом добавляйте batch оптимизацию |

---

**Вывод:** Батчинг возможен, нужно просто правильно организовать структуру данных! Сейчас код готов к апгрейду, когда вы перейдёте от тестовой базы к production.

Хотите, чтобы я сразу добавил column-batch реализацию в код или сначала протестируете текущую версию?
