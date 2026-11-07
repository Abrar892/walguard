import customtkinter as ctk

ctk.set_appearance_mode("Dark")

COLORS = {
    "primary": "#2563EB",
    "secondary": "#1E293B",
    "accent": "#06B6D4",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "background": "#0F172A",
    "card_bg": "#1E293B",
    "text": "#F8FAFC"
}

FONTS = {
    "heading": ("Segoe UI", 30, "bold"),
    "section": ("Segoe UI", 22, "bold"),
    "normal": ("Segoe UI", 14),
    "table": ("Segoe UI", 13),
    "button": ("Segoe UI", 15, "bold"),
    "console": ("Consolas", 13)
}

class ToastNotification(ctk.CTkToplevel):
    def __init__(self, master, message, msg_type="success"):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-alpha", 0.0)
        self.attributes("-topmost", True)
        
        color = COLORS["success"]
        if msg_type == "error": color = COLORS["danger"]
        elif msg_type == "warning": color = COLORS["warning"]
            
        self.configure(fg_color=color)
        
        lbl = ctk.CTkLabel(self, text=message, text_color="#FFF", font=FONTS["normal"])
        lbl.pack(padx=20, pady=10)
        
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (w // 2)
        y = master.winfo_rooty() + master.winfo_height() - h - 50
        self.geometry(f"+{x}+{y}")
        
        self.fade_in()
        self.after(3000, self.fade_out)
        
    def fade_in(self):
        alpha = self.attributes("-alpha")
        if alpha < 0.9:
            self.attributes("-alpha", alpha + 0.1)
            self.after(20, self.fade_in)
            
    def fade_out(self):
        alpha = self.attributes("-alpha")
        if alpha > 0.0:
            self.attributes("-alpha", alpha - 0.1)
            self.after(20, self.fade_out)
        else:
            self.destroy()

class BaseFrame(ctk.CTkFrame):
    def __init__(self, master, app, title="Page Title", **kwargs):
        super().__init__(master, fg_color=COLORS["background"], corner_radius=0, **kwargs)
        self.app = app
        
        # Header area
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=10, padx=20)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text=title, font=FONTS["heading"], text_color=COLORS["text"])
        self.title_label.pack(side="left")
        
    def refresh(self):
        pass
