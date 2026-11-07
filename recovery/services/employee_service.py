import psycopg2
from db_config import get_pg_connection

class EmployeeService:
    @staticmethod
    def get_all_employees(include_inactive=False):
        conn = get_pg_connection()
        cur = conn.cursor()
        query = """
            SELECT e.employee_id, e.first_name, e.last_name, e.role, e.email, b.branch_name, e.hire_date, e.status, e.branch_id
            FROM Employee e
            LEFT JOIN Branch b ON e.branch_id = b.branch_id
        """
        if not include_inactive:
            query += " WHERE e.status = 'ACTIVE'"
        query += " ORDER BY e.employee_id"
        
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def search_employees(query_str):
        conn = get_pg_connection()
        cur = conn.cursor()
        search_pattern = f"%{query_str}%"
        cur.execute("""
            SELECT e.employee_id, e.first_name, e.last_name, e.role, e.email, b.branch_name, e.hire_date, e.status, e.branch_id
            FROM Employee e
            LEFT JOIN Branch b ON e.branch_id = b.branch_id
            WHERE (e.first_name ILIKE %s OR e.last_name ILIKE %s OR e.email ILIKE %s OR e.role ILIKE %s)
            AND e.status = 'ACTIVE'
            ORDER BY e.employee_id
        """, (search_pattern, search_pattern, search_pattern, search_pattern))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def add_employee(branch_id, first_name, last_name, role, email, contact_number, hire_date):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Employee (branch_id, first_name, last_name, role, email, contact_number, hire_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (branch_id, first_name, last_name, role, email, contact_number, hire_date)
            )
            conn.commit()
            return True, "Employee added successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def update_employee(employee_id, branch_id, first_name, last_name, role, email, contact_number, hire_date):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Employee SET branch_id=%s, first_name=%s, last_name=%s, role=%s, email=%s, contact_number=%s, hire_date=%s WHERE employee_id=%s",
                (branch_id, first_name, last_name, role, email, contact_number, hire_date, employee_id)
            )
            conn.commit()
            return True, "Employee updated successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def soft_delete_employee(employee_id):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE Employee SET status='INACTIVE' WHERE employee_id=%s", (employee_id,))
            conn.commit()
            return True, "Employee marked as INACTIVE."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()
