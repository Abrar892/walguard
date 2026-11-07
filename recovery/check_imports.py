import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import traceback

modules_to_check = [
    'db_bootstrap',
    'services.account_service',
    'services.branch_service',
    'services.customer_service',
    'services.employee_service',
    'services.loan_service',
    'gui.app',
    'gui.auth',
    'gui.components',
    'gui.views.crud_accounts',
    'gui.views.crud_branches',
    'gui.views.crud_customers',
    'gui.views.crud_employees',
    'gui.views.crud_loans',
    'gui.views.dashboard',
    'gui.views.recovery_center',
    'gui.views.transaction_history'
]

has_errors = False
for mod in modules_to_check:
    try:
        __import__(mod)
        print(f"[OK] {mod}")
    except Exception as e:
        print(f"[FAIL] {mod}")
        traceback.print_exc()
        has_errors = True

if has_errors:
    sys.exit(1)
print("All imports successful!")
