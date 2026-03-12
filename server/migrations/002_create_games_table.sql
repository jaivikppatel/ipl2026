-- Create ipl_matches table to track IPL fantasy points (F1-style scoring)
-- Points: 1st=25, 2nd=18, 3rd=15, 4th=12, 5th=10, 6th=8, 7th=6, 8th=4, 9th=2, 10th=1, 11+=0
CREATE TABLE IF NOT EXISTS ipl_matches (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    match_name VARCHAR(255) NOT NULL COMMENT 'e.g., MI vs CSK, RCB vs KKR',
    match_date DATE NOT NULL,
    user_rank INT NOT NULL COMMENT 'User ranking in this match (1-10+)',
    points INT NOT NULL COMMENT 'Points earned based on rank',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_match_date (match_date),
    INDEX idx_points (points)
);
