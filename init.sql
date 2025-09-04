-- Database initialization script for the Telegram RPG game bot
-- This script is run when the PostgreSQL container starts for the first time

-- Create the main database (if not exists)
-- Note: The database is already created by the POSTGRES_DB environment variable

-- Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create a schema for the game (optional, for better organization)
-- CREATE SCHEMA IF NOT EXISTS game;

-- Set timezone
SET timezone = 'UTC';

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE telegram_game TO telegram_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO telegram_user;
