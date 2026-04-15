-- Migration: Create email verification tokens table
-- Description: Adds email_verification_tokens table to support mandatory email verification on signup
-- Date: 2026-04-15

CREATE TABLE IF NOT EXISTS `email_verification_tokens` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `token` VARCHAR(255) NOT NULL COMMENT 'Verification token',
  `expires_at` TIMESTAMP NOT NULL COMMENT 'Token expiration time (24 hours)',
  `used` BOOLEAN DEFAULT FALSE COMMENT 'Whether token has been used',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_verification_token` (`token`),
  KEY `idx_verification_user_id` (`user_id`),
  KEY `idx_verification_expires_at` (`expires_at`),
  CONSTRAINT `fk_verification_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Email verification tokens for new user registration';
