# ============================================================
# FILE: main.py
# PURPOSE: Simple menu-driven console interface for the demo.
#
# HOW TO RUN:
#   cd recovery
#   python main.py
#
# MENU OPTIONS:
#   1. Deposit          → WAL + COMMIT (normal flow)
#   2. Withdraw         → WAL + COMMIT or ROLLBACK
#   3. Transfer         → Atomic two-leg transaction
#   4. Simulate Crash   → WAL written, crash before COMMIT
#   5. Run Recovery     → UNDO + REDO after crash
#   6. Show WAL Logs    → All MongoDB log entries
#   7. Show Balances    → Current PostgreSQL balances
#   0. Exit
#
# RECOMMENDED DEMO SEQUENCE FOR VIVA:
#   Option 7 → see starting balances
#   Option 1 → normal deposit, see WAL log created
#   Option 6 → see COMMITTED log in MongoDB
#   Option 4 → crash simulation, see UNCOMMITTED log
#   Option 7 → balance unchanged (PG rolled back)
#   Option 5 → run recovery, see UNDO applied
#   Option 6 → see log changed to ROLLED_BACK
# ============================================================

import sys
from db_config           import test_connections
from transaction_manager import TransactionManager
from crash_simulator     import CrashSimulator
from recovery_manager    import RecoveryManager
from db_config import get_pg_connection


# ── Account numbers used in the demo ────────────────────────
# These match the sample data inserted by 03_sample_data.sql
ACC1 = "ACC-00001"   # Ali Raza   — Savings
ACC2 = "ACC-00003"   # Sara Khan  — Savings
ACC3 = "ACC-00007"   # Ayesha Nawaz — Savings


def print_menu():
    print("\n" + "=" * 46)
    print("  LOG-BASED RECOVERY SYSTEM — ADBMS Project")
    print("=" * 46)
    print("  1. Deposit")
    print("  2. Withdraw")
    print("  3. Transfer")
    print("  4. Simulate Crash   (before COMMIT)")
    print("  5. Run Recovery     (UNDO + REDO)")
    print("  6. Show WAL Logs    (MongoDB)")
    print("  7. Show Balances    (PostgreSQL)")
    print("  0. Exit")
    print("=" * 46)

def get_all_accounts():
    conn = get_pg_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        a.account_number,
        c.first_name || ' ' || c.last_name AS customer_name,
        a.balance
    FROM Account a
    JOIN Customer c
        ON a.customer_id = c.customer_id
    WHERE a.status = 'ACTIVE'
    ORDER BY a.account_number
""")

    accounts = cur.fetchall()

    cur.close()
    conn.close()

    return accounts


def choose_account():
    accounts = get_all_accounts()

    print("\nAvailable Accounts")
    print("-" * 40)

    for i, acc in enumerate(accounts, start=1):
        print(f"{i}. {acc[0]:<10} | "
              f"{acc[1]:<20} | "
              f"Rs. {float(acc[2]):,.2f}")

    while True:
        try:
            choice = int(input("\nSelect account: "))
            if 1 <= choice <= len(accounts):
                return accounts[choice - 1][0]
            print("Invalid selection. Choose a number from the list.")

        except ValueError:
            print("Please enter a valid number.")
# ─────────────────────────────────────────────────────────────
# OPTION 1 — DEPOSIT
#
# Demo shows:
#   WAL log written (UNCOMMITTED) → PG updated → COMMITTED
#
# Sample output:
#   [WAL] Log #1 → UNCOMMITTED  (DEPOSIT, account=1, 10000.00 → 11500.00)
#   [PG]  COMMIT — Transaction_Record id=13
#   [WAL] Log #1 → COMMITTED
#   New balance: 11500.00
#   ✓ Deposit successful.
# ─────────────────────────────────────────────────────────────




def menu_deposit():

    print("\n-- DEPOSIT DEMO --")

    account = choose_account()

    if not account:
        return

    try:
        amount = float(input("Enter amount to deposit: "))
    except ValueError:
        print("  Invalid amount.")
        return

    tm = TransactionManager()
    tm.deposit(account, amount,notes="Demo deposit")

# ─────────────────────────────────────────────────────────────
# OPTION 2 — WITHDRAWAL
#
# Demo shows:
#   Normal: WAL → PG → COMMIT → COMMITTED
#   Fail:   WAL → insufficient funds → ROLLBACK → ROLLED_BACK
#
# Sample output (rollback case):
#   [WAL] Log #2 → UNCOMMITTED  (WITHDRAWAL, account=5, ...)
#   [ERROR] Insufficient funds. Balance: 8000.00, Requested: 50000.00
#   [PG] ROLLBACK — balance unchanged.
#   [WAL] Log #2 → ROLLED_BACK
# ─────────────────────────────────────────────────────────────
def menu_withdraw():
    print("\n  -- WITHDRAWAL DEMO --")
    account = choose_account()

    if not account:
        return
    try:
        amount = float(input("  Enter amount to withdraw: "))
    except ValueError:
        print("  Invalid amount.")
        return
    tm = TransactionManager()
    tm.withdraw(account, amount, notes="Demo withdrawal")


# ─────────────────────────────────────────────────────────────
# OPTION 3 — TRANSFER
#
# Demo shows:
#   Two WAL logs written BEFORE any PG update.
#   Both accounts updated in ONE atomic PG transaction.
#   Both WAL logs → COMMITTED together.
#
# Sample output:
#   [WAL] Log #3 → UNCOMMITTED  (TRANSFER_OUT, account=1, ...)
#   [WAL] Log #4 → UNCOMMITTED  (TRANSFER_IN,  account=7, ...)
#   [PG]  COMMIT — both legs committed atomically
#   [WAL] Log #3 → COMMITTED
#   [WAL] Log #4 → COMMITTED
# ─────────────────────────────────────────────────────────────
def menu_transfer():

    print("\n  -- TRANSFER DEMO --")

    print("\n  Source Account")
    source = choose_account()

    if not source:
        return

    print("\n  Destination Account")
    destination = choose_account()

    if not destination:
        return

    if source == destination:
        print("  Cannot transfer to the same account.")
        return

    try:
        amount = float(input("  Enter amount: "))

        if amount <= 0:
            print("  Amount must be positive.")
            return

    except ValueError:
        print("  Invalid amount.")
        return

    tm = TransactionManager()

    tm.transfer(
        source,
        destination,
        amount,
        notes="User transfer"
    )

# ─────────────────────────────────────────────────────────────
# OPTION 4 — SIMULATE CRASH
#
# Demo shows:
#   WAL log written (UNCOMMITTED) → PG balance changes
#   → Exception raised → COMMIT never runs
#   → PG auto-rollback (connection closed) → back to old balance
#   → MongoDB log STAYS UNCOMMITTED (recovery target!)
#
# Sample output:
#   [WAL] Log #5 → UNCOMMITTED  (WITHDRAWAL, account=1, ...)
#   [PG]  Balance changed: 10000.00 → 7000.00
#   *** SYSTEM CRASH — Exception raised! ***
#   [PG]  Connection closed → PG auto-rollback
#   [WAL] Log #5 still UNCOMMITTED in MongoDB
# ─────────────────────────────────────────────────────────────
def menu_crash():
    print("\n  -- CRASH SIMULATION DEMO --")
    print(f"  Account: {ACC1}")
    print("  A withdrawal will start, WAL log will be written,")
    print("  PG will be updated — then a crash is injected.")
    print("  The WAL log will remain UNCOMMITTED in MongoDB.")
    try:
        amount = float(input("  Enter amount for crash demo: "))
    except ValueError:
        print("  Invalid amount.")
        return
    cs = CrashSimulator()
    cs.simulate_crash(ACC1, amount, txn_type="WITHDRAWAL")
    print(f"\n  → Now run option 5 (Recovery) to undo this transaction.")


# ─────────────────────────────────────────────────────────────
# OPTION 5 — RUN RECOVERY
#
# Demo shows the 3-phase recovery process:
#   Phase 1 — Analysis : Scans MongoDB, finds UNCOMMITTED logs
#   Phase 2 — UNDO     : Restores old_balance in PostgreSQL
#   Phase 3 — REDO     : Re-applies new_balance if needed
#
# Sample output:
#   ── Phase 1: ANALYSIS ──
#   Found 1 UNCOMMITTED log(s) → need UNDO
#   ── Phase 2: UNDO ──
#   UNDO log_id=5  account_id=1
#     PG balance now : 10000.00
#     Restoring to   : 10000.00  ← from WAL log
#     Already at old_balance. UNDO already done. Skipping.
#   ── Phase 3: REDO ──
#   ✓ All committed transactions consistent.
# ─────────────────────────────────────────────────────────────
def menu_recovery():
    print("\n  -- RECOVERY MANAGER DEMO --")
    print("  Scanning MongoDB WAL logs...")
    print("  Will UNDO all UNCOMMITTED transactions.")
    print("  Will REDO COMMITTED transactions if PG state is wrong.")
    rm = RecoveryManager()
    rm.run_recovery()


# ─────────────────────────────────────────────────────────────
# OPTION 6 — SHOW WAL LOGS (MongoDB)
# ─────────────────────────────────────────────────────────────
def menu_show_logs():
    print("\n  -- WAL LOGS (MongoDB: bank_recovery_logs.wal_logs) --")
    logger = RecoveryManager().logger
    logger.display_logs()


# ─────────────────────────────────────────────────────────────
# OPTION 7 — SHOW BALANCES (PostgreSQL)
# ─────────────────────────────────────────────────────────────
def menu_show_balances():
    print("\n  -- ACCOUNT BALANCES (PostgreSQL: bank_recovery_db) --")
    rm = RecoveryManager()
    rm.show_balances([ACC1, ACC2, ACC3])


# ─────────────────────────────────────────────────────────────
# MAIN — Entry point
# ─────────────────────────────────────────────────────────────
def main():
    print("\n  Checking database connections...")
    try:
        test_connections()
    except Exception:
        print("\n  [FATAL] Could not connect to databases.")
        print("  1. Check PG_PASSWORD in db_config.py")
        print("  2. Ensure PostgreSQL is running on port 5432")
        print("  3. Ensure MongoDB is running on port 27017")
        sys.exit(1)

    actions = {
        "1": menu_deposit,
        "2": menu_withdraw,
        "3": menu_transfer,
        "4": menu_crash,
        "5": menu_recovery,
        "6": menu_show_logs,
        "7": menu_show_balances,
    }

    while True:
        print_menu()
        choice = input("  Enter choice: ").strip()

        if choice == "0":
            print("\n  Goodbye!.\n")
            break
        elif choice in actions:
            actions[choice]()
        else:
            print("  Invalid choice. Enter 0–7.")


if __name__ == "__main__":
    main()
