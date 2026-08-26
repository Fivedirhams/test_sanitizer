"""
Generate large test database for batch processing demonstration
Creates ~2000 rows with realistic multi-language data
"""

import random
import string
from datetime import datetime, timedelta


# Multi-language datasets
FIRST_NAMES = {
    'spanish': ['María', 'Carlos', 'Gabriela', 'Roberto', 'Lucía', 'Javier', 'Sofía', 'Antonio', 'Elena', 'Miguel'],
    'russian': ['Ярослав', 'Анна', 'Дмитрий', 'Елена', 'Александр', 'Ольга', 'Сергей', 'Наталья', 'Игорь', 'Татьяна'],
    'brazilian': ['Maria', 'João', 'Ana', 'Pedro', 'Carla', 'Rafael', 'Julia', 'Bruno', 'Camila', 'Fernando'],
    'french': ['Marie', 'Pierre', 'Sophie', 'Jean', 'Claire', 'Nicolas', 'Emma', 'Thomas', 'Léa', 'Antoine'],
    'german': ['Anna', 'Michael', 'Maria', 'Thomas', 'Sarah', 'Stefan', 'Laura', 'Daniel', 'Julia', 'Alexander']
}

LAST_NAMES = {
    'spanish': ['García', 'Martínez', 'Rodríguez', 'López', 'González', 'Hernández', 'Muñoz', 'Díaz', 'Torres', 'Ruiz'],
    'russian': ['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов', 'Попов', 'Васильев', 'Михайлов', 'Новиков', 'Федоров'],
    'brazilian': ['Silva', 'Santos', 'Oliveira', 'Souza', 'Costa', 'Ferreira', 'Almeida', 'Pereira', 'Lima', 'Ribeiro'],
    'french': ['Martin', 'Bernard', 'Dubois', 'Thomas', 'Robert', 'Richard', 'Petit', 'Durand', 'Leroy', 'Moreau'],
    'german': ['Müller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer', 'Wagner', 'Becker', 'Schulz', 'Hoffmann']
}

EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'example.org']

STREETS = {
    'spain': ['Calle Mayor', 'Calle Velázquez', 'Gran Vía', 'Paseo de la Castellana', 'Calle Serrano'],
    'russia': ['ул. Тверская', 'пр. Невский', 'ул. Арбат', 'ул. Ленина', 'ул. Гагарина'],
    'brazil': ['Rua Augusta', 'Av. Paulista', 'Rua Oscar Freire', 'Av. Atlântica', 'Rua da Consolação'],
    'france': ['Rue de Rivoli', 'Boulevard Saint-Germain', 'Avenue des Champs-Élysées', 'Rue de la Paix'],
    'germany': ['Unter den Linden', 'Kurfürstendamm', 'Marienplatz', 'Friedrichstraße', 'Reeperbahn']
}

CITIES = {
    'spain': ['Madrid', 'Barcelona', 'Valencia', 'Seville', 'Zaragoza'],
    'russia': ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань'],
    'brazil': ['São Paulo', 'Rio de Janeiro', 'Salvador', 'Brasília', 'Curitiba'],
    'france': ['Paris', 'Marseille', 'Lyon', 'Toulouse', 'Nice'],
    'germany': ['Berlin', 'München', 'Hamburg', 'Frankfurt', 'Köln']
}

COUNTRIES = {
    'spain': 'Spain',
    'russia': 'Russia', 
    'brazil': 'Brazil',
    'france': 'France',
    'germany': 'Germany'
}

PRODUCTS = [
    ('Laptop Pro 15"', 899.99),
    ('Wireless Mouse', 29.99),
    ('USB-C Hub', 49.99),
    ('Mechanical Keyboard', 129.99),
    ('4K Monitor', 399.99),
    ('Webcam HD', 79.99),
    ('External SSD 1TB', 119.99),
    ('Noise Cancelling Headphones', 249.99),
    ('Smart Watch', 199.99),
    ('Portable Charger', 39.99)
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
]


def random_ip():
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def random_date(start_year=2020):
    start = datetime(start_year, 1, 1)
    end = datetime(2024, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime('%Y-%m-%d')


def generate_customer(customer_id, region_key):
    region = list(FIRST_NAMES.keys())[customer_id % len(FIRST_NAMES)]
    
    first_name = random.choice(FIRST_NAMES[region])
    last_name = random.choice(LAST_NAMES[region])
    
    email_prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    email = f"{email_prefix}@{random.choice(EMAIL_DOMAINS)}"
    
    phone = f"+{random.choice(['34', '7', '55', '33', '49'])}-{random.randint(100,999)}-{random.randint(100,999)}-{random.randint(100,999)}"
    
    city_idx = customer_id % len(CITIES[region])
    street_idx = customer_id % len(STREETS[region])
    
    address = f"{random.randint(1,999)} {STREETS[region][street_idx]}, {CITIES[region][city_idx]}, {COUNTRIES[region]}"
    
    return f"(customer_id, first_name, last_name, email, phone, address)\nINSERT INTO `customers` VALUES (\
{customer_id}, '{first_name}', '{last_name}', '{email}', '{phone}', '{address}');\n"


def generate_order(order_id, customer_id):
    product_name, price = random.choice(PRODUCTS)
    quantity = random.randint(1, 5)
    status = random.choice(['pending', 'shipped', 'delivered', 'cancelled'])
    timestamp = random_date()
    
    return f"(order_id, customer_id, product_name, price, quantity, status, order_timestamp)\nINSERT INTO `orders` VALUES (\
{order_id}, {customer_id}, '{product_name}', {price:.2f}, {quantity}, '{status}', '{timestamp}');\n"


def generate_log(log_id, customer_id):
    ip_addr = random_ip()
    user_agent = random.choice(USER_AGENTS)
    event_type = random.choice(['login', 'logout', 'page_view', 'purchase', 'error'])
    metadata = json.dumps({"session_id": ''.join(random.choices(string.hexdigits[:16], k=16)), 
                          "referrer": random.choice(['google.com', 'facebook.com', 'twitter.com', None])})
    timestamp = random_date()
    
    return f"(log_id, customer_id, ip_address, user_agent, event_type, metadata, log_timestamp)\nINSERT INTO `logs` VALUES (\
{log_id}, {customer_id}, '{ip_addr}', '{user_agent}', '{event_type}', '{metadata}', '{timestamp}');\n"


if __name__ == '__main__':
    import json
    
    OUTPUT_FILE = '/project/my-sql-sanitizer/large_test_dump.sql'
    
    num_customers = 500
    num_orders_per_customer = 3
    num_logs_per_customer = 5
    
    total_lines = 0
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Schema definitions
        f.write("-- Large Test Database Dump\n")
        f.write("-- Generated for batch processing demonstration\n\n")
        
        # CREATE TABLEs
        f.write("CREATE TABLE `customers` (\n")
        f.write("  `customer_id` INT PRIMARY KEY,\n")
        f.write("  `first_name` VARCHAR(50),\n")
        f.write("  `last_name` VARCHAR(50),\n")
        f.write("  `email` VARCHAR(100),\n")
        f.write("  `phone` VARCHAR(20),\n")
        f.write("  `address` TEXT\n");
        f.write(");\n\n")
        
        f.write("CREATE TABLE `orders` (\n")
        f.write("  `order_id` INT PRIMARY KEY,\n")
        f.write("  `customer_id` INT,\n")
        f.write("  `product_name` VARCHAR(100),\n")
        f.write("  `price` DECIMAL(10,2),\n")
        f.write("  `quantity` INT,\n")
        f.write("  `status` VARCHAR(20),\n")
        f.write("  `order_timestamp` DATETIME,\n")
        f.write("  FOREIGN KEY (`customer_id`) REFERENCES `customers`(`customer_id`)\n");
        f.write(");\n\n")
        
        f.write("CREATE TABLE `logs` (\n")
        f.write("  `log_id` INT PRIMARY KEY,\n")
        f.write("  `customer_id` INT,\n")
        f.write("  `ip_address` VARCHAR(45),\n")
        f.write("  `user_agent` TEXT,\n")
        f.write("  `event_type` VARCHAR(50),\n")
        f.write("  `metadata` JSON,\n")
        f.write("  `log_timestamp` DATETIME,\n")
        f.write("  FOREIGN KEY (`customer_id`) REFERENCES `customers`(`customer_id`)\n");
        f.write(");\n\n")
        
        print(f"Generating {num_customers} customers...")
        
        # Generate customers (all 5 languages represented)
        for cid in range(1, num_customers + 1):
            line = generate_customer(cid, cid % 5)
            f.write(line)
            total_lines += 1
        
        print(f"Generating {num_customers * num_orders_per_customer} orders...")
        
        # Generate orders (FK to customers preserved!)
        oid = 1
        for cid in range(1, num_customers + 1):
            for _ in range(num_orders_per_customer):
                line = generate_order(oid, cid)
                f.write(line)
                total_lines += 1
                oid += 1
        
        print(f"Generating {num_customers * num_logs_per_customer} logs...")
        
        # Generate logs (FK to customers preserved!)
        lid = 1
        for cid in range(1, num_customers + 1):
            for _ in range(num_logs_per_customer):
                line = generate_log(lid, cid)
                f.write(line)
                total_lines += 1
                lid += 1
    
    print(f"\n✅ GENERATED DATABASE:")
    print(f"   File: {OUTPUT_FILE}")
    print(f"   Total lines: {total_lines:,}")
    print(f"   Customers: {num_customers:,}")
    print(f"   Orders: {num_customers * num_orders_per_customer:,}")
    print(f"   Logs: {num_customers * num_logs_per_customer:,}")
    print(f"\n   Estimated API calls (single-row): {(num_customers * (2+1)) + (num_customers*num_orders_per_customer) + (num_customers*num_logs_per_customer):,}")
    print(f"   Estimated API calls (batch size 20): ~{(num_customers * (2+1) // 20) + (num_customers*num_orders_per_customer // 20) + (num_customers*num_logs_per_customer // 20):,}")
    print(f"   Speedup: {((num_customers * (2+1)) + (num_customers*num_orders_per_customer) + (num_customers*num_logs_per_customer)) / ((num_customers * (2+1) // 20) + (num_customers*num_orders_per_customer // 20) + (num_customers*num_logs_per_customer // 20)):,.0f}x")
