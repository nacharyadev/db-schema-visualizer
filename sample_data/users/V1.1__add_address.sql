-- V2__drop_column.sql
ALTER TABLE users DROP COLUMN fd; 
ALTER TABLE users ADD COLUMN address VARCHAR(200); 