# ============================================================
# FILE: recovery_manager.py
# PURPOSE: Implements simplified ARIES-inspired crash recovery.
#
# ADBMS CONCEPT — Recovery after Crash:
#   After a crash, the database may be inconsistent.
#   The Recovery Manager reads MongoDB WAL logs and fixes
#   PostgreSQL by applying UNDO and REDO operations.
#
# THREE RECOVERY PHASES (simplified ARIES):
#
#   Phase 1 — ANALYSIS:
#     Scan all MongoDB wal_logs.
#     Separate them into:
#       UNCOMMITTED → will be UNDONE  (crash victims)
#       COMMITTED   → will be REDONE  (if PG state is wrong)
#
#   Phase 2 — UNDO:
#     For each UNCOMMITTED log (newest first):
#       Restore old_balance in PostgreSQL (from the WAL log)
#       Update WAL log status → ROLLED_BACK
#       Write a recovery_log entry (audit trail)
#
#   Phase 3 — REDO:
#     For each COMMITTED log:
#       Read current PostgreSQL balance
#       If it does NOT match new_balance → re-apply new_balance
#       Write a recovery_log entry (audit trail)
#
# WHY THIS IS SAFE:
#   UNDO: Restoring old_balance twice gives the same result
#   REDO: Applying new_balance twice gives the same result
#   → Recovery is idempotent (safe to run multiple times)
#
# COMPARISON WITH FULL ARIES:
#   Full ARIES          | Our Simplified Version
#   ─────────────────────────────────────────────────────
#   LSN ordering        | timestamp + log_id ordering
#   Dirty Page Table    | not needed (simple balance model)
#   Transaction Table   | MongoDB status field
#   CLR records         | recovery_logs collection
#   3-phase recovery    | same 3-phase approach
# ============================================================

from db_config    import get_pg_connection
from mongo_logger import MongoLogger


class RecoveryManager:
    """
    Scans MongoDB WAL logs and repairs PostgreSQL after a crash.
    All three phases run inside run_recovery().
    """

    def __init__(self):
        self.logger = MongoLogger()

    # ─────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────────────────
    def run_recovery(self):
        """
        Runs all three recovery phases in order.
        Call this after any crash simulation.
        Safe to run multiple times (idempotent).
        """
        print(f"\n{'#'*52}")
        print(f"  RECOVERY MANAGER — Starting Recovery")
        print(f"{'#'*52}")

        # Phase 1: Analysis
        uncommitted, committed = self._phase_analysis()

        # Phase 2: Undo
        undo_count = self._phase_undo(uncommitted)

        # Phase 3: Redo
        redo_count = self._phase_redo(committed)

        # Summary
        print(f"\n{'#'*52}")
        print(f"  RECOVERY COMPLETE")
        print(f"  UNDO applied : {undo_count}")
        print(f"  REDO applied : {redo_count}")
        print(f"  PostgreSQL is now in a consistent state.")
        print(f"{'#'*52}\n")

    # ─────────────────────────────────────────────────────────
    # PHASE 1: ANALYSIS
    # Read all WAL logs from MongoDB and classify them.
    # ─────────────────────────────────────────────────────────
    def _phase_analysis(self) -> tuple:
        print(f"\n  ── Phase 1: ANALYSIS ──")
        print(f"  Scanning MongoDB WAL logs...")

        uncommitted = self.logger.get_uncommitted()
        committed   = self.logger.get_committed()

        print(f"  Found {len(uncommitted)} UNCOMMITTED log(s) → need UNDO")
        print(f"  Found {len(committed)}   COMMITTED   log(s) → check REDO")

        # Show UNCOMMITTED details
        if uncommitted:
            print(f"\n  Crash victims (will be UNDONE):")
            for log in uncommitted:
                print(f"    log_id={log['log_id']}  "
                      f"account_id={log['account_id']}  "
                      f"type={log['txn_type']}  "
                      f"old={log['old_balance']:.2f}  "
                      f"new={log['new_balance']:.2f}")

        if not uncommitted and not committed:
            print(f"  ✓ Nothing to recover. Database is consistent.")

        return uncommitted, committed

    # ─────────────────────────────────────────────────────────
    # PHASE 2: UNDO
    # Restore old_balance in PostgreSQL for every UNCOMMITTED log.
    #
    # Key idea: old_balance was captured in the WAL log BEFORE
    # the crash. We use it to reverse the incomplete change.
    # ─────────────────────────────────────────────────────────
    def _phase_undo(self, uncommitted_logs: list) -> int:
        if not uncommitted_logs:
            print(f"\n  ── Phase 2: UNDO — Nothing to undo. Skipping.")
            return 0

        print(f"\n  ── Phase 2: UNDO ──")
        print(f"  Restoring {len(uncommitted_logs)} account(s) "
              f"to pre-crash state...")

        conn       = get_pg_connection()
        cur        = conn.cursor()
        undo_count = 0

        try:
            for log in uncommitted_logs:
                acc_id      = log["account_id"]
                old_balance = log["old_balance"]
                log_id      = log["log_id"]

                # Read current PG balance
                cur.execute(
                    "SELECT balance FROM Account WHERE account_id = %s",
                    (acc_id,)
                )
                row = cur.fetchone()
                if not row:
                    print(f"  [WARN] account_id={acc_id} not found. Skipping.")
                    continue

                pg_balance = float(row[0])
                print(f"\n  UNDO log_id={log_id}  account_id={acc_id}")
                print(f"    PG balance now : {pg_balance:.2f}")
                print(f"    Restoring to   : {old_balance:.2f}  ← from WAL log")

                # Idempotency: if already restored, skip
                if abs(pg_balance - old_balance) < 0.001:
                    print(f"    Already at old_balance. UNDO already done. Skipping.")
                    self.logger.mark_rolled_back(
                        log_id, reason="Already at old_balance"
                    )
                    continue

                # Apply UNDO: restore old_balance
                cur.execute(
                    "UPDATE Account SET balance = %s WHERE account_id = %s",
                    (old_balance, acc_id)
                )
                # Mark any PENDING transaction record as ROLLED_BACK
                cur.execute(
                    """UPDATE Transaction_Record
                       SET transaction_status = 'ROLLED_BACK'
                       WHERE account_id = %s
                         AND transaction_status = 'PENDING'""",
                    (acc_id,)
                )
                conn.commit()
                print(f"    [PG]  Restored: {pg_balance:.2f} → {old_balance:.2f}")

                # Update WAL log → ROLLED_BACK
                self.logger.mark_rolled_back(
                    log_id, reason="UNDO by RecoveryManager"
                )

                # Write recovery_log (audit trail)
                self.logger.write_recovery_log(
                    action     = "UNDO",
                    account_id = acc_id,
                    before_bal = pg_balance,
                    after_bal  = old_balance,
                    reason     = "CRASH_DETECTED",
                )

                undo_count += 1
                print(f"    ✓ UNDO complete.")

        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] UNDO phase failed: {e}")

        finally:
            cur.close()
            conn.close()

        print(f"\n  Phase 2 done — {undo_count} UNDO(s) applied.")
        return undo_count

    # ─────────────────────────────────────────────────────────
    # PHASE 3: REDO
    # Re-apply new_balance for COMMITTED logs if PostgreSQL
    # does not already reflect the committed change.
    #
    # Key idea: If a transaction was committed (MongoDB says so)
    # but PostgreSQL lost the change (e.g., buffer not flushed),
    # we re-apply new_balance from the WAL log.
    # ─────────────────────────────────────────────────────────
    def _phase_redo(self, committed_logs: list) -> int:
        if not committed_logs:
            print(f"\n  ── Phase 3: REDO — No committed logs. Skipping.")
            return 0

        print(f"\n  ── Phase 3: REDO ──")
        print(f"  Checking {len(committed_logs)} committed log(s)...")

        conn       = get_pg_connection()
        cur        = conn.cursor()
        redo_count = 0

        try:
            for log in committed_logs:
                acc_id      = log["account_id"]
                new_balance = log["new_balance"]
                log_id      = log["log_id"]

                cur.execute(
                    "SELECT balance FROM Account WHERE account_id = %s",
                    (acc_id,)
                )
                row = cur.fetchone()
                if not row:
                    continue

                pg_balance = float(row[0])

                # If PG already matches new_balance → no REDO needed
                if abs(pg_balance - new_balance) < 0.001:
                    continue

                # PG does NOT match → committed change was lost → REDO
                print(f"\n  REDO log_id={log_id}  account_id={acc_id}")
                print(f"    PG balance now : {pg_balance:.2f}")
                print(f"    Re-applying    : {new_balance:.2f}  ← from WAL log")

                cur.execute(
                    "UPDATE Account SET balance = %s WHERE account_id = %s",
                    (new_balance, acc_id)
                )
                conn.commit()
                print(f"    [PG]  Re-applied: {pg_balance:.2f} → {new_balance:.2f}")

                # Write recovery_log
                self.logger.write_recovery_log(
                    action     = "REDO",
                    account_id = acc_id,
                    before_bal = pg_balance,
                    after_bal  = new_balance,
                    reason     = "COMMIT_LOSS",
                )

                redo_count += 1
                print(f"    ✓ REDO complete.")

        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] REDO phase failed: {e}")

        finally:
            cur.close()
            conn.close()

        if redo_count == 0:
            print(f"  ✓ All committed transactions consistent. No REDO needed.")
        else:
            print(f"\n  Phase 3 done — {redo_count} REDO(s) applied.")

        return redo_count

    # ── Utility: show PostgreSQL balances ────────────────────
    def show_balances(self, accounts: list = None):
        """Prints current balances from PostgreSQL."""
        conn = get_pg_connection()
        cur  = conn.cursor()
        try:
            if accounts:
                ph = ",".join(["%s"] * len(accounts))
                cur.execute(
                    f"""SELECT a.account_number, a.balance,
                               c.first_name || ' ' || c.last_name
                        FROM Account a
                        JOIN Customer c ON a.customer_id = c.customer_id
                        WHERE a.account_number IN ({ph})
                        ORDER BY a.account_number""",
                    accounts
                )
            else:
                cur.execute(
                    """SELECT a.account_number, a.balance,
                              c.first_name || ' ' || c.last_name
                       FROM Account a
                       JOIN Customer c ON a.customer_id = c.customer_id
                       ORDER BY a.account_number"""
                )
            rows = cur.fetchall()
            print(f"\n  {'Account':<14} {'Balance':>10}   Customer")
            print(f"  {'─'*14} {'─'*10}   {'─'*20}")
            for num, bal, cust in rows:
                print(f"  {num:<14} {bal:>10.2f}   {cust}")
        finally:
            cur.close()
            conn.close()
