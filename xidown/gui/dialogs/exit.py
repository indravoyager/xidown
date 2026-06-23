import customtkinter as ctk
import os
import sys

# --- Icon Path Configuration ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ExitWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback_bye):
        super().__init__(parent)
        
        # [ANTI-GLITCH] Hide first
        self.withdraw()
        
        self.callback_bye = callback_bye
        self.title("Wait...")
        
        # --- CENTER POSITION & COMPACT SIZE ---
        w, h = 280, 130 
        
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        
        # Modal Window
        self.transient(parent)
        self.grab_set()
        self.attributes("-topmost", True)
        
        # --- Icon Setup ---
        import xidown.core.utils as utils
        self.icon_path = utils.get_icon_path()
        def force_icon():
            try:
                if self.icon_path and os.path.exists(self.icon_path):
                    self.iconbitmap(self.icon_path)
            except Exception: pass
        
        force_icon()
        self.after(200, force_icon)
 
        # --- UI Content ---
        self.lbl_msg = ctk.CTkLabel(
            self, 
            text="Leaving already?\nI'll miss you... (｡•́︿•̀｡)", 
            font=("Terminal", 13, "bold"), 
            text_color="#db2777"
        )
        self.lbl_msg.pack(pady=(20, 5)) 
        
        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(pady=(5, 15)) 
        
        self.btn_stay = ctk.CTkButton(
            frame_btn, 
            text="Stay", 
            fg_color="#db2777", 
            hover_color="#be185d", 
            width=80,
            height=28, 
            corner_radius=0,
            font=("Terminal", 11, "bold"),
            command=self.destroy
        )
        self.btn_stay.pack(side="left", padx=10)
        
        self.btn_bye = ctk.CTkButton(
            frame_btn, 
            text="Bye", 
            fg_color="#444", 
            hover_color="#666", 
            width=80, 
            height=28,
            corner_radius=0,
            font=("Terminal", 11, "bold"),
            command=self.action_bye
        )
        self.btn_bye.pack(side="right", padx=10)
 
        # [ANTI-GLITCH] Show after window position is ready
        self.after(50, self.deiconify)
 
    def action_bye(self):
        self.destroy()
        if self.callback_bye:
            self.callback_bye()