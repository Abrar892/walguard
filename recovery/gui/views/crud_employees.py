import customtkinter as ctk
from gui.components import BaseFrame, COLORS, FONTS
from services.employee_service import EmployeeService

class EmployeesFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Employee Management")
        
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=10)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(toolbar, textvariable=self.search_var, placeholder_text="Search Name, Role, Email...", font=FONTS["normal"], width=300)
        self.search_entry.pack(side="left", padx=(0, 10))
        
        btn_search = ctk.CTkButton(toolbar, text="Search", font=FONTS["button"], width=100, command=self.refresh)
        btn_search.pack(side="left")
        
        self.btn_add = ctk.CTkButton(toolbar, text="+ Add Employee", font=FONTS["button"], fg_color=COLORS["success"], hover_color=COLORS["accent"])
        self.btn_add.pack(side="right", padx=(10, 0))
        
        header = ctk.CTkFrame(self, fg_color=COLORS["primary"], height=40, corner_radius=5)
        header.pack(fill="x", padx=20, pady=(10, 0))
        
        cols = [("ID", 0.02), ("First Name", 0.1), ("Last Name", 0.25), ("Role", 0.4), ("Branch", 0.55), ("Hire Date", 0.7), ("Actions", 0.85)]
        for name, relx in cols:
            ctk.CTkLabel(header, text=name, font=("Segoe UI", 12, "bold"), text_color="#fff").place(relx=relx, rely=0.5, anchor="w")
            
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(5, 20))
        
    def refresh(self):
        for w in self.body.winfo_children(): w.destroy()
        
        q = self.search_var.get().strip()
        if q:
            rows = EmployeeService.search_employees(q)
        else:
            rows = EmployeeService.get_all_employees()
            
        for i, row in enumerate(rows):
            bg = COLORS["card_bg"] if i % 2 == 0 else "transparent"
            r = ctk.CTkFrame(self.body, fg_color=bg, height=40, corner_radius=5)
            r.pack(fill="x", pady=2)
            
            e_id, fn, ln, role, email, branch, h_date, status, _ = row
            
            ctk.CTkLabel(r, text=str(e_id), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.02, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=fn, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.1, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=ln, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.25, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=role, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.4, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=branch, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.55, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=str(h_date), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.7, rely=0.5, anchor="w")
            
            if self.app.current_role == "ADMIN":
                btn_del = ctk.CTkButton(r, text="Delete", width=60, height=24, font=("Segoe UI", 11), fg_color=COLORS["danger"], command=lambda eid=e_id: self.delete_employee(eid))
                btn_del.place(relx=0.85, rely=0.5, anchor="w")
            else:
                ctk.CTkLabel(r, text="Restricted", font=("Segoe UI", 11), text_color=COLORS["warning"]).place(relx=0.85, rely=0.5, anchor="w")

    def delete_employee(self, eid):
        succ, msg = EmployeeService.soft_delete_employee(eid)
        if succ:
            self.app.show_toast(msg, "success")
            self.refresh()
        else:
            self.app.show_toast(msg, "error")
