import psycopg2
from db_config import get_pg_connection

def ensure_soft_delete_schema():
    """
    Ensures that Customer, Employee, and Branch tables have a 'status' column 
    to support the Soft Delete policy without breaking the existing schema.
    Account and Loan tables already support status inherently.
    """
    queries = [
        "ALTER TABLE Customer ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE';",
        "ALTER TABLE Employee ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE';",
        "ALTER TABLE Branch ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE';"
    ]
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        for q in queries:
            cur.execute(q)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error ensuring soft-delete schema: {e}")

if __name__ == "__main__":
    ensure_soft_delete_schema()
