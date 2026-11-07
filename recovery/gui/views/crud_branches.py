import customtkinter as ctk
from gui.components import BaseFrame, COLORS, FONTS
from services.branch_service import BranchService

class BranchesFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Branch Management")
        
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=10)
        
        self.btn_add = ctk.CTkButton(toolbar, text="+ Add Branch", font=FONTS["button"], fg_color=COLORS["success"], hover_color=COLORS["accent"])
        self.btn_add.pack(side="right", padx=(10, 0))
        
        header = ctk.CTkFrame(self, fg_color=COLORS["primary"], height=40, corner_radius=5)
        header.pack(fill="x", padx=20, pady=(10, 0))
        
        cols = [("Branch Name", 0.05), ("City", 0.3), ("Employees", 0.5), ("Accounts", 0.7)]
        for name, relx in cols:
            ctk.CTkLabel(header, text=name, font=("Segoe UI", 12, "bold"), text_color="#fff").place(relx=relx, rely=0.5, anchor="w")
            
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(5, 20))
        
    def refresh(self):
        for w in self.body.winfo_children(): w.destroy()
        
        rows = BranchService.get_branch_statistics()
            
        for i, row in enumerate(rows):
            bg = COLORS["card_bg"] if i % 2 == 0 else "transparent"
            r = ctk.CTkFrame(self.body, fg_color=bg, height=40, corner_radius=5)
            r.pack(fill="x", pady=2)
            
            b_name, b_city, emp_c, acc_c = row
            
            ctk.CTkLabel(r, text=b_name, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.05, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=b_city, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.3, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=str(emp_c), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.5, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=str(acc_c), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.7, rely=0.5, anchor="w")
