import customtkinter as ctk
from gui.components import BaseFrame, COLORS, FONTS
from db_config import get_mongo_db
from mongo_logger import MongoLogger
from services.analytics_service import AnalyticsService

class DashboardFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Analytics Dashboard")
        
        self.role = None # Set dynamically
        
        # Row 1: Banking Stats
        self.cards_frame1 = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame1.pack(fill="x", padx=20, pady=5)
        self.cards_frame1.grid_columnconfigure((0,1,2,3), weight=1)
        self.lbl_acc = self.create_card(self.cards_frame1, "Total Accounts", "0", 0)
        self.lbl_cust = self.create_card(self.cards_frame1, "Total Customers", "0", 1)
        self.lbl_txn = self.create_card(self.cards_frame1, "Total Transactions", "0", 2)
        self.lbl_bal = self.create_card(self.cards_frame1, "Total Bank Balance", "Rs. 0", 3)
        
        # Row 2: Banking Stats 2
        self.cards_frame_x = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame_x.pack(fill="x", padx=20, pady=5)
        self.cards_frame_x.grid_columnconfigure((0,1,2,3), weight=1)
        self.lbl_active_acc = self.create_card(self.cards_frame_x, "Active Accounts", "0", 0)
        self.lbl_emp = self.create_card(self.cards_frame_x, "Total Employees", "0", 1)
        self.lbl_branches = self.create_card(self.cards_frame_x, "Total Branches", "0", 2)
        self.lbl_loans = self.create_card(self.cards_frame_x, "Total Loans", "0", 3)

        # Row 3: Recovery Stats (Only visible to ADMIN)
        self.cards_frame2 = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame2.grid_columnconfigure((0,1,2,3), weight=1)
        self.lbl_crashes = self.create_card(self.cards_frame2, "Crash Simulations", "0", 0)
        self.lbl_recoveries = self.create_card(self.cards_frame2, "Total Recoveries", "0", 1)
        self.lbl_pending = self.create_card(self.cards_frame2, "Pending UNCOMMITTED", "0", 2)
        self.lbl_last_rec = self.create_card(self.cards_frame2, "Last Recovery Time", "N/A", 3)
        
        # System Status
        self.status_frame = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=10)
        self.status_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(self.status_frame, text="System Status", font=FONTS["section"], text_color=COLORS["text"]).pack(pady=5, padx=20, anchor="w")
        self.pg_status = ctk.CTkLabel(self.status_frame, text="🔴 PostgreSQL Disconnected", font=FONTS["normal"], text_color=COLORS["text"])
        self.pg_status.pack(pady=2, padx=20, anchor="w")
        self.mongo_status = ctk.CTkLabel(self.status_frame, text="🔴 MongoDB Disconnected", font=FONTS["normal"], text_color=COLORS["text"])
        self.mongo_status.pack(pady=(2, 10), padx=20, anchor="w")

        # Educational ADBMS Panel
        self.adbms_panel = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=10)
        ctk.CTkLabel(self.adbms_panel, text="ADBMS Concepts (Polyglot Persistence Showcase)", font=FONTS["section"], text_color=COLORS["text"]).pack(pady=(10, 5), padx=20, anchor="w")
        
        concepts = [
            ("PostgreSQL", "Structured banking data, strict schema, ACID transactions."),
            ("MongoDB", "Flexible WAL logs, fast inserts, stores recovery metadata."),
            ("WAL", "Write-Ahead Logging. Logs written to Mongo before PG updates."),
            ("UNDO", "Restores old values for incomplete transactions (using WAL old_balance)."),
            ("REDO", "Reapplies committed transactions after recovery (using WAL new_balance)."),
            ("Crash Simulation", "Forces failure mid-transaction leaving an UNCOMMITTED WAL.")
        ]
        for title, desc in concepts:
            row = ctk.CTkFrame(self.adbms_panel, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row, text=f"{title}:", font=("Segoe UI", 14, "bold"), text_color=COLORS["accent"], width=160, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=FONTS["normal"], text_color=COLORS["text"], anchor="w").pack(side="left", fill="x", expand=True)

    def create_card(self, parent, title, value, col):
        card = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"], corner_radius=10)
        card.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=FONTS["normal"], text_color=COLORS["text"]).pack(pady=(10,0))
        val_lbl = ctk.CTkLabel(card, text=value, font=FONTS["section"], text_color=COLORS["accent"])
        val_lbl.pack(pady=(5,10))
        return val_lbl
        
    def refresh(self):
        # RBAC Visibility
        if self.app.current_role == "ADMIN":
            self.cards_frame2.pack(fill="x", padx=20, pady=5, before=self.status_frame)
            self.adbms_panel.pack(fill="x", padx=20, pady=10)
        else:
            self.cards_frame2.pack_forget()
            self.adbms_panel.pack_forget()

        stats = AnalyticsService.get_dashboard_stats()
        if stats.get('db_status', False):
            self.lbl_acc.configure(text=str(stats.get('total_accounts', 0)))
            self.lbl_active_acc.configure(text=str(stats.get('active_accounts', 0)))
            self.lbl_cust.configure(text=str(stats.get('active_customers', 0)))
            self.lbl_emp.configure(text=str(stats.get('active_employees', 0)))
            self.lbl_branches.configure(text=str(stats.get('active_branches', 0)))
            self.lbl_loans.configure(text=str(stats.get('active_loans', 0)))
            self.lbl_txn.configure(text=str(stats.get('total_transactions', 0)))
            self.lbl_bal.configure(text=f"Rs. {stats.get('total_balance', 0.0):,.2f}")
            self.pg_status.configure(text="🟢 PostgreSQL Connected")
        else:
            self.pg_status.configure(text="🔴 PostgreSQL Disconnected")
            
        try:
            db = get_mongo_db()
            db.command("ping")
            self.mongo_status.configure(text="🟢 MongoDB Connected")
            
            if self.app.current_role == "ADMIN":
                logger = MongoLogger()
                uncommitted = logger.col.count_documents({"status": "UNCOMMITTED"})
                crashes = logger.col.count_documents({"notes": {"$regex": "CRASH"}})
                recoveries = logger.rec.count_documents({})
                last_rec = logger.rec.find_one(sort=[("timestamp", -1)])
                
                self.lbl_pending.configure(text=str(uncommitted))
                self.lbl_crashes.configure(text=str(crashes))
                self.lbl_recoveries.configure(text=str(recoveries))
                
                if last_rec and "timestamp" in last_rec:
                    self.lbl_last_rec.configure(text=last_rec["timestamp"].strftime('%H:%M:%S'))
                else:
                    self.lbl_last_rec.configure(text="N/A")
                
        except Exception:
            self.mongo_status.configure(text="🔴 MongoDB Disconnected")
