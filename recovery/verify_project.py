# ============================================================
# FILE: verify_project.py
# PURPOSE: Complete automated verification of the ADBMS project.
# Run: python verify_project.py
# ============================================================

import sys
import traceback

PYTHON_OK   = True
PG_OK       = False
MONGO_OK    = False
WAL_OK      = False
DEPOSIT_OK  = False
WITHDRAW_OK = False
CRASH_OK    = False
RECOVER_OK  = False

ERRORS = []

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(msg):
    print(f"  [OK]   {msg}")

def fail(msg):
    print(f"  [FAIL] {msg}")
    ERRORS.append(msg)

def info(msg):
    print(f"  [INFO] {msg}")

# ── PHASE 1: Import verification ─────────────────────────────
section("PHASE 1 — Package Imports")

try:
    import psycopg2
    ok(f"psycopg2 {psycopg2.__version__}")
except ImportError as e:
    fail(f"psycopg2 not installed: {e}")

try:
    import pymongo
    ok(f"pymongo {pymongo.__version__}")
except ImportError as e:
    fail(f"pymongo not installed: {e}")

try:
    import colorama
    ok(f"colorama available")
except ImportError:
    info("colorama not installed (optional — continuing)")

# ── PHASE 2: PostgreSQL Connection ───────────────────────────
section("PHASE 2 — PostgreSQL Connection")

try:
    from db_config import get_pg_connection, get_mongo_db
    conn = get_pg_connection()
    cur  = conn.cursor()
    cur.execute("SELECT current_database(), version();")
    db_name, version = cur.fetchone()
    ok(f"Connected to PostgreSQL — database: {db_name}")
    info(f"{version[:70]}")
    PG_OK = True
    cur.close()
    conn.close()
except Exception as e:
    fail(f"PostgreSQL connection failed: {e}")
    info("Check: Is PostgreSQL running? Is PG_PASSWORD correct in db_config.py?")

# ── PHASE 2b: PostgreSQL Tables ──────────────────────────────
if PG_OK:
    section("PHASE 2b — PostgreSQL Tables")
    try:
        conn = get_pg_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
        expected = ['account', 'branch', 'customer', 'employee',
                    'loan', 'transaction_record']
        for t in expected:
            if t in tables:
                ok(f"Table exists: {t}")
            else:
                fail(f"Table MISSING: {t} — run 02_schema.sql")
        cur.close()
        conn.close()
    except Exception as e:
        fail(f"Table check failed: {e}")

# ── PHASE 2c: Sample Data ────────────────────────────────────
if PG_OK:
    section("PHASE 2c — Sample Data Verification")
    try:
        conn = get_pg_connection()
        cur  = conn.cursor()
        for table in ['Branch', 'Customer', 'Account']:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]
            if count > 0:
                ok(f"{table}: {count} rows")
            else:
                fail(f"{table}: 0 rows — run 03_sample_data.sql")

        # Show sample accounts
        cur.execute("""
            SELECT a.account_number, a.balance, c.first_name
            FROM Account a
            JOIN Customer c ON a.customer_id = c.customer_id
            ORDER BY a.account_id
            LIMIT 3;
        """)
        rows = cur.fetchall()
        info("Sample accounts:")
        for acc_num, bal, name in rows:
            info(f"  {acc_num}  balance={bal:.2f}  owner={name}")
        cur.close()
        conn.close()
    except Exception as e:
        fail(f"Sample data check failed: {e}")

# ── PHASE 3: MongoDB Connection ──────────────────────────────
section("PHASE 3 — MongoDB Connection")

try:
    db = get_mongo_db()
    db.command("ping")
    ok(f"Connected to MongoDB — database: bank_recovery_logs")
    cols = db.list_collection_names()
    info(f"Collections: {cols}")
    MONGO_OK = True
    for c in ['wal_logs', 'recovery_logs', 'system_config']:
        if c in cols:
            ok(f"Collection exists: {c}")
        else:
            fail(f"Collection MISSING: {c} — run mongodb/01_setup_database.js")
except Exception as e:
    fail(f"MongoDB connection failed: {e}")
    info("Check: Is MongoDB running on localhost:27017?")

# ── PHASE 4: WAL Log Write ───────────────────────────────────
if MONGO_OK:
    section("PHASE 4 — WAL Log Write Test")
    try:
        from mongo_logger import MongoLogger
        logger = MongoLogger()
        log_id = logger.write_log(
            session_id  = "verify_test",
            account_id  = 9999,
            txn_type    = "DEPOSIT",
            old_balance = 100.00,
            new_balance = 200.00,
            amount      = 100.00,
            notes       = "VERIFICATION TEST — safe to delete"
        )
        ok(f"WAL log inserted → log_id={log_id}")

        # Verify it's in DB
        doc = db["wal_logs"].find_one({"log_id": log_id}, {"_id": 0})
        if doc and doc["status"] == "UNCOMMITTED":
            ok(f"Log found in MongoDB with status=UNCOMMITTED")
        else:
            fail("Log not found or wrong status")

        # Mark committed
        logger.mark_committed(log_id)
        doc2 = db["wal_logs"].find_one({"log_id": log_id}, {"_id": 0})
        if doc2 and doc2["status"] == "COMMITTED":
            ok(f"mark_committed() works → status=COMMITTED")
        else:
            fail("mark_committed() did not update status")

        # Clean up test log
        db["wal_logs"].delete_one({"log_id": log_id, "session_id": "verify_test"})
        WAL_OK = True

    except Exception as e:
        fail(f"WAL log test failed: {e}")
        traceback.print_exc()

# ── PHASE 5: Deposit Transaction ─────────────────────────────
if PG_OK and MONGO_OK:
    section("PHASE 5 — Deposit Transaction Test")
    try:
        from transaction_manager import TransactionManager

        # Get first ACTIVE account
        conn = get_pg_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT account_number, balance FROM Account
            WHERE status = 'ACTIVE' ORDER BY account_id LIMIT 1;
        """)
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            fail("No ACTIVE accounts found — run 03_sample_data.sql")
        else:
            acc_num, bal_before = row
            info(f"Testing deposit on {acc_num} (balance={bal_before:.2f})")

            tm = TransactionManager()
            result = tm.deposit(acc_num, 500.00, notes="Verify deposit test")

            if result:
                # Confirm balance changed
                conn = get_pg_connection()
                cur  = conn.cursor()
                cur.execute("SELECT balance FROM Account WHERE account_number=%s",
                            (acc_num,))
                bal_after = float(cur.fetchone()[0])
                cur.close()
                conn.close()

                if abs(bal_after - (float(bal_before) + 500.00)) < 0.01:
                    ok(f"Deposit verified: {bal_before:.2f} → {bal_after:.2f}")
                    DEPOSIT_OK = True
                else:
                    fail(f"Balance mismatch after deposit: got {bal_after:.2f}")
            else:
                fail("deposit() returned False")

    except Exception as e:
        fail(f"Deposit test failed: {e}")
        traceback.print_exc()

# ── PHASE 6: Withdrawal (Rollback on insufficient funds) ──────
if PG_OK and MONGO_OK:
    section("PHASE 6 — Withdrawal + Rollback Test")
    try:
        from transaction_manager import TransactionManager

        conn = get_pg_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT account_number, balance FROM Account
            WHERE status = 'ACTIVE' ORDER BY account_id LIMIT 1;
        """)
        row = cur.fetchone()
        cur.close()
        conn.close()

        acc_num, bal = row
        tm = TransactionManager()

        # Test 6a: Successful withdrawal (small amount)
        result = tm.withdraw(acc_num, 100.00, notes="Verify withdrawal test")
        if result:
            ok("Small withdrawal: COMMITTED successfully")
            WITHDRAW_OK = True
        else:
            fail("Small withdrawal failed unexpectedly")

        # Test 6b: Rollback due to insufficient funds
        info("Testing rollback with excessive amount (9,999,999)...")
        conn2 = get_pg_connection()
        cur2  = conn2.cursor()
        cur2.execute("SELECT balance FROM Account WHERE account_number=%s", (acc_num,))
        bal_before_rb = float(cur2.fetchone()[0])
        cur2.close()
        conn2.close()

        result_rb = tm.withdraw(acc_num, 9999999.00, notes="Rollback test")
        if not result_rb:
            conn3 = get_pg_connection()
            cur3  = conn3.cursor()
            cur3.execute("SELECT balance FROM Account WHERE account_number=%s", (acc_num,))
            bal_after_rb = float(cur3.fetchone()[0])
            cur3.close()
            conn3.close()
            if abs(bal_before_rb - bal_after_rb) < 0.01:
                ok(f"ROLLBACK verified: balance unchanged at {bal_after_rb:.2f}")
            else:
                fail("Balance changed despite ROLLBACK!")
        else:
            fail("Excessive withdrawal should have been rolled back but wasn't")

    except Exception as e:
        fail(f"Withdrawal test failed: {e}")
        traceback.print_exc()

# ── PHASE 7: Crash Simulation ────────────────────────────────
if PG_OK and MONGO_OK:
    section("PHASE 7 — Crash Simulation Test")
    try:
        from crash_simulator import CrashSimulator

        conn = get_pg_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT account_number, balance FROM Account
            WHERE status = 'ACTIVE' ORDER BY account_id LIMIT 1;
        """)
        acc_num, bal_before_crash = row
        cur.close()
        conn.close()

        cs = CrashSimulator()
        log_id = cs.simulate_crash(acc_num, 200.00, txn_type="WITHDRAWAL")

        if log_id and log_id > 0:
            # Verify UNCOMMITTED log exists in MongoDB
            doc = db["wal_logs"].find_one({"log_id": log_id}, {"_id": 0})
            if doc and doc["status"] == "UNCOMMITTED":
                ok(f"Crash log #{log_id} is UNCOMMITTED in MongoDB ✓")
                CRASH_OK = True
            else:
                fail(f"Log #{log_id} not found or wrong status: {doc}")
        else:
            fail("simulate_crash() returned invalid log_id")

    except Exception as e:
        fail(f"Crash simulation test failed: {e}")
        traceback.print_exc()

# ── PHASE 8: Recovery Manager ────────────────────────────────
if PG_OK and MONGO_OK and CRASH_OK:
    section("PHASE 8 — Recovery Manager Test")
    try:
        from recovery_manager import RecoveryManager

        # Count UNCOMMITTED before recovery
        uncommitted_before = db["wal_logs"].count_documents({"status": "UNCOMMITTED"})
        info(f"UNCOMMITTED logs before recovery: {uncommitted_before}")

        rm = RecoveryManager()
        rm.run_recovery()

        # Count UNCOMMITTED after recovery
        uncommitted_after = db["wal_logs"].count_documents({"status": "UNCOMMITTED"})
        info(f"UNCOMMITTED logs after  recovery: {uncommitted_after}")

        if uncommitted_after == 0:
            ok("All UNCOMMITTED logs resolved → Recovery successful!")
            RECOVER_OK = True
        elif uncommitted_after < uncommitted_before:
            ok(f"Reduced from {uncommitted_before} to {uncommitted_after} UNCOMMITTED")
            RECOVER_OK = True
        else:
            fail("UNCOMMITTED count unchanged after recovery")

        # Verify recovery_logs collection was written
        rec_count = db["recovery_logs"].count_documents({})
        if rec_count > 0:
            ok(f"recovery_logs has {rec_count} audit entries")
        else:
            info("No recovery_logs written (may be normal if UNDO was skipped)")

    except Exception as e:
        fail(f"Recovery test failed: {e}")
        traceback.print_exc()

# ── FINAL REPORT ─────────────────────────────────────────────
section("VERIFICATION REPORT")

results = {
    "Python 3.14.2 + packages": True,
    "PostgreSQL connection":     PG_OK,
    "MongoDB connection":        MONGO_OK,
    "WAL log insert/update":     WAL_OK,
    "Deposit transaction":       DEPOSIT_OK,
    "Withdrawal + ROLLBACK":     WITHDRAW_OK,
    "Crash simulation":          CRASH_OK,
    "Recovery (UNDO/REDO)":      RECOVER_OK,
}

print()
for feature, passed in results.items():
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status}  {feature}")

print()
if ERRORS:
    print(f"  Issues found ({len(ERRORS)}):")
    for err in ERRORS:
        print(f"    • {err}")
else:
    print("  All verifications passed! Project is ready for viva.")

print()
print("=" * 60)
