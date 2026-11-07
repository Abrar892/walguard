import customtkinter as ctk
import csv
import os
from datetime import datetime
from gui.components import BaseFrame, COLORS, FONTS
from services.account_service import AccountService

class TransactionHistoryFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Advanced Transaction Viewer")
        
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=10)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(toolbar, textvariable=self.search_var, placeholder_text="Search Account or Type...", font=FONTS["normal"], width=300)
        self.search_entry.pack(side="left", padx=(0, 10))
        
        btn_search = ctk.CTkButton(toolbar, text="Search / Filter", font=FONTS["button"], width=120, command=self.refresh)
        btn_search.pack(side="left")
        
        self.btn_export = ctk.CTkButton(toolbar, text="Export CSV", font=FONTS["button"], fg_color=COLORS["primary"], hover_color=COLORS["accent"], command=self.export_csv)
        self.btn_export.pack(side="right", padx=(10, 0))
        
        header = ctk.CTkFrame(self, fg_color=COLORS["primary"], height=40, corner_radius=5)
        header.pack(fill="x", padx=20, pady=(10, 0))
        
        cols = [("Time", 0.02), ("Acc Number", 0.15), ("Type", 0.3), ("Amount", 0.45), ("Old Bal", 0.6), ("New Bal", 0.72), ("Status", 0.88)]
        for name, relx in cols:
            ctk.CTkLabel(header, text=name, font=("Segoe UI", 12, "bold"), text_color="#fff").place(relx=relx, rely=0.5, anchor="w")
            
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(5, 20))
        
        self.current_rows = []
        
    def refresh(self):
        for w in self.body.winfo_children(): w.destroy()
        
        q = self.search_var.get().strip()
        self.current_rows = AccountService.get_transaction_history(q if q else None)
            
        for i, row in enumerate(self.current_rows):
            bg = COLORS["card_bg"] if i % 2 == 0 else "transparent"
            r = ctk.CTkFrame(self.body, fg_color=bg, height=40, corner_radius=5)
            r.pack(fill="x", pady=2)
            
            t_id, a_num, t_type, amt, old_b, new_b, status, t_time = row
            dt_str = t_time.strftime('%Y-%m-%d %H:%M') if hasattr(t_time, 'strftime') else str(t_time)[:16]
            
            ctk.CTkLabel(r, text=dt_str, font=("Segoe UI", 11), text_color=COLORS["text"]).place(relx=0.02, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=a_num, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.15, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=t_type, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.3, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=f"Rs. {float(amt):,.2f}", font=FONTS["table"], text_color=COLORS["accent"]).place(relx=0.45, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=f"{float(old_b):,.2f}", font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.6, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=f"{float(new_b):,.2f}", font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.72, rely=0.5, anchor="w")
            
            status_color = COLORS["success"] if status == "COMMITTED" else (COLORS["danger"] if status == "ROLLED_BACK" else COLORS["warning"])
            ctk.CTkLabel(r, text=status, font=("Segoe UI", 11, "bold"), text_color=status_color).place(relx=0.88, rely=0.5, anchor="w")

    def export_csv(self):
        if not os.path.exists("exports"):
            os.makedirs("exports")
        filename = f"exports/transactions_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.csv"
        try:
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Transaction ID", "Account", "Type", "Amount", "Old Balance", "New Balance", "Status", "Timestamp"])
                for row in self.current_rows:
                    writer.writerow(row)
            self.app.show_toast(f"Exported to {filename}", "success")
        except Exception as e:
            self.app.show_toast(f"Export Failed: {e}", "error")
