-- Migration 011: Multi-series fantasy cricket support
--
-- 1. Creates fantasy_series table to store CricketData series IDs with names.
--    The series ID previously hardcoded in FANTASY_IPL_SERIES_ID env var is seeded here.
-- 2. Adds series_id FK column to fantasy_match_schedule.
-- 3. Backfills all existing matches to the IPL 2026 series (id=1).
-- 4. Creates fantasy_series_access table: presence of a row = user is allowed to
--    create a team in that series. Default = blocked (no row = no access).

-- ============================================================================
-- 1. fantasy_series
-- ============================================================================

CREATE TABLE IF NOT EXISTS fantasy_series (
    id                INT NOT NULL AUTO_INCREMENT,
    name              VARCHAR(255) NOT NULL,
    cricapi_series_id VARCHAR(100) NOT NULL,
    is_active         TINYINT(1)   NOT NULL DEFAULT 1,
    created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cricapi_series_id (cricapi_series_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed: current IPL 2026 series (was previously in FANTASY_IPL_SERIES_ID env var)
INSERT INTO fantasy_series (name, cricapi_series_id, is_active)
VALUES ('IPL 2026', '87c62aac-bc3c-4738-ab93-19da0690488f', 1)
ON DUPLICATE KEY UPDATE name = name;  -- no-op if already seeded

-- ============================================================================
-- 2. Add series_id to fantasy_match_schedule
-- ============================================================================

ALTER TABLE fantasy_match_schedule
    ADD COLUMN series_id INT NOT NULL DEFAULT 1
        AFTER id;

ALTER TABLE fantasy_match_schedule
    ADD CONSTRAINT fk_fms_series
        FOREIGN KEY (series_id) REFERENCES fantasy_series(id)
        ON DELETE RESTRICT ON UPDATE CASCADE;

-- ============================================================================
-- 3. Backfill existing matches → IPL 2026 (id = 1)
-- ============================================================================

UPDATE fantasy_match_schedule SET series_id = 1;

-- ============================================================================
-- 4. fantasy_series_access
--    Row presence = user is allowed to create a team in that series.
--    No row = access denied (default).
-- ============================================================================

CREATE TABLE IF NOT EXISTS fantasy_series_access (
    id         INT              NOT NULL AUTO_INCREMENT,
    user_id    BIGINT UNSIGNED  NOT NULL,
    series_id  INT              NOT NULL,
    granted_at TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_series (user_id, series_id),
    CONSTRAINT fk_fsa_user   FOREIGN KEY (user_id)   REFERENCES users(id)          ON DELETE CASCADE,
    CONSTRAINT fk_fsa_series FOREIGN KEY (series_id) REFERENCES fantasy_series(id)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
