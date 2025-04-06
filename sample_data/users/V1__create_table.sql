-- V1__create_table.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    fd VARCHAR(50),
    full_name VARCHAR(100),
); 

-- Add an index for faster username lookup
CREATE INDEX idx_users_username ON users (username);