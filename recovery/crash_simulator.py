# ============================================================
# FILE: crash_simulator.py
# PURPOSE: Simulates a system crash mid-transaction to create
#          a realistic inconsistent database state for testing.
#
# ADBMS CONCEPT — Crash Recovery:
#   After a real crash, the system is left with:
#     • WAL log in MongoDB     → still UNCOMMITTED  (never updated)
#     • PostgreSQL balance     → may be changed     (never rolled back)
#     • No COMMIT or ROLLBACK  → transaction never finished
#
#   The Recovery Manager reads the UNCOMMITTED logs and fixes
#   PostgreSQL by restoring the old_balance (UNDO operation).
#
# HOW WE SIMULATE A CRASH:
#   1. Write WAL log to MongoDB (UNCOMMITTED)
#   2. Apply the balance change to PostgreSQL
#   3. Raise an Exception BEFORE conn.commit()
#   4. conn.rollback() auto-reverses the PG change
#      BUT the MongoDB log stays UNCOMMITTED
#   → This leaves MongoDB and PostgreSQL out of sync,
#     which is exactly what a real crash looks like.
#
# NOTE: In a real crash the PG change may or may not persist
#       depending on whether it was flushed to disk.
#       For our simplified demo, we manually apply the PG
#       change OUTSIDE the transaction to simulate persistence.
# ============================================================

import uuid
from db_config    import get_pg_connection
from mongo_logger import MongoLogger


class CrashSimulator:
    """
    Simulates system crashes mid-transaction.
    Creates UNCOMMITTED WAL log entries that the
    RecoveryManager will later detect and UNDO.
    """

    def __init__(self):
        self.logger     = MongoLogger()
        self.session_id = f"crash_{uuid.uuid4().hex[:6]}"

    # ─────────────────────────────────────────────────────────
    # CRASH: Single account (withdrawal or deposit)
    #
    # What happens:
    #   WAL log written (UNCOMMITTED) → PG balance changed
    #   → Exception raised → crash → no COMMIT
    #   → MongoDB stays UNCOMMITTED = recovery target
    # ─────────────────────────────────────────────────────────
    def simulate_crash(
        self,
        account_number: str,
        amount:         float,
        txn_type:       str = "WITHDRAWAL"   # or "DEPOSIT"
    ) -> int:
        """
        Simulates crash on one account. Returns WAL log_id.
        The returned log_id will appear as UNCOMMITTED in MongoDB.
        Run RecoveryManager.run_recovery() after this to fix the DB.
        """
        print(f"\n{'='*52}")
        print(f"  ⚡ CRASH SIMULATION — {txn_type}")
        print(f"  Account : {account_number}  |  Amount: {amount:.2f}")
        print(f"{'='*52}")

        conn   = get_pg_connection()
        cur    = conn.cursor()
        log_id = None

        try:
            # Read current balance
            cur.execute(
                "SELECT account_id, balance FROM Account "
                "WHERE account_number = %s",
                (account_number,)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Account '{account_number}' not found.")

            acc_id, old_bal = row[0], float(row[1])
            print(f"  Current balance: {old_bal:.2f}")

            new_bal = (old_bal - amount) if txn_type == "WITHDRAWAL" \
                      else (old_bal + amount)

            # Step 1: Write WAL log — UNCOMMITTED (WAL written first)
            log_id = self.logger.write_log(
                session_id  = self.session_id,
                account_id  = acc_id,
                txn_type    = txn_type,
                old_balance = old_bal,
                new_balance = new_bal,
                amount      = amount,
                notes       = f"CRASH_DEMO: will not commit",
            )
            print(f"\n  [WAL] Log #{log_id} written → UNCOMMITTED")

            # Step 2: Apply PG change (simulating in-progress transaction)
            cur.execute(
                "UPDATE Account SET balance = %s WHERE account_id = %s",
                (new_bal, acc_id)
            )
            print(f"  [PG]  Balance changed: {old_bal:.2f} → {new_bal:.2f}")
            print(f"  [PG]  (Change applied but NOT yet committed)")

            # Step 3: *** CRASH — Exception raised before COMMIT ***
            print(f"\n  *** SYSTEM CRASH — Exception raised! ***")
            print(f"  *** COMMIT was never executed.        ***")
            raise RuntimeError("SIMULATED CRASH")

        except RuntimeError:
            # Simulate crash: rollback the PG connection
            # In a real crash the OS closes the connection → auto rollback
            conn.rollback()
            print(f"\n  [PG]  Connection closed → PG auto-rollback")
            print(f"        (PG balance restored to {old_bal:.2f})")
            print(f"  [WAL] Log #{log_id} still UNCOMMITTED in MongoDB")
            print(f"\n  Crash simulation complete.")
            print(f"  → Run Recovery Manager (option 5) to fix the database.")
            return log_id

        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] {e}")
            if log_id:
                self.logger.mark_rolled_back(log_id, reason=str(e))
            return -1

        finally:
            cur.close()
            conn.close()
