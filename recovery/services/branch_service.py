import psycopg2
from db_config import get_pg_connection

class BranchService:
    @staticmethod
    def get_all_branches(include_inactive=False):
        conn = get_pg_connection()
        cur = conn.cursor()
        if include_inactive:
            cur.execute("SELECT branch_id, branch_name, branch_city, branch_address, contact_number, status FROM Branch ORDER BY branch_id")
        else:
            cur.execute("SELECT branch_id, branch_name, branch_city, branch_address, contact_number, status FROM Branch WHERE status = 'ACTIVE' ORDER BY branch_id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def get_branch_statistics():
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT b.branch_name, b.branch_city,
                   (SELECT COUNT(*) FROM Employee e WHERE e.branch_id = b.branch_id AND e.status = 'ACTIVE') as emp_count,
                   (SELECT COUNT(*) FROM Account a WHERE a.branch_id = b.branch_id AND a.status = 'ACTIVE') as acc_count
            FROM Branch b
            WHERE b.status = 'ACTIVE'
            ORDER BY b.branch_name
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def add_branch(branch_name, branch_city, branch_address, contact_number):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Branch (branch_name, branch_city, branch_address, contact_number) VALUES (%s, %s, %s, %s)",
                (branch_name, branch_city, branch_address, contact_number)
            )
            conn.commit()
            return True, "Branch added successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def update_branch(branch_id, branch_name, branch_city, branch_address, contact_number):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Branch SET branch_name=%s, branch_city=%s, branch_address=%s, contact_number=%s WHERE branch_id=%s",
                (branch_name, branch_city, branch_address, contact_number, branch_id)
            )
            conn.commit()
            return True, "Branch updated successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def soft_delete_branch(branch_id):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE Branch SET status='INACTIVE' WHERE branch_id=%s", (branch_id,))
            conn.commit()
            return True, "Branch marked as INACTIVE."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()
