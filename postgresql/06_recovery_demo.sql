-- ============================================================
-- FILE: 06_recovery_demo.sql
-- PURPOSE: Step-by-step crash and recovery simulation in pure SQL
--          Shows UNDO and REDO concepts demonstrable in pgAdmin
-- PROJECT: ADBMS Final Project - Log-Based Recovery System
-- ============================================================
-- HOW TO USE:
--   Run each numbered STEP block one at a time.
--   Read the BEFORE/AFTER SELECT results after each step.
--   This simulates what the Python recovery_manager.py does.
-- ============================================================


-- ============================================================
-- STEP 0: Reset demo state (run this to start fresh)
-- ============================================================
UPDATE Account SET balance = 10000.00 WHERE account_number = 'ACC-00001';
UPDATE Account SET balance = 25000.00 WHERE account_number = 'ACC-00003';
UPDATE Account SET balance =  3500.00 WHERE account_number = 'ACC-00007';

DELETE FROM Transaction_Record
WHERE notes LIKE '%CRASH_DEMO%' OR notes LIKE '%RECOVERY_DEMO%';

SELECT account_number, balance FROM Account
WHERE account_number IN ('ACC-00001', 'ACC-00003', 'ACC-00007');


-- ============================================================
-- STEP 1: Normal transaction starts (WAL log would be written to MongoDB here)
-- Account ACC-00001: Withdrawal of 3000
-- ============================================================
RAISE NOTICE '=== STEP 1: Begin transaction, WAL log written to MongoDB (simulated) ===';

-- [MongoDB WAL Log Written]:
-- { transaction_id: 999, account_id: 1, operation: "UPDATE",
--   old_balance: 10000, new_balance: 7000, status: "UNCOMMITTED" }

BEGIN;
    -- Record transaction as PENDING
    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    VALUES
        (1, 'WITHDRAWAL', 3000.00, 10000.00, 7000.00, 'PENDING', 'CRASH_DEMO: withdrawal before crash');

    -- Update balance in PostgreSQL
    UPDATE Account
    SET balance = balance - 3000.00
    WHERE account_number = 'ACC-00001';

    -- >>> CRASH HAPPENS HERE — ROLLBACK never executes, COMMIT never executes <<<
    -- In Python: raise Exception("SIMULATED CRASH")
    -- PostgreSQL auto-rolls-back the implicit transaction on connection drop,
    -- but Transaction_Record INSERT was in the same transaction so it too is lost.

ROLLBACK;   -- Simulates crash (connection drop = implicit rollback in PostgreSQL)

-- What crash leaves behind:
-- • MongoDB wal_log still has status = "UNCOMMITTED"  ← Recovery uses this
-- • PostgreSQL balance is UNCHANGED (auto-rolled back by PG)
-- • Transaction_Record row may not exist (was in same txn)

-- For demo purposes: manually inject a PENDING record to simulate partial crash
INSERT INTO Transaction_Record
    (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
VALUES
    (1, 'WITHDRAWAL', 3000.00, 10000.00, 7000.00, 'PENDING', 'CRASH_DEMO: simulated uncommitted txn');

-- And manually apply the balance change (simulating crash mid-commit):
UPDATE Account SET balance = 7000.00 WHERE account_number = 'ACC-00001';

-- Show current inconsistent state:
SELECT 'AFTER CRASH (INCONSISTENT STATE)' AS phase;
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00001';
SELECT transaction_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes
FROM Transaction_Record WHERE notes LIKE '%CRASH_DEMO%';


-- ============================================================
-- STEP 2: RECOVERY MANAGER STARTS
-- Phase 1 — Analysis: Find all PENDING transactions
-- ============================================================
SELECT '=== PHASE 1: ANALYSIS — Scanning for uncommitted transactions ===' AS recovery_phase;

SELECT
    tr.transaction_id,
    a.account_number,
    tr.transaction_type,
    tr.amount,
    tr.old_balance      AS undo_target,
    tr.new_balance      AS redo_target,
    tr.transaction_status,
    tr.notes
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
WHERE tr.transaction_status = 'PENDING';


-- ============================================================
-- STEP 3: UNDO PHASE — Restore old_balance for PENDING transactions
-- ============================================================
SELECT '=== PHASE 2: UNDO — Restoring old balances for uncommitted transactions ===' AS recovery_phase;

-- UNDO: Restore old balance from the log
UPDATE Account
SET balance = tr.old_balance
FROM Transaction_Record tr
WHERE Account.account_id = tr.account_id
  AND tr.transaction_status = 'PENDING';

-- Mark transactions as ROLLED_BACK
UPDATE Transaction_Record
SET transaction_status = 'ROLLED_BACK',
    notes = notes || ' | UNDONE by Recovery Manager'
WHERE transaction_status = 'PENDING';

-- Verify UNDO
SELECT 'AFTER UNDO' AS phase;
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00001';
-- Expected: balance restored to 10000.00

SELECT transaction_id, transaction_status, notes
FROM Transaction_Record WHERE notes LIKE '%CRASH_DEMO%';


-- ============================================================
-- STEP 4: REDO PHASE — Re-apply COMMITTED transactions if needed
-- (Simulated: we mark a transaction as COMMITTED but manually reset the balance)
-- ============================================================
SELECT '=== PHASE 3: REDO — Re-applying committed transactions ===' AS recovery_phase;

-- Simulate: a COMMITTED transaction whose effect was lost
-- Insert a COMMITTED log entry
INSERT INTO Transaction_Record
    (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
VALUES
    (3, 'DEPOSIT', 2000.00, 25000.00, 27000.00, 'COMMITTED', 'RECOVERY_DEMO: redo target deposit');

-- Manually reset ACC-00003 balance to simulate the effect was lost
UPDATE Account SET balance = 25000.00 WHERE account_number = 'ACC-00003';

SELECT 'Before REDO — balance should be 25000 (lost committed change)' AS note;
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00003';

-- REDO: Re-apply new_balance for COMMITTED transactions where PG state doesn't match
UPDATE Account
SET balance = tr.new_balance
FROM Transaction_Record tr
WHERE Account.account_id = tr.account_id
  AND tr.transaction_status = 'COMMITTED'
  AND tr.notes = 'RECOVERY_DEMO: redo target deposit'
  AND Account.balance <> tr.new_balance;  -- Only redo if state is inconsistent

SELECT 'After REDO — balance should be 27000 (re-applied)' AS note;
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00003';


-- ============================================================
-- STEP 5: FINAL VERIFICATION — Consistent state confirmed
-- ============================================================
SELECT '=== RECOVERY COMPLETE — Final State ===' AS recovery_phase;

SELECT
    a.account_number,
    a.balance,
    a.status
FROM Account a
WHERE a.account_number IN ('ACC-00001','ACC-00003','ACC-00007')
ORDER BY a.account_number;

-- Transaction status summary
SELECT
    transaction_status,
    COUNT(*) AS count
FROM Transaction_Record
GROUP BY transaction_status
ORDER BY transaction_status;


-- ============================================================
-- STEP 6: CLEANUP — Remove demo records
-- ============================================================
-- Run this after the demo to clean up test records
DELETE FROM Transaction_Record
WHERE notes LIKE '%CRASH_DEMO%' OR notes LIKE '%RECOVERY_DEMO%';

UPDATE Account SET balance = 10000.00 WHERE account_number = 'ACC-00001';
UPDATE Account SET balance = 25000.00 WHERE account_number = 'ACC-00003';

SELECT 'Demo cleanup complete. Database restored.' AS status;

-- ============================================================
-- END OF RECOVERY DEMO
-- ============================================================
