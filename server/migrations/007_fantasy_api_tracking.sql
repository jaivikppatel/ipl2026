-- Migration: Fantasy API Call Tracking
-- Description: Track daily API usage to stay within the 2000 calls/day limit
-- Date: 2026-04-13

CREATE TABLE IF NOT EXISTS `fantasy_api_call_log` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `call_date` DATE NOT NULL COMMENT 'UTC date of the API calls',
  `calls_made` INT NOT NULL DEFAULT 0 COMMENT 'Total calls made on this date',
  `last_call_type` VARCHAR(50) NULL COMMENT 'Most recent API endpoint called',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_call_date` (`call_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Daily CricketData API call counter (limit: 2000/day)';
