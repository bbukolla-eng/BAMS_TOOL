-- Initialize BAMS database extensions and schemas
-- Run once on a fresh PostgreSQL 16 instance before migrations

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Full-text search configuration for spec parsing
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS bams_english (COPY = english);
