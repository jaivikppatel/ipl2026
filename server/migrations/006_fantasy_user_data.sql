-- Migration: Fantasy User Data - Teams, Stats, Leaderboard
-- Description: Per-user team selections, per-player match stats, per-match leaderboard
-- Date: 2026-04-13

-- Table: User's team selection for a match (1 team per user per match)
CREATE TABLE IF NOT EXISTS `fantasy_user_selections` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT 'FK to users.id',
  `match_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_match_schedule',
  `is_locked` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Locked at match start, no edits after this',
  `total_credits_used` DECIMAL(5,1) NOT NULL DEFAULT 0 COMMENT 'Sum of selected player credits at time of submission',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_user_match` (`user_id`, `match_id`),
  KEY `idx_match_id` (`match_id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `fk_fus_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fus_match` FOREIGN KEY (`match_id`) REFERENCES `fantasy_match_schedule` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Fantasy team selection per user per match';

-- Table: Which 11 players in a user's team, with Captain/VC flags
CREATE TABLE IF NOT EXISTS `fantasy_user_team_players` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `selection_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_user_selections',
  `player_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_ipl_players',
  `is_captain` TINYINT(1) NOT NULL DEFAULT 0,
  `is_vice_captain` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_selection_player` (`selection_id`, `player_id`),
  KEY `idx_selection_id` (`selection_id`),
  KEY `idx_player_id` (`player_id`),
  CONSTRAINT `fk_futp_selection` FOREIGN KEY (`selection_id`) REFERENCES `fantasy_user_selections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_futp_player` FOREIGN KEY (`player_id`) REFERENCES `fantasy_ipl_players` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Individual players in a user fantasy team';

-- Table: Per-player stats for each match (populated from scorecard API)
CREATE TABLE IF NOT EXISTS `fantasy_player_match_stats` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `match_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_match_schedule',
  `player_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_ipl_players',
  -- Batting stats
  `runs_scored` INT NOT NULL DEFAULT 0,
  `balls_faced` INT NOT NULL DEFAULT 0,
  `fours` INT NOT NULL DEFAULT 0,
  `sixes` INT NOT NULL DEFAULT 0,
  `is_dismissed` TINYINT(1) NOT NULL DEFAULT 0,
  `is_duck` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0 runs and dismissed',
  -- Bowling stats
  `wickets` INT NOT NULL DEFAULT 0,
  `balls_bowled` INT NOT NULL DEFAULT 0 COMMENT 'Balls bowled (multiply by 6 for full overs)',
  `runs_conceded` INT NOT NULL DEFAULT 0,
  `maidens` INT NOT NULL DEFAULT 0,
  -- Fielding stats
  `catches` INT NOT NULL DEFAULT 0,
  `stumpings` INT NOT NULL DEFAULT 0,
  `run_outs_direct` INT NOT NULL DEFAULT 0,
  `run_outs_indirect` INT NOT NULL DEFAULT 0,
  -- Did bat/bowl flags (to distinguish 0 from did-not-bat)
  `did_bat` TINYINT(1) NOT NULL DEFAULT 0,
  `did_bowl` TINYINT(1) NOT NULL DEFAULT 0,
  -- Calculated fantasy points (stored for quick leaderboard queries)
  `fantasy_points` DECIMAL(7,2) NOT NULL DEFAULT 0,
  `last_updated` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_match_player` (`match_id`, `player_id`),
  KEY `idx_match_id` (`match_id`),
  KEY `idx_player_id` (`player_id`),
  KEY `idx_fantasy_points` (`fantasy_points`),
  CONSTRAINT `fk_fpms_match` FOREIGN KEY (`match_id`) REFERENCES `fantasy_match_schedule` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fpms_player` FOREIGN KEY (`player_id`) REFERENCES `fantasy_ipl_players` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Player batting/bowling/fielding stats per match and calculated fantasy points';

-- Table: Per-match leaderboard computed from user selections + player stats
CREATE TABLE IF NOT EXISTS `fantasy_match_leaderboard` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `match_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_match_schedule',
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT 'FK to users',
  `total_points` DECIMAL(8,2) NOT NULL DEFAULT 0 COMMENT 'Sum of player points with C/VC multipliers applied',
  `rank` INT NULL COMMENT 'Rank among all users for this match (NULL if not yet ranked)',
  `captain_player_id` INT UNSIGNED NULL COMMENT 'Denormalized for quick display',
  `vice_captain_player_id` INT UNSIGNED NULL COMMENT 'Denormalized for quick display',
  `last_updated` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_match_user` (`match_id`, `user_id`),
  KEY `idx_match_id` (`match_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_total_points` (`total_points`),
  KEY `idx_rank` (`rank`),
  CONSTRAINT `fk_fml_match` FOREIGN KEY (`match_id`) REFERENCES `fantasy_match_schedule` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fml_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Computed per-match leaderboard for fantasy game';
