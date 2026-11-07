import customtkinter as ctk
from gui.components import BaseFrame, COLORS, FONTS
from services.loan_service import LoanService

class LoansFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Loan Management")
        
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=10)
        
        self.btn_add = ctk.CTkButton(toolbar, text="+ Issue Loan", font=FONTS["button"], fg_color=COLORS["success"], hover_color=COLORS["accent"])
        self.btn_add.pack(side="right", padx=(10, 0))
        
        header = ctk.CTkFrame(self, fg_color=COLORS["primary"], height=40, corner_radius=5)
        header.pack(fill="x", padx=20, pady=(10, 0))
        
        cols = [("ID", 0.02), ("Customer", 0.1), ("Account", 0.3), ("Type", 0.45), ("Amount", 0.6), ("Rate", 0.75), ("Status", 0.85)]
        for name, relx in cols:
            ctk.CTkLabel(header, text=name, font=("Segoe UI", 12, "bold"), text_color="#fff").place(relx=relx, rely=0.5, anchor="w")
            
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(5, 20))
        
    def refresh(self):
        for w in self.body.winfo_children(): w.destroy()
        
        rows = LoanService.get_all_loans(include_closed=True)
            
        for i, row in enumerate(rows):
            bg = COLORS["card_bg"] if i % 2 == 0 else "transparent"
            r = ctk.CTkFrame(self.body, fg_color=bg, height=40, corner_radius=5)
            r.pack(fill="x", pady=2)
            
            l_id, cust, acc, l_type, amt, rate, start, end, status = row
            
            ctk.CTkLabel(r, text=str(l_id), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.02, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=cust, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.1, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=acc, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.3, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=l_type, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.45, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=f"Rs. {float(amt):,.2f}", font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.6, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=f"{float(rate):.2f}%", font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.75, rely=0.5, anchor="w")
            
            scolor = COLORS["success"] if status == "ACTIVE" else (COLORS["warning"] if status == "PENDING_APPROVAL" else COLORS["danger"])
            ctk.CTkLabel(r, text=status, font=FONTS["table"], text_color=scolor).place(relx=0.85, rely=0.5, anchor="w")
