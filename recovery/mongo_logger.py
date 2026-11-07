# ============================================================
# FILE: mongo_logger.py
# PURPOSE: Writes and updates WAL log entries in MongoDB.
#
# ADBMS CONCEPT — Write-Ahead Logging (WAL):
#   The golden rule of WAL:
#     "Write the log FIRST, then update the database."
#
#   Every transaction follows this order:
#     1. write_log()  → Insert into MongoDB (status=UNCOMMITTED)
#     2. PostgreSQL update runs
#     3. mark_committed() OR mark_rolled_back() → update MongoDB
#
#   If a crash happens between steps 1 and 3, the log entry
#   stays UNCOMMITTED — the Recovery Manager uses this to UNDO.
#
# COLLECTION USED: wal_logs (inside bank_recovery_logs database)
# ============================================================

from datetime import datetime, timezone
from db_config import get_mongo_db


class MongoLogger:
    """
    Simple WAL logger. All methods directly access the
    wal_logs collection in MongoDB.
    """

    def __init__(self):
        db          = get_mongo_db()
        self.col    = db["wal_logs"]          # Main WAL log collection
        self.rec    = db["recovery_logs"]     # Written by RecoveryManager
        self.config = db["system_config"]     # Stores log ID counter

    # ── Internal: auto-increment log_id ─────────────────────
    def _next_log_id(self) -> int:
        """
        Generates a sequential log ID by incrementing a counter
        stored in the system_config collection.
        MongoDB does not have auto-increment like PostgreSQL SERIAL,
        so we manage this manually.
        """
        result = self.config.find_one_and_update(
            {"config_key": "log_counter"},
            {"$inc": {"last_log_id": 1}},
            upsert          = True,
            return_document = True
        )
        return result.get("last_log_id", 1)

    # ── STEP 1: Write WAL log BEFORE the PostgreSQL update ──
    def write_log(
        self,
        session_id:  str,
        account_id:  int,
        txn_type:    str,     # DEPOSIT / WITHDRAWAL / TRANSFER_IN / TRANSFER_OUT
        old_balance: float,   # Balance BEFORE change — used for UNDO
        new_balance: float,   # Balance AFTER change  — used for REDO
        amount:      float,
        notes:       str = ""
    ) -> int:
        """
        Inserts one WAL log document with status=UNCOMMITTED.

        This MUST be called before any PostgreSQL update.
        The old_balance and new_balance fields are what make
        Undo and Redo possible after a crash.

        Returns the log_id so the caller can update it later.
        """
        log_id = self._next_log_id()

        self.col.insert_one({
            "log_id":      log_id,
            "session_id":  session_id,
            "account_id":  account_id,
            "txn_type":    txn_type,
            "old_balance": float(old_balance),  # Used in UNDO
            "new_balance": float(new_balance),  # Used in REDO
            "amount":      float(amount),
            "status":      "UNCOMMITTED",        # Starting state
            "timestamp":   datetime.now(timezone.utc),
            "notes":       notes,
        })

        print(f"    [WAL] Log #{log_id} -> UNCOMMITTED  "
              f"({txn_type}, account={account_id}, "
              f"{old_balance:.2f} -> {new_balance:.2f})")
        return log_id

    # ── STEP 3a: Mark COMMITTED after successful PG commit ──
    def mark_committed(self, log_id: int):
        """Updates WAL log status to COMMITTED after PG COMMIT succeeds."""
        self.col.update_one(
            {"log_id": log_id},
            {"$set": {"status": "COMMITTED"}}
        )
        print(f"    [WAL] Log #{log_id} -> COMMITTED")

    # ── STEP 3b: Mark ROLLED_BACK after PG rollback ─────────
    def mark_rolled_back(self, log_id: int, reason: str = ""):
        """Updates WAL log status to ROLLED_BACK after PG ROLLBACK."""
        self.col.update_one(
            {"log_id": log_id},
            {"$set": {"status": "ROLLED_BACK", "notes": reason}}
        )
        print(f"    [WAL] Log #{log_id} -> ROLLED_BACK")

    # ── QUERY: Get all UNCOMMITTED logs (for UNDO phase) ────
    def get_uncommitted(self) -> list:
        """
        Returns all logs with status=UNCOMMITTED.
        These are the crash victims — Recovery Manager undoes them.
        Sorted newest-first so UNDO happens in reverse order.
        """
        return list(
            self.col.find({"status": "UNCOMMITTED"}, {"_id": 0})
                    .sort("timestamp", -1)
        )

    # ── QUERY: Get all COMMITTED logs (for REDO phase) ──────
    def get_committed(self) -> list:
        """
        Returns all logs with status=COMMITTED.
        Recovery Manager checks if PostgreSQL matches new_balance.
        If not, it re-applies the change (REDO).
        """
        return list(
            self.col.find({"status": "COMMITTED"}, {"_id": 0})
                    .sort("timestamp", 1)
        )

    # ── Write a recovery log entry (audit trail) ─────────────
    def write_recovery_log(
        self,
        action:      str,    # "UNDO" or "REDO"
        account_id:  int,
        before_bal:  float,
        after_bal:   float,
        reason:      str
    ):
        """
        Records what the Recovery Manager did.
        This is the equivalent of a Compensation Log Record (CLR) in ARIES.
        """
        self.rec.insert_one({
            "action":      action,
            "account_id":  account_id,
            "before_bal":  before_bal,
            "after_bal":   after_bal,
            "reason":      reason,
            "timestamp":   datetime.now(timezone.utc),
        })

    # ── DISPLAY: Print WAL log table to console ──────────────
    def display_logs(self):
        """Prints all WAL log entries in a formatted table."""
        logs = list(self.col.find({}, {"_id": 0}).sort("log_id", 1))
        if not logs:
            print("  No WAL log entries found.")
            return

        print(f"\n  {'ID':<4} {'Acct':>5} {'Type':<14} "
              f"{'Old Bal':>9} {'New Bal':>9} {'Status':<14} Notes")
        print("  " + "─" * 75)
        for log in logs:
            print(f"  {log['log_id']:<4} "
                  f"{log['account_id']:>5} "
                  f"{log.get('txn_type', log.get('transaction_type', 'UNKNOWN')):<14} "
                  f"{log['old_balance']:>9.2f} "
                  f"{log['new_balance']:>9.2f} "
                  f"{log['status']:<14} "
                  f"{str(log.get('notes',''))[:30]}")
