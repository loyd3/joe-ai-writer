-- 用户收藏脑洞表
CREATE TABLE IF NOT EXISTS saved_brainstorms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(64) DEFAULT '自定义',
    concept TEXT NOT NULL,
    source VARCHAR(32) DEFAULT 'manual',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
