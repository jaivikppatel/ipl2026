-- Migration 015: Switch fantasy data pipeline from Sportmonks Cricket API v2.0
--               to Statpal.io Cricket API v1
--
-- Changes:
--   1. Clean-slate truncation of all fantasy user/match data
--   2. fantasy_ipl_teams: rename sportmonks_team_id → statpal_team_id INT NULL
--   3. fantasy_ipl_players: rename sportmonks_player_id INT → statpal_player_id INT
--   4. fantasy_match_schedule: rename sportmonks_fixture_id INT → statpal_fixture_id BIGINT
--      (Statpal match IDs are large integers e.g. 13072008512, exceeding INT range)
--   5. fantasy_series: rename sportmonks_season_id INT → statpal_tournament_id INT
--      and ADD COLUMN tournament_type VARCHAR(20) DEFAULT 'intl'
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
-- 2. fantasy_ipl_teams: rename sportmonks_team_id → statpal_team_id
-- ============================================================================
ALTER TABLE fantasy_ipl_teams
    DROP INDEX idx_sportmonks_team_id;

ALTER TABLE fantasy_ipl_teams
    CHANGE COLUMN sportmonks_team_id statpal_team_id INT NULL
        COMMENT 'Integer team ID from Statpal API, auto-populated on first fixture sync';

ALTER TABLE fantasy_ipl_teams
    ADD UNIQUE KEY idx_statpal_team_id (statpal_team_id);

-- Re-seed the 10 IPL teams (statpal_team_id left NULL — auto-filled on first fixture sync)
INSERT INTO fantasy_ipl_teams (team_name, short_name, full_name, primary_color) VALUES
  ('Mumbai Indians',              'MI',   'Mumbai Indians',              '#004BA0'),
  ('Chennai Super Kings',         'CSK',  'Chennai Super Kings',         '#F9CD05'),
  ('Royal Challengers Bengaluru', 'RCB',  'Royal Challengers Bengaluru', '#EC1C24'),
  ('Kolkata Knight Riders',       'KKR',  'Kolkata Knight Riders',       '#3A225D'),
  ('Sunrisers Hyderabad',         'SRH',  'Sunrisers Hyderabad',         '#FF822A'),
  ('Delhi Capitals',              'DC',   'Delhi Capitals',              '#00008B'),
  ('Rajasthan Royals',            'RR',   'Rajasthan Royals',            '#E91E8C'),
  ('Punjab Kings',                'PBKS', 'Punjab Kings',                '#ED1C24'),
  ('Lucknow Super Giants',        'LSG',  'Lucknow Super Giants',        '#A2DFEE'),
  ('Gujarat Titans',              'GT',   'Gujarat Titans',              '#1C1C1C')
ON DUPLICATE KEY UPDATE team_name = VALUES(team_name);

-- ============================================================================
-- 3. fantasy_ipl_players: rename sportmonks_player_id → statpal_player_id
-- ============================================================================
ALTER TABLE fantasy_ipl_players
    DROP INDEX idx_sportmonks_player_id;

ALTER TABLE fantasy_ipl_players
    CHANGE COLUMN sportmonks_player_id statpal_player_id INT NOT NULL
        COMMENT 'Numeric profileid from Statpal API (squads.category.team[].player[].name field)';

ALTER TABLE fantasy_ipl_players
    ADD UNIQUE KEY idx_statpal_player_id (statpal_player_id);

-- ============================================================================
-- 4. fantasy_match_schedule: rename sportmonks_fixture_id INT → statpal_fixture_id BIGINT
--    Statpal match IDs like 13072008512 exceed the INT range (~2.1B), must use BIGINT.
-- ============================================================================
ALTER TABLE fantasy_match_schedule
    DROP INDEX idx_sportmonks_fixture_id;

ALTER TABLE fantasy_match_schedule
    CHANGE COLUMN sportmonks_fixture_id statpal_fixture_id BIGINT NOT NULL DEFAULT 0
        COMMENT 'Large-integer match ID from Statpal API (e.g. 13072008512)';

ALTER TABLE fantasy_match_schedule
    ADD UNIQUE KEY idx_statpal_fixture_id (statpal_fixture_id);

-- ============================================================================
-- 5. fantasy_series: rename sportmonks_season_id → statpal_tournament_id
--    and add tournament_type column (e.g. 'intl' or 'tour')
-- ============================================================================
ALTER TABLE fantasy_series
    DROP INDEX uq_sportmonks_season_id;

ALTER TABLE fantasy_series
    CHANGE COLUMN sportmonks_season_id statpal_tournament_id INT NOT NULL DEFAULT 0
        COMMENT 'Tournament ID from Statpal API (0 = not configured yet)';

ALTER TABLE fantasy_series
    ADD COLUMN tournament_type VARCHAR(20) NOT NULL DEFAULT 'intl'
        COMMENT 'Tournament type for Statpal API path: intl or tour'
        AFTER statpal_tournament_id;

ALTER TABLE fantasy_series
    ADD UNIQUE KEY uq_statpal_tournament_id (statpal_tournament_id);

-- Seed placeholder series row — admin must update statpal_tournament_id, tournament_type,
-- and set is_active=1 via the admin panel.
INSERT INTO fantasy_series (name, statpal_tournament_id, tournament_type, is_active)
VALUES ('IPL 2026', 0, 'intl', 0)
ON DUPLICATE KEY UPDATE name = name;
