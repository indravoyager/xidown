import customtkinter as ctk
import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.dirname(current_dir)
    BASE_DIR = os.path.dirname(package_dir)

class SubtitlePopup(ctk.CTkToplevel):
    def __init__(self, parent, available_subs, on_confirm, on_cancel=None, title_context=""):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.available_subs = available_subs
        self.selected_langs = []

        self.withdraw()
        self.title("Select Subtitles")
        
        w_width, w_height = 320, 420
        p_x = parent.winfo_x(); p_y = parent.winfo_y()
        p_w = parent.winfo_width(); p_h = parent.winfo_height()
        pos_x = p_x + (p_w // 2) - (w_width // 2)
        pos_y = p_y + (p_h // 2) - (w_height // 2)
        self.geometry(f"{w_width}x{w_height}+{int(pos_x)}+{int(pos_y)}")

        self.resizable(False, False)
        self.configure(fg_color="#121212")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        import xidown.core.utils as utils
        self.icon_path = utils.get_icon_path()
        
        def force_icon():
            try:
                if self.icon_path and os.path.exists(self.icon_path):
                    self.iconbitmap(self.icon_path)
            except Exception: pass
            
        force_icon()
        self.after(200, force_icon)
        self.after(1000, force_icon)

        self.protocol("WM_DELETE_WINDOW", self.action_cancel)

        # UI Content
        self.lbl_title = ctk.CTkLabel(self, text="Available Subtitles", font=("Terminal", 15, "bold"), text_color="#db2777")
        self.lbl_title.pack(pady=(10, 2))
        
        if title_context:
            self.lbl_context = ctk.CTkLabel(self, text=title_context, font=("Terminal", 11, "italic"), text_color="#00ffcc")
            self.lbl_context.pack(pady=(0, 2), padx=10)
            
        self.lbl_desc = ctk.CTkLabel(self, text="Select languages to download:", font=("Terminal", 11), text_color="#aaaaaa")
        self.lbl_desc.pack(pady=(0, 5))

        # Checkbox container
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a", border_width=1, border_color="#2c2c2c", corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        try: self.scroll_frame._scrollbar.configure(width=10)
        except: pass

        self.checkboxes = {}
        self.var_all = ctk.BooleanVar(value=False)

        # "Select All" Master Checkbox
        self.chk_all = ctk.CTkCheckBox(self.scroll_frame, text="Select All", variable=self.var_all, command=self.toggle_all, fg_color="#db2777", hover_color="#be185d", font=("Terminal", 12, "bold"), checkbox_width=22, checkbox_height=22, border_width=2, corner_radius=2, border_color="#555555", checkmark_color="white")
        self.chk_all.pack(anchor="w", padx=5, pady=(5, 5))
        
        # Divider
        frame_line = ctk.CTkFrame(self.scroll_frame, height=1, fg_color="#333333")
        frame_line.pack(fill="x", padx=5, pady=(0, 5))

        # Individual Checkboxes
        if not self.available_subs:
            lbl_empty = ctk.CTkLabel(self.scroll_frame, text="No subtitles found.", font=("Terminal", 11, "italic"), text_color="gray")
            lbl_empty.pack(pady=10)
        else:
            for code, name in self.available_subs.items():
                var = ctk.BooleanVar(value=False)
                chk = ctk.CTkCheckBox(self.scroll_frame, text=f"{name} ({code})", variable=var, fg_color="#db2777", hover_color="#be185d", font=("Terminal", 11), checkbox_width=22, checkbox_height=22, border_width=2, corner_radius=2, border_color="#555555", checkmark_color="white")
                chk.pack(anchor="w", padx=5, pady=3)
                self.checkboxes[code] = var

        # Bottom Buttons
        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=15, pady=(0, 15))
        frame_btn.grid_columnconfigure(0, weight=3)
        frame_btn.grid_columnconfigure(1, weight=2)

        self.btn_ok = ctk.CTkButton(frame_btn, text="Download", height=34, fg_color="#db2777", hover_color="#be185d", font=("Terminal", 13, "bold"), corner_radius=0, command=self.action_ok)
        self.btn_ok.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.btn_cancel = ctk.CTkButton(frame_btn, text="Cancel", height=34, fg_color="#2b2b2b", hover_color="#3a3a3a", font=("Terminal", 12, "bold"), corner_radius=0, command=self.action_cancel)
        self.btn_cancel.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.after(50, self.deiconify)

    def toggle_all(self):
        state = self.var_all.get()
        for var in self.checkboxes.values():
            if state: var.set(True)
            else: var.set(False)

    def action_cancel(self):
        self.destroy()
        if self.on_cancel: self.on_cancel()

    def action_ok(self):
        # Gather selected codes
        selected = [code for code, var in self.checkboxes.items() if var.get()]
        self.destroy()
        if self.on_confirm:
            if self.var_all.get() and len(selected) == len(self.checkboxes):
                # If they literally checked everything, just pass "all"
                self.on_confirm(["all"])
            else:
                self.on_confirm(selected)
