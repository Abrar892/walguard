-- ============================================================
-- FILE: 02_schema.sql
-- PURPOSE: Create all tables with PK, FK, CHECK constraints
-- PROJECT: ADBMS Final Project - Log-Based Recovery System
-- Run this in 'bank_recovery_db' after creating the database
-- ============================================================

-- Safety: Drop tables in reverse dependency order if re-running
DROP TABLE IF EXISTS Loan             CASCADE;
DROP TABLE IF EXISTS Transaction_Record CASCADE;
DROP TABLE IF EXISTS Account          CASCADE;
DROP TABLE IF EXISTS Employee         CASCADE;
DROP TABLE IF EXISTS Customer         CASCADE;
DROP TABLE IF EXISTS Branch           CASCADE;

-- ============================================================
-- TABLE 1: Branch
-- Stores bank branch information
-- No foreign key dependencies — created first
-- ============================================================
CREATE TABLE Branch (
    branch_id       SERIAL          PRIMARY KEY,
    branch_name     VARCHAR(100)    NOT NULL,
    branch_city     VARCHAR(50)     NOT NULL,
    branch_address  TEXT,
    contact_number  VARCHAR(20),
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_branch_name_notempty CHECK (TRIM(branch_name) <> '')
);

COMMENT ON TABLE  Branch               IS 'Stores bank branch details';
COMMENT ON COLUMN Branch.branch_id     IS 'Auto-incremented primary key';
COMMENT ON COLUMN Branch.branch_name   IS 'Official name of the branch';
COMMENT ON COLUMN Branch.branch_city   IS 'City where branch is located';


-- ============================================================
-- TABLE 2: Customer
-- Stores bank customer personal information
-- No foreign key dependencies — created early
-- ============================================================
CREATE TABLE Customer (
    customer_id     SERIAL          PRIMARY KEY,
    first_name      VARCHAR(50)     NOT NULL,
    last_name       VARCHAR(50)     NOT NULL,
    email           VARCHAR(100)    NOT NULL UNIQUE,
    contact_number  VARCHAR(20),
    address         TEXT,
    date_of_birth   DATE,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_customer_email   CHECK (email LIKE '%@%.%'),
    CONSTRAINT chk_customer_dob     CHECK (date_of_birth < CURRENT_DATE)
);

COMMENT ON TABLE  Customer              IS 'Stores customer personal information';
COMMENT ON COLUMN Customer.customer_id  IS 'Auto-incremented primary key';
COMMENT ON COLUMN Customer.email        IS 'Must be unique across all customers';


-- ============================================================
-- TABLE 3: Employee
-- Stores bank employee details, linked to a Branch
-- FK: branch_id → Branch(branch_id)
-- ============================================================
CREATE TABLE Employee (
    employee_id     SERIAL          PRIMARY KEY,
    branch_id       INT             NOT NULL,
    first_name      VARCHAR(50)     NOT NULL,
    last_name       VARCHAR(50)     NOT NULL,
    role            VARCHAR(50)     NOT NULL DEFAULT 'TELLER',
    email           VARCHAR(100)    UNIQUE,
    contact_number  VARCHAR(20),
    hire_date       DATE            DEFAULT CURRENT_DATE,

    CONSTRAINT fk_employee_branch
        FOREIGN KEY (branch_id)
        REFERENCES Branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT chk_employee_role
        CHECK (role IN ('MANAGER','TELLER','LOAN_OFFICER','CASHIER','AUDITOR'))
);

COMMENT ON TABLE  Employee               IS 'Bank employees assigned to branches';
COMMENT ON COLUMN Employee.branch_id     IS 'FK to Branch — employee works at this branch';
COMMENT ON COLUMN Employee.role          IS 'Job role: MANAGER, TELLER, LOAN_OFFICER, etc.';


-- ============================================================
-- TABLE 4: Account
-- Core banking table — links Customer and Branch
-- FK: customer_id → Customer, branch_id → Branch
-- ============================================================
CREATE TABLE Account (
    account_id      SERIAL          PRIMARY KEY,
    customer_id     INT             NOT NULL,
    branch_id       INT             NOT NULL,
    account_number  VARCHAR(20)     NOT NULL UNIQUE,
    account_type    VARCHAR(30)     NOT NULL DEFAULT 'SAVINGS',
    balance         DECIMAL(12,2)   NOT NULL DEFAULT 0.00,
    status          VARCHAR(20)     NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_account_customer
        FOREIGN KEY (customer_id)
        REFERENCES Customer(customer_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_account_branch
        FOREIGN KEY (branch_id)
        REFERENCES Branch(branch_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT chk_account_type
        CHECK (account_type IN ('SAVINGS','CURRENT','FIXED_DEPOSIT')),

    CONSTRAINT chk_account_status
        CHECK (status IN ('ACTIVE','INACTIVE','FROZEN','CLOSED')),

    CONSTRAINT chk_account_balance
        CHECK (balance >= 0.00)
);

COMMENT ON TABLE  Account                IS 'Bank accounts owned by customers';
COMMENT ON COLUMN Account.account_number IS 'Unique account identifier shown to customer';
COMMENT ON COLUMN Account.balance        IS 'Current balance — cannot go negative';
COMMENT ON COLUMN Account.status         IS 'ACTIVE | INACTIVE | FROZEN | CLOSED';


-- ============================================================
-- TABLE 5: Transaction_Record
-- Records every financial transaction on an account
-- FK: account_id → Account
-- Captures old_balance and new_balance for WAL/recovery demo
-- ============================================================
CREATE TABLE Transaction_Record (
    transaction_id      SERIAL          PRIMARY KEY,
    account_id          INT             NOT NULL,
    transaction_type    VARCHAR(20)     NOT NULL,
    amount              DECIMAL(12,2)   NOT NULL,
    old_balance         DECIMAL(12,2)   NOT NULL,
    new_balance         DECIMAL(12,2)   NOT NULL,
    transaction_status  VARCHAR(20)     NOT NULL DEFAULT 'PENDING',
    transaction_time    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes               TEXT,

    CONSTRAINT fk_transaction_account
        FOREIGN KEY (account_id)
        REFERENCES Account(account_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT chk_txn_type
        CHECK (transaction_type IN ('DEPOSIT','WITHDRAWAL','TRANSFER_IN','TRANSFER_OUT')),

    CONSTRAINT chk_txn_status
        CHECK (transaction_status IN ('PENDING','COMMITTED','ROLLED_BACK')),

    CONSTRAINT chk_txn_amount
        CHECK (amount > 0),

    CONSTRAINT chk_txn_balances
        CHECK (old_balance >= 0 AND new_balance >= 0)
);

COMMENT ON TABLE  Transaction_Record                    IS 'Logs all financial operations on accounts';
COMMENT ON COLUMN Transaction_Record.old_balance        IS 'Balance BEFORE this transaction — used in Undo';
COMMENT ON COLUMN Transaction_Record.new_balance        IS 'Balance AFTER this transaction — used in Redo';
COMMENT ON COLUMN Transaction_Record.transaction_status IS 'PENDING | COMMITTED | ROLLED_BACK';


-- ============================================================
-- TABLE 6: Loan
-- Stores loan records linked to a customer and account
-- FK: customer_id → Customer, account_id → Account
-- ============================================================
CREATE TABLE Loan (
    loan_id         SERIAL          PRIMARY KEY,
    customer_id     INT             NOT NULL,
    account_id      INT             NOT NULL,
    loan_type       VARCHAR(50)     NOT NULL DEFAULT 'PERSONAL',
    loan_amount     DECIMAL(12,2)   NOT NULL,
    interest_rate   DECIMAL(5,2)    NOT NULL DEFAULT 10.00,
    start_date      DATE            NOT NULL DEFAULT CURRENT_DATE,
    end_date        DATE,
    loan_status     VARCHAR(20)     NOT NULL DEFAULT 'ACTIVE',

    CONSTRAINT fk_loan_customer
        FOREIGN KEY (customer_id)
        REFERENCES Customer(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_loan_account
        FOREIGN KEY (account_id)
        REFERENCES Account(account_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_loan_type
        CHECK (loan_type IN ('HOME','CAR','PERSONAL','EDUCATION','BUSINESS')),

    CONSTRAINT chk_loan_status
        CHECK (loan_status IN ('ACTIVE','CLOSED','DEFAULTED','PENDING_APPROVAL')),

    CONSTRAINT chk_loan_amount
        CHECK (loan_amount > 0),

    CONSTRAINT chk_loan_rate
        CHECK (interest_rate >= 0 AND interest_rate <= 100),

    CONSTRAINT chk_loan_dates
        CHECK (end_date IS NULL OR end_date > start_date)
);

COMMENT ON TABLE  Loan                IS 'Loan records linked to customers and accounts';
COMMENT ON COLUMN Loan.interest_rate  IS 'Annual interest rate in percentage (e.g. 12.50 = 12.5%)';
COMMENT ON COLUMN Loan.loan_status    IS 'ACTIVE | CLOSED | DEFAULTED | PENDING_APPROVAL';


-- ============================================================
-- INDEXES: Improve query performance on frequently used columns
-- ============================================================
CREATE INDEX idx_account_customer    ON Account(customer_id);
CREATE INDEX idx_account_branch      ON Account(branch_id);
CREATE INDEX idx_txn_account         ON Transaction_Record(account_id);
CREATE INDEX idx_txn_status          ON Transaction_Record(transaction_status);
CREATE INDEX idx_txn_time            ON Transaction_Record(transaction_time DESC);
CREATE INDEX idx_employee_branch     ON Employee(branch_id);
CREATE INDEX idx_loan_customer       ON Loan(customer_id);
CREATE INDEX idx_loan_status         ON Loan(loan_status);

-- ============================================================
-- SCHEMA COMPLETE
-- Tables created: Branch, Customer, Employee, Account,
--                 Transaction_Record, Loan
-- Run 03_sample_data.sql next
-- ============================================================
