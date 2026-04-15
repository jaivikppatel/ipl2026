-- Migration 010: Add image_url column to fantasy_ipl_players
-- Stores the CDN image URL from the CricketData.org match_squad API (playerImg field)
-- NULL means no image available (default placeholder filtered out at application level)

ALTER TABLE fantasy_ipl_players
  ADD COLUMN image_url VARCHAR(500) NULL AFTER country;
