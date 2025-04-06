-- Table for comments on posts
CREATE TABLE comments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    commenter_id INT NULL, -- Allow anonymous comments initially
    comment_text VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE, -- Delete comments if post is deleted
    FOREIGN KEY (commenter_id) REFERENCES users(id) ON DELETE SET NULL -- Keep comment if user is deleted, but mark as anonymous
);

-- Index for retrieving comments for a specific post
CREATE INDEX idx_comments_post_id ON comments (post_id);