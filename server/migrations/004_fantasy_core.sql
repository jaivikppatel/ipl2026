-- Migration: Fantasy Core Tables - Teams & Players
-- Description: Standalone fantasy cricket tables for IPL 2026
-- Date: 2026-04-13

CREATE TABLE IF NOT EXISTS `fantasy_ipl_teams` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `cricapi_team_name` VARCHAR(100) NOT NULL COMMENT 'Team name as returned by CricketData API',
  `short_name` VARCHAR(10) NOT NULL COMMENT 'Short abbreviation e.g. MI, CSK, RCB',
  `full_name` VARCHAR(150) NOT NULL COMMENT 'Full franchise name',
  `logo_url` VARCHAR(500) NULL COMMENT 'URL to team logo from CDN',
  `primary_color` VARCHAR(7) NOT NULL DEFAULT '#333333' COMMENT 'Hex color for UI theming',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_short_name` (`short_name`),
  KEY `idx_cricapi_team_name` (`cricapi_team_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='IPL 2026 franchise teams';

CREATE TABLE IF NOT EXISTS `fantasy_ipl_players` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `cricapi_player_id` VARCHAR(36) NOT NULL COMMENT 'UUID from CricketData API',
  `name` VARCHAR(150) NOT NULL COMMENT 'Full player name',
  `team_id` INT UNSIGNED NOT NULL COMMENT 'FK to fantasy_ipl_teams',
  `role` ENUM('WK','BAT','AR','BOWL') NOT NULL COMMENT 'WK=Wicket-Keeper, BAT=Batsman, AR=All-Rounder, BOWL=Bowler',
  `batting_style` VARCHAR(50) NULL COMMENT 'e.g. Right Handed Bat',
  `bowling_style` VARCHAR(100) NULL COMMENT 'e.g. Right-arm fast',
  `country` VARCHAR(100) NULL,
  `credits` DECIMAL(4,1) NOT NULL DEFAULT 8.0 COMMENT 'Fantasy salary (out of 100cr team budget)',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Whether player is in IPL 2026 squad',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_cricapi_player_id` (`cricapi_player_id`),
  KEY `idx_team_id` (`team_id`),
  KEY `idx_role` (`role`),
  KEY `idx_credits` (`credits`),
  CONSTRAINT `fk_fantasy_players_team` FOREIGN KEY (`team_id`) REFERENCES `fantasy_ipl_teams` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='IPL 2026 player roster with fantasy credits';

-- Seed the 10 IPL 2026 teams
INSERT INTO `fantasy_ipl_teams` (`cricapi_team_name`, `short_name`, `full_name`, `primary_color`) VALUES
  ('Mumbai Indians', 'MI', 'Mumbai Indians', '#004BA0'),
  ('Chennai Super Kings', 'CSK', 'Chennai Super Kings', '#F9CD05'),
  ('Royal Challengers Bengaluru', 'RCB', 'Royal Challengers Bengaluru', '#EC1C24'),
  ('Kolkata Knight Riders', 'KKR', 'Kolkata Knight Riders', '#3A225D'),
  ('Sunrisers Hyderabad', 'SRH', 'Sunrisers Hyderabad', '#FF822A'),
  ('Delhi Capitals', 'DC', 'Delhi Capitals', '#00008B'),
  ('Rajasthan Royals', 'RR', 'Rajasthan Royals', '#E91E8C'),
  ('Punjab Kings', 'PBKS', 'Punjab Kings', '#ED1C24'),
  ('Lucknow Super Giants', 'LSG', 'Lucknow Super Giants', '#A2DFEE'),
  ('Gujarat Titans', 'GT', 'Gujarat Titans', '#1C4F9C')
ON DUPLICATE KEY UPDATE `full_name` = VALUES(`full_name`);
