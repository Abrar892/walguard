-- ============================================================
-- FILE: 05_views_and_functions.sql
-- PURPOSE: Useful views and stored functions for the demo
-- PROJECT: ADBMS Final Project - Log-Based Recovery System
-- Run AFTER 03_sample_data.sql
-- ============================================================


-- ============================================================
-- VIEWS
-- ============================================================

-- View 1: Full account overview (used in demo)
CREATE OR REPLACE VIEW vw_account_overview AS
SELECT
    a.account_id,
    a.account_number,
    a.account_type,
    a.balance,
    a.status,
    c.customer_id,
    c.first_name || ' ' || c.last_name  AS customer_name,
    c.email,
    b.branch_name,
    b.branch_city,
    a.created_at
FROM Account a
JOIN Customer c ON a.customer_id = c.customer_id
JOIN Branch   b ON a.branch_id   = b.branch_id;

COMMENT ON VIEW vw_account_overview IS 'Full account view with customer and branch info';


-- View 2: Transaction history with account number
CREATE OR REPLACE VIEW vw_transaction_history AS
SELECT
    tr.transaction_id,
    a.account_number,
    c.first_name || ' ' || c.last_name AS customer_name,
    tr.transaction_type,
    tr.amount,
    tr.old_balance,
    tr.new_balance,
    tr.transaction_status,
    tr.transaction_time,
    tr.notes
FROM Transaction_Record tr
JOIN Account  a ON tr.account_id  = a.account_id
JOIN Customer c ON a.customer_id  = c.customer_id
ORDER BY tr.transaction_time DESC;

COMMENT ON VIEW vw_transaction_history IS 'Complete transaction log with customer details';


-- View 3: Uncommitted / Pending transactions (recovery candidate view)
CREATE OR REPLACE VIEW vw_pending_recovery AS
SELECT
    tr.transaction_id,
    a.account_number,
    tr.transaction_type,
    tr.amount,
    tr.old_balance       AS restore_balance,
    tr.transaction_status,
    tr.transaction_time  AS started_at
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
WHERE tr.transaction_status = 'PENDING'
ORDER BY tr.transaction_time ASC;

COMMENT ON VIEW vw_pending_recovery IS 'All PENDING transactions — candidates for UNDO recovery';


-- View 4: Recovery audit — what was rolled back / redone
CREATE OR REPLACE VIEW vw_recovery_audit AS
SELECT
    tr.transaction_id,
    a.account_number,
    tr.transaction_type,
    tr.amount,
    tr.old_balance,
    tr.new_balance,
    tr.transaction_status,
    tr.notes,
    tr.transaction_time
FROM Transaction_Record tr
JOIN Account a ON tr.account_id = a.account_id
WHERE tr.transaction_status IN ('ROLLED_BACK', 'COMMITTED')
ORDER BY tr.transaction_time DESC;


-- ============================================================
-- STORED FUNCTIONS
-- ============================================================

-- Function 1: Perform a DEPOSIT — returns new balance
CREATE OR REPLACE FUNCTION fn_deposit(
    p_account_number  VARCHAR,
    p_amount          DECIMAL,
    p_notes           TEXT DEFAULT 'Counter deposit'
)
RETURNS DECIMAL AS $$
DECLARE
    v_account_id    INT;
    v_old_balance   DECIMAL(12,2);
    v_new_balance   DECIMAL(12,2);
BEGIN
    -- Get account
    SELECT account_id, balance
    INTO v_account_id, v_old_balance
    FROM Account
    WHERE account_number = p_account_number AND status = 'ACTIVE';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Account % not found or not active', p_account_number;
    END IF;

    v_new_balance := v_old_balance + p_amount;

    -- [WAL NOTE] In full system: write MongoDB log BEFORE next two statements

    -- Update balance
    UPDATE Account SET balance = v_new_balance
    WHERE account_id = v_account_id;

    -- Record transaction
    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    VALUES
        (v_account_id, 'DEPOSIT', p_amount, v_old_balance, v_new_balance, 'COMMITTED', p_notes);

    RAISE NOTICE 'DEPOSIT: Account %, Amount %, Old Balance: %, New Balance: %',
        p_account_number, p_amount, v_old_balance, v_new_balance;

    RETURN v_new_balance;
END;
$$ LANGUAGE plpgsql;


-- Function 2: Perform a WITHDRAWAL — returns new balance
CREATE OR REPLACE FUNCTION fn_withdraw(
    p_account_number  VARCHAR,
    p_amount          DECIMAL,
    p_notes           TEXT DEFAULT 'Counter withdrawal'
)
RETURNS DECIMAL AS $$
DECLARE
    v_account_id    INT;
    v_old_balance   DECIMAL(12,2);
    v_new_balance   DECIMAL(12,2);
BEGIN
    SELECT account_id, balance
    INTO v_account_id, v_old_balance
    FROM Account
    WHERE account_number = p_account_number AND status = 'ACTIVE';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Account % not found or not active', p_account_number;
    END IF;

    IF v_old_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds. Balance: %, Requested: %', v_old_balance, p_amount;
    END IF;

    v_new_balance := v_old_balance - p_amount;

    -- [WAL NOTE] Write MongoDB log here before DB change

    UPDATE Account SET balance = v_new_balance
    WHERE account_id = v_account_id;

    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    VALUES
        (v_account_id, 'WITHDRAWAL', p_amount, v_old_balance, v_new_balance, 'COMMITTED', p_notes);

    RAISE NOTICE 'WITHDRAWAL: Account %, Amount %, Old Balance: %, New Balance: %',
        p_account_number, p_amount, v_old_balance, v_new_balance;

    RETURN v_new_balance;
END;
$$ LANGUAGE plpgsql;


-- Function 3: Transfer between two accounts (atomic)
CREATE OR REPLACE FUNCTION fn_transfer(
    p_from_account  VARCHAR,
    p_to_account    VARCHAR,
    p_amount        DECIMAL,
    p_notes         TEXT DEFAULT 'Inter-account transfer'
)
RETURNS TEXT AS $$
DECLARE
    v_from_id       INT;
    v_to_id         INT;
    v_from_old      DECIMAL(12,2);
    v_to_old        DECIMAL(12,2);
BEGIN
    -- Get sender
    SELECT account_id, balance INTO v_from_id, v_from_old
    FROM Account WHERE account_number = p_from_account AND status = 'ACTIVE';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Sender account % not found or inactive', p_from_account;
    END IF;

    -- Get receiver
    SELECT account_id, balance INTO v_to_id, v_to_old
    FROM Account WHERE account_number = p_to_account AND status = 'ACTIVE';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Receiver account % not found or inactive', p_to_account;
    END IF;

    -- Check funds
    IF v_from_old < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds in account %. Balance: %', p_from_account, v_from_old;
    END IF;

    -- [WAL NOTE] Write both leg logs to MongoDB before any UPDATE

    -- Deduct from sender
    UPDATE Account SET balance = balance - p_amount WHERE account_id = v_from_id;
    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    VALUES (v_from_id, 'TRANSFER_OUT', p_amount, v_from_old, v_from_old - p_amount, 'COMMITTED',
            p_notes || ' → ' || p_to_account);

    -- Credit receiver
    UPDATE Account SET balance = balance + p_amount WHERE account_id = v_to_id;
    INSERT INTO Transaction_Record
        (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
    VALUES (v_to_id, 'TRANSFER_IN', p_amount, v_to_old, v_to_old + p_amount, 'COMMITTED',
            p_notes || ' ← ' || p_from_account);

    RETURN FORMAT('Transfer of %s from %s to %s completed successfully.',
                  p_amount, p_from_account, p_to_account);
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- USAGE EXAMPLES FOR STORED FUNCTIONS
-- Run these individually in pgAdmin to test:
-- ============================================================

-- Deposit 1500 into ACC-00009
SELECT fn_deposit('ACC-00009', 1500.00, 'Test deposit via function');

-- Withdraw 500 from ACC-00007
SELECT fn_withdraw('ACC-00007', 500.00, 'Test withdrawal via function');

-- Transfer 1000 from ACC-00003 to ACC-00005
SELECT fn_transfer('ACC-00003', 'ACC-00005', 1000.00, 'Test transfer via function');

-- View updated accounts
SELECT * FROM vw_account_overview WHERE account_number IN ('ACC-00003','ACC-00005','ACC-00007','ACC-00009');

-- View latest transactions
SELECT * FROM vw_transaction_history LIMIT 10;

-- ============================================================
-- END OF VIEWS AND FUNCTIONS
-- ============================================================
