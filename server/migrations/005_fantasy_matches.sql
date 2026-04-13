-- Migration: Fantasy Match Schedule & Squads
-- Description: Tables to track IPL 2026 matches from CricketData API and per-match playing XI
-- Date: 2026-04-13

CREATE TABLE IF NOT EXISTS `fantasy_match_schedule` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `cricapi_match_id` VARCHAR(36) NOT NULL COMMENT 'UUID match ID from CricketData API',
  `match_name` VARCHAR(255) NOT NULL COMMENT 'e.g. Mumbai Indians vs Chennai Super Kings',
  `short_name` VARCHAR(100) NULL COMMENT 'Short match label e.g. MI vs CSK',
  `team1_id` INT UNSIGNED NULL COMMENT 'FK to fantasy_ipl_teams',
  `team2_id` INT UNSIGNED NULL COMMENT 'FK to fantasy_ipl_teams',
  `match_date` DATE NULL,
  `match_datetime_gmt` DATETIME NULL COMMENT 'Match start time in UTC for deadline calculation',
  `venue` VARCHAR(255) NULL,
  `match_type` VARCHAR(20) NULL DEFAULT 't20',
  `status` ENUM('upcoming','live','completed','abandoned') NOT NULL DEFAULT 'upcoming',
  `status_note` VARCHAR(255) NULL COMMENT 'Human-readable status from API e.g. CSK won by 5 wickets',
  `squad_fetched` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether match_squad API has been called',
  `scorecard_fetched` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether final scorecard was fetched after match',
  `last_synced_at` TIMESTAMP NULL COMMENT 'Last time any API call updated this row',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_cricapi_match_id` (`cricapi_match_id`),
  KEY `idx_status` (`status`),
  KEY `idx_match_date` (`match_date`),
  KEY `idx_match_datetime_gmt` (`match_datetime_gmt`),
  KEY `idx_team1_id` (`team1_id`),
  KEY `idx_team2_id` (`team2_id`),
  CONSTRAINT `fk_fms_team1` FOREIGN KEY (`team1_id`) REFERENCES `fantasy_ipl_teams` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_fms_team2` FOREIGN KEY (`team2_id`) REFERENCES `fantasy_ipl_teams` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='IPL 2026 match schedule from CricketData API';

CREATE TABLE IF NOT EXISTS `fantasy_match_squads` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `match_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_match_schedule',
  `player_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_ipl_players',
  `is_announced` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether squad was announced',
  `is_playing_xi` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether player is in playing XI',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_match_player` (`match_id`, `player_id`),
  KEY `idx_match_id` (`match_id`),
  KEY `idx_player_id` (`player_id`),
  CONSTRAINT `fk_fms_match` FOREIGN KEY (`match_id`) REFERENCES `fantasy_match_schedule` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fms_player` FOREIGN KEY (`player_id`) REFERENCES `fantasy_ipl_players` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Per-match squad / playing XI data';
