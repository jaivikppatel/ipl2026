-- Migration 016: Add blob image storage to fantasy_ipl_players
-- image_data: stores base64 data URI like data:image/jpeg followed by base64 encoded bytes
-- image_data_url: tracks which image_url was used to populate image_data
--                 used for change detection (stale when image_url != image_data_url)

ALTER TABLE fantasy_ipl_players
  ADD COLUMN image_data MEDIUMTEXT NULL AFTER image_url,
  ADD COLUMN image_data_url VARCHAR(500) NULL AFTER image_data
