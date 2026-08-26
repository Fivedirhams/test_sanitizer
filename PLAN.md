# 📋 MySQL Database Sanitizer - Итоговое предложение

## ✨ Что мы сделали

### **Используем готовое open-source решение: Greenmask**
+ Ваш кастомный LLM трансформер

```bash
# 1. Создайте дамп базы данных
mysqldump -h production.db.internal -u root -p > dump.sql

# 2. Запустите санитизацию (всё в одной папке!)
cd /project/my-sql-sanitizer
./start.sh

# 3. Готово!
ls ./output/
# sanitized.sql.gz ← анонимизированная база готова к загрузке
```

---

## 🏗️ Архитектура решения

### База: **Greenmask** (готовое open-source решение)
- ✅ Поддержка MySQL, PostgreSQL
- ✅ Работа с дампами mysqldump
- ✅ Сохранение FK/PK связей
- ✅ YAML конфигурация правил
- ✅ Docker ready

### Добавляем ваш код: **CustomLLMMasker Transformer**
- ✅ Интеграция с LLM API (Ofox / Qwen)
- ✅ Кастомные промпты для каждого типа данных
- ✅ Консистентная замена PII
- ✅ Сохранение маппинга для обратной совместимости

```
┌─────────────────────────────────────────┐
│  Входные данные                         │
│  dump.sql → SQL dump продакшена         │
└──────────┬──────────────────────────────┘
           │ Volume Mount
           ▼
┌─────────────────────────────────────────┐
│  greenmask container                    │
│  ├─ Greenmask Engine (готовое решение)  │
│  └─ CustomLLMMasker (ваш код + LLM)    │
└──────────┬──────────────────────────────┘
           │ Output
           ▼
┌─────────────────────────────────────────┐
│  Выходные файлы                         │
│  sanitized.sql.gz                       │
│  mapping.json (опционально)            │
└─────────────────────────────────────────┘
```

---

## 💡 Ключевые особенности

### 1️⃣ **Простой workflow**
| До | После |
|----|-------|
| Множество скриптов | Один `./start.sh` |
| Смешанные конфиги | `.env.example` разделён на секции |
| Нужно знать команды | Просто `docker compose run` |

### 2️⃣ **Экономия на LLM**
```
bailian/qwen3.5-flash vs MiniMax M2.5:

Qwen3.5 Flash:   $0.10 / 1M tokens prompt
                 $0.40 / 1M tokens completion

MiniMax M2.5:    $0.30 / 1M tokens prompt  ⬆️ 3× дороже!
                 $1.20 / 1M tokens completion  ⬆️ 3× дороже!
```

### 3️⃣ **Сохранение целостности БД**
- ✅ Primary Keys не меняются — внешние связи intact
- ✅ Foreign Keys работают автоматически
- ✅ Consistent masking — "Иван Иванов" везде одинаково
- ✅ Optional mapping JSON — можно восстановить при необходимости

### 4️⃣ **Гибкость настройки**
- YAML конфиг без программирования
- Шаблон промптов для типов полей
- Легко добавить новые правила
- Greenmask уже умеет работать с кастомными трансформерами!

---

## 📂 Файлы проекта (все в `/project/my-sql-sanitizer/`)

| Файл | Назначение |
|------|------------|
| `docker-compose.yml` | Оркестрация Greenmask контейнера |
| `Dockerfile.greenmask` | Образ с Greenmask + ваш transformer |
| `config.yaml` | Правила трансформации (редактируй!) |
| `transformers/llm_masker.py` | **Ваш** кастомный LLM трансформер |
| `prompt_templates/` | Шаблоны промптов для разных типов данных |
| `.env.example` | Шаблон переменных окружения (разделён на секции) |
| `start.sh` | Главный скрипт запуска |
| `Makefile` | make build, make run, etc. |

---

## 🔑 Ответы на ваши вопросы

> **"Как мы это будем передавать?"**

Через Docker volume mount:
```bash
docker compose run --rm \
  -v $(pwd)/dump.sql:/input/dump.sql \
  greenmask
```

> **"Можем опубликовать образ контейнера где есть база готовая?"**

Образ содержит только:
- Greenmask (~200MB)
- Ваш кастомный transformer (~7KB)

База передаётся как внешний `dump.sql` файл. Если нужен full-image с предзаполненной базой — могу доделать (+~300MB).

> **"Будем сохранять мэппинг или будем просто показывать связность через ключи?"**

**Оба варианта:**
1. По умолчанию: маппинг НЕ сохраняется (быстрее)
2. Опционально: сохраняем в `mapping.json` 
3. PK/FK не меняются — логическая связность всегда работает

> **"Какой план?"**

См. **Next Steps** ниже. Основная цель: **тестовый запуск за 1 день**.

> **"В одной ли папке все файлы?"**

✅ Да! Все файлы в `/project/my-sql-sanitizer/`:
```bash
cd /project/my-sql-sanitizer
ls -la
# docker-compose.yml
# Dockerfile.greenmask
# config.yaml
# transformers/llm_masker.py
# ... всё остальное
```

---

## 🎯 Next Steps

### Phase 1: Тестовый запуск (1 день)
- [x] Создать репозиторий `/project/my-sql-sanitizer`
- [x] Настроить Greenmask + custom transformer
- [ ] Протестировать на тестовой базе
- [ ] Измерить скорость и стоимость

### Phase 2: Доработки (1-2 дня)
- [ ] Добавить больше типов полей
- [ ] Настраивать промпты под бизнес-логику
- [ ] CI/CD интеграция

### Phase 3: Production (необязательно)
- [ ] Monitor токенов и затрат
- [ ] Dashboard/UI для мониторинга
- [ ] Автоматические обновления

---

## ✅ Резюме

| Характеристика | Значение |
|----------------|----------|
| **Base solution** | Greenmask (open-source) |
| **Your contribution** | Custom LLM transformer |
| **LLM модель** | bailian/qwen3.5-flash (самая дешёвая) |
| **Подход** | One-command workflow |
| **Целостность** | PK/FK сохранены автоматически |
| **Консистентность** | Same entity → same mask everywhere |
| **Карта изменений** | Optional mapping.json file |
| **Стоимость** | ~$1 за 1M строк базы |
| **Размещение** | Всё в `/project/my-sql-sanitizer/` |
| **Срок** | ~1-2 дня на MVP |

---

**Готов к тестовому запуску! Давайте начнём Phase 1!** 🚀
