-- MySQL Sample Database with PII fields for GDPR anonymization testing
-- This dump contains customer data, orders, and logs suitable for testing sanitization

CREATE DATABASE IF NOT EXISTS test_db;
USE test_db;

-- Customers table (contains PII)
CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    birth_date DATE,
    address VARCHAR(200),
    city VARCHAR(50),
    country VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    product VARCHAR(100),
    quantity INT,
    price DECIMAL(10,2),
    shipping_address VARCHAR(200),
    shipping_phone VARCHAR(20),
    status ENUM('pending', 'processing', 'shipped', 'delivered') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- System logs (some sensitive info)
CREATE TABLE system_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data (multilingual to test language preservation)
INSERT INTO customers VALUES
(1, 'Maria', 'Garcia', 'maria.garcia@gmail.com', '+34-612-345-678', '1990-05-15', 'Calle Mayor 123', 'Madrid', 'Spain', '2024-01-15'),
(2, 'Roberto', 'Silva', 'roberto.silva@hotmail.com', '+55-11-99876-5432', '1985-08-22', 'Rua das Flores 45', 'São Paulo', 'Brazil', '2024-01-16'),
(3, 'Emma', 'Johnson', 'emma.johnson@yahoo.com', '+1-212-555-0123', '1992-12-03', '123 Broadway Ave', 'New York', 'USA', '2024-01-17'),
(4, 'Ярослав', 'Иванов', 'yaroslav.ivanov@mail.ru', '+7-495-123-4567', '1988-03-10', 'ул. Ленина 15', 'Москва', 'Russia', '2024-01-18'),
(5, 'Sophie', 'Dubois', 'sophie.dubois@orange.fr', '+33-6-12-34-56-78', '1995-07-20', '15 Rue de la Paix', 'Paris', 'France', '2024-01-19');

INSERT INTO orders VALUES
(1, 1, 'Laptop Dell XPS 13', 1, 1299.99, 'Calle Mayor 123, Madrid, Spain', '+34-612-345-678', 'delivered', '2024-01-20'),
(2, 2, 'Smartphone Samsung S23', 2, 899.00, 'Rua das Flores 45, São Paulo, Brazil', '+55-11-99876-5432', 'shipped', '2024-01-21'),
(3, 3, 'MacBook Pro 16"', 1, 2499.00, '123 Broadway Ave, New York, USA', '+1-212-555-0123', 'pending', '2024-01-22'),
(4, 4, 'iPhone 15 Pro', 1, 1199.99, 'ул. Ленина 15, Москва, Россия', '+7-495-123-4567', 'processing', '2024-01-23'),
(5, 5, 'ASUS ZenBook 14', 1, 999.00, '15 Rue de la Paix, Paris, France', '+33-6-12-34-56-78', 'delivered', '2024-01-24');

INSERT INTO system_logs VALUES
(1, 1, 'login_success', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'),
(2, 2, 'purchase_completed', '203.0.113.50', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15'),
(3, 3, 'password_change', '198.51.100.25', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148'),
(4, 4, 'account_viewed', '::1', 'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'),
(5, 5, 'order_cancelled', '2001:DB8::1', 'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0');

-- Summary:
-- - 5 customers from 5 different countries (Spain, Brazil, USA, Russia, France)
-- - 5 orders linking to customers via FK
-- - 5 system logs with IP addresses and user agents
-- - Fields include: names (Latin & Cyrillic scripts), emails, phones (various formats), dates, addresses
