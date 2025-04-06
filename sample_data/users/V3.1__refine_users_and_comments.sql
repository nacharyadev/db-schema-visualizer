-- Decide 'full_name' isn't needed on users table
ALTER TABLE users
    DROP COLUMN full_name;

-- Make comments require a commenter (no longer anonymous)
-- NOTE: This would require data migration in real life if anonymous comments exist!
-- Here, we just alter the schema constraint.
ALTER TABLE comments
    ALTER COLUMN commenter_id SET NOT NULL; -- Change NULL constraint

-- Let's drop the title index on posts, maybe it wasn't useful
DROP INDEX idx_posts_title ON posts;