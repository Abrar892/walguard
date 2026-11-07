import psycopg2
from db_config import get_pg_connection

class LoanService:
    @staticmethod
    def get_all_loans(include_closed=False):
        conn = get_pg_connection()
        cur = conn.cursor()
        query = """
            SELECT l.loan_id, c.first_name || ' ' || c.last_name as customer_name, 
                   a.account_number, l.loan_type, l.loan_amount, l.interest_rate, 
                   l.start_date, l.end_date, l.loan_status 
            FROM Loan l
            JOIN Customer c ON l.customer_id = c.customer_id
            JOIN Account a ON l.account_id = a.account_id
        """
        if not include_closed:
            query += " WHERE l.loan_status != 'CLOSED'"
        query += " ORDER BY l.loan_id"
        
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def add_loan(customer_id, account_id, loan_type, loan_amount, interest_rate, start_date):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Loan (customer_id, account_id, loan_type, loan_amount, interest_rate, start_date, loan_status) VALUES (%s, %s, %s, %s, %s, %s, 'PENDING_APPROVAL')",
                (customer_id, account_id, loan_type, loan_amount, interest_rate, start_date)
            )
            conn.commit()
            return True, "Loan created successfully (Pending Approval)."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def approve_loan(loan_id):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE Loan SET loan_status='ACTIVE' WHERE loan_id=%s AND loan_status='PENDING_APPROVAL'", (loan_id,))
            if cur.rowcount == 0:
                conn.rollback()
                return False, "Loan not found or already processed."
            conn.commit()
            return True, "Loan approved."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def close_loan(loan_id):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE Loan SET loan_status='CLOSED' WHERE loan_id=%s", (loan_id,))
            conn.commit()
            return True, "Loan closed."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()
