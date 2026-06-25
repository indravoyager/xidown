import customtkinter as ctk
import os
import sys
import threading
import requests
import urllib3 
import hashlib 
import time
from PIL import Image, ImageOps
from io import BytesIO
import tkinter 
from xidown.core import utils

# [MARIBEL] Import data from version.py for convenience
try:
    from xidown.core.version import WINDOW_TITLE, APP_NAME
except ImportError:
    WINDOW_TITLE = "Downloader App"
    APP_NAME = "My Downloader"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# NAVIGATION FIX (Fix to ensure data resides in Root, not package)
if getattr(sys, 'frozen', False):
    # If run as EXE (frozen)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # If run as Python script (Development)
    # Location of this file: xidown/xidown/gui/window.py
    current_dir = os.path.dirname(os.path.abspath(__file__)) # .../xidown/gui
    package_dir = os.path.dirname(current_dir)               # .../xidown (Package)
    BASE_DIR = os.path.dirname(package_dir)                  # .../xidown (Project Root)

DATA_DIR = os.path.join(BASE_DIR, "data")
THUMB_DIR = os.path.join(DATA_DIR, "thumbs")
if not os.path.exists(THUMB_DIR):
    os.makedirs(THUMB_DIR)

# UTILS: GHOST CLASS & MENU
class RightClickMenu(ctk.CTkToplevel):
    def __init__(self, parent, coords, commands, mode="single"):
        super().__init__(parent)
        self.overrideredirect(True); self.attributes("-topmost", True)
        x, y = coords
        
        # [MARIBEL UI] Adjust menu height to fit perfectly
        h_menu = 90 if mode == "batch" else 120 
        
        self.geometry(f"160x{h_menu}+{x}+{y}")
        self.configure(fg_color="#333333") # Using Toplevel bg as border
        self.frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)
        self.frame.pack(fill="both", expand=True, padx=1, pady=1) # Leave 1px to make border smooth without holes
        self.is_destroyed = False
        ctk.CTkFrame(self.frame, height=5, fg_color="transparent").pack(fill="x")
        
        if mode == "batch":
            if 'menu_list' in commands:
                for label, func, is_dest in commands['menu_list']: 
                    self.add_menu_item(label, func, is_destructive=is_dest, text_color="#ffffff")
        else:
            self.add_menu_item("Test Play (15s)", commands['test'], text_color="#ffffff") 
            
            if 'download' in commands:
                self.add_menu_item("Download", commands['download'], text_color="#ffffff")
            # -------------------------------

            text_pin = "Unpin Item" if commands.get('is_locked') else "Pin Item"
            self.add_menu_item(text_pin, commands['pin'], text_color="#ffffff")
            
            ctk.CTkFrame(self.frame, height=1, fg_color="#333333").pack(fill="x", padx=0, pady=2)
            self.add_menu_item("Delete", commands['delete'], is_destructive=True, text_color="#ffffff")
            
        ctk.CTkFrame(self.frame, height=5, fg_color="transparent").pack(fill="x")
        self.update_idletasks(); self.safe_focus_immediate()
        self.bind("<Button-1>", self.check_click_outside) 

    def safe_focus_immediate(self):
        if self.is_destroyed: return
        try: 
            self.focus_set()
            self.after(50, self.focus_force)
        except: pass
        
        # Delay FocusOut binding by 200ms so menu does not disappear instantly
        self.after(200, self.activate_focus_out)

    def activate_focus_out(self):
        if not self.is_destroyed:
            self.bind("<FocusOut>", self.on_focus_out)
            
    def on_focus_out(self, event): 
        focused = self.focus_get()
        if focused is None or str(self) not in str(focused):
            self.close_safely()
            
    def check_click_outside(self, event): pass 
    
    def close_safely(self):
        if self.is_destroyed: return
        self.is_destroyed = True
        try: self.destroy()
        except: pass
        
    def add_menu_item(self, text, command, is_destructive=False, text_color=None):
        hover_col = "#330000" if is_destructive else "#2a2a2a" 
        if text_color: final_text_col = text_color
        else: final_text_col = "#ff7777" if is_destructive else "#e0e0e0"
        def wrapper():
            try: command()
            except: pass
            self.close_safely()
        btn = ctk.CTkButton(self.frame, text=text, anchor="w", fg_color="transparent", text_color=final_text_col, hover_color=hover_col, font=("Terminal", 10, "bold"), height=24, corner_radius=0, command=wrapper)
        btn.pack(fill="x", padx=5, pady=1)

# [MARIBEL] UPDATED THUMBNAIL CARD
class ThumbnailCard(ctk.CTkFrame):
    # [MARIBEL UPDATE] Add callback_download_satu parameter
    def __init__(self, parent, data_video, callback_delete_satu, callback_toggle=None, callback_reorder=None, callback_lock=None, callback_test=None, callback_download_satu=None):
        self.default_bg = "#1e1e1e"
        super().__init__(parent, fg_color=self.default_bg, corner_radius=0, border_width=1, border_color="#2c2c2c") 
        self.pack(pady=4, padx=5, fill="x") 
        self.data = data_video 
        self.callback_delete = callback_delete_satu 
        self.callback_toggle = callback_toggle 
        self.callback_reorder = callback_reorder
        self.callback_lock = callback_lock 
        self.callback_test = callback_test 
        
        # [NEW] Save download callback
        self.callback_download = callback_download_satu
        
        self.is_dragging = False; self.ghost_window = None
        self.pil_image_cache = None; self.ctk_image_cache = None
        self._drag_bind_id = None; self._click_bind_id = None
        
        self.grid_columnconfigure(2, weight=1) 
        self.var_select = ctk.BooleanVar(value=data_video.get('selected', True))
        
        self.checkbox = ctk.CTkCheckBox(self, text="", variable=self.var_select, width=24, height=24, checkbox_width=22, checkbox_height=22, border_width=2, corner_radius=2, border_color="#555555", fg_color="#db2777", hover_color="#be185d", checkmark_color="white", command=self.action_check)
        self.checkbox.grid(row=0, column=0, rowspan=3, padx=(10, 5), pady=0) 

        self.image_label = ctk.CTkLabel(self, text="...", width=75, height=45, fg_color="#3a3a3a", corner_radius=0)
        self.image_label.grid(row=0, column=1, rowspan=3, padx=5, pady=5) 
        if data_video.get('thumb_url'): threading.Thread(target=self.load_image_smart, args=(data_video['thumb_url'],), daemon=True).start()
        else: self.image_label.configure(text="NO IMG", text_color="gray", font=("Terminal", 9))

        # Row 1: Title
        self.lbl_title = ctk.CTkLabel(self, text="", font=("Terminal", 10, "bold"), anchor="w", text_color="#f0f0f0", height=16)
        self.lbl_title.grid(row=0, column=2, sticky="ew", padx=8, pady=(4,0))
        
        # Row 2: Combined Info (Res • Size • Duration)
        self.lbl_info = ctk.CTkLabel(self, text="...", font=("Terminal", 9), text_color="#aaaaaa", anchor="w", height=14)
        self.lbl_info.grid(row=1, column=2, sticky="w", padx=8, pady=0) 
        
        # Row 3: Realtime Status (Speed/ETA) - Default Grey
        self.lbl_status_row = ctk.CTkLabel(self, text="Ready.", font=("Terminal", 9), text_color="#aaaaaa", anchor="w", height=14)
        self.lbl_status_row.grid(row=2, column=2, sticky="nw", padx=8, pady=(0,4))

        self.update_visual_data()
        
        try:
            ic_del = self.winfo_toplevel().ic_delete
            text_del = ""
        except:
            ic_del = None
            text_del = "X"
            
        self.btn_delete = ctk.CTkButton(self, text=text_del, image=ic_del, width=28, height=28, fg_color="#2b2b2b", hover_color="#8B0000", text_color="#777777", font=("Terminal", 10, "bold"), command=self.action_delete_self, corner_radius=0)
        self.btn_delete.grid(row=0, column=3, rowspan=3, padx=(0, 8))

        # Bindings
        for w in [self, self.lbl_title, self.lbl_info, self.lbl_status_row, self.image_label]:
            w.bind("<Button-1>", self.on_start_reorder)
            w.bind("<B1-Motion>", self.on_drag_reorder)
            w.bind("<Button-3>", self.open_context_menu) # Windows/Linux Right-Click
            w.bind("<Button-2>", self.open_context_menu) # macOS Right-Click
        self.checkbox.bind("<Button-1>", self.on_click_start_select); self.checkbox.bind("<B1-Motion>", self.on_drag_motion_select)
        self.checkbox._canvas.bind("<Button-1>", self.on_click_start_select); self.checkbox._canvas.bind("<B1-Motion>", self.on_drag_motion_select)

    def open_context_menu(self, event):
        commands = { 
            'pin': self.toggle_lock, 
            'delete': self.action_delete_self, 
            'test': self.call_test_play,
            
            # [NEW] Bridge trigger download
            'download': self.call_forced_download,
            
            'is_locked': self.data.get('locked', False) 
        }
        RightClickMenu(self, (event.x_root, event.y_root), commands, mode="single")
    
    def call_test_play(self):
        if self.callback_test: self.callback_test(self.data)

    # [NEW] Bridge function for downloading
    def call_forced_download(self):
        if self.callback_download:
            self.callback_download(self)
        else:
            print("[ThumbnailCard] Download callback has not been bound!")

    def toggle_lock(self):
        self.data['locked'] = not self.data.get('locked', False); self.update_visual_data(); 
        if self.callback_lock: self.callback_lock(self)
    
    def update_visual_data(self):
        title = self.data.get('title', 'Unknown'); prefix = "" if self.data.get('locked', False) else ""; display_text = prefix + title
        if len(display_text) > 75: display_text = display_text[:72] + ".."
        self.lbl_title.configure(text=display_text)
        if self.data.get('locked', False): self.configure(border_color="#db2777", border_width=1); self.lbl_title.configure(text_color="#db2777")
        else: self.configure(border_color="#2c2c2c", border_width=1); self.lbl_title.configure(text_color="#f0f0f0")
        self.set_size_display("mp3" if "Audio" in self.lbl_info.cget("text") or "🎵" in self.lbl_info.cget("text") else "mp4")

    def set_download_status(self, text, color="#aaaaaa"):
        self.lbl_status_row.configure(text=text, text_color=color)

    # --- DRAG LOGIC (Simplified for brevity, logic remains same) ---
    def transform_to_placeholder(self):
        try: self.image_label.configure(image=None, text=""); self.lbl_title.configure(text_color="#181818"); self.lbl_info.configure(text_color="#181818"); self.lbl_status_row.configure(text_color="#181818"); self.configure(fg_color="#181818", border_width=1, border_color="#333"); self.btn_delete.grid_remove()
        except: pass
    def restore_appearance(self):
        try: self.configure(fg_color=self.default_bg, border_width=0); self.lbl_status_row.configure(text_color="#aaaaaa"); self.btn_delete.grid(row=0, column=3, rowspan=3, padx=(0, 8))
        except: pass
        self.update_visual_data()
        if self.ctk_image_cache: 
            try: self.image_label.configure(image=self.ctk_image_cache, text="")
            except: pass
        elif self.data.get('thumb_url'): threading.Thread(target=self.load_image_smart, args=(self.data['thumb_url'],), daemon=True).start()

    def create_ghost(self):
        if self.ghost_window: return
        self.ghost_window = ctk.CTkToplevel(self)
        self.ghost_window.overrideredirect(True); self.ghost_window.attributes("-topmost", True); self.ghost_window.attributes("-alpha", 0.90) 
        self.ghost_window.configure(fg_color="#000001"); 
        import sys
        if sys.platform == 'win32':
            try: self.ghost_window.attributes("-transparentcolor", "#000001")
            except: pass
        ghost_frame = ctk.CTkFrame(self.ghost_window, fg_color="#2b2b2b", corner_radius=0, border_width=1, border_color="#db2777")
        ghost_frame.pack(fill="both", expand=True)
        ghost_frame.grid_columnconfigure(1, weight=1); ghost_frame.grid_rowconfigure(0, weight=1) 
        
        ghost_img_w, ghost_img_h = 60, 36
        ghost_img_lbl = ctk.CTkLabel(ghost_frame, text="", width=ghost_img_w, height=ghost_img_h, fg_color="#3a3a3a", corner_radius=0)
        ghost_img_lbl.grid(row=0, column=0, padx=(8, 5), pady=6) 
        
        if self.pil_image_cache:
            try: mini_pil = self.pil_image_cache.copy(); mini_ctk = ctk.CTkImage(light_image=mini_pil, dark_image=mini_pil, size=(ghost_img_w, ghost_img_h)); ghost_img_lbl.configure(image=mini_ctk)
            except: ghost_img_lbl.configure(text="IMG")
        elif self.ctk_image_cache: ghost_img_lbl.configure(image=self.ctk_image_cache) 
        else: ghost_img_lbl.configure(text="IMG")
            
        text_frame = ctk.CTkFrame(ghost_frame, fg_color="transparent")
        text_frame.grid(row=0, column=1, sticky="w", padx=(0, 10))
        text_title = self.lbl_title.cget("text"); text_title = text_title[:22] + "..." if len(text_title) > 25 else text_title
        ctk.CTkLabel(text_frame, text=text_title, font=("Terminal", 10, "bold"), anchor="w", text_color="#f0f0f0", height=14).pack(anchor="w", pady=0) 
        ctk.CTkLabel(text_frame, text="Moving item...", font=("Terminal", 9), text_color="#aaaaaa", anchor="w", height=12).pack(anchor="w", pady=0) 
        self.ghost_window.geometry("280x48") 

    def update_ghost_position(self, x_root, y_root):
        if self.ghost_window: self.ghost_window.geometry(f"+{x_root - 100}+{y_root - 20}")

    def on_start_reorder(self, event):
        self.is_dragging = True; self.create_ghost(); self.update_ghost_position(event.x_root, event.y_root); self.transform_to_placeholder()
        root = self.winfo_toplevel()
        self._drag_bind_id = root.bind("<ButtonRelease-1>", self.on_stop_reorder, add="+")
        self._click_bind_id = root.bind("<Button-1>", self.on_stop_reorder_force, add="+")

    def on_stop_reorder(self, event): self.finish_drag()
    def on_stop_reorder_force(self, event): self.finish_drag()
    def force_stop_drag(self): 
        if self.is_dragging: self.finish_drag()
    def finish_drag(self):
        if not self.is_dragging: return
        self.is_dragging = False
        if self.ghost_window: self.ghost_window.destroy(); self.ghost_window = None
        self.restore_appearance()
        try:
            root = self.winfo_toplevel()
            if self._drag_bind_id: root.unbind("<ButtonRelease-1>", self._drag_bind_id); self._drag_bind_id = None
            if self._click_bind_id: root.unbind("<Button-1>", self._click_bind_id); self._click_bind_id = None
        except: pass

    def on_drag_reorder(self, event):
        if not self.is_dragging: return
        self.update_ghost_position(event.x_root, event.y_root)
        y_global = event.y_root; myself = self; siblings = self.master.winfo_children()
        for widget in siblings:
            if not isinstance(widget, ThumbnailCard) or widget == myself: continue
            try:
                wy = widget.winfo_rooty(); wh = widget.winfo_height(); cy = wy + (wh // 2)
                if (wy < y_global < wy + wh):
                    should_swap = False
                    if y_global > cy and self.winfo_rooty() < wy: should_swap = True
                    elif y_global < cy and self.winfo_rooty() > wy: should_swap = True
                    if should_swap and self.callback_reorder: self.callback_reorder(myself, widget); return 
            except: pass
            
    def action_check(self):
        self.data['selected'] = self.var_select.get()
        if self.callback_toggle: self.callback_toggle()
    def on_click_start_select(self, event):
        self.drag_target_state = not self.var_select.get(); self.var_select.set(self.drag_target_state); self.action_check(); return "break" 
    def on_drag_motion_select(self, event):
        if not self.master: return
        for widget in self.master.winfo_children():
            if isinstance(widget, ThumbnailCard):
                try:
                    if (widget.winfo_rooty() < event.y_root < widget.winfo_rooty() + widget.winfo_height()):
                        if widget.var_select.get() != self.drag_target_state: widget.var_select.set(self.drag_target_state); widget.action_check()
                except: pass
    def action_delete_self(self): self.callback_delete(self)
    
    def set_size_display(self, mode):
        duration = self.data.get('duration', '??:??')
        if mode == "mp3": 
            size = self.data.get('size_audio', '? MB')
            text_combined = f"Audio • {size} • {duration}"
            self.lbl_info.configure(text=text_combined, text_color="#FF69B4") 
        else: 
            res = self.data.get('res', '??p')
            size = self.data.get('size_video', '? MB')
            text_combined = f"Video • {res} • {size} • {duration}"
            self.lbl_info.configure(text=text_combined, text_color="#aaaaaa")

    def load_image_smart(self, url):
        if not url: return
        local_path = os.path.join(THUMB_DIR, f"{hashlib.md5(url.encode()).hexdigest()}.jpg")
        img_loaded = None
        if os.path.exists(local_path):
            try: img_loaded = Image.open(local_path)
            except: pass
        if img_loaded is None:
            try:
                response = requests.get(url, timeout=10, verify=False, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200:
                    img_data = Image.open(BytesIO(response.content))
                    if img_data.mode in ("RGBA", "P"): img_data = img_data.convert("RGB")
                    try: img_data.save(local_path, "JPEG", quality=80)
                    except: pass
                    img_loaded = img_data
            except: pass
        if img_loaded:
            try:
                img_cropped = ImageOps.fit(img_loaded, (75, 45), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                self.pil_image_cache = img_cropped 
                ctk_img = ctk.CTkImage(light_image=img_cropped, dark_image=img_cropped, size=(75, 45))
                self.ctk_image_cache = ctk_img 
                if self.winfo_exists(): self.after(0, lambda: self.update_image_label_safe(ctk_img))
            except: pass
    def update_image_label_safe(self, img):
        try: self.image_label.configure(image=img, text="")
        except: pass


# BASE LAYOUT (FIXED BOX STRUCTURE)
class BaseLayout(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.withdraw()
        self.title(WINDOW_TITLE)
        self.configure(fg_color="#121212") 
        
        w_awal, h_awal = 750, 460 
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (w_awal // 2)
        y = (screen_height // 2) - (h_awal // 2)
        
        self.geometry(f"{w_awal}x{h_awal}+{x}+{y}")
        self.minsize(720, 460) 
        self.resizable(True, True)
        self.install_my_icon(self) 

        self.grid_columnconfigure(0, weight=0, minsize=250) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)    

        self.load_icons()
        self.setup_ui_kiri()
        self.setup_right_ui()
        
        self._resize_job = None
        self._is_frozen = False
        self._last_dims = (0, 0)
        self.bind("<Configure>", self.on_window_configure)

        self.update_idletasks()
        self.deiconify() 

    def load_icons(self):
        if getattr(sys, 'frozen', False):
            icon_dir = os.path.join(getattr(sys, '_MEIPASS', BASE_DIR), "assets", "icons")
        else:
            icon_dir = os.path.join(BASE_DIR, "assets", "icons")
            
        def get_icon(name, size=20):
            path = os.path.join(icon_dir, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
                except: return None
            return None
        
        self.ic_settings = get_icon("settings.png", 22)
        self.ic_notes = get_icon("notes.png", 22)
        self.ic_folder = get_icon("folder.png", 22)
        self.ic_delete = get_icon("delete.png", 16)
        self.ic_clear = get_icon("clear.png", 16)
        self.ic_video = get_icon("video.png", 14)
        self.ic_audio = get_icon("audio.png", 14)
        self.ic_paste = get_icon("paste.png", 16)
        self.ic_search = get_icon("search.png", 16)

    # --- ANTI-LAG: SWAP CONTENT ONLY ---
    def on_window_configure(self, event):
        if event.widget != self: return
        current_dims = (event.width, event.height)
        if self._last_dims == current_dims: return
        self._last_dims = current_dims

        if not self._is_frozen:
            self._is_frozen = True
            self.freeze_view()

        if self._resize_job: self.after_cancel(self._resize_job)
        self._resize_job = self.after(250, self.unfreeze_view)

    def freeze_view(self):
        self.kill_all_drags()
        self.curtain_msg.configure(text="Adjusting View...")
        try: 
            self.curtain_frame.pack(fill="both", expand=True) 
            self.scroll_frame.pack_forget()
        except: pass

    def unfreeze_view(self):
        self.curtain_msg.configure(text="Rendering...")
        self.after(50, self._final_show_list)

    def _final_show_list(self):
        self._is_frozen = False
        try:
            self.update_idletasks() 
            self.scroll_frame.pack(side="top", fill="both", expand=True, padx=3, pady=3) 
            self.curtain_frame.pack_forget()
        except: pass

    def kill_all_drags(self):
        try:
            for widget in self.scroll_frame.winfo_children():
                if isinstance(widget, ThumbnailCard):
                    widget.force_stop_drag()
        except: pass

    # ------------------------------------------------------------------------
    # SETUP LEFT UI
    # ------------------------------------------------------------------------
    def setup_ui_kiri(self):
        self.frame_kiri = ctk.CTkFrame(self, fg_color="transparent", width=250, corner_radius=0)
        self.frame_kiri.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        self.inner_kiri = ctk.CTkFrame(self.frame_kiri, fg_color="transparent")
        self.inner_kiri.pack(fill="both", expand=True, padx=15, pady=15)
        self.frame_kiri.grid_propagate(False); self.frame_kiri.pack_propagate(False)
        
        self.head_kiri = ctk.CTkFrame(self.inner_kiri, fg_color="transparent", height=75)
        self.head_kiri.pack(side="top", fill="x", pady=0)
        self.head_kiri.pack_propagate(False)

        ctk.CTkLabel(self.head_kiri, text=f"◇ {APP_NAME} ◇", font=("Fixedsys", 26), text_color="#db2777").pack(side="top", anchor="w", pady=(2, 0))
        ctk.CTkLabel(self.head_kiri, text="Paste links:", font=("Terminal", 12, "bold"), text_color="#eeeeee").pack(side="bottom", anchor="w", pady=(0, 6))
        
        self.log_box = ctk.CTkTextbox(self.inner_kiri, height=100, fg_color="#1a1a1a", text_color="#00FF00", font=("Terminal", 10), corner_radius=0, border_width=1, border_color="#2c2c2c", scrollbar_button_color="#333333", scrollbar_button_hover_color="#db2777")
        self.log_box.pack(side="bottom", fill="x", pady=(0, 0)) 
        try: self.log_box._scrollbar.configure(width=4)
        except: pass

        frame_btn = ctk.CTkFrame(self.inner_kiri, fg_color="transparent")
        frame_btn.pack(side="bottom", fill="x", pady=(10, 10)) 
        frame_btn.grid_columnconfigure(0, weight=1); frame_btn.grid_columnconfigure(1, weight=1); frame_btn.grid_columnconfigure(2, weight=1)
        
        self.btn_paste = ctk.CTkButton(frame_btn, text="Paste", height=32, fg_color="#2b2b2b", hover_color="#3a3a3a", font=("Terminal", 13), width=50, corner_radius=0)
        self.btn_paste.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_scan = ctk.CTkButton(frame_btn, text="Scan", height=32, font=("Terminal", 13), fg_color="#db2777", hover_color="#be185d", width=50, corner_radius=0)
        self.btn_scan.grid(row=0, column=1, sticky="ew", padx=4)
        self.btn_clear = ctk.CTkButton(frame_btn, text="Clear", height=32, fg_color="#2b2b2b", hover_color="#3a3a3a", font=("Terminal", 13), width=50, corner_radius=0)
        self.btn_clear.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        self.box_link = ctk.CTkTextbox(self.inner_kiri, font=("Consolas", 11), fg_color="#1a1a1a", text_color="#eeeeee", corner_radius=0, border_width=1, border_color="#2c2c2c", scrollbar_button_color="#333333", scrollbar_button_hover_color="#db2777")
        self.box_link.pack(side="top", fill="both", expand=True, pady=(5, 0))
        try: self.box_link._scrollbar.configure(width=4)
        except: pass

    # ------------------------------------------------------------------------
    # SETUP RIGHT UI (UPDATED: RESTORED OLD BUTTON STYLE)
    # ------------------------------------------------------------------------
    def setup_right_ui(self):
        self.frame_kanan = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_kanan.grid(row=0, column=1, sticky="nsew", padx=(0,15), pady=15)
        
        # Header Container
        self.head_kanan = ctk.CTkFrame(self.frame_kanan, fg_color="transparent", height=75) # Slightly increased height to accommodate large buttons
        self.head_kanan.pack(side="top", fill="x", pady=0)
        self.head_kanan.pack_propagate(False) 
        
        # Row 1: Title & Icon Buttons
        row1 = ctk.CTkFrame(self.head_kanan, fg_color="transparent", height=36)
        row1.pack(side="top", fill="x", pady=0)
        ctk.CTkLabel(row1, text="Scan Results", font=("Terminal", 18, "bold"), text_color="#eeeeee").pack(side="left", padx=5, pady=0)
        
        btn_style = {"width": 24, "height": 24, "fg_color": "transparent", "hover_color": "#333333", "text": "", "corner_radius": 0}
        self.btn_settings = ctk.CTkButton(row1, image=self.ic_settings, **btn_style); self.btn_settings.pack(side="right", padx=0)
        self.btn_notes = ctk.CTkButton(row1, image=self.ic_notes, **btn_style); self.btn_notes.pack(side="right", padx=2) 
        self.btn_open_folder = ctk.CTkButton(row1, image=self.ic_folder, state="disabled", **btn_style); self.btn_open_folder.pack(side="right", padx=2)
        
        # Row 2: Options (Select All & Format)
        row2 = ctk.CTkFrame(self.head_kanan, fg_color="transparent", height=40)
        row2.pack(side="bottom", fill="x", pady=(0, 0)) 
        
        self.var_semua = ctk.BooleanVar(value=False)
        self.var_subs = ctk.BooleanVar(value=False)

        # Toggle "Select All" - True Square Style
        self.btn_select_all = ctk.CTkButton(
            row2, text="Select All", width=70, height=24, corner_radius=0,
            font=("Terminal", 11, "bold"), fg_color="#1a1a1a", hover_color="#2b2b2b",
            text_color="#888888", border_width=1, border_color="#555555",
            command=self._update_switch_all
        )
        self.btn_select_all.pack(side="left", padx=(10, 5), pady=0)

        # Toggle "Subs" - True Square Style
        self.btn_subs = ctk.CTkButton(
            row2, text="Subs", width=50, height=24, corner_radius=0,
            font=("Terminal", 11, "bold"), fg_color="#1a1a1a", hover_color="#2b2b2b",
            text_color="#888888", border_width=1, border_color="#555555",
            command=self._update_switch_subs
        )
        self.btn_subs.pack(side="left", padx=5, pady=0)

        self.var_format = ctk.StringVar(value="Video") 
        
        # Video/Audio Toggle Buttons (like settings style)
        f_format = ctk.CTkFrame(row2, fg_color="transparent")
        f_format.pack(side="right", padx=10)
        
        self.btn_format_video = ctk.CTkButton(
            f_format, text="Video", width=70, height=28, corner_radius=0,
            font=("Terminal", 11, "bold"), fg_color="#db2777", hover_color="#be185d",
            command=lambda: self._set_format("Video")
        )
        self.btn_format_video.pack(side="left", padx=(0, 1))
        
        self.btn_format_audio = ctk.CTkButton(
            f_format, text="Audio", width=70, height=28, corner_radius=0,
            font=("Terminal", 11, "bold"), fg_color="#2b2b2b", hover_color="#3a3a3a",
            command=lambda: self._set_format("Audio")
        )
        self.btn_format_audio.pack(side="left")
        
        # Footer & List (Same as before, with cleaned spacing)
        frame_dl = ctk.CTkFrame(self.frame_kanan, fg_color="transparent", height=50) 
        frame_dl.pack(side="bottom", fill="x", padx=0, pady=(5, 0)) 
        frame_dl.grid_columnconfigure(0, weight=1); frame_dl.grid_columnconfigure(1, weight=0); frame_dl.grid_columnconfigure(2, weight=0)
        
        frame_info = ctk.CTkFrame(frame_dl, fg_color="transparent")
        frame_info.grid(row=0, column=0, sticky="sew", padx=(10, 10), pady=0)
        
        self.lbl_status_text = ctk.CTkLabel(frame_info, text="Ready.", font=("Terminal", 11), text_color="#aaaaaa", anchor="w")
        self.lbl_status_text.pack(side="top", fill="x", anchor="w", pady=(0, 2))
        
        self.progress_bar = ctk.CTkProgressBar(frame_info, height=8, progress_color="#db2777", fg_color="#1a1a1a", corner_radius=0)
        self.progress_bar.set(0)
        self.progress_bar.pack(side="bottom", fill="x", pady=0)
        
        self.btn_download = ctk.CTkButton(frame_dl, text="Download", width=120, height=32, font=("Terminal", 13), fg_color="#db2777", hover_color="#be185d", state="disabled", corner_radius=0)
        self.btn_download.grid(row=0, column=1, sticky="s", padx=(0, 5), pady=0)
        self.btn_clean_list = ctk.CTkButton(frame_dl, text="Clear", width=70, height=32, font=("Terminal", 13), fg_color="#2b2b2b", hover_color="#3a3a3a", corner_radius=0)
        self.btn_clean_list.grid(row=0, column=2, sticky="s", padx=(0, 0), pady=0)

        # [RESULTS BOX]
        self.box_results = ctk.CTkFrame(self.frame_kanan, fg_color="#1a1a1a", corner_radius=0, border_width=1, border_color="#2c2c2c")
        self.box_results.pack(side="top", fill="both", expand=True, pady=(5, 0)) 

        # [LIST]
        self.scroll_frame = ctk.CTkScrollableFrame(self.box_results, label_text=None, fg_color="transparent", scrollbar_button_color="#333333", scrollbar_button_hover_color="#db2777", corner_radius=0) 
        self.scroll_frame.pack(side="top", fill="both", expand=True, padx=3, pady=3)
        try:
            if hasattr(self.scroll_frame, "_scrollbar"):
                self.scroll_frame._scrollbar.configure(width=10)
        except: pass
        
        # [CURTAIN]
        self.curtain_frame = ctk.CTkFrame(self.box_results, fg_color="#1a1a1a", corner_radius=0)
        self.curtain_msg = ctk.CTkLabel(self.curtain_frame, text="Adjusting View...", font=("Terminal", 12), text_color="#888888")
        self.curtain_msg.place(relx=0.5, rely=0.5, anchor="center")
        
    def _update_switch_all(self):
        self.var_semua.set(not self.var_semua.get())
        if self.var_semua.get():
            self.btn_select_all.configure(fg_color="#db2777", hover_color="#be185d", text_color="#ffffff", border_color="#db2777")
        else:
            self.btn_select_all.configure(fg_color="#1a1a1a", hover_color="#2b2b2b", text_color="#888888", border_color="#555555")

    def _update_switch_subs(self):
        self.var_subs.set(not self.var_subs.get())
        if self.var_subs.get():
            self.btn_subs.configure(fg_color="#db2777", hover_color="#be185d", text_color="#ffffff", border_color="#db2777")
        else:
            self.btn_subs.configure(fg_color="#1a1a1a", hover_color="#2b2b2b", text_color="#888888", border_color="#555555")

    def _set_format(self, value):
        self.var_format.set(value)
        if value == "Video":
            self.btn_format_video.configure(fg_color="#db2777", hover_color="#be185d")
            self.btn_format_audio.configure(fg_color="#2b2b2b", hover_color="#3a3a3a")
        else:
            self.btn_format_video.configure(fg_color="#2b2b2b", hover_color="#3a3a3a")
            self.btn_format_audio.configure(fg_color="#db2777", hover_color="#be185d")
        # Trigger format change callback if connected
        try: self.action_change_size_display(value)
        except: pass
        
    def install_my_icon(self, win):
        def run():
            try:
                ico = utils.get_icon_path()
                if ico and os.path.exists(ico): win.iconbitmap(ico)
            except: pass
        win.after(300, run)