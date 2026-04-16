-- Migration 014: Switch fantasy data pipeline from CricAPI (cricketdata.org)
--               to Sportmonks Cricket API v2.0
--
-- Changes:
--   1. Clean-slate truncation of all fantasy user/match data
--   2. fantasy_ipl_teams: rename cricapi_team_name → team_name, add sportmonks_team_id INT
--   3. fantasy_ipl_players: rename cricapi_player_id VARCHAR(36) → sportmonks_player_id INT
--   4. fantasy_match_schedule: rename cricapi_match_id VARCHAR(36) → sportmonks_fixture_id INT
--   5. fantasy_series: rename cricapi_series_id VARCHAR(100) → sportmonks_season_id INT
--   6. Re-seed teams and placeholder series row

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================================
-- 1. TRUNCATE all fantasy data tables (dependency order doesn't matter with FK checks off)
-- ============================================================================
TRUNCATE TABLE fantasy_user_team_players;
TRUNCATE TABLE fantasy_user_selections;
TRUNCATE TABLE fantasy_match_leaderboard;
TRUNCATE TABLE fantasy_player_match_stats;
TRUNCATE TABLE fantasy_match_squads;
TRUNCATE TABLE fantasy_match_schedule;
TRUNCATE TABLE fantasy_ipl_players;
TRUNCATE TABLE fantasy_series_access;
TRUNCATE TABLE fantasy_api_call_log;
TRUNCATE TABLE fantasy_series;
TRUNCATE TABLE fantasy_ipl_teams;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- 2. fantasy_ipl_teams: rename cricapi_team_name → team_name, add sportmonks_team_id
-- ============================================================================
ALTER TABLE fantasy_ipl_teams
    DROP INDEX idx_cricapi_team_name;

ALTER TABLE fantasy_ipl_teams
    CHANGE COLUMN cricapi_team_name team_name VARCHAR(100) NOT NULL
        COMMENT 'Team name as used for display and fuzzy matching';

ALTER TABLE fantasy_ipl_teams
    ADD COLUMN sportmonks_team_id INT NULL
        COMMENT 'Integer team ID from Sportmonks API, auto-populated on first fixture sync'
        AFTER team_name,
    ADD UNIQUE KEY idx_sportmonks_team_id (sportmonks_team_id),
    ADD KEY idx_team_name (team_name);

-- Re-seed the 10 IPL teams (sportmonks_team_id left NULL — auto-filled on first fixture sync)
INSERT INTO fantasy_ipl_teams (team_name, short_name, full_name, primary_color) VALUES
  ('Mumbai Indians',            'MI',   'Mumbai Indians',              '#004BA0'),
  ('Chennai Super Kings',       'CSK',  'Chennai Super Kings',         '#F9CD05'),
  ('Royal Challengers Bengaluru','RCB', 'Royal Challengers Bengaluru', '#EC1C24'),
  ('Kolkata Knight Riders',     'KKR',  'Kolkata Knight Riders',       '#3A225D'),
  ('Sunrisers Hyderabad',       'SRH',  'Sunrisers Hyderabad',         '#FF822A'),
  ('Delhi Capitals',            'DC',   'Delhi Capitals',              '#00008B'),
  ('Rajasthan Royals',          'RR',   'Rajasthan Royals',            '#E91E8C'),
  ('Punjab Kings',              'PBKS', 'Punjab Kings',                '#ED1C24'),
  ('Lucknow Super Giants',      'LSG',  'Lucknow Super Giants',        '#A2DFEE'),
  ('Gujarat Titans',            'GT',   'Gujarat Titans',              '#1C1C1C')
ON DUPLICATE KEY UPDATE team_name = VALUES(team_name);

-- ============================================================================
-- 3. fantasy_ipl_players: rename cricapi_player_id VARCHAR(36) → sportmonks_player_id INT
-- ============================================================================
ALTER TABLE fantasy_ipl_players
    DROP INDEX idx_cricapi_player_id;

ALTER TABLE fantasy_ipl_players
    CHANGE COLUMN cricapi_player_id sportmonks_player_id INT NOT NULL
        COMMENT 'Integer player ID from Sportmonks API';

ALTER TABLE fantasy_ipl_players
    ADD UNIQUE KEY idx_sportmonks_player_id (sportmonks_player_id);

-- ============================================================================
-- 4. fantasy_match_schedule: rename cricapi_match_id VARCHAR(36) → sportmonks_fixture_id INT
-- ============================================================================
ALTER TABLE fantasy_match_schedule
    DROP INDEX idx_cricapi_match_id;

ALTER TABLE fantasy_match_schedule
    CHANGE COLUMN cricapi_match_id sportmonks_fixture_id INT NOT NULL
        COMMENT 'Integer fixture ID from Sportmonks API';

ALTER TABLE fantasy_match_schedule
    ADD UNIQUE KEY idx_sportmonks_fixture_id (sportmonks_fixture_id);

-- ============================================================================
-- 5. fantasy_series: rename cricapi_series_id VARCHAR(100) → sportmonks_season_id INT
-- ============================================================================
ALTER TABLE fantasy_series
    DROP INDEX uq_cricapi_series_id;

ALTER TABLE fantasy_series
    CHANGE COLUMN cricapi_series_id sportmonks_season_id INT NOT NULL DEFAULT 0
        COMMENT 'Integer season ID from Sportmonks API (0 = not configured yet)';

ALTER TABLE fantasy_series
    ADD UNIQUE KEY uq_sportmonks_season_id (sportmonks_season_id);

-- Seed placeholder series row — admin must update sportmonks_season_id and set is_active=1
-- via the admin panel once they know the correct Sportmonks season ID for IPL 2026.
INSERT INTO fantasy_series (name, sportmonks_season_id, is_active)
VALUES ('IPL 2026', 0, 0)
ON DUPLICATE KEY UPDATE name = name;
