# ADBMS Final Project — Setup & Run Guide
## Log-Based Recovery System | PostgreSQL + MongoDB | Python

---

## Prerequisites

| Software | Version | Download |
|---|---|---|
| Python | 3.9+ | python.org |
| PostgreSQL | 14+ | postgresql.org |
| MongoDB | 6.0+ | mongodb.com |
| pgAdmin 4 | any | pgadmin.org |
| mongosh | any | mongodb.com/tools |

---

## Step 1 — Install Python Packages

Open PowerShell or Command Prompt inside the `recovery/` folder:

```powershell
cd "c:\Abrar\study\2024-CS-59\4th Semester\ADBMS Final Project\recovery"
pip install -r requirements.txt
```

**Packages installed:**
- `psycopg2-binary` — connects Python to PostgreSQL
- `pymongo` — connects Python to MongoDB
- `colorama` — optional colored terminal output

---

## Step 2 — PostgreSQL Setup

### 2a. Open pgAdmin 4

1. Connect to your local PostgreSQL server (localhost:5432)
2. Open **Query Tool** on the `postgres` database

### 2b. Run SQL scripts in order

Open each file in pgAdmin Query Tool and press **F5** to run:

```
postgresql/01_create_database.sql    ← Run on 'postgres' DB
postgresql/02_schema.sql             ← Switch to 'bank_recovery_db' first
postgresql/03_sample_data.sql        ← Run on 'bank_recovery_db'
```

> **Important:** After running `01_create_database.sql`, disconnect from
> `postgres` and reconnect to `bank_recovery_db` before running the next scripts.

### 2c. Verify tables exist

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected output: `account, branch, customer, employee, loan, transaction_record`

### 2d. Update db_config.py

Open `recovery/db_config.py` and change the password:

```python
PG_PASSWORD = "your_actual_password"   # ← change this
```

---

## Step 3 — MongoDB Setup

### 3a. Verify MongoDB is running

```powershell
mongosh --eval "db.runCommand({ping:1})"
```

Expected: `{ ok: 1 }`

If MongoDB is not running:
```powershell
net start MongoDB
```

### 3b. Run MongoDB setup scripts

```powershell
cd "c:\Abrar\study\2024-CS-59\4th Semester\ADBMS Final Project\mongodb"

mongosh < 01_setup_database.js
mongosh < 02_sample_wal_logs.js
mongosh < 03_recovery_logs.js
```

### 3c. Verify collections exist

```javascript
use("bank_recovery_logs")
db.getCollectionNames()
```

Expected: `["crash_log", "recovery_logs", "system_config", "wal_logs"]`

---

## Step 4 — Run the Project

```powershell
cd "c:\Abrar\study\2024-CS-59\4th Semester\ADBMS Final Project\recovery"
python main.py
```

### Expected startup output:

```
  Checking database connections...
  [OK] PostgreSQL connected  → database: bank_recovery_db
  [OK] MongoDB connected     → database: bank_recovery_logs

==============================================
  LOG-BASED RECOVERY SYSTEM — ADBMS Project
==============================================
  1. Deposit
  2. Withdraw
  3. Transfer
  4. Simulate Crash   (before COMMIT)
  5. Run Recovery     (UNDO + REDO)
  6. Show WAL Logs    (MongoDB)
  7. Show Balances    (PostgreSQL)
  0. Exit
```

---

## Step 5 — Recommended Demo Sequence (For Viva)

Run these options in order during your viva or presentation:

### Demo A — Normal Transaction (Option 1)
```
Choose: 1 (Deposit)
Amount: 1500
```
**What to show:** WAL log appears as UNCOMMITTED, then immediately COMMITTED.

---

### Demo B — Rollback (Option 2 with large amount)
```
Choose: 2 (Withdraw)
Amount: 999999
```
**What to show:** Insufficient funds → ROLLBACK → WAL log = ROLLED_BACK.

---

### Demo C — Crash Simulation (Option 4)
```
Choose: 4 (Simulate Crash)
Amount: 3000
```
**What to show:**
```
[WAL] Log #8 → UNCOMMITTED  (WITHDRAWAL, account=1, ...)
[PG]  Balance changed: 10000.00 → 7000.00
*** SYSTEM CRASH — Exception raised! ***
[PG]  Connection closed → PG auto-rollback
[WAL] Log #8 still UNCOMMITTED in MongoDB
```

---

### Demo D — View WAL Logs (Option 6)
Show the UNCOMMITTED log still sitting in MongoDB — this is what the Recovery Manager will fix.

---

### Demo E — Recovery (Option 5)
```
Choose: 5 (Run Recovery)
```
**What to show:**
```
── Phase 1: ANALYSIS ──
  Found 1 UNCOMMITTED log(s) → need UNDO

── Phase 2: UNDO ──
  UNDO log_id=8  account_id=1
    PG balance now : 10000.00
    Restoring to   : 10000.00
    ✓ UNDO complete.

── Phase 3: REDO ──
  ✓ All committed transactions consistent.

RECOVERY COMPLETE
  UNDO applied : 1
  REDO applied : 0
```

---

### Demo F — Verify Recovery (Option 7 + 6)
- Option 7: PostgreSQL balance restored
- Option 6: WAL log now shows ROLLED_BACK

---

## File Reference

| File | Purpose | ADBMS Concept |
|---|---|---|
| `db_config.py` | DB connections | Polyglot Persistence |
| `mongo_logger.py` | WAL log writes | Write-Ahead Logging |
| `transaction_manager.py` | Banking transactions | Transactions, ACID |
| `crash_simulator.py` | Crash injection | Crash Recovery |
| `recovery_manager.py` | UNDO + REDO | Recovery, ARIES |
| `main.py` | Menu interface | Demo runner |

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `OperationalError: FATAL: password auth failed` | Wrong PG password | Update `PG_PASSWORD` in db_config.py |
| `ConnectionRefusedError: [Errno 111]` | PostgreSQL not running | Start PostgreSQL service |
| `ConnectionFailure: ... 27017` | MongoDB not running | Run `net start MongoDB` |
| `relation "account" does not exist` | Wrong database | Connect to `bank_recovery_db` not `postgres` |
| `No module named 'psycopg2'` | Package not installed | Run `pip install -r requirements.txt` |

---

## ADBMS Concepts Quick Reference (For Viva)

| Concept | Where Shown |
|---|---|
| **Write-Ahead Logging** | `mongo_logger.write_log()` called BEFORE any PG update |
| **UNCOMMITTED state** | WAL log status right after crash simulation |
| **UNDO** | `recovery_manager._phase_undo()` restores `old_balance` |
| **REDO** | `recovery_manager._phase_redo()` re-applies `new_balance` |
| **ACID Atomicity** | Transfer uses one `conn.commit()` for both accounts |
| **ROLLBACK** | Insufficient funds → `conn.rollback()` → balance unchanged |
| **Polyglot Persistence** | PostgreSQL for data + MongoDB for logs |
| **Crash Recovery** | `crash_simulator.simulate_crash()` → recovery sequence |
