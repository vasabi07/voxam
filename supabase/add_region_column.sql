-- Add region column to User table
-- Default to 'india' for existing users
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "region" TEXT NOT NULL DEFAULT 'india';
