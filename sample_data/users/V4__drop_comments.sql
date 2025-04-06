-- Simulate removing the comments feature entirely
-- Drop foreign keys first if necessary (handled by ON DELETE CASCADE/SET NULL here, but good practice)

--DROP TABLE comments;

-- Maybe we also decide the bio isn't needed anymore
ALTER TABLE users
    DROP COLUMN bio;