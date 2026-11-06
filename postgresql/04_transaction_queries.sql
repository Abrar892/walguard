-- ============================================================
-- FILE: 04_transaction_queries.sql
-- PURPOSE: Demonstrate real PostgreSQL transactions with
--          COMMIT, ROLLBACK, and WAL-simulation comments
-- PROJECT: ADBMS Final Project - Log-Based Recovery System
-- ============================================================
-- HOW TO USE IN pgAdmin:
--   1. Open Query Tool in bank_recovery_db
--   2. Run each transaction block separately (select the block, press F5)
--   3. Observe before/after state with SELECT queries
-- ============================================================


-- ============================================================
-- PART A: USEFUL SELECT QUERIES (run anytime)
-- ============================================================

-- A1: View all accounts with customer names and branch
SELECT
    a.account_id,
    a.account_number,
    a.account_type,
    a.balance,
    a.status,
    c.first_name || ' ' || c.last_name  AS customer_name,
    b.branch_name
FROM Account a
JOIN Customer c ON a.customer_id = c.customer_id
JOIN Branch   b ON a.branch_id   = b.branch_id
ORDER BY a.account_id;


-- A2: View all transactions with account number
SELECT
    tr.transaction_id,
    a.account_number,
    tr.transaction_type,
    tr.amount,
    tr.old_balance,
    tr.new_balance,
    tr.transaction_status,
    tr.transaction_time,
    tr.notes
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
ORDER BY tr.transaction_time DESC;


-- A3: View COMMITTED transactions only
SELECT
    tr.transaction_id,
    a.account_number,
    tr.transaction_type,
    tr.amount,
    tr.transaction_status
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
WHERE tr.transaction_status = 'COMMITTED';


-- A4: View PENDING / UNCOMMITTED transactions (for recovery demo)
SELECT
    tr.transaction_id,
    a.account_number,
    tr.transaction_type,
    tr.amount,
    tr.old_balance,
    tr.new_balance,
    tr.transaction_status
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
WHERE tr.transaction_status = 'PENDING';


-- A5: View ROLLED_BACK transactions
SELECT
    tr.transaction_id,
    a.account_number,
    tr.transaction_type,
    tr.amount,
    tr.transaction_status
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
WHERE tr.transaction_status = 'ROLLED_BACK';


-- A6: Balance summary per customer
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    COUNT(a.account_id)                 AS total_accounts,
    SUM(a.balance)                      AS total_balance
FROM Customer c
JOIN Account a ON c.customer_id = a.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
ORDER BY total_balance DESC;


-- A7: Active loans with customer name
SELECT
    l.loan_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    l.loan_type,
    l.loan_amount,
    l.interest_rate,
    l.loan_status
FROM Loan l
JOIN Customer c ON l.customer_id = c.customer_id
WHERE l.loan_status = 'ACTIVE';


-- ============================================================
-- PART B: TRANSACTION 1 — Successful DEPOSIT with COMMIT
-- Scenario: Customer Ali Raza deposits 2000 into ACC-00001
-- ============================================================

-- CHECK: Balance before transaction
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00001';

BEGIN;  -- Start transaction

    -- [WAL LOG STEP] In real system: write to MongoDB BEFORE this update
    -- MongoDB doc: { transaction_id: NEW_ID, old_balance: 10000, new_balance: 12000, status: "UNCOMMITTED" }

    -- Step 1: Record the transaction with PENDING status
    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    VALUES
        (1, 'DEPOSIT', 2000.00, 10000.00, 12000.00, 'PENDING', 'Counter deposit by Ali Raza');

    -- Step 2: Update the account balance
    UPDATE Account
    SET balance = balance + 2000.00
    WHERE account_number = 'ACC-00001';

    -- Step 3: Mark transaction as COMMITTED
    UPDATE Transaction_Record
    SET transaction_status = 'COMMITTED'
    WHERE transaction_id = (SELECT MAX(transaction_id) FROM Transaction_Record WHERE account_id = 1);

    -- [WAL LOG STEP] In real system: update MongoDB log status to "COMMITTED"

COMMIT;  -- <-- All changes are now permanent

-- CHECK: Balance after commit — should be 12000.00
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00001';


-- ============================================================
-- PART C: TRANSACTION 2 — Successful WITHDRAWAL with COMMIT
-- Scenario: Sara Khan withdraws 3000 from ACC-00003
-- ============================================================

-- CHECK: Before
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00003';

BEGIN;

    -- [WAL LOG STEP] MongoDB: { old_balance: 25000, new_balance: 22000, status: "UNCOMMITTED" }

    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    VALUES
        (3, 'WITHDRAWAL', 3000.00, 25000.00, 22000.00, 'PENDING', 'Withdrawal by Sara Khan');

    UPDATE Account
    SET balance = balance - 3000.00
    WHERE account_number = 'ACC-00003';

    UPDATE Transaction_Record
    SET transaction_status = 'COMMITTED'
    WHERE transaction_id = (SELECT MAX(transaction_id) FROM Transaction_Record WHERE account_id = 3);

    -- [WAL LOG STEP] MongoDB: update status to "COMMITTED"

COMMIT;

-- CHECK: After — should be 22000.00
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00003';


-- ============================================================
-- PART D: TRANSACTION 3 — FUND TRANSFER with COMMIT
-- Scenario: Transfer 1500 from ACC-00001 (Ali) to ACC-00007 (Ayesha)
-- This involves TWO UPDATE statements in one transaction
-- ============================================================

-- CHECK: Both balances before
SELECT account_number, balance FROM Account
WHERE account_number IN ('ACC-00001', 'ACC-00007');

BEGIN;

    -- [WAL STEP] Log both legs in MongoDB before any DB update

    -- Deduct from sender
    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    SELECT 1, 'TRANSFER_OUT', 1500.00, balance, balance - 1500.00, 'PENDING', 'Transfer to ACC-00007'
    FROM Account WHERE account_number = 'ACC-00001';

    UPDATE Account SET balance = balance - 1500.00 WHERE account_number = 'ACC-00001';

    -- Credit to receiver
    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    SELECT 7, 'TRANSFER_IN', 1500.00, balance, balance + 1500.00, 'PENDING', 'Transfer from ACC-00001'
    FROM Account WHERE account_number = 'ACC-00007';

    UPDATE Account SET balance = balance + 1500.00 WHERE account_number = 'ACC-00007';

-- Mark both COMMITTED
UPDATE Transaction_Record
SET transaction_status = 'COMMITTED'
WHERE transaction_id IN (
    SELECT MAX(transaction_id)
    FROM Transaction_Record
    WHERE account_id IN (1,7)
    GROUP BY account_id
);

COMMIT;

-- CHECK: After
SELECT account_number, balance FROM Account
WHERE account_number IN ('ACC-00001', 'ACC-00007');


-- ============================================================
-- PART E: TRANSACTION 4 — ROLLBACK (Insufficient Funds)
-- Scenario: Ahmed Malik tries to withdraw 20000 but has only 15000
-- ============================================================


-- CHECK: Before
SELECT account_number, balance
FROM Account
WHERE account_number = 'ACC-00004';

BEGIN;

    -- [WAL STEP]
    -- MongoDB log written first in real system

    INSERT INTO Transaction_Record
        (
            account_id,
            transaction_type,
            amount,
            old_balance,
            new_balance,
            transaction_status,
            notes
        )
    VALUES
        (
            4,
            'WITHDRAWAL',
            20000.00,
            15000.00,
            15000.00,
            'PENDING',
            'Insufficient funds test'
        );

    -- Simulate failure detection
    -- No account update performed because application detected insufficient funds

ROLLBACK;

-- CHECK: Balance unchanged
SELECT account_number, balance
FROM Account
WHERE account_number = 'ACC-00004';

-- ============================================================
-- PART F: TRANSACTION 5 — ROLLBACK (Manual / Explicit)
-- Scenario: Operator starts a deposit but cancels it manually
-- ============================================================

-- CHECK: Before
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00005';

BEGIN;

    -- [WAL STEP] MongoDB log written (UNCOMMITTED)

    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    VALUES
        (5, 'DEPOSIT', 5000.00, 8000.00, 13000.00, 'PENDING', 'Manual rollback demo');

    UPDATE Account
    SET balance = balance + 5000.00
    WHERE account_number = 'ACC-00005';

    -- Operator decides to cancel — explicit rollback
ROLLBACK;  -- <-- Changes to both tables above are fully reversed

-- [WAL STEP] MongoDB: update log to ROLLED_BACK

-- CHECK: Balance unchanged — still 8000.00
SELECT account_number, balance FROM Account WHERE account_number = 'ACC-00005';


-- ============================================================
-- PART G: SAVEPOINT DEMONSTRATION
-- ============================================================

BEGIN;

    -- First operation: deposit
    INSERT INTO Transaction_Record
        (
            account_id,
            transaction_type,
            amount,
            old_balance,
            new_balance,
            transaction_status,
            notes
        )
    VALUES
        (
            9,
            'DEPOSIT',
            500.00,
            6500.00,
            7000.00,
            'PENDING',
            'Savepoint demo - deposit'
        );

    UPDATE Account
    SET balance = balance + 500.00
    WHERE account_id = 9;

    SAVEPOINT after_deposit;

    -- Second operation (bad withdrawal simulation)
    INSERT INTO Transaction_Record
        (
            account_id,
            transaction_type,
            amount,
            old_balance,
            new_balance,
            transaction_status,
            notes
        )
    VALUES
        (
            9,
            'WITHDRAWAL',
            10000.00,
            7000.00,
            7000.00,
            'PENDING',
            'Savepoint demo - bad withdrawal'
        );

    -- DO NOT update account balance here
    -- We simulate failure before update happens

    ROLLBACK TO SAVEPOINT after_deposit;

    -- Commit only deposit
    UPDATE Transaction_Record
    SET transaction_status = 'COMMITTED'
    WHERE account_id = 9
      AND notes = 'Savepoint demo - deposit';

COMMIT;

-- CHECK
SELECT account_number, balance
FROM Account
WHERE account_id = 9;
-- ============================================================
-- PART H: CRASH SIMULATION QUERY
-- Scenario: Show what uncommitted transactions look like after crash
-- This is what the Recovery Manager reads to trigger UNDO
-- ============================================================

-- Find all PENDING transactions (simulates what crash leaves behind)
SELECT
    tr.transaction_id,
    a.account_number,
    tr.transaction_type,
    tr.amount,
    tr.old_balance,
    tr.new_balance,
    tr.transaction_status,
    tr.transaction_time,
    tr.notes
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
WHERE tr.transaction_status = 'PENDING'
ORDER BY tr.transaction_time DESC;


-- ============================================================
-- PART I: UNDO RECOVERY QUERY
-- Scenario: Recovery manager restores old_balance for all PENDING txns
-- This simulates UNDO operation after crash detection
-- ============================================================

-- Step 1: Show current balances for accounts with PENDING transactions
SELECT a.account_id, a.account_number, a.balance AS current_balance,
       tr.old_balance AS should_restore_to
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
WHERE tr.transaction_status = 'PENDING';

-- Step 2: Restore old balances (UNDO operation)
UPDATE Account
SET balance = tr.old_balance
FROM Transaction_Record tr
WHERE Account.account_id = tr.account_id
  AND tr.transaction_status = 'PENDING';

-- Step 3: Mark these transactions as ROLLED_BACK
UPDATE Transaction_Record
SET transaction_status = 'ROLLED_BACK'
WHERE transaction_status = 'PENDING';

-- Step 4: Confirm recovery
SELECT a.account_id, a.account_number, a.balance AS restored_balance
FROM Account a
JOIN Transaction_Record tr ON a.account_id = tr.account_id
WHERE tr.transaction_status = 'ROLLED_BACK'
GROUP BY a.account_id, a.account_number, a.balance;


-- ============================================================
-- PART J: REDO RECOVERY QUERY
-- Scenario: Re-apply a COMMITTED transaction whose PG change was lost
-- ============================================================

-- Simulate finding a COMMITTED log in MongoDB that has no match in PG
-- (In practice, Python code coordinates this — shown here for SQL demo)

-- Example: Re-apply transaction_id = 1 (COMMITTED deposit of 2000)
DO $$
DECLARE
    v_account_id    INT := 1;
    v_new_balance   DECIMAL(12,2) := 12000.00;  -- from MongoDB log
    v_txn_id        INT := 1;
BEGIN
    -- REDO: Apply the new_balance from the log
    UPDATE Account
    SET balance = v_new_balance
    WHERE account_id = v_account_id;

    -- Confirm the transaction is COMMITTED in PostgreSQL
    UPDATE Transaction_Record
    SET transaction_status = 'COMMITTED'
    WHERE transaction_id = v_txn_id;

    RAISE NOTICE 'REDO applied for transaction_id %, account_id % → balance = %',
        v_txn_id, v_account_id, v_new_balance;
END;
$$;


-- ============================================================
-- PART K: USEFUL AGGREGATE QUERIES (for reporting/demo)
-- ============================================================

-- K1: Transaction summary per account
SELECT
    a.account_number,
    COUNT(*)                                       AS total_transactions,
    SUM(CASE WHEN tr.transaction_status = 'COMMITTED'   THEN 1 ELSE 0 END) AS committed,
    SUM(CASE WHEN tr.transaction_status = 'ROLLED_BACK' THEN 1 ELSE 0 END) AS rolled_back,
    SUM(CASE WHEN tr.transaction_status = 'PENDING'     THEN 1 ELSE 0 END) AS pending,
    SUM(CASE WHEN tr.transaction_type   = 'DEPOSIT'     THEN tr.amount ELSE 0 END) AS total_deposited,
    SUM(CASE WHEN tr.transaction_type   = 'WITHDRAWAL'  THEN tr.amount ELSE 0 END) AS total_withdrawn
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
GROUP BY a.account_number
ORDER BY a.account_number;


-- K2: Branch performance summary
SELECT
    b.branch_name,
    b.branch_city,
    COUNT(DISTINCT a.account_id)    AS total_accounts,
    COUNT(DISTINCT e.employee_id)   AS total_employees,
    SUM(a.balance)                  AS total_deposits
FROM Branch b
LEFT JOIN Account  a ON b.branch_id = a.branch_id
LEFT JOIN Employee e ON b.branch_id = e.branch_id
GROUP BY b.branch_id, b.branch_name, b.branch_city
ORDER BY total_deposits DESC;


-- K3: Find customers with multiple accounts
SELECT
    c.first_name || ' ' || c.last_name AS customer_name,
    COUNT(a.account_id)                AS account_count,
    SUM(a.balance)                     AS total_balance
FROM Customer c
JOIN Account a ON c.customer_id = a.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
HAVING COUNT(a.account_id) > 1;


-- K4: All active loans with monthly payment estimate
SELECT
    l.loan_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    l.loan_type,
    l.loan_amount,
    l.interest_rate,
    ROUND(
        (l.loan_amount * (l.interest_rate/100/12)) /
        (1 - POWER(1 + l.interest_rate/100/12,
            -(EXTRACT(YEAR FROM AGE(l.end_date, l.start_date)) * 12 +
              EXTRACT(MONTH FROM AGE(l.end_date, l.start_date))))
        ), 2
    ) AS estimated_monthly_payment
FROM Loan l
JOIN Customer c ON l.customer_id = c.customer_id
WHERE l.loan_status = 'ACTIVE';

-- ============================================================
-- END OF TRANSACTION QUERIES
-- ============================================================
