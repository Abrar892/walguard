import os
import sys

# Ensure the root directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_config import test_connections
from gui.app import BankingApp

def main():
    print("==================================================")
    print(" ADBMS Final Project - Banking Management System")
    print("==================================================")

    # 1. Test database connections first
    try:
        test_connections()
    except Exception as e:
        print("\nCRITICAL ERROR: Cannot connect to databases.")
        print("Please check db_config.py and ensure PostgreSQL and MongoDB are running.")
        print("Detailed Error:", str(e))
        sys.exit(1)

    # 2. Launch the Application
    app = BankingApp()
    app.mainloop()

if __name__ == "__main__":
    main()
