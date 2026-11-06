-- ============================================================
-- FILE: 07_README_pgAdmin_Guide.sql (Commented Guide)
-- PURPOSE: Step-by-step instructions to run all scripts in pgAdmin
-- PROJECT: ADBMS Final Project - Log-Based Recovery System
-- ============================================================
-- This is a COMMENT-ONLY file. Nothing executes. Just read it.
-- ============================================================

/*
========================================================
 PGADMIN SETUP GUIDE — LOG-BASED RECOVERY SYSTEM
 ADBMS Final Project
========================================================

PREREQUISITES:
--------------
  • PostgreSQL 14+ installed and running
  • pgAdmin 4 installed
  • Default 'postgres' superuser available

STEP-BY-STEP INSTRUCTIONS:
---------------------------

[STEP 1] — Create the Database
  1. Open pgAdmin → Connect to your local PostgreSQL server
  2. Click "Query Tool" on the 'postgres' database
  3. Open file: 01_create_database.sql
  4. Press F5 to run
  5. Refresh the server → you should see 'bank_recovery_db' appear

[STEP 2] — Connect to the new database
  1. In pgAdmin left panel: expand Servers → PostgreSQL → Databases
  2. Right-click 'bank_recovery_db' → Query Tool

[STEP 3] — Create Schema (Tables)
  1. In the 'bank_recovery_db' Query Tool
  2. Open file: 02_schema.sql
  3. Press F5 to run
  4. Verify: Left panel → bank_recovery_db → Schemas → public → Tables
  5. You should see: Branch, Customer, Employee, Account, Transaction_Record, Loan

[STEP 4] — Insert Sample Data
  1. Open file: 03_sample_data.sql
  2. Press F5 to run
  3. The verification query at the end shows row counts:
     Branch: 5, Customer: 8, Employee: 6, Account: 10,
     Transaction_Record: 12, Loan: 5

[STEP 5] — Run Transaction Queries (Demo)
  1. Open file: 04_transaction_queries.sql
  2. Select each PART (A through K) and run separately (F5)
  3. Observe BEFORE and AFTER balances to see COMMIT/ROLLBACK effects

[STEP 6] — Create Views and Functions
  1. Open file: 05_views_and_functions.sql
  2. Press F5 to run the whole file
  3. Test the functions using the USAGE EXAMPLES at the bottom

[STEP 7] — Run Recovery Demo (Most Important for Viva)
  1. Open file: 06_recovery_demo.sql
  2. Run STEP 0 first (reset state)
  3. Run STEP 1 (simulate crash)
  4. Run STEP 2 (show inconsistent state)
  5. Run STEP 3 (UNDO phase)
  6. Run STEP 4 (REDO phase)
  7. Run STEP 5 (verify consistent state)
  8. Run STEP 6 (cleanup)

QUICK VERIFICATION QUERIES:
----------------------------

  -- Check all tables exist:
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public' ORDER BY table_name;

  -- Check all constraints:
  SELECT conname, contype, conrelid::regclass
  FROM pg_constraint
  WHERE connamespace = 'public'::regnamespace
  ORDER BY conrelid::regclass::text;

  -- Check all indexes:
  SELECT indexname, tablename
  FROM pg_indexes
  WHERE schemaname = 'public'
  ORDER BY tablename;

  -- Check all views:
  SELECT viewname FROM pg_views
  WHERE schemaname = 'public';

  -- Check all functions:
  SELECT routine_name FROM information_schema.routines
  WHERE routine_schema = 'public' AND routine_type = 'FUNCTION';

COMMON ERRORS AND FIXES:
-------------------------

  ERROR: relation "account" does not exist
  FIX: Make sure you are connected to 'bank_recovery_db', not 'postgres'

  ERROR: duplicate key value violates unique constraint
  FIX: Run the DROP TABLE statements at top of 02_schema.sql first,
       then re-run the file

  ERROR: insert or update on table violates foreign key constraint
  FIX: Always run inserts in this order:
       Branch → Customer → Employee → Account → Transaction_Record → Loan

  ERROR: new row for relation "account" violates check constraint "chk_account_balance"
  FIX: This is INTENTIONAL for the ROLLBACK demo — it shows constraint enforcement

FILE EXECUTION ORDER:
---------------------
  01_create_database.sql       ← Run on 'postgres' DB
  02_schema.sql                ← Run on 'bank_recovery_db'
  03_sample_data.sql           ← Run on 'bank_recovery_db'
  04_transaction_queries.sql   ← Run on 'bank_recovery_db' (section by section)
  05_views_and_functions.sql   ← Run on 'bank_recovery_db'
  06_recovery_demo.sql         ← Run on 'bank_recovery_db' (step by step)

CONCEPT MAPPING FOR VIVA:
--------------------------
  File                         ADBMS Concept Demonstrated
  ----                         ----------------------------
  02_schema.sql                Relational model, normalization, FK constraints
  03_sample_data.sql           Data population, referential integrity
  04_transaction_queries.sql   Transactions, COMMIT, ROLLBACK, SAVEPOINT, ACID
  05_views_and_functions.sql   Abstraction, stored procedures, query optimization
  06_recovery_demo.sql         WAL, Undo, Redo, Crash Recovery, ARIES-inspired

========================================================
 Good luck with your ADBMS project and viva!
========================================================
*/

SELECT 'Read the comments in this file for pgAdmin setup instructions.' AS info;
