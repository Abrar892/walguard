import customtkinter as ctk
from gui.components import BaseFrame, COLORS, FONTS
from services.account_service import AccountService
from transaction_manager import TransactionManager

class AccountsFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Account Management")
        
        # Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=10)
        
        # Table Header
        header = ctk.CTkFrame(self, fg_color=COLORS["primary"], height=40, corner_radius=5)
        header.pack(fill="x", padx=20, pady=(10, 0))
        
        cols = [("Acc ID", 0.02), ("Account Number", 0.1), ("Customer Name", 0.25), ("Branch", 0.45), ("Type", 0.6), ("Balance", 0.7), ("Status", 0.85)]
        for name, relx in cols:
            ctk.CTkLabel(header, text=name, font=("Segoe UI", 12, "bold"), text_color="#fff").place(relx=relx, rely=0.5, anchor="w")
            
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(5, 20))
        
    def refresh(self):
        for w in self.body.winfo_children(): w.destroy()
        
        rows = AccountService.get_all_accounts(include_inactive=True)
            
        for i, row in enumerate(rows):
            bg = COLORS["card_bg"] if i % 2 == 0 else "transparent"
            r = ctk.CTkFrame(self.body, fg_color=bg, height=40, corner_radius=5)
            r.pack(fill="x", pady=2)
            
            a_id, a_num, cust, branch, a_type, bal, status = row
            
            ctk.CTkLabel(r, text=str(a_id), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.02, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=a_num, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.1, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=cust, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.25, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=branch, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.45, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=a_type, font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.6, rely=0.5, anchor="w")
            ctk.CTkLabel(r, text=f"Rs. {float(bal):,.2f}", font=FONTS["table"], text_color=COLORS["accent"]).place(relx=0.7, rely=0.5, anchor="w")
            
            status_color = COLORS["success"] if status == "ACTIVE" else COLORS["warning"]
            ctk.CTkLabel(r, text=status, font=FONTS["table"], text_color=status_color).place(relx=0.85, rely=0.5, anchor="w")


class DepositFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Deposit Funds")
        form = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=10)
        form.pack(pady=20, padx=20, fill="x")
        self.acc_var = ctk.StringVar(value="Select Account")
        self.acc_dropdown = ctk.CTkOptionMenu(form, variable=self.acc_var, values=[], font=FONTS["normal"], fg_color=COLORS["primary"], button_color=COLORS["primary"], button_hover_color=COLORS["accent"])
        self.acc_dropdown.pack(pady=15, padx=20, fill="x")
        self.amount_entry = ctk.CTkEntry(form, placeholder_text="Enter Amount", font=FONTS["normal"])
        self.amount_entry.pack(pady=15, padx=20, fill="x")
        self.notes_entry = ctk.CTkEntry(form, placeholder_text="Notes (Optional)", font=FONTS["normal"])
        self.notes_entry.pack(pady=15, padx=20, fill="x")
        btn = ctk.CTkButton(form, text="Deposit", font=FONTS["button"], fg_color=COLORS["primary"], hover_color=COLORS["accent"], command=self.do_deposit)
        btn.pack(pady=20, padx=20)
        
    def refresh(self):
        self.acc_dropdown.configure(values=AccountService.get_active_account_strings())
        self.acc_var.set("Select Account")
        self.amount_entry.delete(0, 'end')
        self.notes_entry.delete(0, 'end')

    def do_deposit(self):
        acc_str = self.acc_var.get()
        if "Select" in acc_str:
            self.app.show_toast("Please select an account", "error")
            return
        account_number = acc_str.split(" | ")[0]
        try:
            amt = float(self.amount_entry.get())
            if amt <= 0: raise ValueError
        except ValueError:
            self.app.show_toast("Invalid amount", "error")
            return
        notes = self.notes_entry.get()
        tm = TransactionManager()
        if tm.deposit(account_number, amt, notes):
            self.app.show_toast(f"✓ Deposit Successful: Rs. {amt:,.2f}", "success")
            self.refresh()
        else:
            self.app.show_toast("✖ Deposit Failed", "error")

class WithdrawFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Withdraw Funds")
        form = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=10)
        form.pack(pady=20, padx=20, fill="x")
        self.acc_var = ctk.StringVar(value="Select Account")
        self.acc_dropdown = ctk.CTkOptionMenu(form, variable=self.acc_var, values=[], font=FONTS["normal"], fg_color=COLORS["primary"], button_color=COLORS["primary"], button_hover_color=COLORS["accent"])
        self.acc_dropdown.pack(pady=15, padx=20, fill="x")
        self.amount_entry = ctk.CTkEntry(form, placeholder_text="Enter Amount", font=FONTS["normal"])
        self.amount_entry.pack(pady=15, padx=20, fill="x")
        self.notes_entry = ctk.CTkEntry(form, placeholder_text="Notes (Optional)", font=FONTS["normal"])
        self.notes_entry.pack(pady=15, padx=20, fill="x")
        btn = ctk.CTkButton(form, text="Withdraw", font=FONTS["button"], fg_color=COLORS["primary"], hover_color=COLORS["accent"], command=self.do_withdraw)
        btn.pack(pady=20, padx=20)
        
    def refresh(self):
        self.acc_dropdown.configure(values=AccountService.get_active_account_strings())
        self.acc_var.set("Select Account")
        self.amount_entry.delete(0, 'end')
        self.notes_entry.delete(0, 'end')

    def do_withdraw(self):
        acc_str = self.acc_var.get()
        if "Select" in acc_str:
            self.app.show_toast("Please select an account", "error")
            return
        account_number = acc_str.split(" | ")[0]
        try:
            amt = float(self.amount_entry.get())
            if amt <= 0: raise ValueError
        except ValueError:
            self.app.show_toast("Invalid amount", "error")
            return
        notes = self.notes_entry.get()
        tm = TransactionManager()
        if tm.withdraw(account_number, amt, notes):
            self.app.show_toast(f"✓ Withdrawal Successful: Rs. {amt:,.2f}", "success")
            self.refresh()
        else:
            self.app.show_toast("✖ Withdrawal Failed", "error")

class TransferFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Transfer Funds")
        form = ctk.CTkFrame(self, fg_color=COLORS["card_bg"], corner_radius=10)
        form.pack(pady=20, padx=20, fill="x")
        self.src_var = ctk.StringVar(value="Select Source Account")
        self.src_dropdown = ctk.CTkOptionMenu(form, variable=self.src_var, values=[], font=FONTS["normal"], fg_color=COLORS["primary"], button_color=COLORS["primary"], button_hover_color=COLORS["accent"])
        self.src_dropdown.pack(pady=15, padx=20, fill="x")
        self.dst_var = ctk.StringVar(value="Select Destination Account")
        self.dst_dropdown = ctk.CTkOptionMenu(form, variable=self.dst_var, values=[], font=FONTS["normal"], fg_color=COLORS["primary"], button_color=COLORS["primary"], button_hover_color=COLORS["accent"])
        self.dst_dropdown.pack(pady=15, padx=20, fill="x")
        self.amount_entry = ctk.CTkEntry(form, placeholder_text="Enter Amount", font=FONTS["normal"])
        self.amount_entry.pack(pady=15, padx=20, fill="x")
        self.notes_entry = ctk.CTkEntry(form, placeholder_text="Notes (Optional)", font=FONTS["normal"])
        self.notes_entry.pack(pady=15, padx=20, fill="x")
        btn = ctk.CTkButton(form, text="Transfer", font=FONTS["button"], fg_color=COLORS["primary"], hover_color=COLORS["accent"], command=self.do_transfer)
        btn.pack(pady=20, padx=20)
        
    def refresh(self):
        accs = AccountService.get_active_account_strings()
        self.src_dropdown.configure(values=accs)
        self.dst_dropdown.configure(values=accs)
        self.src_var.set("Select Source Account")
        self.dst_var.set("Select Destination Account")
        self.amount_entry.delete(0, 'end')
        self.notes_entry.delete(0, 'end')

    def do_transfer(self):
        src_str = self.src_var.get()
        dst_str = self.dst_var.get()
        if "Select" in src_str or "Select" in dst_str:
            self.app.show_toast("Please select both accounts", "error")
            return
        src_acc = src_str.split(" | ")[0]
        dst_acc = dst_str.split(" | ")[0]
        if src_acc == dst_acc:
            self.app.show_toast("Source and Destination cannot be the same", "warning")
            return
        try:
            amt = float(self.amount_entry.get())
            if amt <= 0: raise ValueError
        except ValueError:
            self.app.show_toast("Invalid amount", "error")
            return
        notes = self.notes_entry.get()
        tm = TransactionManager()
        if tm.transfer(src_acc, dst_acc, amt, notes):
            self.app.show_toast(f"✓ Transfer Successful: Rs. {amt:,.2f}", "success")
            self.refresh()
        else:
            self.app.show_toast("✖ Transfer Failed", "error")
