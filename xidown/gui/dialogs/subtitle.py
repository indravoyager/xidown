import customtkinter as ctk
import os
import sys
import xidown.core.utils as utils

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.dirname(current_dir)
    BASE_DIR = os.path.dirname(package_dir)

class SubtitlePopup(ctk.CTkToplevel):
    def __init__(self, parent, available_subs, on_confirm, on_cancel=None, title_context=""):
        super().__init__(parent, fg_color="#121212")
        self.attributes("-alpha", 0.0)

        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.available_subs = available_subs
        self.icon_path = utils.get_icon_path()

        # Window setup
        self.title("Select Subtitles")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.action_cancel)

        w, h = 320, 420
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{int(x)}+{int(y)}")

        # Header
        ctk.CTkLabel(self, text="Available Subtitles", font=("Terminal", 15, "bold"), text_color="#db2777").pack(pady=(10, 2))
        if title_context:
            ctk.CTkLabel(self, text=title_context, font=("Terminal", 11, "italic"), text_color="#00ffcc").pack(pady=(0, 2), padx=10)
        ctk.CTkLabel(self, text="Select languages to download:", font=("Terminal", 11), text_color="#aaaaaa").pack(pady=(0, 5))

        # Checkbox list
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a", border_width=1, border_color="#2c2c2c", corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        try: self.scroll_frame._scrollbar.configure(width=10)
        except: pass

        self.checkboxes = {}
        self.var_all = ctk.BooleanVar(value=False)

        chk_style = {"fg_color": "#db2777", "hover_color": "#be185d", "checkbox_width": 22, "checkbox_height": 22, "border_width": 2, "corner_radius": 2, "border_color": "#555555", "checkmark_color": "white"}

        ctk.CTkCheckBox(self.scroll_frame, text="Select All", variable=self.var_all, command=self.toggle_all, font=("Terminal", 12, "bold"), **chk_style).pack(anchor="w", padx=5, pady=(5, 5))
        ctk.CTkFrame(self.scroll_frame, height=1, fg_color="#333333").pack(fill="x", padx=5, pady=(0, 5))

        if not self.available_subs:
            ctk.CTkLabel(self.scroll_frame, text="No subtitles found.", font=("Terminal", 11, "italic"), text_color="gray").pack(pady=10)
        else:
            for code, name in self.available_subs.items():
                var = ctk.BooleanVar(value=False)
                ctk.CTkCheckBox(self.scroll_frame, text=f"{name} ({code})", variable=var, font=("Terminal", 11), **chk_style).pack(anchor="w", padx=5, pady=3)
                self.checkboxes[code] = var

        # Bottom buttons
        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=15, pady=(0, 15))
        frame_btn.grid_columnconfigure(0, weight=3)
        frame_btn.grid_columnconfigure(1, weight=2)

        ctk.CTkButton(frame_btn, text="Download", height=34, fg_color="#db2777", hover_color="#be185d", font=("Terminal", 13, "bold"), corner_radius=0, command=self.action_ok).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(frame_btn, text="Cancel", height=34, fg_color="#2b2b2b", hover_color="#3a3a3a", font=("Terminal", 12, "bold"), corner_radius=0, command=self.action_cancel).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        # Reveal after render
        self.after(150, self._reveal)

    def _reveal(self):
        try:
            if self.icon_path and os.path.exists(self.icon_path):
                self.iconbitmap(self.icon_path)
        except: pass
        self.attributes("-alpha", 1.0)
        self.grab_set()

    def toggle_all(self):
        state = self.var_all.get()
        for var in self.checkboxes.values():
            var.set(state)

    def action_cancel(self):
        try: self.grab_release()
        except: pass
        self.destroy()
        if self.on_cancel: self.on_cancel()

    def action_ok(self):
        selected = [code for code, var in self.checkboxes.items() if var.get()]
        try: self.grab_release()
        except: pass
        self.destroy()
        if self.on_confirm:
            if self.var_all.get() and len(selected) == len(self.checkboxes):
                self.on_confirm(["all"])
            else:
                self.on_confirm(selected)
