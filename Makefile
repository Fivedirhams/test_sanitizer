.PHONY: all build run help dump verify clean

all: help

help:
	@echo "========================================"
	@echo "MySQL Database Sanitizer - Commands"
	@echo "========================================"
	@echo ""
	@echo "Available commands:"
	@echo "  make dump      - Create database dump (requires DB credentials)"
	@echo "  make build     - Build Docker images"
	@echo "  make run       - Run sanitization (requires dump)"
	@echo "  make verify    - Check output files"
	@echo "  make clean     - Clean output files"
	@echo ""
	@echo "Quick start:"
	@echo "  1. mysqldump -h HOST -u USER -p > dump.sql"
	@echo "  2. docker compose build && docker compose run --rm greenmask"
	@echo "  3. ls -la ./output/"
	@echo ""

build:
	@echo "[BUILD] Building Docker images..."
	docker compose build

run:
	@if [ ! -f dump.sql ]; then \
		echo "[ERROR] No dump.sql found!"; \
		echo "Create it with: mysqldump -h HOST -u USER -p DATABASE > dump.sql"; \
		exit 1; \
	fi
	@echo "[RUN] Starting sanitization..."
	docker compose run --rm greenmask

dump:
	@echo "[DUMP] Creating database dump..."
	@read -p "Enter MySQL host: " HOST; \
	read -p "Enter MySQL user: " USER; \
	read -sp "Enter MySQL password: " PASS; echo; \
	mysqldump -h $$HOST -u $$USER -p$$PASS > dump.sql
	@echo "[SUCCESS] Dump created: dump.sql"

verify:
	@echo "[VERIFY] Checking output files..."
	@test -f ./output/sanitized.sql.gz && echo "✅ sanitized.sql.gz exists" || echo "❌ sanitized.sql.gz missing"
	@test -f ./output/mapping.json && echo "✅ mapping.json exists" || echo "⚠️  mapping.json not generated"

clean:
	@echo "[CLEAN] Removing output files..."
	rm -rf ./output/*
	@echo "[DONE]"
