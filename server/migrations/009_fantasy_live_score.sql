-- Migration 009: Add live_score column to store current innings scores for display
ALTER TABLE `fantasy_match_schedule`
  ADD COLUMN `live_score` TEXT DEFAULT NULL
    COMMENT 'JSON array of innings scores, e.g. [{"inning":"MI 1st","r":150,"w":3,"o":15.2}]'
    AFTER `status_note`;
