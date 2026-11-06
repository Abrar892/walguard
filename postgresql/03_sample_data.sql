-- ============================================================
-- FILE: 03_sample_data.sql
-- PURPOSE: Insert realistic sample data into all tables
-- PROJECT: ADBMS Final Project - Log-Based Recovery System
-- Run AFTER 02_schema.sql in 'bank_recovery_db'
-- ============================================================

-- ============================================================
-- 1. BRANCH DATA (5 branches)
-- ============================================================
INSERT INTO Branch (branch_name, branch_city, branch_address, contact_number) VALUES
    ('Main Branch',        'Lahore',     '12 Mall Road, Lahore',              '042-35761001'),
    ('Gulberg Branch',     'Lahore',     '47 Main Blvd, Gulberg III, Lahore', '042-35761002'),
    ('Karachi Central',    'Karachi',    '10 I.I. Chundrigar Road, Karachi',  '021-32561003'),
    ('Islamabad Branch',   'Islamabad',  'Blue Area, Jinnah Avenue',          '051-28761004'),
    ('Faisalabad Branch',  'Faisalabad', 'Susan Road, Faisalabad',            '041-27261005');


-- ============================================================
-- 2. CUSTOMER DATA (8 customers)
-- ============================================================
INSERT INTO Customer (first_name, last_name, email, contact_number, address, date_of_birth) VALUES
    ('Ali',     'Raza',     'ali.raza@gmail.com',     '0300-1234567', '12 Gulberg, Lahore',         '1990-03-15'),
    ('Sara',    'Khan',     'sara.khan@gmail.com',    '0301-2345678', '45 DHA Phase 5, Lahore',     '1988-07-22'),
    ('Ahmed',   'Malik',    'ahmed.malik@yahoo.com',  '0302-3456789', '78 Clifton, Karachi',        '1995-11-30'),
    ('Fatima',  'Siddiqui', 'fatima.s@outlook.com',  '0303-4567890', 'F-8/1, Islamabad',           '1992-05-18'),
    ('Usman',   'Butt',     'usman.butt@gmail.com',   '0304-5678901', '23 Jinnah Town, Faisalabad', '1985-09-10'),
    ('Ayesha',  'Nawaz',    'ayesha.nawaz@gmail.com', '0305-6789012', '5 Garden Town, Lahore',      '1998-02-28'),
    ('Hassan',  'Sheikh',   'hassan.s@gmail.com',     '0306-7890123', '90 Tariq Road, Karachi',     '1993-12-05'),
    ('Zainab',  'Ali',      'zainab.ali@gmail.com',   '0307-8901234', 'G-10, Islamabad',            '1996-08-14');


-- ============================================================
-- 3. EMPLOYEE DATA (6 employees)
-- ============================================================
INSERT INTO Employee (branch_id, first_name, last_name, role, email, contact_number, hire_date) VALUES
    (1, 'Tariq',   'Hussain', 'MANAGER',      'tariq.h@bank.com',   '0311-1111111', '2015-06-01'),
    (1, 'Nadia',   'Iqbal',   'TELLER',       'nadia.i@bank.com',   '0312-2222222', '2018-03-15'),
    (2, 'Bilal',   'Ahmed',   'MANAGER',      'bilal.a@bank.com',   '0313-3333333', '2016-09-01'),
    (3, 'Sana',    'Mirza',   'LOAN_OFFICER', 'sana.m@bank.com',    '0314-4444444', '2019-01-10'),
    (4, 'Kamran',  'Javed',   'CASHIER',      'kamran.j@bank.com',  '0315-5555555', '2020-07-20'),
    (5, 'Hira',    'Qureshi', 'TELLER',       'hira.q@bank.com',    '0316-6666666', '2021-02-14');


-- ============================================================
-- 4. ACCOUNT DATA (10 accounts)
-- ============================================================
INSERT INTO Account (customer_id, branch_id, account_number, account_type, balance, status) VALUES
    (1, 1, 'ACC-00001', 'SAVINGS',       10000.00, 'ACTIVE'),   -- Ali Raza, Main Branch
    (1, 1, 'ACC-00002', 'CURRENT',        5000.00, 'ACTIVE'),   -- Ali Raza, 2nd account
    (2, 2, 'ACC-00003', 'SAVINGS',       25000.00, 'ACTIVE'),   -- Sara Khan
    (3, 3, 'ACC-00004', 'CURRENT',       15000.00, 'ACTIVE'),   -- Ahmed Malik
    (4, 4, 'ACC-00005', 'SAVINGS',        8000.00, 'ACTIVE'),   -- Fatima Siddiqui
    (5, 5, 'ACC-00006', 'FIXED_DEPOSIT', 50000.00, 'ACTIVE'),   -- Usman Butt
    (6, 1, 'ACC-00007', 'SAVINGS',        3500.00, 'ACTIVE'),   -- Ayesha Nawaz
    (7, 3, 'ACC-00008', 'CURRENT',       12000.00, 'ACTIVE'),   -- Hassan Sheikh
    (8, 4, 'ACC-00009', 'SAVINGS',        6500.00, 'ACTIVE'),   -- Zainab Ali
    (2, 2, 'ACC-00010', 'SAVINGS',        2000.00, 'INACTIVE'); -- Sara Khan, inactive account


-- ============================================================
-- 5. TRANSACTION_RECORD DATA (12 sample transactions)
-- ============================================================
INSERT INTO Transaction_Record
    (account_id, transaction_type, amount, old_balance, new_balance, transaction_status, notes)
VALUES
    -- Deposits
    (1, 'DEPOSIT',       2000.00,  8000.00,  10000.00, 'COMMITTED', 'Initial deposit'),
    (3, 'DEPOSIT',       5000.00, 20000.00,  25000.00, 'COMMITTED', 'Salary credit'),
    (5, 'DEPOSIT',       1000.00,  7000.00,   8000.00, 'COMMITTED', 'Cash deposit at counter'),

    -- Withdrawals
    (2, 'WITHDRAWAL',     500.00,  5500.00,   5000.00, 'COMMITTED', 'ATM withdrawal'),
    (4, 'WITHDRAWAL',    1500.00, 16500.00,  15000.00, 'COMMITTED', 'Utility bill payment'),
    (7, 'WITHDRAWAL',     500.00,  4000.00,   3500.00, 'COMMITTED', 'Cash withdrawal'),

    -- Transfers (pair: OUT from ACC-1, IN to ACC-7)
    (1, 'TRANSFER_OUT',  1000.00, 11000.00,  10000.00, 'COMMITTED', 'Transfer to ACC-00007'),
    (7, 'TRANSFER_IN',   1000.00,  2500.00,   3500.00, 'COMMITTED', 'Transfer from ACC-00001'),

    -- A pending (in-progress) transaction — for demo purposes
    (8, 'WITHDRAWAL',    2000.00, 12000.00,  10000.00, 'PENDING',   'Online bill payment — pending'),

    -- A rolled-back transaction — demonstrates undo logging
    (9, 'WITHDRAWAL',    3000.00,  6500.00,   3500.00, 'ROLLED_BACK', 'Insufficient-funds trigger test'),

    -- A deposit that will be used in crash-recovery demo
    (1, 'DEPOSIT',       500.00,  10000.00,  10500.00, 'PENDING',   'Crash demo — uncommitted'),

    -- Another committed transaction
    (6, 'DEPOSIT',      10000.00, 40000.00,  50000.00, 'COMMITTED', 'Fixed deposit top-up');


-- ============================================================
-- 6. LOAN DATA (5 loans)
-- ============================================================
INSERT INTO Loan
    (customer_id, account_id, loan_type, loan_amount, interest_rate, start_date, end_date, loan_status)
VALUES
    (1, 1, 'HOME',      500000.00, 12.50, '2024-01-01', '2034-01-01', 'ACTIVE'),
    (2, 3, 'CAR',        800000.00,  9.99, '2023-06-15', '2028-06-15', 'ACTIVE'),
    (3, 4, 'PERSONAL',   200000.00, 18.00, '2024-03-01', '2026-03-01', 'ACTIVE'),
    (5, 6, 'BUSINESS',  1500000.00, 14.25, '2022-09-01', '2027-09-01', 'ACTIVE'),
    (7, 8, 'EDUCATION',  300000.00,  7.50, '2023-01-01', '2027-01-01', 'CLOSED');


-- ============================================================
-- VERIFY: Quick row count after inserts
-- ============================================================
SELECT 'Branch'             AS table_name, COUNT(*) AS row_count FROM Branch
UNION ALL
SELECT 'Customer',            COUNT(*) FROM Customer
UNION ALL
SELECT 'Employee',            COUNT(*) FROM Employee
UNION ALL
SELECT 'Account',             COUNT(*) FROM Account
UNION ALL
SELECT 'Transaction_Record',  COUNT(*) FROM Transaction_Record
UNION ALL
SELECT 'Loan',                COUNT(*) FROM Loan
ORDER BY table_name;

-- ============================================================
-- SAMPLE DATA COMPLETE
-- Run 04_transaction_queries.sql next
-- ============================================================
