import customtkinter as ctk
import os
import sys
from datetime import datetime
from gui.components import BaseFrame, COLORS, FONTS
from mongo_logger import MongoLogger
from crash_simulator import CrashSimulator
from recovery_manager import RecoveryManager
from services.account_service import AccountService

# Redefine log_event locally or import
def log_event(message):
    print(message)

class RecoveryCenterFrame(BaseFrame):
    def __init__(self, master, app):
        super().__init__(master, app, title="Recovery Center (ADBMS Advanced)")
        
        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tab_wal = self.tabview.add("WAL Logs")
        self.tab_crash = self.tabview.add("Crash Simulation")
        self.tab_recover = self.tabview.add("Recovery Manager")
        self.tab_console = self.tabview.add("Recovery Console")
        
        self.setup_wal_tab()
        self.setup_crash_tab()
        self.setup_recover_tab()
        self.setup_console_tab()
        
    def refresh(self):
        self.refresh_wal()
        self.acc_dropdown.configure(values=AccountService.get_active_account_strings())
        self.acc_var.set("Select Account")
        self.amount_entry.delete(0, 'end')

    # --- WAL Logs Tab ---
    def setup_wal_tab(self):
        header = ctk.CTkFrame(self.tab_wal, fg_color=COLORS["primary"], height=40, corner_radius=5)
        header.pack(fill="x", pady=(10, 0))
        
        cols = [
            ("ID", 0.02), ("Time", 0.07), ("Session", 0.16), ("Acc ID", 0.28), 
            ("Type", 0.35), ("Old", 0.48), ("New", 0.58), ("Amt", 0.68), 
            ("Status", 0.77), ("Notes", 0.88)
        ]
        for name, relx in cols:
            ctk.CTkLabel(header, text=name, font=("Segoe UI", 12, "bold"), text_color="#fff").place(relx=relx, rely=0.5, anchor="w")
            
        self.wal_body = ctk.CTkScrollableFrame(self.tab_wal, fg_color="transparent")
        self.wal_body.pack(fill="both", expand=True, pady=(5, 20))
        
    def refresh_wal(self):
        for w in self.wal_body.winfo_children(): w.destroy()
        try:
            logger = MongoLogger()
            logs = list(logger.col.find({}, {"_id": 0}).sort("timestamp", -1).limit(100))
            for i, log in enumerate(logs):
                bg = COLORS["card_bg"] if i % 2 == 0 else "transparent"
                r = ctk.CTkFrame(self.wal_body, fg_color=bg, height=40, corner_radius=5)
                r.pack(fill="x", pady=2)
                
                dt_str = log.get("timestamp", "").strftime('%H:%M:%S') if hasattr(log.get("timestamp"), 'strftime') else str(log.get("timestamp", ""))[:8]
                
                ctk.CTkLabel(r, text=str(log.get("log_id", "")), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.02, rely=0.5, anchor="w")
                ctk.CTkLabel(r, text=dt_str, font=("Segoe UI", 11), text_color=COLORS["text"]).place(relx=0.07, rely=0.5, anchor="w")
                ctk.CTkLabel(r, text=str(log.get("session_id", ""))[:8], font=("Segoe UI", 11), text_color=COLORS["text"]).place(relx=0.16, rely=0.5, anchor="w")
                ctk.CTkLabel(r, text=str(log.get("account_id", "")), font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.28, rely=0.5, anchor="w")
                ctk.CTkLabel(r, text=log.get("txn_type", "")[:12], font=("Segoe UI", 11), text_color=COLORS["text"]).place(relx=0.35, rely=0.5, anchor="w")
                ctk.CTkLabel(r, text=f"{float(log.get('old_balance', 0)):.1f}", font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.48, rely=0.5, anchor="w")
                ctk.CTkLabel(r, text=f"{float(log.get('new_balance', 0)):.1f}", font=FONTS["table"], text_color=COLORS["text"]).place(relx=0.58, rely=0.5, anchor="w")
                ctk.CTkLabel(r, text=f"{float(log.get('amount', 0)):.1f}", font=FONTS["table"], text_color=COLORS["accent"]).place(relx=0.68, rely=0.5, anchor="w")
                
                status = log.get("status", "")
                status_color = COLORS["success"] if status == "COMMITTED" else (COLORS["danger"] if status == "ROLLED_BACK" else COLORS["warning"])
                ctk.CTkLabel(r, text=status, font=("Segoe UI", 11, "bold"), text_color=status_color).place(relx=0.77, rely=0.5, anchor="w")
                
                ctk.CTkLabel(r, text=str(log.get("notes", ""))[:20], font=("Segoe UI", 11), text_color=COLORS["text"]).place(relx=0.88, rely=0.5, anchor="w")
        except Exception as e:
            pass

    # --- Crash Tab ---
    def setup_crash_tab(self):
        form = ctk.CTkFrame(self.tab_crash, fg_color=COLORS["card_bg"], corner_radius=10)
        form.pack(pady=10, fill="x")
        
        self.acc_var = ctk.StringVar(value="Select Account")
        self.acc_dropdown = ctk.CTkOptionMenu(form, variable=self.acc_var, values=[], font=FONTS["normal"], fg_color=COLORS["danger"], button_color=COLORS["danger"], button_hover_color=COLORS["warning"])
        self.acc_dropdown.pack(pady=15, padx=20, side="left", expand=True, fill="x")
        
        self.amount_entry = ctk.CTkEntry(form, placeholder_text="Enter Amount to Withdraw", font=FONTS["normal"])
        self.amount_entry.pack(pady=15, padx=20, side="left", expand=True, fill="x")
        
        btn = ctk.CTkButton(form, text="Simulate Crash", font=FONTS["button"], fg_color=COLORS["danger"], hover_color=COLORS["warning"], command=self.do_crash)
        btn.pack(pady=20, padx=20, side="right")
        
        self.crash_console = ctk.CTkTextbox(self.tab_crash, font=FONTS["console"], fg_color="#000000", text_color="#00FF00", state="disabled")
        self.crash_console.pack(fill="both", expand=True, pady=10)
        
    def append_crash_log(self, msg):
        self.crash_console.configure(state="normal")
        self.crash_console.insert("end", msg)
        self.crash_console.see("end")
        self.crash_console.configure(state="disabled")

    def do_crash(self):
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
            
        sys.stdout.add_listener(self.append_crash_log)
        self.crash_console.configure(state="normal")
        self.crash_console.delete("1.0", "end")
        self.crash_console.configure(state="disabled")
        
        log_event(f"CRASH SIMULATION INITIATED: {account_number} | -{amt}")
        cs = CrashSimulator()
        log_id = cs.simulate_crash(account_number, amt, txn_type="WITHDRAWAL")
        
        if log_id != -1:
            self.app.show_toast("⚠ Crash Simulated! Please Run Recovery.", "warning")
            log_event(f"SIMULATION COMPLETE. RUN RECOVERY TO RECONCILE DB.")
        else:
            self.app.show_toast("✖ Error during crash simulation.", "error")
            
        sys.stdout.remove_listener(self.append_crash_log)

    # --- Recovery Tab ---
    def setup_recover_tab(self):
        panel = ctk.CTkFrame(self.tab_recover, fg_color=COLORS["card_bg"], corner_radius=10)
        panel.pack(pady=10, fill="x")
        
        self.btn_rec = ctk.CTkButton(panel, text="Run ARIES Recovery", font=FONTS["button"], fg_color=COLORS["success"], hover_color=COLORS["accent"], command=self.do_recovery)
        self.btn_rec.pack(pady=20)
        
        self.rec_console = ctk.CTkTextbox(self.tab_recover, font=FONTS["console"], fg_color="#000000", text_color="#00FF00", state="disabled")
        self.rec_console.pack(fill="both", expand=True, pady=10)
        
    def append_rec_log(self, msg):
        self.rec_console.configure(state="normal")
        self.rec_console.insert("end", msg)
        self.rec_console.see("end")
        self.rec_console.configure(state="disabled")

    def do_recovery(self):
        self.btn_rec.configure(state="disabled")
        self.app.update()
        
        sys.stdout.add_listener(self.append_rec_log)
        self.rec_console.configure(state="normal")
        self.rec_console.delete("1.0", "end")
        self.rec_console.configure(state="disabled")
        
        log_event("RECOVERY MANAGER INITIATED.")
        rm = RecoveryManager()
        try:
            rm.run_recovery()
            self.app.show_toast("✓ Recovery Completed", "success")
            self.refresh_wal()
        except Exception as e:
            self.app.show_toast(f"✖ Recovery Failed: {e}", "error")
            
        sys.stdout.remove_listener(self.append_rec_log)
        self.btn_rec.configure(state="normal")

    # --- Global Console Tab ---
    def setup_console_tab(self):
        top_bar = ctk.CTkFrame(self.tab_console, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))
        
        btn = ctk.CTkButton(top_bar, text="Export Session Logs", font=FONTS["button"], fg_color=COLORS["success"], hover_color=COLORS["accent"], command=self.export_logs)
        btn.pack(side="right")
        
        self.global_console = ctk.CTkTextbox(self.tab_console, font=FONTS["console"], fg_color="#000000", text_color="#00FF00", state="disabled")
        self.global_console.pack(fill="both", expand=True, pady=(0, 20))
        
        # Load history
        self.global_console.configure(state="normal")
        for line in sys.stdout.history:
            self.global_console.insert("end", line)
        self.global_console.see("end")
        self.global_console.configure(state="disabled")
        
        sys.stdout.add_listener(self.append_global_log)
        
    def append_global_log(self, msg):
        self.global_console.configure(state="normal")
        self.global_console.insert("end", msg)
        self.global_console.see("end")
        self.global_console.configure(state="disabled")
        
    def export_logs(self):
        if not os.path.exists("logs"):
            os.makedirs("logs")
        filename = f"logs/session_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.writelines(sys.stdout.history)
        self.app.show_toast(f"Logs exported to {filename}", "success")
        log_event(f"Session logs exported to {filename}")
