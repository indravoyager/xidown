import customtkinter as ctk
import os
import sys

class PlaylistGuard(ctk.CTkToplevel):
    def __init__(self, parent, on_yes, on_no):
        super().__init__(parent)
        self.on_yes = on_yes
        self.on_no = on_no
        
        self.title("Whoa, wait a sec! ( `ε´ )")
        
        # 1. CENTER POSITION
        w, h = 350, 200
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set() # Block interaction with the main window (modal)
        
        # 2. ICON LOGIC (Same as settings.py)
        import xidown.core.utils as utils
        self.icon_path = utils.get_icon_path()
        
        def force_icon():
            try:
                if self.icon_path and os.path.exists(self.icon_path):
                    self.iconbitmap(self.icon_path)
            except Exception:
                pass

        # Call multiple times to ensure icon applies (Tkinter trick)
        force_icon() 
        self.after(200, force_icon)   
        self.after(1000, force_icon)

        # 3. UI CONTENT
        message = "Hey! I see a PLAYLIST link there!\n\nAre you trying to overwork me? (¬_¬ )\nHmph... fine, I can handle it.\n\nBut are you absolutely sure?"
        
        lbl = ctk.CTkLabel(self, text=message, font=("Arial", 13), text_color="#db2777")
        lbl.pack(pady=20, padx=20)
        
        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(pady=10)

        btn_no = ctk.CTkButton(frame_btn, text="No, sorry!", fg_color="#444", hover_color="#666", command=self.action_no)
        btn_no.pack(side="left", padx=10)
        
        btn_yes = ctk.CTkButton(frame_btn, text="Yes, Do it!", fg_color="#db2777", hover_color="#be185d", command=self.action_yes)
        btn_yes.pack(side="right", padx=10)

    def action_yes(self):
        self.destroy()
        if self.on_yes: self.on_yes()

    def action_no(self):
        self.destroy()
        if self.on_no: self.on_no()

# Helper function to be invoked from the main application
def check_playlist_and_ask(parent, links, callback_continue, callback_cancel):
    ada_playlist = False
    for L in links:
        if "list=" in L or "playlist" in L:
            ada_playlist = True
            break
    
    if ada_playlist:
        PlaylistGuard(parent, callback_continue, callback_cancel)
    else:
        callback_continue()