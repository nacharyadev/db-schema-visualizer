-- Change the default status for posts and add an index
ALTER TABLE posts
    ALTER COLUMN status TYPE VARCHAR(30),
    ALTER COLUMN status SET DEFAULT "pending_review"; -- Changed default and maybe length

-- Add index for searching by status
CREATE INDEX idx_posts_status ON posts (status);

-- Let's also add an index on title for searching
CREATE INDEX idx_posts_title ON posts (title);