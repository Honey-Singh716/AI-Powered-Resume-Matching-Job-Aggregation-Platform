-- Add email verification fields to users table
-- Run this using your DB migration tool or apply manually against PostgreSQL

ALTER TABLE users
  ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE users
  ADD COLUMN verification_token_hash VARCHAR(255);

ALTER TABLE users
  ADD COLUMN verification_token_expires_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE users
  ADD COLUMN verification_token_sent_at TIMESTAMP WITH TIME ZONE;

-- Optional: create an index on verification_token_hash for lookup
CREATE INDEX IF NOT EXISTS idx_users_verification_token_hash ON users (verification_token_hash);