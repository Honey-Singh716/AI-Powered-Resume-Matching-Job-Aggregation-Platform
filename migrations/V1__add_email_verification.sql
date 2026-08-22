-- Add email verification fields to an existing users table without dropping data.
-- This migration is safe to run more than once.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS verification_token_hash VARCHAR(255);

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS verification_token_expires_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS verification_token_sent_at TIMESTAMP WITH TIME ZONE;

UPDATE users
SET is_verified = FALSE
WHERE is_verified IS NULL;

-- Optional: create an index on verification_token_hash for lookup
CREATE INDEX IF NOT EXISTS idx_users_verification_token_hash ON users (verification_token_hash);