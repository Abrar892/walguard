import customtkinter as ctk
from gui.components import BaseFrame, COLORS, FONTS
from services.customer_service import CustomerService

class CustomersFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Customer Management")
        
        # Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=10)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(toolbar, textvariable=self.search_var, placeholder_text="Search Name, Email, Phone...", font=FONTS["normal"], width=300)
        self.search_entry.pack(side="left", padx=(0, 10))
        
        btn_search = ctk.CTkButton(toolbar, text="Search", font=FONTS["button"], width=100, command=self.refresh)
        btn_search.pack(side="left")
        
        # Action Buttons
        self.btn_add = ctk.CTkButton(toolbar, text="+ Add Customer", font=FONTS["button"], fg_color=COLORS["success"], hover_color=COLORS["accent"], command=self.add_customer_dialog)
        self.btn_add.pack(side="right", padx=(10, 0))
        
        # Table Header
        header = ctk.CTkFrame(self, fg_color=COLORS["primary"], height=40, corner_radius=5)
        header.pack(fill="x", padx=20, pady=(10, 0))
        
        cols = [("ID", 0.02), ("First Name", 0.1), ("Last Name", 0.25), ("Email", 0.4), ("Phone", 0.6), ("DOB", 0.75), ("Actions", 0.88)]
        for name, relx in cols:
            ctk.CTkLabel(header, text=name, font=("Segoe UI", 12, "bold"), text_color="#fff").place(relx=relx, rely=0.5, anchor="w")
            
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(5, 20))
        
    def refresh(self):
        for w in self.body.winfo_children(): w.destroy()
        
        q = self.search_var.get().strip()
        if q:
            rows = CustomerService.search_customers(q)
        else:
            rows = CustomerService.get_all_customers()
            
        for i, row in enumerate(rows):
            bg = COLORS["card_bg"] if i % 2 == 0 else "transparent"
            r = ctk.CTkFrame(self.body, fg_color=bg, height=40, corner_radius=5)
            r.pack(fill="x", pady=2)
            
            c_id, fn, ln, email, phone, addr, dob, status = row
            
            ctk.CTkLabel(r, text=str(c_id), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.02, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=fn, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.1, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=ln, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.25, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=email, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.4, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=phone or "N/A", font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.6, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=str(dob) if dob else "N/A", font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.75, rely=0.5, anchor="w")
            
            if self.app.current_role == "ADMIN":
                btn_del = ctk.CTkButton(r, text="Delete", width=60, height=24, font=("Segoe UI", 11), fg_color=COLORS["danger"], command=lambda cid=c_id: self.delete_customer(cid))
                btn_del.place(relx=0.88, rely=0.5, anchor="w")
            else:
                ctk.CTkLabel(r, text="Restricted", font=("Segoe UI", 11), text_color=COLORS["warning"]).place(relx=0.88, rely=0.5, anchor="w")

    def add_customer_dialog(self):
        # A simple placeholder for adding a customer in a real app this would be a Toplevel window
        # For simplicity, we just trigger a toast that says "Form not implemented in this demo"
        # Since I need to show actual functionality, I'll implement a basic popup
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Customer")
        dialog.geometry("400x500")
        dialog.attributes("-topmost", True)
        
        ctk.CTkLabel(dialog, text="First Name").pack(pady=5)
        fn_entry = ctk.CTkEntry(dialog)
        fn_entry.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Last Name").pack(pady=5)
        ln_entry = ctk.CTkEntry(dialog)
        ln_entry.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="Email").pack(pady=5)
        em_entry = ctk.CTkEntry(dialog)
        em_entry.pack(pady=5)
        
        def save():
            succ, msg = CustomerService.add_customer(fn_entry.get(), ln_entry.get(), em_entry.get(), "0000", "N/A", "1990-01-01")
            if succ:
                self.app.show_toast(msg, "success")
                dialog.destroy()
                self.refresh()
            else:
                self.app.show_toast(msg, "error")
                
        ctk.CTkButton(dialog, text="Save", command=save).pack(pady=20)
        
    def delete_customer(self, cid):
        succ, msg = CustomerService.soft_delete_customer(cid)
        if succ:
            self.app.show_toast(msg, "success")
            self.refresh()
        else:
            self.app.show_toast(msg, "error")
