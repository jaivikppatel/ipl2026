-- Migration 008: Add playing_xi_announced column to track post-toss XI announcement
-- This is separate from squad_fetched (which only means the full squad was loaded)
ALTER TABLE `fantasy_match_schedule`
  ADD COLUMN `playing_xi_announced` TINYINT(1) NOT NULL DEFAULT 0
    COMMENT 'Set to 1 after toss when playing XI is confirmed (playing11=true in match_squad API)'
    AFTER `squad_fetched`;

-- Also ensure is_playing_xi exists in match squads (should already exist from migration 006)
ALTER TABLE `fantasy_match_squads`
  MODIFY COLUMN `is_playing_xi` TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '1 if player is confirmed in playing XI for this match';
