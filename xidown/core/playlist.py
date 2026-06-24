import os
import customtkinter as ctk
from typing import Any, Callable, Dict, Iterable, Optional

from xidown.core import utils

UI_STYLE: Dict[str, Dict[str, Any]] = {
    'label': {
        'font': ('Arial', 13),  # Font name, Font size
        'text_color': '#DB2777'
    },
    'frame_btn': {
        'fg_color': 'transparent'
    },
    'btn_no': {
        'fg_color': '#444444',
        'hover_color': '#666666',
    },
    'btn_yes': {
        'fg_color': '#DB2777',
        'hover_color': '#BE185D',
    }
}

class PlaylistGuard(ctk.CTkToplevel):
    def __init__(self, parent,
                 on_yes: Optional[Callable[..., Any]],
                 on_no: Optional[Callable[..., Any]]):
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

        label_style = UI_STYLE['label']
        lbl = ctk.CTkLabel(self, text=message, font=label_style['font'], text_color=label_style['text_color'])
        lbl.pack(pady=20, padx=20)

        frame_btn_style = UI_STYLE['frame_btn']
        frame_btn = ctk.CTkFrame(self, fg_color=frame_btn_style['fg_color'])
        frame_btn.pack(pady=10)

        btn_no_style = UI_STYLE['btn_no']
        btn_no = ctk.CTkButton(frame_btn, text="No, sorry!",
                               fg_color=btn_no_style['fg_color'],
                               hover_color=btn_no_style['hover_color'],
                               command=self.action_no)
        btn_no.pack(side="left", padx=10)

        btn_yes_style = UI_STYLE['btn_yes']
        btn_yes = ctk.CTkButton(frame_btn, text="Yes, Do it!",
                                fg_color=btn_yes_style['fg_color'],
                                hover_color=btn_yes_style['hover_color'],
                                command=self.action_yes)
        btn_yes.pack(side="right", padx=10)

    def action_yes(self):
        self.destroy()
        if self.on_yes: self.on_yes()

    def action_no(self):
        self.destroy()
        if self.on_no: self.on_no()

# Helper function to be invoked from the main application
def check_playlist_and_ask(parent, links: Iterable[str],
                           callback_continue: Callable[..., Any],
                           callback_cancel: Callable[..., Any]):
    is_playlist = False
    for L in links:
        if "list=" in L or "playlist" in L:
            is_playlist = True
            break

    if is_playlist:
        PlaylistGuard(parent, callback_continue, callback_cancel)
    else:
        callback_continue()
