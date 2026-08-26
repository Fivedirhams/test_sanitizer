#!/bin/bash
# Быстрый старт: один скрипт - всё работает
set -e

echo "========================================"
echo "MySQL Database Sanitizer - Quick Start"
echo "========================================"
echo ""

# Проверка наличия dump.sql
if [ ! -f ./dump.sql ]; then
    echo "⚠️  dump.sql не найден!"
    echo ""
    echo "Создайте дамп базы данных:"
    echo "  mysqldump -h HOST -u USER -p DATABASE > dump.sql"
    echo ""
    echo "Или переместите существующий дампи в ./dump.sql"
    exit 1
fi

echo "✅ Dump найден: dump.sql ($(du -h dump.sql | cut -f1))"

# Создаём output директорию
mkdir -p ./output

# Запускаем контейнер
echo ""
echo "🚀 Запуск санитизации..."
docker compose run --rm greenmask

echo ""
echo "✅ Готово!"
echo ""
echo "Результат:"
echo "  📁 ./output/sanitized.sql.gz - заархивированный SQL с анонимизированными данными"
test -f ./output/mapping.json && echo "  🗺️  ./output/mapping.json - маппинг для обратной совместимости" || echo "  ℹ️  Маппинг не создан (опционально)"
echo ""
echo "Загрузите результат в dev базу:"
echo "  gunzip -c ./output/sanitized.sql.gz | mysql -h dev-host db_name"
