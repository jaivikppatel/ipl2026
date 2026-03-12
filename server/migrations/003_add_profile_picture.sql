-- Migration: Add profile_picture column to users table
-- Description: Adds support for storing user profile pictures as binary data

ALTER TABLE users 
ADD COLUMN profile_picture LONGBLOB NULL COMMENT 'Profile picture stored as binary data';

-- Add index for faster queries  
CREATE INDEX idx_users_profile_picture ON users(id);
