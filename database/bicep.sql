CREATE DATABASE IF NOT EXISTS bicepdb;

USE bicepdb;

CREATE TABLE IF NOT EXISTS fruits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL
);

INSERT INTO fruits (name, quantity) VALUES
    ('Apple', 10),
    ('Banana', 20),
    ('Cherry', 30);