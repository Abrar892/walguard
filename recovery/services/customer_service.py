import psycopg2
from db_config import get_pg_connection

class CustomerService:
    @staticmethod
    def get_all_customers(include_inactive=False):
        conn = get_pg_connection()
        cur = conn.cursor()
        if include_inactive:
            cur.execute("SELECT customer_id, first_name, last_name, email, contact_number, address, date_of_birth, status FROM Customer ORDER BY customer_id")
        else:
            cur.execute("SELECT customer_id, first_name, last_name, email, contact_number, address, date_of_birth, status FROM Customer WHERE status = 'ACTIVE' ORDER BY customer_id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def search_customers(query):
        conn = get_pg_connection()
        cur = conn.cursor()
        search_pattern = f"%{query}%"
        cur.execute("""
            SELECT customer_id, first_name, last_name, email, contact_number, address, date_of_birth, status 
            FROM Customer 
            WHERE (first_name ILIKE %s OR last_name ILIKE %s OR email ILIKE %s OR contact_number ILIKE %s) 
            AND status = 'ACTIVE'
            ORDER BY customer_id
        """, (search_pattern, search_pattern, search_pattern, search_pattern))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def add_customer(first_name, last_name, email, contact_number, address, dob):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Customer (first_name, last_name, email, contact_number, address, date_of_birth) VALUES (%s, %s, %s, %s, %s, %s)",
                (first_name, last_name, email, contact_number, address, dob)
            )
            conn.commit()
            return True, "Customer added successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def update_customer(customer_id, first_name, last_name, email, contact_number, address, dob):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Customer SET first_name=%s, last_name=%s, email=%s, contact_number=%s, address=%s, date_of_birth=%s WHERE customer_id=%s",
                (first_name, last_name, email, contact_number, address, dob, customer_id)
            )
            conn.commit()
            return True, "Customer updated successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def soft_delete_customer(customer_id):
        conn = get_pg_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE Customer SET status='INACTIVE' WHERE customer_id=%s", (customer_id,))
            conn.commit()
            return True, "Customer marked as INACTIVE."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            cur.close()
            conn.close()
