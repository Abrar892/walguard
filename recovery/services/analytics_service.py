import psycopg2
from db_config import get_pg_connection

class AnalyticsService:
    @staticmethod
    def get_dashboard_stats():
        """
        Returns a dictionary of counts and sums for the dashboard.
        """
        conn = get_pg_connection()
        cur = conn.cursor()
        
        stats = {}
        try:
            cur.execute("SELECT COUNT(*) FROM Account")
            stats['total_accounts'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Account WHERE status='ACTIVE'")
            stats['active_accounts'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Customer WHERE status='ACTIVE'")
            stats['active_customers'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Employee WHERE status='ACTIVE'")
            stats['active_employees'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Branch WHERE status='ACTIVE'")
            stats['active_branches'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Loan WHERE loan_status='ACTIVE'")
            stats['active_loans'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Transaction_Record")
            stats['total_transactions'] = cur.fetchone()[0]
            
            cur.execute("SELECT SUM(balance) FROM Account WHERE status='ACTIVE'")
            total = cur.fetchone()[0] or 0.0
            stats['total_balance'] = float(total)
            
            stats['db_status'] = True
        except Exception:
            stats['db_status'] = False
        finally:
            cur.close()
            conn.close()
            
        return stats
