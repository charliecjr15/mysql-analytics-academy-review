-- BeanRoute portfolio capstone — MySQL 8.0+
-- WARNING: resets only the dedicated beanroute_capstone database.
DROP DATABASE IF EXISTS beanroute_capstone;
CREATE DATABASE beanroute_capstone CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE beanroute_capstone;

CREATE TABLE stores (store_id INT PRIMARY KEY, store_name VARCHAR(80) NOT NULL, city VARCHAR(80) NOT NULL);
CREATE TABLE customers (customer_id INT PRIMARY KEY, customer_name VARCHAR(100) NOT NULL, email VARCHAR(150), signup_date DATE NOT NULL);
CREATE TABLE products (product_id INT PRIMARY KEY, product_name VARCHAR(100) NOT NULL, category VARCHAR(50), current_price DECIMAL(8,3));
CREATE TABLE orders (
  order_id INT PRIMARY KEY, store_id INT NOT NULL, customer_id INT, order_date DATE NOT NULL, status VARCHAR(20) NOT NULL,
  FOREIGN KEY (store_id) REFERENCES stores(store_id), FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
CREATE TABLE order_items (
  order_item_id INT PRIMARY KEY, order_id INT NOT NULL, product_id INT NOT NULL,
  raw_product_name VARCHAR(100), quantity INT, unit_price DECIMAL(8,3),
  FOREIGN KEY (order_id) REFERENCES orders(order_id), FOREIGN KEY (product_id) REFERENCES products(product_id)
);

INSERT INTO stores VALUES (1,'Central','Kuwait City'),(2,'Marina','Salmiya'),(3,'Campus','Shuwaikh');
INSERT INTO customers VALUES
(1,'Amina Saleh','amina@example.com','2025-11-02'),(2,'Omar Ali','omar@example.com','2025-12-12'),
(3,'Layla Noor','layla@example.com','2026-01-08'),(4,'Yousef Sami',NULL,'2026-01-20'),
(5,'Mariam Adel','mariam@example.com','2026-02-10'),(6,'Hamad Essa','hamad@example.com','2026-02-15'),
(7,'Noor Fahad','noor@example.com','2026-03-01'),(8,'Sara Nabil','sara@example.com','2026-03-05');
INSERT INTO products VALUES
(1,'Iced Latte','Coffee',2.750),(2,'Cold Brew','Coffee',3.000),(3,'Croissant','Pastry',1.500),
(4,'Brownie','Dessert',1.750),(5,'Matcha Latte','Tea',2.900),(6,'Americano','Coffee',1.250),
(7,'Turkey Sandwich','Food',3.800),(8,'Berry Bowl','Food',4.200),(9,'Seasonal Tea','',NULL);
INSERT INTO orders VALUES
(101,1,1,'2026-01-05','completed'),(102,1,2,'2026-01-18','completed'),(103,2,3,'2026-01-20','cancelled'),
(104,3,4,'2026-01-29','completed'),(105,2,5,'2026-02-02','completed'),(106,1,1,'2026-02-09','completed'),
(107,3,6,'2026-02-14','pending'),(108,2,2,'2026-02-21','completed'),(109,3,7,'2026-02-26','completed'),
(110,1,3,'2026-03-03','completed'),(111,2,5,'2026-03-08','completed'),(112,3,1,'2026-03-12','cancelled'),
(113,1,NULL,'2026-03-18','completed'),(114,2,6,'2026-03-22','completed'),(115,3,4,'2026-03-28','completed'),
(116,1,2,'2026-04-04','completed'),(117,2,3,'2026-04-11','completed'),(118,3,7,'2026-04-19','completed');
INSERT INTO order_items VALUES
(1,101,1,'Iced Latte',2,2.750),(2,101,3,'Croissant',1,1.500),(3,102,2,'Cold Brew',2,3.000),
(4,103,5,'Matcha Latte',2,2.900),(5,104,6,'Americano',4,1.250),(6,105,7,'Turkey Sandwich',2,3.800),
(7,105,2,'Cold Brew',1,3.000),(8,106,1,' iced latte ',3,2.750),(9,107,8,'Berry Bowl',2,4.200),
(10,108,5,'Matcha Latte',2,2.900),(11,109,3,'Croissant',5,1.500),(12,109,4,'Brownie',2,1.750),
(13,110,7,'Turkey Sandwich',1,3.800),(14,110,1,'Iced Latte',2,2.750),(15,111,8,'Berry Bowl',2,4.200),
(16,112,2,'Cold Brew',3,3.000),(17,113,6,'Americano',5,1.250),(18,114,5,'MATCHA LATTE',1,2.900),
(19,114,4,'Brownie',3,1.750),(20,115,3,'Croissant',NULL,1.500),(21,116,1,'Iced Latte',4,2.500),
(22,116,7,'Turkey Sandwich',2,3.800),(23,117,2,'Cold Brew',2,3.000),(24,117,8,'Berry Bowl',1,4.200),
(25,118,6,'Americano',6,1.250),(26,118,3,'Croissant',3,-1.500);

SELECT 'stores' table_name, COUNT(*) row_count FROM stores UNION ALL
SELECT 'customers',COUNT(*) FROM customers UNION ALL SELECT 'products',COUNT(*) FROM products UNION ALL
SELECT 'orders',COUNT(*) FROM orders UNION ALL SELECT 'order_items',COUNT(*) FROM order_items;
