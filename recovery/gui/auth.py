import customtkinter as ctk
from gui.components import COLORS, FONTS

# Hardcoded roles for demo
USERS = {
    "admin": {"password": "admin", "role": "ADMIN"},
    "employee": {"password": "emp", "role": "EMPLOYEE"}
}

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["background"], corner_radius=0)
        self.app = app
        
        # Center container
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Logo / Title
        self.logo_lbl = ctk.CTkLabel(self.center_frame, text="Bank ADBMS", font=("Segoe UI", 36, "bold"), text_color=COLORS["primary"])
        self.logo_lbl.pack(pady=(0, 5))
        
        self.subtitle_lbl = ctk.CTkLabel(self.center_frame, text="Sign in to your account", font=FONTS["normal"], text_color=COLORS["text"])
        self.subtitle_lbl.pack(pady=(0, 30))
        
        # Login Box
        self.box = ctk.CTkFrame(self.center_frame, fg_color=COLORS["card_bg"], corner_radius=15, width=400)
        self.box.pack(pady=10, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(self.box, text="Username", font=FONTS["normal"], text_color=COLORS["text"]).pack(anchor="w", padx=30, pady=(30, 5))
        self.user_entry = ctk.CTkEntry(self.box, font=FONTS["normal"], placeholder_text="Enter username (admin / employee)", width=300)
        self.user_entry.pack(padx=30, pady=(0, 15))
        
        ctk.CTkLabel(self.box, text="Password", font=FONTS["normal"], text_color=COLORS["text"]).pack(anchor="w", padx=30, pady=(5, 5))
        self.pass_entry = ctk.CTkEntry(self.box, font=FONTS["normal"], placeholder_text="Enter password (admin / emp)", show="*", width=300)
        self.pass_entry.pack(padx=30, pady=(0, 20))
        
        # Options row
        self.opt_frame = ctk.CTkFrame(self.box, fg_color="transparent")
        self.opt_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        self.remember_var = ctk.BooleanVar(value=True)
        self.remember_chk = ctk.CTkCheckBox(self.opt_frame, text="Remember Me", variable=self.remember_var, font=("Segoe UI", 12), text_color=COLORS["text"], fg_color=COLORS["primary"], hover_color=COLORS["accent"])
        self.remember_chk.pack(side="left")
        
        self.show_pass_var = ctk.BooleanVar(value=False)
        self.show_pass_chk = ctk.CTkCheckBox(self.opt_frame, text="Show", variable=self.show_pass_var, font=("Segoe UI", 12), text_color=COLORS["text"], fg_color=COLORS["primary"], hover_color=COLORS["accent"], command=self.toggle_password)
        self.show_pass_chk.pack(side="right")
        
        # Login Button
        self.login_btn = ctk.CTkButton(self.box, text="Sign In", font=FONTS["button"], fg_color=COLORS["primary"], hover_color=COLORS["accent"], width=300, command=self.do_login)
        self.login_btn.pack(padx=30, pady=(0, 30))
        
    def toggle_password(self):
        if self.show_pass_var.get():
            self.pass_entry.configure(show="")
        else:
            self.pass_entry.configure(show="*")
            
    def do_login(self):
        user = self.user_entry.get().strip().lower()
        pwd = self.pass_entry.get()
        
        if user in USERS and USERS[user]["password"] == pwd:
            role = USERS[user]["role"]
            self.app.login_success(role)
        else:
            self.app.show_toast("Invalid username or password", "error")

    def refresh(self):
        self.pass_entry.delete(0, 'end')
        if not self.remember_var.get():
            self.user_entry.delete(0, 'end')
