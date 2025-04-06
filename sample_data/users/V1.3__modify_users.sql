-- Add essential columns for user authentication and profile
ALTER TABLE users
    ADD COLUMN password_hash VARCHAR(255) NOT NULL,
    ADD COLUMN bio TEXT,
    ADD COLUMN last_login TIMESTAMP NULL; -- Allow null for users who haven't logged in

-- Make the email unique now that it's established
ALTER TABLE users
    ADD CONSTRAINT uq_users_email UNIQUE (email);