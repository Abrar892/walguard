# ============================================================
# FILE: transaction_manager.py
# PURPOSE: Executes banking transactions using WAL protocol.
#
# ADBMS CONCEPTS DEMONSTRATED:
#   • Transactions   — explicit BEGIN / COMMIT / ROLLBACK
#   • WAL            — MongoDB log written BEFORE PostgreSQL update
#   • ACID Atomicity — all steps succeed or all are reversed
#   • Polyglot       — PostgreSQL and MongoDB coordinated together
#
# WAL SEQUENCE (must follow this order every time):
#   1. Read old_balance from PostgreSQL
#   2. Write WAL log to MongoDB  (status = UNCOMMITTED)  ← FIRST
#   3. Update Account balance in PostgreSQL
#   4. Insert Transaction_Record in PostgreSQL
#   5. conn.commit()   → PostgreSQL transaction finalized
#   6. mark_committed() → MongoDB log updated to COMMITTED
#
#   If ANY step between 2 and 6 fails:
#   → conn.rollback()     → PostgreSQL changes reversed
#   → mark_rolled_back()  → MongoDB log updated to ROLLED_BACK
# ============================================================

import uuid
from db_config    import get_pg_connection
from mongo_logger import MongoLogger


class TransactionManager:
    """
    Handles all banking transactions with WAL support.
    Each public method (deposit / withdraw / transfer) follows
    the same 6-step WAL sequence described above.
    """

    def __init__(self):
        self.logger     = MongoLogger()
        self.session_id = f"sess_{uuid.uuid4().hex[:6]}"
        print(f"  [Session] {self.session_id}")

    # ── Helper: read account from PostgreSQL ─────────────────
    def _get_account(self, cur, account_number: str) -> tuple:
        """Returns (account_id, balance) or raises if not found/inactive."""
        cur.execute(
            "SELECT account_id, balance, status "
            "FROM Account WHERE account_number = %s",
            (account_number,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Account '{account_number}' not found.")
        acc_id, balance, status = row
        if status != "ACTIVE":
            raise ValueError(f"Account '{account_number}' is {status}.")
        return acc_id, float(balance)

    # ── Helper: insert a Transaction_Record row ───────────────
    def _record_transaction(self, cur, account_id, txn_type,
                             amount, old_bal, new_bal, notes):
        """Inserts one row into PostgreSQL Transaction_Record table."""
        cur.execute(
            """
            INSERT INTO Transaction_Record
              (account_id, transaction_type, amount,
               old_balance, new_balance, transaction_status, notes)
            VALUES (%s, %s, %s, %s, %s, 'COMMITTED', %s)
            RETURNING transaction_id
            """,
            (account_id, txn_type, amount, old_bal, new_bal, notes)
        )
        return cur.fetchone()[0]

    # ─────────────────────────────────────────────────────────
    # DEPOSIT
    # Adds money to an account.
    # Simplest demo of the WAL sequence.
    # ─────────────────────────────────────────────────────────
    def deposit(self, account_number: str, amount: float,
                notes: str = "") -> bool:
        print(f"\n{'='*52}")
        print(f"  DEPOSIT | {account_number} | +{amount:.2f}")
        print(f"{'='*52}")

        if amount <= 0:
            print("  [ERROR] Amount must be positive.")
            return False

        conn   = get_pg_connection()
        cur    = conn.cursor()
        log_id = None

        try:
            # Step 1: Read old balance
            acc_id, old_bal = self._get_account(cur, account_number)
            new_bal = old_bal + amount
            print(f"  Old balance: {old_bal:.2f}")

            # Step 2: Write WAL log (UNCOMMITTED) — BEFORE PG update
            log_id = self.logger.write_log(
                session_id  = self.session_id,
                account_id  = acc_id,
                txn_type    = "DEPOSIT",
                old_balance = old_bal,
                new_balance = new_bal,
                amount      = amount,
                notes       = notes or f"Deposit to {account_number}",
            )

            # Step 3: Update PostgreSQL balance
            cur.execute(
                "UPDATE Account SET balance = %s WHERE account_id = %s",
                (new_bal, acc_id)
            )

            # Step 4: Insert Transaction_Record
            txn_id = self._record_transaction(
                cur, acc_id, "DEPOSIT", amount, old_bal, new_bal,
                notes or f"Deposit to {account_number}"
            )

            # Step 5: COMMIT PostgreSQL
            conn.commit()
            print(f"  [PG] COMMIT — Transaction_Record id={txn_id}")

            # Step 6: Update WAL log → COMMITTED
            self.logger.mark_committed(log_id)

            print(f"  New balance: {new_bal:.2f}")
            print(f"  ✓ Deposit successful.")
            return True

        except Exception as e:
            # Any error → ROLLBACK and mark log ROLLED_BACK
            conn.rollback()
            print(f"  [ERROR] {e}")
            print(f"  [PG] ROLLBACK — balance unchanged.")
            if log_id:
                self.logger.mark_rolled_back(log_id, reason=str(e))
            return False

        finally:
            cur.close()
            conn.close()

    # ─────────────────────────────────────────────────────────
    # WITHDRAWAL
    # Removes money from an account.
    # Demonstrates constraint-based ROLLBACK when funds are low.
    # ─────────────────────────────────────────────────────────
    def withdraw(self, account_number: str, amount: float,
                 notes: str = "") -> bool:
        print(f"\n{'='*52}")
        print(f"  WITHDRAWAL | {account_number} | -{amount:.2f}")
        print(f"{'='*52}")

        if amount <= 0:
            print("  [ERROR] Amount must be positive.")
            return False

        conn   = get_pg_connection()
        cur    = conn.cursor()
        log_id = None

        try:
            # Step 1: Read old balance
            acc_id, old_bal = self._get_account(cur, account_number)
            print(f"  Old balance: {old_bal:.2f}")

            # Check: sufficient funds?
            if old_bal < amount:
                raise ValueError(
                    f"Insufficient funds. "
                    f"Balance: {old_bal:.2f}, Requested: {amount:.2f}"
                )

            new_bal = old_bal - amount

            # Step 2: Write WAL log (UNCOMMITTED) — BEFORE PG update
            log_id = self.logger.write_log(
                session_id  = self.session_id,
                account_id  = acc_id,
                txn_type    = "WITHDRAWAL",
                old_balance = old_bal,
                new_balance = new_bal,
                amount      = amount,
                notes       = notes or f"Withdrawal from {account_number}",
            )

            # Step 3: Update PostgreSQL balance
            cur.execute(
                "UPDATE Account SET balance = %s WHERE account_id = %s",
                (new_bal, acc_id)
            )

            # Step 4: Insert Transaction_Record
            txn_id = self._record_transaction(
                cur, acc_id, "WITHDRAWAL", amount, old_bal, new_bal,
                notes or f"Withdrawal from {account_number}"
            )

            # Step 5: COMMIT PostgreSQL
            conn.commit()
            print(f"  [PG] COMMIT — Transaction_Record id={txn_id}")

            # Step 6: Update WAL log → COMMITTED
            self.logger.mark_committed(log_id)

            print(f"  New balance: {new_bal:.2f}")
            print(f"  ✓ Withdrawal successful.")
            return True

        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] {e}")
            print(f"  [PG] ROLLBACK — balance unchanged.")
            if log_id:
                self.logger.mark_rolled_back(log_id, reason=str(e))
            return False

        finally:
            cur.close()
            conn.close()

    # ─────────────────────────────────────────────────────────
    # TRANSFER
    # Moves money between two accounts in ONE transaction.
    # Two WAL logs written (one per account) before any PG update.
    # Both legs COMMIT together — demonstrates ACID Atomicity.
    # ─────────────────────────────────────────────────────────
    def transfer(self, from_acc: str, to_acc: str,
                 amount: float, notes: str = "") -> bool:
        print(f"\n{'='*52}")
        print(f"  TRANSFER | {from_acc} → {to_acc} | {amount:.2f}")
        print(f"{'='*52}")

        if amount <= 0:
            print("  [ERROR] Amount must be positive.")
            return False
        if from_acc == to_acc:
            print("  [ERROR] Cannot transfer to the same account.")
            return False

        conn       = get_pg_connection()
        cur        = conn.cursor()
        log_out_id = None
        log_in_id  = None

        try:
            # Step 1: Read both balances
            from_id, from_bal = self._get_account(cur, from_acc)
            to_id,   to_bal   = self._get_account(cur, to_acc)
            print(f"  {from_acc}: {from_bal:.2f}   {to_acc}: {to_bal:.2f}")

            if from_bal < amount:
                raise ValueError(
                    f"Insufficient funds in {from_acc}. "
                    f"Balance: {from_bal:.2f}, Required: {amount:.2f}"
                )

            from_new = from_bal - amount
            to_new   = to_bal   + amount
            label    = notes or f"Transfer {from_acc}→{to_acc}"

            # Step 2: Write BOTH WAL logs BEFORE any PostgreSQL update
            log_out_id = self.logger.write_log(
                session_id  = self.session_id,
                account_id  = from_id,
                txn_type    = "TRANSFER_OUT",
                old_balance = from_bal,
                new_balance = from_new,
                amount      = amount,
                notes       = label + " [OUT]",
            )
            log_in_id = self.logger.write_log(
                session_id  = self.session_id,
                account_id  = to_id,
                txn_type    = "TRANSFER_IN",
                old_balance = to_bal,
                new_balance = to_new,
                amount      = amount,
                notes       = label + " [IN]",
            )

            # Step 3: Apply both PostgreSQL updates
            cur.execute(
                "UPDATE Account SET balance = %s WHERE account_id = %s",
                (from_new, from_id)
            )
            cur.execute(
                "UPDATE Account SET balance = %s WHERE account_id = %s",
                (to_new, to_id)
            )

            # Step 4: Two Transaction_Records
            self._record_transaction(
                cur, from_id, "TRANSFER_OUT", amount,
                from_bal, from_new, label + " [OUT]"
            )
            self._record_transaction(
                cur, to_id, "TRANSFER_IN", amount,
                to_bal, to_new, label + " [IN]"
            )

            # Step 5: COMMIT both legs in one PG transaction
            conn.commit()
            print(f"  [PG] COMMIT — both legs committed atomically")

            # Step 6: Mark both WAL logs COMMITTED
            self.logger.mark_committed(log_out_id)
            self.logger.mark_committed(log_in_id)

            print(f"  {from_acc}: {from_bal:.2f} → {from_new:.2f}")
            print(f"  {to_acc}: {to_bal:.2f} → {to_new:.2f}")
            print(f"  ✓ Transfer successful.")
            return True

        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] {e}")
            print(f"  [PG] ROLLBACK — both accounts unchanged.")
            if log_out_id:
                self.logger.mark_rolled_back(log_out_id, reason=str(e))
            if log_in_id:
                self.logger.mark_rolled_back(log_in_id, reason=str(e))
            return False

        finally:
            cur.close()
            conn.close()

    # ── Utility: show account balance ─────────────────────────
    def show_balance(self, account_number: str):
        """Reads and prints balance from PostgreSQL (read-only)."""
        conn = get_pg_connection()
        cur  = conn.cursor()
        try:
            cur.execute(
                """
                SELECT a.account_number, a.balance,
                       c.first_name || ' ' || c.last_name
                FROM   Account a
                JOIN   Customer c ON a.customer_id = c.customer_id
                WHERE  a.account_number = %s
                """,
                (account_number,)
            )
            row = cur.fetchone()
            if row:
                print(f"  {row[0]}  Balance: {row[1]:.2f}  ({row[2]})")
            else:
                print(f"  Account '{account_number}' not found.")
        finally:
            cur.close()
            conn.close()
