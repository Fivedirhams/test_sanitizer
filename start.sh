#!/bin/bash
# MySQL Database Sanitizer - Quick Start
# Один скрипт для запуска санитизации дампа базы данных
set -e

echo "========================================"
echo "MySQL Database Sanitizer"
echo "========================================"
echo ""

# Проверка наличия dump.sql
if [ ! -f ./dump.sql ]; then
    echo "⚠️  dump.sql не найден!"
    echo ""
    echo "Создайте дамп продакшен базы:"
    echo "  mysqldump -h PRODUCTION_HOST -u PRODUCTION_USER -p > dump.sql"
    echo ""
    exit 1
fi

echo "✅ Входные данные: dump.sql ($(du -h dump.sql | cut -f1))"

# Создаём output директорию
mkdir -p ./output

echo ""
echo "🚀 Запуск Greenmask контейнера..."
echo "   - Читает: ./dump.sql"
echo "   - Пишет:  ./output/sanitized.sql.gz"
echo "   - LLM:    bailian/qwen3.5-flash (через Ofox API)"
echo ""

# Запускаем контейнер
docker compose run --rm greenmask

echo ""
echo "✅ Санитизация завершена!"
echo ""
echo "Результат:"
ls -lh ./output/

echo ""
test -f ./output/mapping.json && echo "ℹ️  Маппинг сохранён: ./output/mapping.json (для обратной совместимости)" || echo "ℹ️  Маппинг не создаётся (опционально)"

echo ""
echo "Загрузка в dev базу:"
echo "  gunzip -c ./output/sanitized.sql.gz | mysql -h DEV_HOST db_name"
