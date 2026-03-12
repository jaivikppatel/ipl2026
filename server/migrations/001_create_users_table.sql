-- Migration: Create users table
-- Description: Creates the users table to store user authentication and profile information
-- Date: 2026-01-14

-- Drop tables if exists (use with caution in production)
-- Must drop sessions first due to foreign key constraint
DROP TABLE IF EXISTS `password_reset_tokens`;
DROP TABLE IF EXISTS `user_sessions`;
DROP TABLE IF EXISTS `users`;

-- Create users table
CREATE TABLE `users` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `display_name` VARCHAR(100) NOT NULL COMMENT 'Public display name visible to other users',
  `email` VARCHAR(255) NOT NULL COMMENT 'User email for authentication',
  `password_hash` VARCHAR(255) NOT NULL COMMENT 'Hashed password using bcrypt',
  `email_verified` BOOLEAN DEFAULT FALSE COMMENT 'Email verification status',
  `is_active` BOOLEAN DEFAULT TRUE COMMENT 'Account active status',
  `last_login` TIMESTAMP NULL DEFAULT NULL COMMENT 'Last login timestamp',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Account creation timestamp',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_email_unique` (`email`),
  KEY `idx_display_name` (`display_name`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_email_active` (`email`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User accounts and authentication information';

-- Create a sessions table for managing user sessions
CREATE TABLE `user_sessions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `session_token` VARCHAR(255) NOT NULL COMMENT 'Unique session token',
  `ip_address` VARCHAR(45) NULL COMMENT 'IP address of the session',
  `user_agent` VARCHAR(500) NULL COMMENT 'Browser/device user agent',
  `expires_at` TIMESTAMP NOT NULL COMMENT 'Session expiration time',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_session_token` (`session_token`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_expires_at` (`expires_at`),
  KEY `idx_user_expires` (`user_id`, `expires_at`),
  CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User session management';

-- Create password reset tokens table
CREATE TABLE `password_reset_tokens` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `token` VARCHAR(255) NOT NULL COMMENT 'Reset token',
  `expires_at` TIMESTAMP NOT NULL COMMENT 'Token expiration time',
  `used` BOOLEAN DEFAULT FALSE COMMENT 'Whether token has been used',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_token` (`token`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_expires_at` (`expires_at`),
  CONSTRAINT `fk_reset_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Password reset tokens';