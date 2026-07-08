-- MetroMart portfolio project dataset — MySQL 8.0+
-- WARNING: resets only the dedicated metromart_project database.
-- Purpose: larger simulated retail data for practicing every course section.

DROP DATABASE IF EXISTS metromart_project;
CREATE DATABASE metromart_project CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE metromart_project;
SET SESSION cte_max_recursion_depth = 6000;

CREATE TABLE regions (
    region_id INT PRIMARY KEY,
    region_name VARCHAR(80) NOT NULL
);

CREATE TABLE stores (
    store_id INT PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL,
    region_id INT NOT NULL,
    city VARCHAR(80) NOT NULL,
    opened_date DATE NOT NULL,
    store_format VARCHAR(30) NOT NULL,
    FOREIGN KEY (region_id) REFERENCES regions(region_id)
);

CREATE TABLE employees (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(100) NOT NULL,
    store_id INT NOT NULL,
    manager_id INT NULL,
    job_title VARCHAR(80) NOT NULL,
    hire_date DATE NOT NULL,
    active_flag CHAR(1) NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
);

CREATE TABLE product_categories (
    category_id INT PRIMARY KEY,
    category_name VARCHAR(80) NOT NULL,
    department VARCHAR(80) NOT NULL
);

CREATE TABLE products (
    product_id INT PRIMARY KEY,
    sku VARCHAR(30) NOT NULL,
    product_name VARCHAR(120) NOT NULL,
    category_id INT NOT NULL,
    brand VARCHAR(80),
    standard_cost DECIMAL(9,2) NOT NULL,
    list_price DECIMAL(9,2) NOT NULL,
    launch_date DATE NOT NULL,
    discontinued_flag CHAR(1) NOT NULL DEFAULT 'N',
    FOREIGN KEY (category_id) REFERENCES product_categories(category_id)
);

CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(120) NOT NULL,
    email VARCHAR(160),
    phone VARCHAR(40),
    city VARCHAR(80),
    signup_date DATE NOT NULL,
    loyalty_tier VARCHAR(30),
    birth_date DATE
);

CREATE TABLE promotions (
    promotion_id INT PRIMARY KEY,
    promotion_name VARCHAR(120) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    discount_pct DECIMAL(5,2) NOT NULL
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    store_id INT NOT NULL,
    customer_id INT NULL,
    employee_id INT NOT NULL,
    order_date DATETIME NOT NULL,
    channel VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    promotion_id INT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    FOREIGN KEY (promotion_id) REFERENCES promotions(promotion_id)
);

CREATE TABLE order_items (
    order_item_id INT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT,
    unit_price DECIMAL(9,2),
    discount_amount DECIMAL(9,2) NOT NULL DEFAULT 0,
    raw_product_name VARCHAR(140),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE returns (
    return_id INT PRIMARY KEY,
    order_item_id INT NOT NULL,
    return_date DATE NOT NULL,
    return_reason VARCHAR(100) NOT NULL,
    refund_amount DECIMAL(9,2) NOT NULL,
    FOREIGN KEY (order_item_id) REFERENCES order_items(order_item_id)
);

CREATE TABLE inventory_snapshots (
    snapshot_id INT PRIMARY KEY,
    store_id INT NOT NULL,
    product_id INT NOT NULL,
    snapshot_date DATE NOT NULL,
    on_hand_quantity INT NOT NULL,
    reorder_point INT NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE customer_feedback (
    feedback_id INT PRIMARY KEY,
    order_id INT NOT NULL,
    rating INT,
    comment_text VARCHAR(255),
    submitted_at DATETIME NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE raw_customer_import (
    import_id INT PRIMARY KEY,
    raw_name VARCHAR(120),
    raw_email VARCHAR(160),
    raw_phone VARCHAR(40),
    raw_city VARCHAR(80),
    raw_loyalty_tier VARCHAR(40),
    import_batch VARCHAR(30) NOT NULL
);

INSERT INTO regions VALUES
(1,'Capital'),(2,'Coastal'),(3,'University'),(4,'Suburban');

INSERT INTO stores VALUES
(1,'MetroMart Downtown',1,'Kuwait City','2024-01-10','Flagship'),
(2,'MetroMart Marina',2,'Salmiya','2024-03-15','Mall'),
(3,'MetroMart Campus',3,'Shuwaikh','2024-09-01','Express'),
(4,'MetroMart Oasis',4,'Farwaniya','2025-02-20','Neighborhood'),
(5,'MetroMart Seaside',2,'Mahboula','2025-05-12','Mall'),
(6,'MetroMart Gate',1,'Hawalli','2025-10-05','Express');

INSERT INTO employees VALUES
(1,'Maya Haddad',1,NULL,'Operations Director','2023-12-01','Y'),
(2,'Omar Nasser',1,1,'Store Manager','2024-01-05','Y'),
(3,'Lina Karim',2,1,'Store Manager','2024-03-01','Y'),
(4,'Fahad Salem',3,1,'Store Manager','2024-08-15','Y'),
(5,'Noura Adel',4,1,'Store Manager','2025-02-01','Y'),
(6,'Hamad Essa',5,1,'Store Manager','2025-05-01','Y'),
(7,'Sara Nabil',6,1,'Store Manager','2025-09-20','Y'),
(8,'Zaid Khaled',1,2,'Sales Associate','2024-01-18','Y'),
(9,'Amal Noor',2,3,'Sales Associate','2024-04-05','Y'),
(10,'Yousef Sami',3,4,'Sales Associate','2024-09-12','Y'),
(11,'Layla Mansour',4,5,'Sales Associate','2025-02-25','Y'),
(12,'Rami Saleh',5,6,'Sales Associate','2025-05-20','Y'),
(13,'Dana Fares',6,7,'Sales Associate','2025-10-18','Y'),
(14,'Kareem Ali',1,2,'Sales Associate','2024-02-01','N');

INSERT INTO product_categories VALUES
(1,'Coffee','Grocery'),(2,'Tea','Grocery'),(3,'Bakery','Fresh Food'),(4,'Prepared Meals','Fresh Food'),
(5,'Household','Home'),(6,'Personal Care','Health'),(7,'Electronics','General Merchandise'),(8,'Seasonal','General Merchandise');

INSERT INTO products VALUES
(1,'COF-100','Iced Latte 250ml',1,'BeanRoute',0.85,2.75,'2024-01-01','N'),
(2,'COF-101','Cold Brew 300ml',1,'BeanRoute',1.05,3.10,'2024-01-01','N'),
(3,'COF-102','Espresso Beans 500g',1,'BeanRoute',3.80,7.90,'2024-05-15','N'),
(4,'TEA-200','Matcha Latte 250ml',2,'LeafLab',0.95,2.90,'2024-02-10','N'),
(5,'TEA-201','Mint Tea Box',2,'LeafLab',1.10,2.40,'2024-02-10','N'),
(6,'BAK-300','Butter Croissant',3,'Oven&Co',0.45,1.50,'2024-01-15','N'),
(7,'BAK-301','Chocolate Brownie',3,'Oven&Co',0.60,1.85,'2024-01-15','N'),
(8,'MEAL-400','Turkey Sandwich',4,'FreshDesk',1.80,3.95,'2024-04-01','N'),
(9,'MEAL-401','Berry Yogurt Bowl',4,'FreshDesk',1.90,4.25,'2024-04-01','N'),
(10,'HH-500','Eco Dish Soap',5,'CleanNest',0.95,2.25,'2024-06-01','N'),
(11,'HH-501','Paper Towels 2-pack',5,'CleanNest',1.75,3.80,'2024-06-01','N'),
(12,'PC-600','Travel Hand Sanitizer',6,'CarePlus',0.40,1.25,'2024-03-10','N'),
(13,'PC-601','Bamboo Toothbrush',6,'CarePlus',0.70,1.90,'2024-03-10','N'),
(14,'ELE-700','Wireless Earbuds Basic',7,'MetroTech',6.50,14.90,'2024-11-20','N'),
(15,'ELE-701','USB-C Cable 1m',7,'MetroTech',1.20,4.50,'2024-11-20','N'),
(16,'SEA-800','Ramadan Gift Tin',8,'MetroMart',4.00,9.90,'2026-02-01','N'),
(17,'SEA-801','Summer Cooler Bag',8,'MetroMart',3.50,8.75,'2026-05-01','N'),
(18,'TEA-OLD','Seasonal Tea Old Label',2,'LeafLab',1.00,2.20,'2023-12-01','Y');

INSERT INTO promotions VALUES
(1,'New Year Grocery Boost','2026-01-01','2026-01-20',10.00),
(2,'February Fresh Food','2026-02-01','2026-02-28',12.50),
(3,'Ramadan Essentials','2026-03-01','2026-03-31',15.00),
(4,'Spring Electronics','2026-04-01','2026-04-20',8.00),
(5,'Summer Prep','2026-05-01','2026-06-15',10.00);

INSERT INTO customers VALUES
(1,'Amina Saleh','amina.saleh@example.com','555-0101','Kuwait City','2024-01-12','Gold','1991-04-12'),
(2,'Omar Ali','omar.ali@example.com','555-0102','Salmiya','2024-02-03','Silver','1988-07-20'),
(3,'Layla Noor','layla.noor@example.com','555-0103','Hawalli','2024-03-18','Bronze','1997-11-05'),
(4,'Yousef Sami',NULL,'555-0104','Shuwaikh','2024-05-01','Silver','1985-01-13'),
(5,'Mariam Adel','mariam.adel@example.com','555-0105','Farwaniya','2024-06-09','Gold','1993-02-28'),
(6,'Hamad Essa','hamad.essa@example.com','555-0106','Mahboula','2024-07-14','Bronze','2000-10-02'),
(7,'Noor Fahad','noor.fahad@example.com','555-0107','Salmiya','2024-08-22','Silver','1996-09-17'),
(8,'Sara Nabil','sara.nabil@example.com','555-0108','Kuwait City','2024-09-30','Gold','1990-12-08'),
(9,'Test Customer','test@example.com','000-0000','Test City','2024-10-01','Bronze','1999-01-01'),
(10,'Amina Saleh',' AMINA.SALEH@example.com ','5550101','kuwait city','2025-01-05','gold','1991-04-12');

INSERT INTO raw_customer_import VALUES
(1,' Amina Saleh ','AMINA.SALEH@example.com','5550101','kuwait city','gold','batch_2026_06'),
(2,'Omar Ali','omar.ali@example.com','555-0102','Salmiya','Silver','batch_2026_06'),
(3,'Layla Noor','layla.noor@example.com','','Hawalli','bronze','batch_2026_06'),
(4,'Yousef Sami',NULL,'555-0104','Shuwaikh','Silver','batch_2026_06'),
(5,'Bad Email Person','not-an-email','555-0199','Farwaniya','Platinum','batch_2026_06'),
(6,'','blank.name@example.com','555-0188',' ','Bronze','batch_2026_06'),
(7,'Amina Saleh','amina.saleh@example.com','555-0101','Kuwait City','Gold','batch_2026_06');

-- Add 240 additional synthetic customers, with intentional blanks, duplicate-like emails, and tier variants.
INSERT INTO customers (customer_id, customer_name, email, phone, city, signup_date, loyalty_tier, birth_date)
WITH RECURSIVE seq(n) AS (
    SELECT 11
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 250
)
SELECT
    n,
    CONCAT('Customer ', LPAD(n, 3, '0')),
    CASE
        WHEN n % 37 = 0 THEN NULL
        WHEN n % 41 = 0 THEN CONCAT(' customer', n, '@example.com ')
        ELSE CONCAT('customer', n, '@example.com')
    END,
    CASE WHEN n % 29 = 0 THEN '' ELSE CONCAT('555-', LPAD(1000 + n, 4, '0')) END,
    CASE n % 7
        WHEN 0 THEN 'Kuwait City'
        WHEN 1 THEN 'Salmiya'
        WHEN 2 THEN 'Hawalli'
        WHEN 3 THEN 'Shuwaikh'
        WHEN 4 THEN 'Farwaniya'
        WHEN 5 THEN 'Mahboula'
        ELSE ''
    END,
    DATE_ADD('2024-01-01', INTERVAL (n * 3) DAY),
    CASE n % 5 WHEN 0 THEN 'Gold' WHEN 1 THEN 'Silver' WHEN 2 THEN 'Bronze' WHEN 3 THEN 'gold' ELSE NULL END,
    DATE_ADD('1975-01-01', INTERVAL (n * 47) DAY)
FROM seq;

-- Add 1,800 orders across six months and channels.
INSERT INTO orders (order_id, store_id, customer_id, employee_id, order_date, channel, status, payment_method, promotion_id)
WITH RECURSIVE seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 1800
)
SELECT
    100000 + n AS order_id,
    1 + (n % 6) AS store_id,
    CASE WHEN n % 113 = 0 THEN NULL ELSE 1 + (n % 250) END AS customer_id,
    CASE 1 + (n % 6)
        WHEN 1 THEN IF(n % 5 = 0, 8, 2)
        WHEN 2 THEN IF(n % 5 = 0, 9, 3)
        WHEN 3 THEN IF(n % 5 = 0, 10, 4)
        WHEN 4 THEN IF(n % 5 = 0, 11, 5)
        WHEN 5 THEN IF(n % 5 = 0, 12, 6)
        ELSE IF(n % 5 = 0, 13, 7)
    END AS employee_id,
    TIMESTAMP(DATE_ADD('2026-01-01', INTERVAL (n % 181) DAY), MAKETIME(8 + (n % 14), (n * 7) % 60, 0)) AS order_date,
    CASE n % 4 WHEN 0 THEN 'Store' WHEN 1 THEN 'Pickup' WHEN 2 THEN 'Delivery' ELSE 'Kiosk' END AS channel,
    CASE
        WHEN n % 53 = 0 THEN 'cancelled'
        WHEN n % 71 = 0 THEN 'pending'
        WHEN n % 97 = 0 THEN 'refunded'
        ELSE 'completed'
    END AS status,
    CASE n % 5 WHEN 0 THEN 'Cash' WHEN 1 THEN 'Card' WHEN 2 THEN 'KNET' WHEN 3 THEN 'Apple Pay' ELSE 'Gift Card' END AS payment_method,
    CASE
        WHEN DATE_ADD('2026-01-01', INTERVAL (n % 181) DAY) BETWEEN '2026-01-01' AND '2026-01-20' THEN 1
        WHEN DATE_ADD('2026-01-01', INTERVAL (n % 181) DAY) BETWEEN '2026-02-01' AND '2026-02-28' THEN 2
        WHEN DATE_ADD('2026-01-01', INTERVAL (n % 181) DAY) BETWEEN '2026-03-01' AND '2026-03-31' THEN 3
        WHEN DATE_ADD('2026-01-01', INTERVAL (n % 181) DAY) BETWEEN '2026-04-01' AND '2026-04-20' THEN 4
        WHEN DATE_ADD('2026-01-01', INTERVAL (n % 181) DAY) BETWEEN '2026-05-01' AND '2026-06-15' THEN 5
        ELSE NULL
    END AS promotion_id
FROM seq;

-- Add three item rows per order: 5,400 order item rows total.
INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, discount_amount, raw_product_name)
WITH RECURSIVE seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 5400
)
SELECT
    200000 + n AS order_item_id,
    100000 + CEIL(n / 3) AS order_id,
    1 + ((n * 7) % 18) AS product_id,
    CASE
        WHEN n % 811 = 0 THEN NULL
        WHEN n % 997 = 0 THEN -1
        ELSE 1 + (n % 4)
    END AS quantity,
    CASE
        WHEN n % 887 = 0 THEN -2.00
        WHEN n % 3 = 0 THEN ROUND(p.list_price * 0.95, 2)
        WHEN n % 10 = 0 THEN ROUND(p.list_price * 1.05, 2)
        ELSE p.list_price
    END AS unit_price,
    CASE WHEN n % 6 = 0 THEN ROUND(p.list_price * 0.10, 2) ELSE 0 END AS discount_amount,
    CASE
        WHEN n % 43 = 0 THEN CONCAT(' ', p.product_name, ' ')
        WHEN n % 47 = 0 THEN UPPER(p.product_name)
        WHEN n % 101 = 0 THEN REPLACE(p.product_name, 'Latte', 'Latte ')
        ELSE p.product_name
    END AS raw_product_name
FROM seq
JOIN products AS p ON p.product_id = 1 + ((n * 7) % 18);

-- Add 130 returns tied to real item rows.
INSERT INTO returns (return_id, order_item_id, return_date, return_reason, refund_amount)
WITH RECURSIVE seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 130
)
SELECT
    300000 + n,
    200000 + (n * 37),
    DATE_ADD(DATE((SELECT order_date FROM orders WHERE order_id = 100000 + CEIL((n * 37) / 3))), INTERVAL (2 + (n % 10)) DAY),
    CASE n % 5 WHEN 0 THEN 'Damaged' WHEN 1 THEN 'Changed mind' WHEN 2 THEN 'Wrong item' WHEN 3 THEN 'Late delivery' ELSE 'Quality issue' END,
    ROUND(GREATEST(0, (SELECT quantity * unit_price - discount_amount FROM order_items WHERE order_item_id = 200000 + (n * 37))), 2)
FROM seq;

-- Add 648 inventory snapshots: 6 stores x 18 products x 6 month-start dates.
INSERT INTO inventory_snapshots (snapshot_id, store_id, product_id, snapshot_date, on_hand_quantity, reorder_point)
WITH RECURSIVE seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 648
)
SELECT
    400000 + n,
    1 + ((n - 1) % 6) AS store_id,
    1 + (FLOOR((n - 1) / 6) % 18) AS product_id,
    DATE_ADD('2026-01-01', INTERVAL FLOOR((n - 1) / 108) MONTH) AS snapshot_date,
    CASE WHEN n % 59 = 0 THEN 0 ELSE 5 + ((n * 13) % 120) END AS on_hand_quantity,
    12 + ((n * 5) % 20) AS reorder_point
FROM seq;

-- Add feedback on roughly every fourth order, including imperfect ratings/comments.
INSERT INTO customer_feedback (feedback_id, order_id, rating, comment_text, submitted_at)
WITH RECURSIVE seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 450
)
SELECT
    500000 + n,
    100000 + (n * 4),
    CASE WHEN n % 89 = 0 THEN NULL WHEN n % 97 = 0 THEN 6 ELSE 1 + (n % 5) END,
    CASE n % 6
        WHEN 0 THEN 'Fast checkout'
        WHEN 1 THEN 'Fresh food was good'
        WHEN 2 THEN 'Price label was confusing'
        WHEN 3 THEN 'Delivery took too long'
        WHEN 4 THEN ''
        ELSE 'Staff were helpful'
    END,
    DATE_ADD((SELECT order_date FROM orders WHERE order_id = 100000 + (n * 4)), INTERVAL 1 DAY)
FROM seq;

SELECT 'regions' AS table_name, COUNT(*) AS row_count FROM regions
UNION ALL SELECT 'stores', COUNT(*) FROM stores
UNION ALL SELECT 'employees', COUNT(*) FROM employees
UNION ALL SELECT 'product_categories', COUNT(*) FROM product_categories
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'promotions', COUNT(*) FROM promotions
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'returns', COUNT(*) FROM returns
UNION ALL SELECT 'inventory_snapshots', COUNT(*) FROM inventory_snapshots
UNION ALL SELECT 'customer_feedback', COUNT(*) FROM customer_feedback
UNION ALL SELECT 'raw_customer_import', COUNT(*) FROM raw_customer_import;

SELECT
    COUNT(*) AS order_rows,
    SUM(status = 'completed') AS completed_orders,
    MIN(order_date) AS first_order_at,
    MAX(order_date) AS last_order_at
FROM orders;
