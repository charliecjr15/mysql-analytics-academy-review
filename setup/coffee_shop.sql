-- Query Grounds baseline database (MySQL 8.0+)
-- Safe for a dedicated learning environment. This resets coffee_shop completely.

DROP DATABASE IF EXISTS coffee_shop;
CREATE DATABASE coffee_shop CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE coffee_shop;

CREATE TABLE products (
    product_id INT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(6,3) NOT NULL,
    PRIMARY KEY (product_id)
);

INSERT INTO products (product_id, product_name, category, price) VALUES
    (1, 'Iced Latte', 'Coffee', 2.750),
    (2, 'Cold Brew', 'Coffee', 3.000),
    (3, 'Croissant', 'Pastry', 1.500),
    (4, 'Brownie', 'Dessert', 1.750),
    (5, 'Matcha Latte', 'Tea', 2.900),
    (6, 'Americano', 'Coffee', 1.250);

-- This baseline intentionally repeats product attributes. Sections 6 and 7
-- explain the risk and migrate the relationship to stable product IDs.
CREATE TABLE orders (
    order_id INT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(6,3) NOT NULL,
    order_date DATE NOT NULL,
    PRIMARY KEY (order_id),
    CONSTRAINT chk_orders_quantity CHECK (quantity > 0),
    CONSTRAINT chk_orders_price CHECK (unit_price >= 0)
);

INSERT INTO orders (order_id, product_name, category, quantity, unit_price, order_date) VALUES
    (1, 'Iced Latte', 'Coffee', 2, 2.750, '2026-06-20'),
    (2, 'Cold Brew', 'Coffee', 1, 3.000, '2026-06-20'),
    (3, 'Croissant', 'Pastry', 3, 1.500, '2026-06-20'),
    (4, 'Brownie', 'Dessert', 2, 1.750, '2026-06-21'),
    (5, 'Iced Latte', 'Coffee', 1, 2.750, '2026-06-21'),
    (6, 'Matcha Latte', 'Tea', 2, 2.900, '2026-06-21'),
    (7, 'Americano', 'Coffee', 4, 1.250, '2026-06-22'),
    (8, 'Cold Brew', 'Coffee', 2, 3.000, '2026-06-22'),
    (9, 'Croissant', 'Pastry', 1, 1.500, '2026-06-22'),
    (10, 'Iced Latte', 'Coffee', 3, 2.750, '2026-06-23');

SELECT 'products' AS table_name, COUNT(*) AS row_count FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;

SELECT SUM(quantity) AS expected_21_units,
       SUM(quantity * unit_price) AS expected_45_800_revenue
FROM orders;
