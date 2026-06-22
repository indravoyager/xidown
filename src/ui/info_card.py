import customtkinter as ctk
import os
import sys

# --- Path Configuration ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 
class InfoCard(ctk.CTkToplevel):
    def __init__(self, parent, data_video):
        super().__init__(parent)
        
        # [ANTI-GLITCH] Hide window initially
        self.withdraw()
        self.title("Video Details")
        
        # --- ICON SETUP ---
        try:
            import logic.utils as utils
            icon_path = utils.get_icon_path()
            if icon_path and os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except: pass
        
        # --- CENTER GEOMETRY ---
        w_pop, h_pop = 420, 260
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w_pop // 2)
        y = (hs // 2) - (h_pop // 2)
        
        self.geometry(f"{w_pop}x{h_pop}+{int(x)}+{int(y)}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # --- UI CONTENT ---
        self.configure(fg_color="#181818")
        
        # Main Container
        frame_main = ctk.CTkFrame(self, corner_radius=12, fg_color="#1a1a1a", border_width=1, border_color="#333333")
        frame_main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 1. Video Title
        lbl_title_header = ctk.CTkLabel(frame_main, text="VIDEO TITLE", font=("Terminal", 10, "bold"), text_color="#db2777")
        lbl_title_header.pack(anchor="w", padx=15, pady=(15, 0))
        
        # Textbox for Title (Read-only but allows text selection)
        self.txt_title = ctk.CTkTextbox(frame_main, height=60, font=("Terminal", 12), fg_color="#2b2b2b", text_color="#f0f0f0", corner_radius=6)
        self.txt_title.pack(fill="x", padx=15, pady=(5, 10))
        self.txt_title.insert("0.0", data_video.get('title', 'Unknown Title'))
        self.txt_title.configure(state="disabled") # Read only
        
        # 2. Channel / Uploader
        lbl_channel_header = ctk.CTkLabel(frame_main, text="CHANNEL / UPLOADER", font=("Terminal", 10, "bold"), text_color="#db2777")
        lbl_channel_header.pack(anchor="w", padx=15, pady=(5, 0))
        
        # Retrieve uploader data, defaulting to 'Unknown' if missing
        channel_name = data_video.get('uploader', 'Unknown Channel') 
        lbl_channel = ctk.CTkLabel(frame_main, text=channel_name, font=("Terminal", 11), text_color="#aaaaaa", anchor="w")
        lbl_channel.pack(anchor="w", fill="x", padx=15, pady=(0, 10))
        
        # 3. Link Area (Entry + Copy Button)
        lbl_link_header = ctk.CTkLabel(frame_main, text="VIDEO URL", font=("Terminal", 10, "bold"), text_color="#db2777")
        lbl_link_header.pack(anchor="w", padx=15, pady=(5, 0))
        
        frame_link = ctk.CTkFrame(frame_main, fg_color="transparent")
        frame_link.pack(fill="x", padx=15, pady=(0, 15))
        
        self.entry_link = ctk.CTkEntry(frame_link, font=("Terminal", 11), fg_color="#2b2b2b", border_width=0, height=32)
        self.entry_link.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_link.insert(0, data_video.get('url_dl', ''))
        self.entry_link.configure(state="readonly") # Read-only but copyable
        
        self.btn_copy = ctk.CTkButton(
            frame_link, text="Copy", width=60, height=32, 
            fg_color="#db2777", hover_color="#be185d", 
            font=("Terminal", 11, "bold"),
            command=self.action_copy
        )
        self.btn_copy.pack(side="right")
 
        # [SMOOTH APPEARANCE] Show when ready
        self.after(100, self.deiconify)
 
    def action_copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.entry_link.get())
        self.update() # Ensure clipboard is updated
        
        # Visual button effect changing momentarily
        self.btn_copy.configure(text="Copied!", fg_color="#28a745")
        self.after(1000, lambda: self.btn_copy.configure(text="Copy", fg_color="#db2777"))