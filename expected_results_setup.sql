-- Clean normalized schema used to capture Segments 7–13 in lesson order.
DROP DATABASE IF EXISTS course_audit;
CREATE DATABASE course_audit CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE course_audit;
CREATE TABLE products (
  product_id INT AUTO_INCREMENT PRIMARY KEY,
  product_name VARCHAR(100) NOT NULL,
  category VARCHAR(50) NOT NULL,
  price DECIMAL(6,3) NOT NULL
);
CREATE TABLE orders (
  order_id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  quantity INT NOT NULL,
  unit_price DECIMAL(6,3) NOT NULL,
  order_date DATE NOT NULL,
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);
INSERT INTO products (product_name, category, price) VALUES
('Iced Latte','Coffee',2.750),('Cold Brew','Coffee',3.000),('Croissant','Pastry',1.500),
('Brownie','Dessert',1.750),('Matcha Latte','Tea',2.900),('Americano','Coffee',1.250);
INSERT INTO orders (product_id, quantity, unit_price, order_date) VALUES
(1,2,2.750,'2026-06-20'),(2,1,3.000,'2026-06-20'),(3,3,1.500,'2026-06-20'),
(4,2,1.750,'2026-06-21'),(1,1,2.750,'2026-06-21'),(5,2,2.900,'2026-06-21'),
(6,4,1.250,'2026-06-22'),(2,2,3.000,'2026-06-22'),(3,1,1.500,'2026-06-22'),
(1,3,2.750,'2026-06-23');
CREATE TABLE products_staging AS SELECT * FROM products;
