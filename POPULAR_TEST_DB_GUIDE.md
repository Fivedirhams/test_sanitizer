# 🌐 Популярные бесплатные тестовые базы данных для SQL

## Top 5 Публичных Test Datasets (ссылки на GitHub/GitLab)

### 1️⃣ **Chinook Database** (MOST RECOMMENDED) ⭐⭐⭐⭐⭐

**Описание:** Продажа музыки/артистов/альбомов
- **Рекомендуется для:** E-commerce аналогии, relationships testing
- **URL:** https://github.com/lerocha/chinook-database
- **Формат:** MySQL dump + SQLite + PostgreSQL
- **Размер:** ~1K rows across 11 tables
- **Состав:**
  - `Artists` (57 artists)
  - `Albums` (347 albums)  
  - `Tracks` (3,503 tracks)
  - `Invoices` (412 invoices)
  - `Customers` (59 customers) ← PII поля есть! ✅
  - `Employees`, `Genres`, `MediaTypes`, `Playlist`, `PlaylistTrack`, `InvoiceItem`

**Почему хорошо для вашего кейса:**
- Contains real customer PII (name, email, phone, address)
- Clear FK relationships between tables
- Well-documented schema
- Already has both anonymized and non-anonymized versions for validation

**Download:**
```bash
git clone https://github.com/lerocha/chinook-database.git
cd chinook-database/ChinookDatabase/DataSources/MySQL
mysql -u root -p chinook < Chinook_MySQL.sql
```

---

### 2️⃣ **IMDb Dataset** (LARGE SCALE)

**Описание:** Фильмы, актёры, рейтинги
- **URL:** https://github.com/danielgrijalva/sqlite-files/blob/master/imdb.sqlite
- **Формат:** Primarily SQLite (можно конвертировать)
- **Размер:** 1M+ rows
- **PII:** Minimal (mostly public metadata)
- **Использование:** Large-scale benchmarking

**Alternative (more complete):**
https://github.com/rongwei/DBbench → MySQL dumps with realistic schemas

---

### 3️⃣ **Northwind Traders** (Classic E-commerce)

**Описание:** Классическая база поставщиков/заказчиков (как Microsoft Demo DB)
- **URL:** https://github.com/microsoft/SQL-Server-Samples/tree/main/Northwind
- **Формат:** SQL Server (но есть MySQL forks!)
- **Лучший форк:** https://github.com/BobPozo/Northwind-for-MySQL
- **Размер:** ~60 tables, 10K+ rows
- **PII:** customers, suppliers (names, emails, addresses) ← ПРАВИЛЬНОЕ ПОДХОДИТ!

**Почему идеально:**
- Standard business database structure
- Rich foreign key constraints
- Real-world entity relationships

---

### 4️⃣ **Sakila Sample Database** (OFFICIAL MySQL)

**Описание:** Официальная sample database от Oracle/MySQL
- **URL:** https://dev.mysql.com/doc/sakila/en/
- **Прямая ссылка на download:** https://cdn.mysql.com/db-download.sakila.tar.gz
- **Формат:** Официальный MySQL dump
- **Размер:** 5K+ rows, 10 tables
- **Schema:** Video rental store (customers, films, rentals, payments)

**Преимущества:**
- Created by MySQL team themselves
- Production-quality schema
- Includes realistic indexes & constraints
- No external dependencies

**Download commands:**
```bash
wget https://cdn.mysql.com/db-download.sakila.tar.gz
tar -xzf db-download.sakila.tar.gz
cd sakila-mysql
source sakila.schema.sql
source sakila.insert-data.sql
```

---

### 5️⃣ **Employee Database** (HR System)

**Описание:** HR система с сотрудниками/отделами/зарплатами
- **URL:** https://github.com/nicholasnba/mysql-sample-databases
- **Специфично:** https://github.com/nicholasnba/mysql-sample-databases/tree/master/employees
- **Размер:** ~30K rows
- **PII:** employee names, salaries, hire dates
- **Tables:** employees, departments, dept_emp, dept_manager, salaries, titles

---

## 🎯 Мой рекомендация для ВАШЕГО проекта

| База | Когда использовать | Почему |
|------|-------------------|---------|
| **Chinook** ⭐ | **BEST CHOICE!** | Уже содержит customer PII (email, phone, address) для masking |
| **Sakila** | Official MySQL validation | No custom scripts needed, comes pre-packaged |
| **Northwind fork** | Enterprise analogies | Richer schema if you need complex relations |

---

## 📥 Quick Setup Scripts

### Option A: Chinook (Recommended)

```bash
#!/bin/bash
# setup_chinook.sh

echo "📥 Downloading Chinook Database..."
curl -L https://github.com/birdhouses/chinook-data/archive/master.zip \
  -o chinook.zip && unzip chinook.zip -d chinook && rm chinook.zip

cd chinook-chinook-data/ChinookData/MySQL/
ls -la

echo "✅ Files ready:"
ls *.sql

# Copy to your project
cp Chinook_MySQL.sql /project/my-sql-sanitizer/chinook_test.sql
echo "Copied to project!"
```

---

### Option B: Sakila (Official MySQL)

```bash
#!/bin/bash
# setup_sakila.sh

echo "📥 Downloading Sakila Database..."
curl -L https://cdn.mysql.com/db-download.sakila.tar.gz \
  -o sakila.tar.gz && tar -xzf sakila.tar.gz && rm sakila.tar.gz

cd sakila-mysql/
chmod +x *.sql
./sakila-schema.sql --user=root # Or copy contents
./sakila-insert-data.sql --user=root

echo "✅ Sakila installed successfully!"

# Extract relevant tables for testing
mysqldump -u root sakila customers films rentals payments > /project/my-sql-sanitizer/sakila_test.sql
```

---

### Option C: Mix of multiple (for comprehensive testing)

```bash
#!/bin/bash
# Comprehensive test setup

echo "🔄 Setting up multiple test databases..."

# 1. Chinook (customer PII)
curl -L https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/MySQL/Chinook_MySQL.sql \
  -o /project/my-sql-sanitizer/chinook.sql

# 2. Sakila (rental transactions)  
curl -L https://cdn.mysql.com/db-download.sakila.tar.gz \
  -o /tmp/sakila.tar.gz && tar -xzf /tmp/sakila.tar.gz -C /tmp && \
  cp /tmp/sakila-mysql/sakila*.sql /project/my-sql-sanitizer/

# 3. Employee (HR data)
curl -L https://raw.githubusercontent.com/nicholasnba/mysql-sample-databases/master/employees/schema.sql \
  -o /project/my-sql-sanitizer/employees_schema.sql
curl -L https://raw.githubusercontent.com/nicholasnba/mysql-sample-databases/master/employees/data.sql \
  -o /project/my-sql-sanitizer/employees_data.sql

echo "✅ All test databases downloaded!"
ls -lh /project/my-sql-sanitizer/*.sql
```

---

## 🔍 Анализ PII coverage

| База | Customer Names | Emails | Phone | Address | Total Rows | Best For |
|------|----------------|--------|-------|---------|------------|----------|
| Chinook | ✅ 59 customers | ✅ | ✅ | ✅ | 4,685 | E-commerce PII testing |
| Sakila | ✅ Customers table | ✅ | ❌ | ✅ | 5,462 | Rental business |
| Northwind | ✅ Customers/Sales | ✅ | ✅ | ✅ | 63,000+ | Enterprise scale |
| Employees | ✅ 3K employees | ❌ | ❌ | ❌ | 30,000 | HR systems |

**ВЫВОД: Chinook лучше всего подходит для вашей задачи** 🏆

---

## 🎲 Сравнение: Self-generated vs Public datasets

| Критерий | generate_large_test.py | Chinook | Sakila |
|----------|------------------------|---------|--------|
| **Готовность** | Требует run Python script | Download & use ✅ | Download & use ✅ |
| **Realism** | Generated randomly | Real user data ✅ | Real user data ✅ |
| **Schema quality** | Simple | Production-quality ✅ | Production-quality ✅ |
| **Size control** | Configurable ✅ | Fixed (~5K rows) | Fixed (~5K rows) |
| **PII diversity** | Hand-coded languages | Multi-country ✅ | European focus |
| **Industry standard** | ❌ Custom | ⭐ Popular in tutorials | ⭐ MySQL official |

---

## 💡 Final Recommendation

**Для быстрой валидации концепции:**
```bash
# Download Chinook (best balance of simplicity + realistic PII)
cd /project/my-sql-sanitizer
curl -LO https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/MySQL/Chinook_MySQL.sql
mv Chinook_MySQL.sql chinook_test.sql
cp chinook_test.sql dump.sql
./start.sh
```

**Для production-like benchmarks:**
```bash
# Download multiple sources for variety
./comprehensive_test_setup.sh  # Создайте этот скрипт как выше

# Или просто используйте комбинацию:
cp chinook_test.sql dump_customers.sql  # Customer PII
cp sakila-insert-data.sql dump_transactions.sql  # Transaction logs
cat *.sql > combined_dump.sql
./start.sh
```

---

## 📚 Полезные ссылки

| Ресурс | Описание | URL |
|--------|----------|-----|
| **MySQL官方Sample** | Официальные sample базы от Oracle/MySQL | dev.mysql.com/doc/sakila/en/ |
| **GitHub SQL datasets** | Собранные репозитории с базами | github.com/topics/sql-database |
| **Awesome Public Datasets** | Список публичных датасетов | github.com/awesomedata/awesome-public-datasets |
| **Test Data Generator** | Онлайн генератор тестовых данных | rohanalexander.github.io/fake-data-api |

---

## ✅ Check-list после выбора

- [ ] Скачать базу из выбранного источника
- [ ] Проверить размер файла (должен быть > 5K строк)
- [ ] Убедиться что есть таблицы с PII (customers, users, employees)
- [ ] Проверить наличие FK constraints для integrity testing
- [ ] Скопировать в `dump.sql` или создать symlink
- [ ] Запустить через `./start.sh`
- [ ] Validate результат: FK intact? Languages preserved? Consistency maintained?

---

**Выбирайте Chinook — это промышленный стандарт с правильной структурой и реальными PII данными!** 🎯
