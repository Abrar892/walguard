# ADBMS Final Project: Log-Based Recovery System
## PostgreSQL + MongoDB | Undergraduate Level

---

## 1. Project Overview

### Objective
Demonstrate core Advanced DBMS concepts — Write-Ahead Logging (WAL), crash recovery, Undo/Redo operations, and polyglot persistence — using a simplified banking simulation built on **PostgreSQL** and **MongoDB**.

### Why Hybrid Databases?
| Concern | PostgreSQL | MongoDB |
|---|---|---|
| Structured banking data | ✅ ACID-compliant relational tables | ❌ |
| Flexible, fast log writes | ❌ Schema rigid | ✅ Schema-free JSON documents |
| Transaction integrity | ✅ FK constraints, rollback | ❌ |
| Recovery logs & audit trail | ❌ | ✅ Timestamped, rich metadata |

This is **polyglot persistence**: each database is used where it excels.

### How the Recovery System Works
1. Before any DB change, a **WAL log entry** is written to MongoDB (`UNCOMMITTED`)
2. The PostgreSQL data change is applied
3. On `COMMIT` → log updated to `COMMITTED`
4. On `ROLLBACK` or crash → **Undo** logic reads MongoDB logs and reverses PostgreSQL changes
5. On restart → **Redo** logic replays committed-but-lost transactions

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│         (Python scripts / CLI demo / psycopg2)           │
└────────────┬────────────────────────┬───────────────────┘
             │                        │
     ┌───────▼────────┐     ┌─────────▼──────────┐
     │   PostgreSQL   │     │      MongoDB        │
     │  Banking Data  │     │   Transaction Logs  │
     │                │     │                     │
     │ • Customer     │     │ • wal_logs          │
     │ • Account      │     │ • recovery_logs     │
     │ • Transaction  │     │ • crash_log         │
     │ • Branch       │     │                     │
     │ • Employee     │     │                     │
     │ • Loan         │     │                     │
     └───────┬────────┘     └─────────┬───────────┘
             │                        │
     ┌───────▼────────────────────────▼───────────┐
     │              Recovery Module                │
     │  • recovery_manager.py                      │
     │  • undo_manager.py                          │
     │  • redo_manager.py                          │
     │  • crash_simulator.py                       │
     └─────────────────────────────────────────────┘
```

### Module Roles
- **PostgreSQL**: Stores ground-truth banking state (accounts, balances, transactions)
- **MongoDB**: Stores every log record written BEFORE the DB change (WAL principle)
- **Recovery Module**: Reads MongoDB logs → determines what to undo or redo → fixes PostgreSQL

---

## 3. Simplified ER Diagram

```
Branch (1) ──< Employee (many)
Branch (1) ──< Account (many)
Customer (1) ──< Account (many)
Account (1) ──< Transaction_Record (many)
Customer (1) ──< Loan (many)
Account (1) ──< Loan (many)
Account / Transaction_Record ──> MongoDB Logs (conceptual link via account_id / transaction_id)
```

### Cardinality Summary
| Relationship | Type | Explanation |
|---|---|---|
| Branch → Employee | 1:N | One branch has many employees |
| Branch → Account | 1:N | One branch hosts many accounts |
| Customer → Account | 1:N | One customer can have multiple accounts |
| Account → Transaction_Record | 1:N | One account has many transactions |
| Customer → Loan | 1:N | One customer can have many loans |
| Account → Loan | 1:N | One account linked to many loans |

### Normalization
- **1NF**: All attributes are atomic (no multi-valued or composite fields)
- **2NF**: All non-key attributes fully depend on the primary key (no partial dependencies)
- **3NF**: No transitive dependencies (e.g., branch info is in its own table, not repeated in Account)

---

## 4. PostgreSQL Schema Design

```sql
-- ============================================================
-- SCHEMA: Log-Based Recovery System Banking Database
-- ============================================================

CREATE TABLE Branch (
    branch_id       SERIAL PRIMARY KEY,
    branch_name     VARCHAR(100) NOT NULL,
    branch_city     VARCHAR(50),
    branch_address  TEXT,
    contact_number  VARCHAR(20),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Customer (
    customer_id     SERIAL PRIMARY KEY,
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    email           VARCHAR(100) UNIQUE NOT NULL,
    contact_number  VARCHAR(20),
    address         TEXT,
    date_of_birth   DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Employee (
    employee_id     SERIAL PRIMARY KEY,
    branch_id       INT NOT NULL,
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    role            VARCHAR(50),
    email           VARCHAR(100) UNIQUE,
    contact_number  VARCHAR(20),
    hire_date       DATE,
    CONSTRAINT fk_employee_branch
        FOREIGN KEY (branch_id) REFERENCES Branch(branch_id)
        ON DELETE RESTRICT
);

CREATE TABLE Account (
    account_id      SERIAL PRIMARY KEY,
    customer_id     INT NOT NULL,
    branch_id       INT NOT NULL,
    account_number  VARCHAR(20) UNIQUE NOT NULL,
    account_type    VARCHAR(30) CHECK (account_type IN ('SAVINGS', 'CURRENT', 'FIXED')),
    balance         DECIMAL(12,2) DEFAULT 0.00 CHECK (balance >= 0),
    status          VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE','FROZEN')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_account_customer
        FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_account_branch
        FOREIGN KEY (branch_id) REFERENCES Branch(branch_id)
        ON DELETE RESTRICT
);

CREATE TABLE Transaction_Record (
    transaction_id      SERIAL PRIMARY KEY,
    account_id          INT NOT NULL,
    transaction_type    VARCHAR(20) CHECK (transaction_type IN ('DEPOSIT','WITHDRAWAL','TRANSFER')),
    amount              DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    old_balance         DECIMAL(12,2),
    new_balance         DECIMAL(12,2),
    transaction_status  VARCHAR(20) DEFAULT 'PENDING'
                            CHECK (transaction_status IN ('PENDING','COMMITTED','ROLLED_BACK')),
    transaction_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_transaction_account
        FOREIGN KEY (account_id) REFERENCES Account(account_id)
        ON DELETE RESTRICT
);

CREATE TABLE Loan (
    loan_id         SERIAL PRIMARY KEY,
    customer_id     INT NOT NULL,
    account_id      INT NOT NULL,
    loan_type       VARCHAR(50) CHECK (loan_type IN ('HOME','CAR','PERSONAL','EDUCATION')),
    loan_amount     DECIMAL(12,2) NOT NULL CHECK (loan_amount > 0),
    interest_rate   DECIMAL(5,2),
    start_date      DATE,
    end_date        DATE,
    loan_status     VARCHAR(20) DEFAULT 'ACTIVE'
                        CHECK (loan_status IN ('ACTIVE','CLOSED','DEFAULTED')),
    CONSTRAINT fk_loan_customer
        FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
    CONSTRAINT fk_loan_account
        FOREIGN KEY (account_id) REFERENCES Account(account_id)
);
```

### Sample INSERT Queries

```sql
-- Branch
INSERT INTO Branch (branch_name, branch_city, branch_address, contact_number)
VALUES ('Main Branch', 'Lahore', '12 Mall Road, Lahore', '042-1234567');

-- Customer
INSERT INTO Customer (first_name, last_name, email, contact_number, address, date_of_birth)
VALUES ('Ali', 'Raza', 'ali.raza@email.com', '0300-1234567', 'Gulberg, Lahore', '1995-03-15');

-- Employee
INSERT INTO Employee (branch_id, first_name, last_name, role, email, hire_date)
VALUES (1, 'Sara', 'Khan', 'Manager', 'sara.khan@bank.com', '2020-01-10');

-- Account
INSERT INTO Account (customer_id, branch_id, account_number, account_type, balance)
VALUES (1, 1, 'ACC-00001', 'SAVINGS', 10000.00);

-- Transaction_Record
INSERT INTO Transaction_Record (account_id, transaction_type, amount, old_balance, new_balance, transaction_status)
VALUES (1, 'WITHDRAWAL', 500.00, 10000.00, 9500.00, 'COMMITTED');

-- Loan
INSERT INTO Loan (customer_id, account_id, loan_type, loan_amount, interest_rate, start_date, end_date, loan_status)
VALUES (1, 1, 'HOME', 500000.00, 12.50, '2024-01-01', '2034-01-01', 'ACTIVE');
```

---

## 5. MongoDB Schema Design

### Collection: `wal_logs`

Each document is written **before** the PostgreSQL update (Write-Ahead Log).

```json
{
  "_id": ObjectId("..."),
  "log_id": 1,
  "transaction_id": 101,
  "operation": "UPDATE",
  "table_name": "Account",
  "account_id": 5,
  "old_balance": 5000.00,
  "new_balance": 4500.00,
  "amount": 500.00,
  "transaction_type": "WITHDRAWAL",
  "status": "UNCOMMITTED",
  "timestamp": "2026-05-17T10:20:00Z",
  "session_id": "sess_abc123"
}
```

### Collection: `recovery_logs`

Written when recovery module runs.

```json
{
  "_id": ObjectId("..."),
  "recovery_id": 1,
  "recovery_type": "UNDO",
  "transaction_id": 101,
  "account_id": 5,
  "balance_restored": 5000.00,
  "reason": "CRASH_DETECTED",
  "recovered_at": "2026-05-17T10:25:00Z"
}
```

### Collection: `crash_log`

```json
{
  "_id": ObjectId("..."),
  "crash_id": 1,
  "crash_time": "2026-05-17T10:22:00Z",
  "uncommitted_transactions": [101, 102],
  "committed_transactions": [99, 100],
  "recovery_triggered": true
}
```

### Transaction Logging Workflow (MongoDB)
1. **START** → Insert log with `status: "UNCOMMITTED"`
2. **OPERATION** → Log includes old_value + new_value
3. **COMMIT** → Update log: `status: "COMMITTED"`
4. **ROLLBACK** → Update log: `status: "ROLLED_BACK"`
5. **CRASH** → Logs remain `UNCOMMITTED` → Recovery reads and undoes

---

## 6. Transaction Workflow (Step-by-Step)

```
Step 1: BEGIN TRANSACTION
        → Generate transaction_id
        → Write WAL log to MongoDB (status=UNCOMMITTED)

Step 2: EXECUTE OPERATION
        → Read current balance from PostgreSQL (old_balance)
        → Calculate new_balance
        → Update log: old_balance, new_balance captured

Step 3: UPDATE PostgreSQL
        → UPDATE Account SET balance = new_balance WHERE account_id = X
        → INSERT into Transaction_Record (status=PENDING)

Step 4a: COMMIT
        → UPDATE Transaction_Record SET status = 'COMMITTED'
        → UPDATE MongoDB wal_logs SET status = 'COMMITTED'

Step 4b: ROLLBACK
        → ROLLBACK PostgreSQL transaction (auto-undoes Step 3)
        → UPDATE MongoDB log status = 'ROLLED_BACK'

Step 5: CRASH SCENARIO
        → PostgreSQL change may be partial
        → MongoDB log still shows UNCOMMITTED
        → Recovery module detects uncommitted logs
        → UNDO: restore old_balance in PostgreSQL
        → Write to recovery_logs collection
```

---

## 7. Recovery Module

### Undo Logic
- Scan MongoDB `wal_logs` for `status = "UNCOMMITTED"`
- For each uncommitted log: `UPDATE Account SET balance = old_balance WHERE account_id = X`
- Update Transaction_Record status → `ROLLED_BACK`
- Insert into `recovery_logs` with `recovery_type = "UNDO"`

### Redo Logic
- Scan MongoDB `wal_logs` for `status = "COMMITTED"` where no corresponding committed Transaction_Record exists in PostgreSQL
- Reapply: `UPDATE Account SET balance = new_balance WHERE account_id = X`
- Insert into `recovery_logs` with `recovery_type = "REDO"`

### Recovery Manager Workflow
```
1. SCAN phase       → Read all WAL logs from MongoDB
2. CLASSIFY phase   → Separate COMMITTED vs UNCOMMITTED
3. UNDO phase       → Undo all UNCOMMITTED logs (newest first)
4. REDO phase       → Redo all COMMITTED logs missing in PostgreSQL
5. LOG phase        → Write recovery actions to recovery_logs
6. VERIFY phase     → Confirm PostgreSQL state is consistent
```

### ARIES-Inspired Simplification
| ARIES Phase | Our Simplified Version |
|---|---|
| Analysis | Scan MongoDB logs, classify by status |
| Redo | Re-apply committed transactions |
| Undo | Reverse uncommitted transactions |
| CLR (Compensation Log) | Write to `recovery_logs` collection |

---

## 8. Project Folder Structure

```
LogRecoverySystem/
│
├── postgresql/
│   ├── schema.sql              # All CREATE TABLE statements
│   ├── sample_data.sql         # INSERT statements
│   └── queries.sql             # Useful SELECT queries
│
├── mongodb/
│   ├── collections_setup.js    # db.createCollection() scripts
│   ├── sample_logs.json        # Example log documents
│   └── indexes.js              # Index creation scripts
│
├── recovery/
│   ├── db_config.py            # PG + Mongo connection config
│   ├── transaction_manager.py  # Begin, commit, rollback
│   ├── wal_logger.py           # Write-Ahead Log writer
│   ├── undo_manager.py         # Undo uncommitted txns
│   ├── redo_manager.py         # Redo committed txns
│   ├── recovery_manager.py     # Orchestrates full recovery
│   └── crash_simulator.py      # Simulates mid-txn crash
│
├── demo/
│   ├── demo_normal_txn.py      # Normal transfer demo
│   ├── demo_rollback.py        # Rollback demo
│   ├── demo_crash_recovery.py  # Crash + recovery demo
│   └── demo_undo_redo.py       # Undo/Redo demo
│
├── docs/
│   ├── ER_Diagram.png
│   ├── Architecture_Diagram.png
│   └── Project_Report.pdf
│
├── requirements.txt            # psycopg2, pymongo, etc.
└── README.md
```

---

## 9. Recovery Pseudocode

### WAL Logger
```
FUNCTION write_wal_log(transaction_id, account_id, old_balance, new_balance, operation):
    log = {
        transaction_id: transaction_id,
        operation: operation,
        account_id: account_id,
        old_balance: old_balance,
        new_balance: new_balance,
        status: "UNCOMMITTED",
        timestamp: NOW()
    }
    MongoDB.wal_logs.insert(log)
    RETURN log._id
```

### Undo Pseudocode
```
FUNCTION undo_recovery():
    logs = MongoDB.wal_logs.find({ status: "UNCOMMITTED" })
    sort logs by timestamp DESCENDING  // Undo newest first
    FOR each log in logs:
        PostgreSQL.execute(
            "UPDATE Account SET balance = %s WHERE account_id = %s",
            [log.old_balance, log.account_id]
        )
        PostgreSQL.execute(
            "UPDATE Transaction_Record SET transaction_status = 'ROLLED_BACK'
             WHERE transaction_id = %s",
            [log.transaction_id]
        )
        MongoDB.wal_logs.update(
            { _id: log._id },
            { status: "ROLLED_BACK" }
        )
        write_recovery_log("UNDO", log.transaction_id, log.account_id, log.old_balance)
    RETURN "UNDO COMPLETE"
```

### Redo Pseudocode
```
FUNCTION redo_recovery():
    committed_logs = MongoDB.wal_logs.find({ status: "COMMITTED" })
    FOR each log in committed_logs:
        pg_record = PostgreSQL.execute(
            "SELECT transaction_status FROM Transaction_Record
             WHERE transaction_id = %s", [log.transaction_id]
        )
        IF pg_record.transaction_status != 'COMMITTED':
            PostgreSQL.execute(
                "UPDATE Account SET balance = %s WHERE account_id = %s",
                [log.new_balance, log.account_id]
            )
            PostgreSQL.execute(
                "UPDATE Transaction_Record SET transaction_status = 'COMMITTED'
                 WHERE transaction_id = %s",
                [log.transaction_id]
            )
            write_recovery_log("REDO", log.transaction_id, log.account_id, log.new_balance)
    RETURN "REDO COMPLETE"
```

### Recovery Manager Pseudocode
```
FUNCTION run_recovery():
    PRINT "Recovery Manager Started"
    
    // Phase 1: Analysis
    all_logs = MongoDB.wal_logs.find_all()
    uncommitted = filter(all_logs, status == "UNCOMMITTED")
    committed   = filter(all_logs, status == "COMMITTED")
    
    // Phase 2: Undo
    IF uncommitted is not empty:
        PRINT "Undoing", count(uncommitted), "uncommitted transactions"
        undo_recovery()
    
    // Phase 3: Redo
    IF committed is not empty:
        PRINT "Redoing", count(committed), "committed transactions"
        redo_recovery()
    
    // Phase 4: Log crash event
    MongoDB.crash_log.insert({
        crash_time: crash_time,
        uncommitted_transactions: [log.transaction_id for log in uncommitted],
        committed_transactions: [log.transaction_id for log in committed],
        recovery_triggered: True,
        recovered_at: NOW()
    })
    
    PRINT "Recovery Complete"
```

---

## 10. ADBMS Concepts Covered

| Concept | How Demonstrated |
|---|---|
| **Transactions** | Python script wraps DB ops in BEGIN/COMMIT/ROLLBACK |
| **ACID** | Atomicity via rollback; Isolation via PG transactions; Durability via WAL |
| **WAL** | MongoDB log written BEFORE PostgreSQL update |
| **Undo** | Old balance restored from MongoDB log on crash/rollback |
| **Redo** | New balance re-applied for committed-but-lost transactions |
| **Recovery** | Recovery manager reads logs and restores consistent state |
| **Logging** | Every operation has timestamped JSON entry in MongoDB |
| **Polyglot Persistence** | PG for structured data + MongoDB for flexible logs |
| **Hybrid Databases** | Two different DB paradigms working in the same system |
| **Crash Simulation** | Python raises exception mid-transaction to simulate crash |

### ACID Breakdown
- **Atomicity**: Transaction either fully completes or is fully undone
- **Consistency**: CHECK constraints, FK constraints in PostgreSQL
- **Isolation**: PostgreSQL handles concurrent transaction isolation
- **Durability**: WAL in MongoDB ensures log survives before PG is touched

---

## 11. Viva Preparation

### Expected Teacher Questions

**Q1: What is Write-Ahead Logging?**
> WAL means the log record is written to durable storage BEFORE the actual data change is applied. In our system, MongoDB receives the log entry (with old and new values) BEFORE PostgreSQL is updated. This guarantees that even if PostgreSQL crashes mid-update, the log exists and we can recover.

**Q2: How does your system differ from ARIES?**
> Full ARIES uses three phases (Analysis, Redo, Undo), a Log Sequence Number (LSN) system, and Compensation Log Records (CLRs). Our simplified version uses the same three-phase approach but without LSNs. We use MongoDB timestamps and `status` fields to classify and order log records. It is ARIES-inspired, not a full ARIES implementation.

**Q3: Why use MongoDB for logs instead of a PostgreSQL table?**
> MongoDB allows flexible, schema-free JSON documents that are fast to insert without transaction overhead. Since we need to write logs before PG updates, we want the log write to be independent of the PG transaction. MongoDB's document model also naturally captures before/after values and metadata in a single record.

**Q4: What is polyglot persistence?**
> Using multiple database technologies in the same system, each chosen for what it does best. PostgreSQL handles ACID-compliant relational banking data. MongoDB handles flexible, high-speed log storage. Together they form a more capable system than either could alone.

**Q5: How do you identify uncommitted transactions after a crash?**
> After a crash, we scan the MongoDB `wal_logs` collection for documents where `status = "UNCOMMITTED"`. These are transactions that were started but never reached the COMMIT step, meaning their PostgreSQL changes may be partial or inconsistent.

**Q6: What is the difference between Undo and Redo?**
> **Undo** reverses an uncommitted transaction — we restore the `old_balance` from the log. **Redo** re-applies a committed transaction that may have been lost — we apply the `new_balance` from the log. Undo removes incorrect changes; Redo re-instates correct changes.

**Q7: What is a checkpoint in recovery?**
> A checkpoint is a point where all committed transactions are guaranteed to be flushed to disk. After a checkpoint, we only need to recover transactions that happened after it. Our simplified system doesn't implement checkpoints, but you can explain the concept.

**Q8: What happens if recovery itself crashes?**
> Idempotency is key. Our undo and redo operations check the current state before applying changes, so re-running recovery produces the same result. This is why we update log `status` fields atomically.

### Counter Questions You May Face
- "Show me the WAL log being written before the DB update in your code"
- "What if MongoDB crashes while writing the log?"
- "Can two transactions run simultaneously in your system?"
- "What is the LSN equivalent in your system?"

---

## 12. Demonstration Flow

### Demo Scenario: Transfer with Crash Recovery

```
STEP 1 — Setup
  • Show PostgreSQL: Account A (balance=10000), Account B (balance=5000)
  • Show MongoDB: wal_logs collection (empty)

STEP 2 — Normal Transfer (demo_normal_txn.py)
  • Transfer 1000 from Account A to Account B
  • Show WAL log written BEFORE balance update
  • Show PostgreSQL balance updated
  • Show log status changed to COMMITTED
  • Result: A=9000, B=6000

STEP 3 — Rollback Demo (demo_rollback.py)
  • Begin transfer of 2000 from Account A
  • Show WAL log written (status=UNCOMMITTED)
  • Trigger ROLLBACK (e.g., insufficient funds check fails)
  • Show PostgreSQL balance unchanged
  • Show log status updated to ROLLED_BACK

STEP 4 — Crash Simulation (demo_crash_recovery.py)
  • Begin transfer of 3000 from Account A
  • WAL log written to MongoDB (status=UNCOMMITTED)
  • PostgreSQL update begins
  • CRASH INJECTED (raise Exception mid-transaction)
  • Show: PostgreSQL may be inconsistent
  • Show: MongoDB log still shows UNCOMMITTED

STEP 5 — Recovery Execution (recovery_manager.py)
  • Run recovery manager
  • UNDO phase: old_balance restored in PostgreSQL
  • Show: Account A balance back to pre-crash value
  • Show: recovery_logs entry written
  • Show: wal_log status updated to ROLLED_BACK

STEP 6 — Redo Demo (demo_undo_redo.py)
  • Manually set a log to COMMITTED but undo PostgreSQL change
  • Run redo recovery
  • Show: balance re-applied from new_balance in log
```

---

## 13. Scope Control Summary

### ✅ In Scope (Keep)
- 6 PostgreSQL tables (Customer, Branch, Employee, Account, Transaction_Record, Loan)
- 3 MongoDB collections (wal_logs, recovery_logs, crash_log)
- Python recovery scripts (psycopg2 + pymongo)
- Undo / Redo / Recovery demos
- Transaction simulation with crash injection

### ❌ Out of Scope (Avoid)
- Full ARIES with LSN chains
- ATM, Card, Locker modules
- Web frontend or REST API
- Distributed databases or replication
- Real concurrent multi-user sessions
- Full production-grade error handling

---

## Requirements

```
# requirements.txt
psycopg2-binary==2.9.9
pymongo==4.6.1
python-dotenv==1.0.0
```

### Connection Config (`db_config.py`)
```python
import psycopg2
from pymongo import MongoClient

def get_pg_connection():
    return psycopg2.connect(
        host="localhost",
        database="bank_recovery_db",
        user="postgres",
        password="your_password",
        port=5432
    )

def get_mongo_client():
    client = MongoClient("mongodb://localhost:27017/")
    return client["bank_recovery_logs"]
```

---

*Project: Log-Based Recovery System | ADBMS Final Project | Undergraduate Level*
*Technologies: PostgreSQL 15+, MongoDB 7+, Python 3.10+*
