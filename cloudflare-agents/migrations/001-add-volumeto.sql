-- Migration: Add volume_to column and rename volume to volume_from
-- SQLite doesn't support column renaming directly, so we need to:
-- 1. Add new columns
-- 2. Copy data
-- 3. Drop old column (if needed)

-- Add volume_to column
ALTER TABLE price_data ADD COLUMN volume_to REAL;

-- For backward compatibility, volume_from will be populated from existing 'volume' column
-- The application code will handle this during data collection
