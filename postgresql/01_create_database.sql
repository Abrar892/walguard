-- ============================================================
-- FILE: 01_create_database.sql
-- PURPOSE: Create the database for the Log-Based Recovery System
-- PROJECT: ADBMS Final Project - Log-Based Recovery System
-- Run this script FIRST in pgAdmin using the default 'postgres' database
-- ============================================================

-- Step 1: Create the database
CREATE DATABASE bank_recovery_db
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE bank_recovery_db
    IS 'ADBMS Final Project: Log-Based Recovery System using PostgreSQL + MongoDB';

-- ============================================================
-- After running this script:
-- 1. Disconnect from 'postgres' database
-- 2. Connect to 'bank_recovery_db'
-- 3. Run 02_schema.sql
-- ============================================================
