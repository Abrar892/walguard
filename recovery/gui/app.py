import customtkinter as ctk
import sys
import datetime
from gui.components import COLORS, ToastNotification
from gui.auth import LoginFrame
from gui.views.dashboard import DashboardFrame
from gui.views.crud_customers import CustomersFrame
from gui.views.crud_accounts import AccountsFrame, DepositFrame, WithdrawFrame, TransferFrame
from gui.views.crud_employees import EmployeesFrame
from gui.views.crud_branches import BranchesFrame
from gui.views.crud_loans import LoansFrame
from gui.views.transaction_history import TransactionHistoryFrame
from gui.views.recovery_center import RecoveryCenterFrame
import db_bootstrap

class StreamRedirector:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        self.listeners = []
        self.history = []

    def write(self, message):
        self.original_stdout.write(message)
        if message.strip():
            ts = datetime.datetime.now().strftime("[%H:%M:%S] ")
            fmt_msg = ts + message
            if not message.endswith('\n'):
                fmt_msg += '\n'
            self.history.append(fmt_msg)
            for listener in self.listeners:
                listener(fmt_msg)

    def flush(self):
        self.original_stdout.flush()

    def add_listener(self, callback):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

class BankingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Setup stdout interception globally
        if not isinstance(sys.stdout, StreamRedirector):
            sys.stdout = StreamRedirector(sys.stdout)
            
        self.title("Banking Management System")
        self.geometry("1400x850")
        self.configure(fg_color=COLORS["background"])
        
        db_bootstrap.ensure_soft_delete_schema()
        
        self.current_role = None
        self.frames = {}
        self.current_frame = None
        
        # Build layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.sidebar = ctk.CTkFrame(self, fg_color=COLORS["secondary"], corner_radius=0, width=250)
        self.main_area = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        
        self.show_login()
        
    def show_toast(self, message, msg_type="success"):
        ToastNotification(self, message, msg_type)
        
    def show_login(self):
        self.sidebar.grid_forget()
        self.main_area.grid_forget()
        
        if "login" not in self.frames:
            self.frames["login"] = LoginFrame(self, self)
            
        self.current_frame = self.frames["login"]
        self.current_frame.pack(fill="both", expand=True)
        self.current_frame.refresh()
        
    def login_success(self, role):
        self.current_role = role
        self.frames["login"].pack_forget()
        
        self.build_sidebar()
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.main_area.grid(row=0, column=1, sticky="nsew")
        
        self.init_views()
        self.navigate("Dashboard")
        
    def init_views(self):
        # Clear old views to force RBAC redraw
        for frame in list(self.frames.values()):
            if frame != self.frames["login"]:
                frame.destroy()
                
        self.frames = {"login": self.frames["login"]}
        self.frames["Dashboard"] = DashboardFrame(self.main_area, self)
        self.frames["Customers"] = CustomersFrame(self.main_area, self)
        self.frames["Accounts"] = AccountsFrame(self.main_area, self)
        self.frames["Deposit"] = DepositFrame(self.main_area, self)
        self.frames["Withdraw"] = WithdrawFrame(self.main_area, self)
        self.frames["Transfer"] = TransferFrame(self.main_area, self)
        self.frames["Transaction History"] = TransactionHistoryFrame(self.main_area, self)
        
        if self.current_role == "ADMIN":
            self.frames["Employees"] = EmployeesFrame(self.main_area, self)
            self.frames["Branches"] = BranchesFrame(self.main_area, self)
            self.frames["Loans"] = LoansFrame(self.main_area, self)
            self.frames["Recovery Center"] = RecoveryCenterFrame(self.main_area, self)
            
    def build_sidebar(self):
        for w in self.sidebar.winfo_children(): w.destroy()
        
        lbl = ctk.CTkLabel(self.sidebar, text=f"BANK {self.current_role}", font=("Segoe UI", 24, "bold"), text_color=COLORS["primary"])
        lbl.pack(pady=(30, 20))
        
        nav_items = ["Dashboard", "Customers", "Accounts", "Deposit", "Withdraw", "Transfer", "Transaction History"]
        
        if self.current_role == "ADMIN":
            nav_items.extend(["Employees", "Branches", "Loans", "Recovery Center"])
            
        for item in nav_items:
            btn = ctk.CTkButton(self.sidebar, text=item, font=("Segoe UI", 16), fg_color="transparent", 
                              text_color=COLORS["text"], hover_color=COLORS["card_bg"], anchor="w",
                              command=lambda name=item: self.navigate(name))
            btn.pack(fill="x", padx=10, pady=5)
            
        logout_btn = ctk.CTkButton(self.sidebar, text="Logout", font=("Segoe UI", 16, "bold"), fg_color=COLORS["danger"], hover_color=COLORS["warning"], command=self.do_logout)
        logout_btn.pack(side="bottom", pady=20, padx=20)
        
    def navigate(self, page_name):
        if self.current_frame and self.current_frame != self.frames["login"]:
            self.current_frame.pack_forget()
            
        self.current_frame = self.frames[page_name]
        self.current_frame.pack(fill="both", expand=True)
        self.current_frame.refresh()
        
    def do_logout(self):
        self.current_role = None
        self.sidebar.grid_forget()
        self.main_area.grid_forget()
        self.show_login()
