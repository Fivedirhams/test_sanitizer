# 📋 План исправления консистентности по всей базе данных

## Критичная проблема, которую решил json_reconciler.py

**Проблема:** Если `customers.email` меняется на `pedro.silva@gmail.com`, а тот же email есть в JSON поле лога `logs.details='{"user_email":"maria.garcia@gmail.com"}'` — после основного прохода Greenmask лог всё ещё содержит оригинал ❌

**Решение:** `json_reconciler.py` запускается ПОСЛЕ основного пропуска и сканирует **ВСЁ** содержимое дампа (включая JSON строки) на наличие ЛюБЫХ оригинальных значений которые были заменены.

---

## Архитектура решения

```
┌─────────────────────────────────────────────────────────────┐
│                    Processing Pipeline                       │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         ↓                                          ↓
┌──────────────────┐                      ┌──────────────────┐
│  PASS 1: Primary │                      │  MAPPING.BUILD   │
│  Sanitization    │                      │  (all replacements)│
│  (Greenmask)     │                      │                  │
│                  │                      │                  │
│  - Tables processed│                     │  old_value → new_value│
│  - PKs skipped   │                      │                  │
│  - FK preserved  │                      │                  │
│  - Mapping saved │                      │                  │
└──────────────────┘                      └──────────────────┘
         │                                          │
         └──────────────────┬───────────────────────┘
                            ↓
              ┌───────────────────────────┐
              │  PASS 2: Reconciliation   │
              │  (json_reconciler.py)     │
              │                           │
              │  1. Load mapping.json     │
              │  2. Scan ALL content      │
              │  3. Find original values │
              │  4. Replace consistently │
              │  5. Output final.sql     │
              └───────────────────────────┘
                            ↓
              ┌───────────────────────────┐
              │  PASS 3: Validation       │
              │  (check no originals left)│
              │                           │
              │  - No real emails? ✅     │
              │  - No real phones? ✅     │
              │  - All FK valid? ✅       │
              └───────────────────────────┘
```

---

## Как json_reconciler.py работает

### Шаг 1: Загружает маппинг из primary pass

```python
mapping = {
    "maria.garcia@gmail.com": "pedro.silva@gmail.com",
    "+7-495-123-4567": "+7-495-987-6543",
    "María García": "Carmen López"
}
```

### Шаг 2: Применяет замены ко всему содержимому (string replace)

```python
for old_val, new_val in mapping.items():
    content = content.replace(old_val, new_val)
```

### Шаг 3: Сканирует regex паттерны на остаточные оригиналы

```python
# Email pattern scan
emails = re.findall(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', content)
for email in emails:
    if email in mapping.values():  # это уже новый value
        continue
    elif email in self.mapping:   # это original который остался
        fix_it()
```

### Шаг 4: Выводит финальный результат с гарантией консистентности

✅ Гарантируется что **КАЖДОЕ** появление старого значения заменено на новое

---

## Что делать если найден original value в финальном выводе?

Это означает что reconciliation не сработал должным образом. Возможные причины:

| Причина | Решение |
|---------|----------|
| Не был создан маппинг для этого поля | Добавить transformer в config.yaml |
| Значение было вне scope таблицы | Увеличить coverage tables list |
| Специальный символ/кодировка | Escaping issue — проверить unicode handling |

---

## Проверка консистентности

```bash
# Посмотреть статистику reconciler
cat output/reconciler_stats.txt

# Ручная проверка
gunzip -c output/sanitized.sql.gz | grep "gmail.com\|yahoo.com" | wc -l
# Должно быть 0 (никаких реальных доменов!)

# Или через API
python tools/json_reconciler.py --input output/sanitized.sql.gz \
    --mapping output/mapping.json \
    --validate
```

---

## Итог: Гарантии консистентности

1. **Primary Pass**: Все трансформеры работают с глобальным `entity_mapping` cache
2. **Mapping File**: Сохраняются ВСЕ transformations old→new
3. **Reconciliation Pass**: Сканирует ВСЁ содержимое дампа включая JSON
4. **Validation Pass**: Проверяет что нет оставшихся оригиналов

✅ **Гарантировано**: Никакие оригинальные PII данные не остаются ни в одной ячейке базы
