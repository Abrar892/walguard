import psycopg2
from db_config import get_pg_connection

class AccountService:
    @staticmethod
    def get_active_account_strings():
        """
        Returns a list of formatted strings for dropdowns:
        ACC-00001 | Ali Raza | SAVINGS | Rs 10000.00
        """
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT a.account_number, c.first_name || ' ' || c.last_name, a.account_type, a.balance 
            FROM Account a 
            JOIN Customer c ON a.customer_id = c.customer_id 
            WHERE a.status = 'ACTIVE' 
            ORDER BY a.account_number
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [f"{r[0]} | {r[1]} | {r[2]} | Rs. {float(r[3]):,.2f}" for r in rows]

    @staticmethod
    def get_all_accounts(include_inactive=False):
        conn = get_pg_connection()
        cur = conn.cursor()
        query = """
            SELECT a.account_id, a.account_number, c.first_name || ' ' || c.last_name as customer_name, 
                   b.branch_name, a.account_type, a.balance, a.status 
            FROM Account a
            JOIN Customer c ON a.customer_id = c.customer_id
            JOIN Branch b ON a.branch_id = b.branch_id
        """
        if not include_inactive:
            query += " WHERE a.status = 'ACTIVE'"
        query += " ORDER BY a.account_number"
        
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def create_account(customer_id, branch_id, account_number, account_type, initial_balance):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Account (customer_id, branch_id, account_number, account_type, balance, status) VALUES (%s, %s, %s, %s, %s, 'ACTIVE')",
                (customer_id, branch_id, account_number, account_type, initial_balance)
            )
            conn.commit()
            return True, "Account created successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def set_account_status(account_id, status):
        # status should be ACTIVE, INACTIVE, CLOSED, or FROZEN
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE Account SET status=%s WHERE account_id=%s", (status, account_id))
            conn.commit()
            return True, f"Account status updated to {status}."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_transaction_history(search_query=None):
        """
        Advanced Transaction Viewer Data (Phase 11)
        """
        conn = get_pg_connection()
        cur = conn.cursor()
        
        base_query = """
            SELECT t.transaction_id, a.account_number, t.transaction_type, t.amount, 
                   t.old_balance, t.new_balance, t.transaction_status, t.transaction_time 
            FROM Transaction_Record t 
            JOIN Account a ON t.account_id = a.account_id 
        """
        params = ()
        
        if search_query:
            base_query += " WHERE a.account_number ILIKE %s OR t.transaction_type ILIKE %s"
            params = (f"%{search_query}%", f"%{search_query}%")
            
        base_query += " ORDER BY t.transaction_time DESC LIMIT 500"
        
        cur.execute(base_query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
