import sys
import os
import threading
import json
import logging
import ctypes 
from concurrent.futures import ThreadPoolExecutor

# PATH CONFIGURATION

# 1. Set Root Directory
if getattr(sys, 'frozen', False):
    # [EXE MODE] Root is the location of the .exe file
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    # [SCRIPT MODE] Root is the parent directory of this package
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Removed old source paths since xidown is now a package

# 3. Define BASE_DIR
BASE_DIR = ROOT_DIR

sys.path.insert(0, ROOT_DIR)

# IMPORTS
import customtkinter as ctk
from flask import Flask, request, jsonify
from flask_cors import CORS

from xidown.gui.window import BaseLayout, ThumbnailCard, RightClickMenu 
from xidown.gui import settings
from xidown.gui.dialogs.exit import ExitWindow
from xidown.gui import notes 

from xidown.core import utils
from xidown.core import downloader
from xidown.core import playlist
from xidown.core import scanner
from xidown.core.version import WINDOW_TITLE, APP_NAME

# CONSTANTS & SETUP
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

THUMB_DIR = os.path.join(DATA_DIR, "thumbs")
if not os.path.exists(THUMB_DIR): os.makedirs(THUMB_DIR)

HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# LOCAL SERVER
class MaribelServer:
    def __init__(self, gui_instance):
        self.app = Flask(__name__)
        CORS(self.app)
        self.gui = gui_instance
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        @self.app.route('/download', methods=['POST'])
        def receive_url():
            try:
                data = request.json
                url = data.get('url')
                filename = data.get('filename') 
                headers = data.get('headers')

                if url:
                    print(f"[Server] Received URL: {url}")
                    self.gui.after(0, lambda: self.gui.receive_link_from_ext(url, filename, headers))
                    return jsonify({"status": "success", "message": "Link & Identity received!"})
                return jsonify({"status": "error", "message": "Empty URL"})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)})

        @self.app.route('/update_cookies', methods=['POST'])
        def receive_cookies():
            try:
                data = request.json
                content = data.get('content')
                raw_domain = data.get('domain', 'unknown')
                clean_domain = raw_domain.replace("www.", "").replace(".", "_")
                nama_file = f"cookies_{clean_domain}.txt"

                if content:
                    cookie_file_path = os.path.join(DATA_DIR, nama_file)
                    with open(cookie_file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    current_conf = settings.load_config()
                    current_conf['cookie_path'] = cookie_file_path
                    settings.save_config(current_conf)

                    self.gui.after(0, lambda: self.gui.write_log(f"Cookies Synced: {clean_domain}"))
                    self.gui.after(0, lambda: self.gui.update_dashboard(f"Cookies updated: {clean_domain}", 0))
                    return jsonify({"status": "success", "message": f"Cookies {clean_domain} saved!"})
                return jsonify({"status": "error", "message": "Empty Data"})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)})

    def run(self):
        self.app.run(port=3000, use_reloader=False)


# MAIN APPLICATION
class CyreneApp(BaseLayout): 
    def __init__(self):
        super().__init__() 
        
        self.withdraw()
        self.attributes("-alpha", 0.0)
        self.title(WINDOW_TITLE) 
        self.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.show_loading_screen()

        # --- Init Logic ---
        self.tools = utils.check_setup()
        self.settings_window = None 
        self.exit_window = None 
        self.notes_window = None 
        
        self.is_scanning = False 
        self.is_downloading = False 
        self.stop_event_scan = threading.Event()      
        self.stop_event_download = threading.Event()  
        
        self.scan_data = [] 
        self.custom_save_path = ""
        self.widget_list = [] 
        self.result_folder_terakhir = ""
        self.url_meta_cache = {} 
        self.log_filter_cache = {} 
        
        self.undo_stack = []
        self.redo_stack = []

        # --- Bind UI Actions ---
        self.btn_scan.configure(command=self.action_scan)
        self.btn_download.configure(command=self.start_download)
        self.btn_paste.configure(command=self.action_smart_paste)
        self.btn_clear.configure(command=self.clear_input)
        
        self.btn_open_folder.configure(state="normal", command=self.open_folder)
        
        self.btn_settings.configure(command=self.open_settings_popup)
        self.btn_notes.configure(command=self.open_notes_popup) 
        self.btn_clean_list.configure(command=self.action_clear_results)
        
        self.btn_back.configure(command=self.action_back)
        self.btn_forward.configure(command=self.action_forward)
        
        self.btn_select_all.configure(command=self.action_toggle_all)
        try: 
            self.btn_select_all.bind("<Button-3>", self.open_batch_menu)
            self.btn_select_all.bind("<Button-2>", self.open_batch_menu)
        except Exception as e: print(f"Error: {e}")

        # Removed seg_format binding because we replaced it with toggle buttonsup ---
        self.reload_initial_config()
        self.load_last_memory()

        self.var_format.set("Video") 
        self.action_change_size_display("Video") 

        self.server_thread = threading.Thread(target=self.start_maribel_server, daemon=True)
        self.server_thread.start()

        if not self.tools: 
            self.update_dashboard("ERROR: Tools missing! Check bin folder.", 0)
            self.btn_scan.configure(state="disabled")
            self.btn_download.configure(state="disabled")
            self.after(1000, self.prompt_binaries_download)
        else: 
            if self.scan_data:
                self.update_dashboard(f"Ready. {len(self.scan_data)} videos loaded.", 0)
            else:
                self.update_dashboard("System Ready.", 0)

    # UI COMPONENTS 
    def show_loading_screen(self):
        splash = ctk.CTkToplevel(self)
        w_splash, h_splash = 250, 280 
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        x_pos = (screen_width // 2) - (w_splash // 2)
        y_pos = (screen_height // 2) - (h_splash // 2)
        
        splash.geometry(f"{w_splash}x{h_splash}+{x_pos}+{y_pos}")
        splash.overrideredirect(True) 
        splash.attributes("-topmost", True)
        
        transparent_color = "#000001"
        splash.configure(fg_color=transparent_color)
        import sys
        if sys.platform == 'win32':
            try: splash.attributes("-transparentcolor", transparent_color)
            except Exception as e: print(f"Error: {e}")

        # Premium rounded border for splash screen
        card_frame = ctk.CTkFrame(splash, fg_color="#121212", corner_radius=0, border_width=1, border_color="#333333")
        card_frame.pack(fill="both", expand=True, padx=2, pady=2)

        frame_pusat = ctk.CTkFrame(card_frame, fg_color="transparent")
        frame_pusat.pack(expand=True, fill="both", padx=15, pady=20)

        try:
            from PIL import Image
            ico_path = utils.get_icon_path()

            if ico_path and os.path.exists(ico_path):
                img_asli = Image.open(ico_path)
                img_logo = ctk.CTkImage(light_image=img_asli, dark_image=img_asli, size=(90, 90))
                lbl_logo = ctk.CTkLabel(frame_pusat, text="", image=img_logo)
                lbl_logo.pack(pady=(5, 10)) 
            else:
                ctk.CTkLabel(frame_pusat, text="♢", font=("Terminal", 60), text_color="#db2777").pack(pady=(5, 10))
        except Exception as e: print(f"Error: {e}")

        ctk.CTkLabel(frame_pusat, text=APP_NAME, font=("Terminal", 22, "bold"), text_color="#db2777").pack(pady=(0, 2))
        lbl_status = ctk.CTkLabel(frame_pusat, text="Initializing...", font=("Terminal", 10, "italic"), text_color="#888888")
        lbl_status.pack(pady=(0, 15)) 

        progress_loading = ctk.CTkProgressBar(frame_pusat, width=180, height=4, corner_radius=0, progress_color="#db2777", fg_color="#2b2b2b")
        progress_loading.pack()
        progress_loading.set(0)

        def run_loading(value=0):
            if value <= 1.0:
                progress_loading.set(value)
                if value < 0.99: lbl_status.configure(text="Loading xidown...")
                else: lbl_status.configure(text="Ready!")
                splash.after(15, lambda: run_loading(value + 0.01)) 
            else:
                self.deiconify()
                self.update() 
                splash.destroy()
                self.attributes("-alpha", 1.0) 
                self.install_my_icon(self)

        splash.after(200, lambda: run_loading(0))
    
    def setup_right_ui(self):
        super().setup_right_ui()
        try:
            row1 = self.head_kanan.winfo_children()[0]
            btn_style = {"width": 28, "height": 24, "fg_color": "transparent", "hover_color": "#333333", "font": ("Segoe UI Emoji", 16), "text_color": "#e0e0e0", "corner_radius": 0}
            self.btn_forward = ctk.CTkButton(row1, text="↷", state="disabled", **btn_style)
            self.btn_forward.pack(side="right", padx=0)
            self.btn_back = ctk.CTkButton(row1, text="↶", state="disabled", **btn_style)
            self.btn_back.pack(side="right", padx=0)
        except Exception as e:
            print(f"UI Injection Error: {e}")

        # LOGIC FUNCTIONS
        
    def start_maribel_server(self):
        server = MaribelServer(self)
        try:
            print("[System] Activating Maribel Portal (Port 3000)...")
            server.run()
        except Exception as e:
            print(f"[System] Server start failed: {e}")

    def receive_link_from_ext(self, url, filename=None, headers=None):
        current_text = self.box_link.get("0.0", "end").strip()
        if filename: filename = filename.replace("_哔哩哔哩_bilibili", "")

        if filename or headers:
            self.url_meta_cache[url] = {
                'title': filename,
                'headers': headers
            }
            
        if url in current_text:
            self.update_dashboard("Link updated in cache!", 0)
        else:
            if current_text: self.box_link.insert("end", "\n" + url)
            else: self.box_link.insert("0.0", url)    
            self.update_dashboard("Incoming Link Detected!", 0)
            
            log_msg = f"Received: {filename[:30]}..." if filename else f"Received: {url}"
            self.write_log(log_msg)
            
            self.deiconify()
            self.lift()
            
            if not self.is_scanning: 
                playlist.check_playlist_and_ask(
                    parent=self, 
                    links=[url],  
                    callback_continue=lambda: self.continue_scan([url]), 
                    callback_cancel=lambda: (self.update_dashboard("Scan cancelled.", 0), self.write_log("Cancelled."))
                )

    def action_scan(self):
        if not self.tools: return self.update_dashboard("ERROR: Tools missing!", 0)
        
        if self.is_scanning:
            self.stop_event_scan.set() 
            self.btn_scan.configure(text="Wait...", state="disabled") 
            return
        
        raw_text = self.box_link.get("0.0", "end").strip()
        if not raw_text: return self.update_dashboard("Empty Link!", 0)
        links = [L.strip() for L in raw_text.split('\n') if L.strip()]
        if not links: return

        playlist.check_playlist_and_ask(
            parent=self, links=links, 
            callback_continue=lambda: self.continue_scan(links),
            callback_cancel=lambda: (self.update_dashboard("Playlist scan cancelled.", 0), self.write_log("Cancelled by user."))
        )

    def continue_scan(self, links):
        self.is_scanning = True 
        self.stop_event_scan.clear() 
        self.btn_scan.configure(text="Stop", fg_color="#FF3333", hover_color="#CC0000")
        self.var_semua.set(False)
        self.update_dashboard("Initializing Scan...", 0.05)
        
        threading.Thread(target=self.thread_scan_wrapper, args=(links,), daemon=True).start()

    def thread_scan_wrapper(self, links):
        if not self.tools:
            self.after(0, lambda: self.write_log("Scan error: yt-dlp or ffmpeg is missing."))
            self.after(0, lambda: self.update_dashboard("ERROR: Tools missing! Scan aborted.", 0))
            self.after(0, lambda: self.btn_scan.configure(text="Scan", fg_color="#db2777", hover_color="#be185d", state="disabled"))
            self.is_scanning = False
            return

        cfg = settings.load_config()
        tools_updated = (self.tools[0], self.tools[1], cfg.get("cookie_path", ""))

        scanner.run_scan(
            links=links,
            tools=tools_updated, 
            data_dir=DATA_DIR, 
            scan_data=self.scan_data,
            stop_event=self.stop_event_scan, 
            meta_cache=self.url_meta_cache, 
            callback_log=lambda t: self.after(0, lambda: self.write_log(t)),
            callback_progress=lambda t, v: self.after(0, lambda: self.update_dashboard(t, v)),
            callback_item_found=lambda item: (self.scan_data.append(item), self.after(0, lambda: self.add_one_widget(item))),
            callback_done=lambda count: self.after(0, lambda: self.finish_scan_gui(count))
        )

    def finish_scan_gui(self, count):
        self.is_scanning = False
        self.btn_scan.configure(text="Scan", fg_color="#db2777", hover_color="#be185d", state="normal")
        
        if self.scan_data:
            self.save_last_memory() 
            if not self.is_downloading:
                self.update_dashboard(f"Scan Done! {len(self.scan_data)} items.", 1.0)
                self.btn_download.configure(state="normal")
        else:
            if not self.is_downloading:
                self.update_dashboard("Done/Stop. 0 new videos.", 0)
                
        if count == 0 and not self.stop_event_scan.is_set():
            self.write_log("⚠️ 0 results! Check TERMINAL to enter Cookies.")
            threading.Thread(target=self.prompt_cookie_terminal, daemon=True).start()

    def prompt_cookie_terminal(self):
        print("\n" + "="*50)
        print(">>> WARNING: Scan results are empty or failed!")
        print(">>> The video might require a login or the cookies are invalid.")
        print(">>> Please enter the Cookies format (Netscape) or Cookies File Path.")
        print(">>> Press ENTER to skip.")
        cookie_val = input(">>> Enter Cookies (Path/String): ").strip()
        if cookie_val:
            config = settings.load_config()
            if os.path.exists(cookie_val):
                config["cookie_path"] = cookie_val
                settings.save_config(config)
                print(f">>> Cookie path saved: {cookie_val}")
                self.after(0, lambda: self.write_log("Cookie path updated via terminal!"))
            else:
                custom_path = os.path.join(DATA_DIR, "custom_terminal_cookies.txt")
                with open(custom_path, "w", encoding="utf-8") as f:
                    f.write(cookie_val)
                config["cookie_path"] = custom_path
                settings.save_config(config)
                print(f">>> Cookie string saved to: {custom_path}")
                self.after(0, lambda: self.write_log("Cookie string saved via terminal!"))
        print("="*50 + "\n")

    # --- Widget & List Management ---
    def add_one_widget(self, data_item):
        current_format_mode = "mp3" if "🎵" in self.var_format.get() else "mp4"
        card = ThumbnailCard(
            self.scroll_frame, 
            data_item, 
            self.action_delete_one_item, 
            callback_toggle=self.aksi_cek_seleksi_manual,
            callback_reorder=self.action_swap_position,
            callback_lock=self.action_on_pin_change,
            callback_test=self.action_test_play,
            callback_download_satu=self.action_download_one_item
        )
        card.set_size_display(current_format_mode)
        
        if 'last_status' in data_item:
            status_text = data_item['last_status']
            color = "#aaaaaa" 
            if "100%" in status_text or "Done" in status_text: color = "#db2777" 
            elif "Error" in status_text: color = "#ff5555" 
            elif "Paused" in status_text or "Stopped" in status_text: color = "#ffb86c" 
            elif "%" in status_text: color = "#ffffff" 
            
            card.set_download_status(status_text, color)

        self.widget_list.append(card)
        self.aksi_cek_seleksi_manual()
        
        if len(self.scan_data) > 0 and not self.is_downloading:
            self.btn_download.configure(state="normal")

    def action_swap_position(self, widget_a, widget_b):
        try:
            status_a = widget_a.data.get('locked', False)
            status_b = widget_b.data.get('locked', False)
            if status_a != status_b: return 

            idx_a = self.widget_list.index(widget_a)
            idx_b = self.widget_list.index(widget_b)
            if idx_a == idx_b: return

            self.widget_list[idx_a], self.widget_list[idx_b] = self.widget_list[idx_b], self.widget_list[idx_a]
            
            data_a = widget_a.data
            data_b = widget_b.data
            
            real_idx_a = self.scan_data.index(data_a)
            real_idx_b = self.scan_data.index(data_b)
            self.scan_data[real_idx_a], self.scan_data[real_idx_b] = self.scan_data[real_idx_b], self.scan_data[real_idx_a]
            
            if idx_a < idx_b: widget_a.pack(after=widget_b)
            else: widget_a.pack(before=widget_b)
            
            self.save_last_memory()
                
        except ValueError: pass

    def action_on_pin_change(self, widget_yg_diklik=None):
        self.scan_data.sort(key=lambda x: x.get('locked', False), reverse=True)
        widget_map = {w.data['url_dl']: w for w in self.widget_list} 
        self.widget_list = []
        for item_data in self.scan_data:
            w = widget_map.get(item_data['url_dl'])
            if w:
                self.widget_list.append(w)
                w.pack_forget()
                w.pack(pady=2, padx=5, fill="x")
        self.save_last_memory()

    def hide_folder(self, path):
        try:
            if os.name == 'nt' and os.path.exists(path):
                ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)
        except Exception as e:
            print(f"[System] Failed to hide folder: {e}")

    def action_test_play(self, item_data):
        threading.Thread(target=self.run_test_play, args=(item_data,), daemon=True).start()

    def run_test_play(self, item_data):
        if not self.tools:
            self.after(0, lambda: self.update_dashboard("ERROR: Tools missing! Preview aborted.", 0))
            return

        url = item_data.get('url_dl')
        title_asli = item_data.get('title', 'video_test')
        
        self.after(0, lambda: self.update_dashboard("Preparing Preview...", 0.1))
        self.after(0, lambda: self.write_log(f"Test Play: {title_asli[:30]}..."))

        config = settings.load_config()
        yt_dlp_p = self.tools[0]
        ffmpeg_p = self.tools[1]
        cookie_path_global = config.get("cookie_path", "")
        
        domain_detect = "unknown"
        if "facebook.com" in url: domain_detect = "facebook_com"
        elif "bilibili.com" in url: domain_detect = "bilibili_com"
        elif "tiktok.com" in url: domain_detect = "tiktok_com"
        elif "youtube.com" in url: domain_detect = "youtube_com"
        elif "x.com" in url or "twitter.com" in url: domain_detect = "x_com"
        
        specific_cookie = os.path.join(DATA_DIR, f"cookies_{domain_detect}.txt")
        if os.path.exists(specific_cookie): used_cookie = specific_cookie
        else: used_cookie = cookie_path_global

        folder_preview = os.path.join(DATA_DIR, "preview_cache")
        if not os.path.exists(folder_preview): 
            os.makedirs(folder_preview)
            self.hide_folder(folder_preview) 
        
        tools_utk_ini = (yt_dlp_p, ffmpeg_p, used_cookie)
        stop_dummy = threading.Event()
        
        import time
        unique_id = int(time.time())
        preview_filename = f"preview_{unique_id}" 

        downloader.run(
            url, folder_preview, False, None, tools_utk_ini, "mp4", None, None, stop_dummy, 
            config.get("proxy"), "medium", ('00:00:00', '00:00:15'), 'timpa', part_count=4, custom_title=preview_filename 
        )
        
        target_file = None
        try:
            for f in os.listdir(folder_preview):
                if f.startswith(preview_filename):
                    target_file = os.path.join(folder_preview, f)
                    break
        except Exception as e: print(f"Error: {e}")
        
        if target_file and os.path.exists(target_file):
            if os.path.getsize(target_file) < 1024:
                self.after(0, lambda: self.update_dashboard("Preview Failed (Empty File).", 0))
                self.after(0, lambda: self.write_log("Error: File is empty (DRM?)."))
                return
            self.after(0, lambda: self.update_dashboard("Opening Preview...", 1.0))
            self.after(0, lambda: self.write_log("Opening Player..."))
            try: os.startfile(target_file)
            except Exception as e: self.after(0, lambda: self.write_log(f"Error opening player: {e}"))
        else:
            self.after(0, lambda: self.update_dashboard("Preview Failed/DRM Protected.", 0))
            self.after(0, lambda: self.write_log("Failed to download preview."))

    def open_batch_menu(self, event):
        selected_count = sum(1 for d in self.scan_data if d.get('selected', False))
        if selected_count == 0:
            self.update_dashboard("No items selected for batch action.", 0)
            return
        menu_items = [
            (f"Pin Selected ({selected_count})", lambda: self.action_batch_lock(True), False),
            (f"Unpin Selected ({selected_count})", lambda: self.action_batch_lock(False), False),
            (f"Delete Selected ({selected_count})", self.action_batch_delete, True)
        ]
        RightClickMenu(self, (event.x_root, event.y_root), {'menu_list': menu_items}, mode="batch")

    def action_batch_lock(self, status_lock):
        changed = False
        for d in self.scan_data:
            if d.get('selected', False):
                if d.get('locked', False) != status_lock:
                    d['locked'] = status_lock
                    changed = True
        if changed:
            for w in self.widget_list: w.update_visual_data()
            self.action_on_pin_change()
            self.update_dashboard(f"Batch {'Pin' if status_lock else 'Unpin'} done.", 0)
        else:
            self.update_dashboard("No changes made.", 0)

    def action_batch_delete(self):
        if self.is_downloading: 
            self.update_dashboard("Cannot delete while downloading!", 0)
            return
        
        didelete_batch = [d for d in self.scan_data if d.get('selected', False)]
        if not didelete_batch: return

        self.undo_stack.append({'type': 'batch', 'data': didelete_batch})
        self.redo_stack.clear()
        
        remaining_data = [d for d in self.scan_data if not d.get('selected', False)]
        self.scan_data = remaining_data
        
        for w in self.widget_list: w.destroy()
        self.widget_list = []
        for data in self.scan_data: self.add_one_widget(data)
        
        self.save_last_memory()
        self.update_history_buttons()
        self.update_dashboard(f"Batch delete: {len(didelete_batch)} removed.", 0)
        self.var_semua.set(False)

        if not self.scan_data:
            self.btn_download.configure(state="disabled")

    def update_history_buttons(self):
        state_undo = "normal" if self.undo_stack else "disabled"
        state_redo = "normal" if self.redo_stack else "disabled"
        if hasattr(self, 'btn_back'): self.btn_back.configure(state=state_undo)
        if hasattr(self, 'btn_forward'): self.btn_forward.configure(state=state_redo)

    def action_delete_one_item(self, widget_target, is_redo=False):
        if getattr(self, 'is_downloading', False):
            self.write_log("Cannot delete items while downloading.")
            return

        if not is_redo: self.redo_stack.clear()
        
        if widget_target.data in self.scan_data:
            self.undo_stack.append({'type': 'single', 'data': widget_target.data})
            self.scan_data.remove(widget_target.data)
        
        widget_target.destroy()
        if widget_target in self.widget_list: self.widget_list.remove(widget_target)
        
        self.save_last_memory() 
        self.update_history_buttons()

        if not self.scan_data:
            self.btn_download.configure(state="disabled")
            self.update_dashboard("Removed.", 0)
        else: 
            self.update_dashboard("Item removed.", 0)
        self.aksi_cek_seleksi_manual()

    def action_clear_results(self):
        if self.is_downloading: return 
        
        yang_deleted = [d for d in self.scan_data if not d.get('locked', False)]
        if not yang_deleted: return 

        self.undo_stack.append({'type': 'batch', 'data': yang_deleted})
        self.redo_stack.clear() 

        data_sisa = [d for d in self.scan_data if d.get('locked', False)]
        for widget in self.widget_list: widget.destroy()
        self.widget_list = []
        self.scan_data = data_sisa
        for data in self.scan_data: self.add_one_widget(data)
        
        self.save_last_memory()
        self.update_history_buttons()

        if not self.scan_data:
            self.btn_download.configure(state="disabled")
            self.update_dashboard("List cleared.", 0)
        else:
            self.btn_download.configure(state="normal")
            self.update_dashboard(f"List cleared. {len(self.scan_data)} locked.", 0)
        self.aksi_cek_seleksi_manual()

    def action_back(self): 
        if not self.undo_stack: return
        action = self.undo_stack.pop()
        self.redo_stack.append(action) 
        if action['type'] == 'single':
            item = action['data']
            self.scan_data.append(item)
            self.add_one_widget(item)
            msg = "Undo: Item restored."
        elif action['type'] == 'batch':
            items = action['data']
            for item in items:
                self.scan_data.append(item)
                self.add_one_widget(item)
            msg = f"Undo: {len(items)} items restored."
        self.save_last_memory()
        self.update_history_buttons()
        self.update_dashboard(msg, 0)

    def action_forward(self): 
        if not self.redo_stack: return
        action = self.redo_stack.pop()
        self.undo_stack.append(action) 
        items_to_remove = []
        if action['type'] == 'single':
            items_to_remove = [action['data']]
            msg = "Redo: Item deleted."
        elif action['type'] == 'batch':
            items_to_remove = action['data']
            msg = f"Redo: {len(items_to_remove)} items deleted."
        for item in items_to_remove:
            if item in self.scan_data: 
                self.scan_data.remove(item)
                for w in list(self.widget_list):
                    if w.data == item:
                        w.destroy()
                        if w in self.widget_list: self.widget_list.remove(w)
                        break
        self.save_last_memory()
        self.update_history_buttons()
        self.update_dashboard(msg, 0)
        if not self.scan_data: self.btn_download.configure(state="disabled")
    
    # --- Download Logic ---
    def check_subtitle_then_continue(self, items, callback):
        if self.var_subs.get():
            subs_dict = {}
            for item in items:
                item_subs = item.get('subs', {})
                for code, name in item_subs.items():
                    if code not in subs_dict:
                        subs_dict[code] = name
            
            if len(items) == 1:
                title = items[0].get('title', 'Unknown Video')
                if len(title) > 35: title = title[:32] + "..."
                title_context = f"For: {title}"
            else:
                title_context = f"For {len(items)} selected videos"
                
            self.show_subs_popup(subs_dict, callback, title_context)
        else:
            callback(None)

    def show_subs_popup(self, subs_dict, callback, title_context):
        self.curtain_frame.place_forget()
        from xidown.gui.dialogs.subtitle import SubtitlePopup
        self.subs_popup = SubtitlePopup(self, subs_dict, on_confirm=callback, on_cancel=lambda: None, title_context=title_context)

    def start_download(self):
        selected_items = [d for d in self.scan_data if d.get('selected', False)]
        if not selected_items: return self.update_dashboard("Select video first!", 0)
        
        valid_items = []
        for d in selected_items:
            st = str(d.get('last_status') or '')
            if "Done" not in st and "100%" not in st:
                valid_items.append(d)
                
        if not valid_items: return self.update_dashboard("Selected items already downloaded.", 0)
        
        self.check_subtitle_then_continue(valid_items, lambda subs: self.continue_download(valid_items, subs))

    def continue_download(self, selected_items, sub_langs):
        self.stop_event_download.clear()
        self.log_filter_cache.clear()
        
        for item in selected_items:
            item['last_status'] = "Waiting..."
            self.after(0, lambda u=item['url_dl']: self.send_status_to_card(u, "Waiting...", 0))

        chosen_format = "mp3" if "🎵" in self.var_format.get() else "mp4"
        config = settings.load_config()
        
        thread_count = config.get("threads", 2)       
        parallel_count = config.get("parallel_count", 1) 
        cookie_path_global = config.get("cookie_path", "")
        self.custom_save_path = config.get("save_path", "")
        if config.get("use_default_path", True): self.custom_save_path = ""
        
        self.btn_clean_list.configure(state="disabled")
        self.btn_download.configure(text="CANCEL", fg_color="#FF3333", hover_color="#CC0000", command=self.action_cancel_download)
        self.btn_open_folder.configure(state="normal", fg_color="transparent") 
        
        self.is_downloading = True
        
        threading.Thread(
            target=self.real_download_process, 
            args=(selected_items, chosen_format, config.get("proxy"), config.get("quality"), thread_count, parallel_count, cookie_path_global, sub_langs), 
            daemon=True
        ).start()

    def action_download_one_item(self, widget_target):
        item_data = widget_target.data
        status = str(item_data.get('last_status') or '')
        if "Done" in status or "100%" in status:
            self.update_dashboard("Item already downloaded.", 0)
            return
        self.check_subtitle_then_continue([item_data], lambda subs: self.continue_download_satu_item(item_data, subs))

    def continue_download_satu_item(self, item_data, sub_langs):
        item_data['last_status'] = "Waiting..."
        self.send_status_to_card(item_data['url_dl'], "Waiting...", 0)
        
        single_list = [item_data]
        
        chosen_format = "mp3" if "🎵" in self.var_format.get() else "mp4"
        config = settings.load_config()
        thread_count = config.get("threads", 2)       
        parallel_count = 1 
        cookie_path_global = config.get("cookie_path", "")
        self.custom_save_path = config.get("save_path", "")
        if config.get("use_default_path", True): self.custom_save_path = ""
        
        if not self.is_downloading:
            self.btn_clean_list.configure(state="disabled")
            self.btn_download.configure(text="CANCEL", fg_color="#FF3333", hover_color="#CC0000", command=self.action_cancel_download)
            self.btn_open_folder.configure(state="normal", fg_color="transparent")
        
        self.is_downloading = True
        self.stop_event_download.clear()
        
        threading.Thread(
            target=self.real_download_process, 
            args=(single_list, chosen_format, config.get("proxy"), config.get("quality"), thread_count, parallel_count, cookie_path_global, sub_langs), 
            daemon=True
        ).start()

    def action_cancel_download(self):
        if self.is_downloading:
            self.stop_event_download.set() 
            self.btn_download.configure(text="Cancelling...", state="disabled")

    def real_download_process(self, list_data, format_type, proxy_string, quality_mode, thread_count, parallel_count, cookie_path_global, sub_langs=None):
        from datetime import datetime
        
        if self.custom_save_path and os.path.exists(self.custom_save_path):
            result_folder = self.custom_save_path
        else:
            folder_bulan = f"{datetime.now().year}_{datetime.now().month:02d}"
            result_folder = os.path.join(DATA_DIR, folder_bulan)
        
        result_folder = os.path.abspath(result_folder)
        
        if not os.path.exists(result_folder): os.makedirs(result_folder)
        self.result_folder_terakhir = result_folder
        cancelled = False
        
        if not self.tools:
            self.after(0, lambda: self.update_dashboard("ERROR: Tools missing! Download aborted.", 0))
            self.is_downloading = False
            return

        yt_dlp_p = self.tools[0]
        ffmpeg_p = self.tools[1]

        total_files = len(list_data)
        self.progress_tracker = {item['url_dl']: 0.0 for item in list_data}
        self.progress_lock = threading.Lock() 

        def progress_manager(url_key, progress_val, text_status):
            if self.stop_event_download.is_set(): return
            with self.progress_lock:
                self.progress_tracker[url_key] = progress_val
                total_progress = sum(self.progress_tracker.values()) / total_files
            
            if total_files == 1:
                self.after(0, lambda: self.update_dashboard(f"Downloading {int(total_progress)}%...", total_progress/100))
            else:
                self.after(0, lambda: self.update_dashboard(f"Batch Processing ({int(total_progress)}%) - {len(list_data)} Files", total_progress/100))

            status_lengkap = f"{int(progress_val)}% - {text_status}"
            for item in list_data:
                if item['url_dl'] == url_key:
                    item['last_status'] = status_lengkap
                    break
            self.after(0, lambda: self.send_status_to_card(url_key, status_lengkap, progress_val))

        def worker_tugas(item):
            if self.stop_event_download.is_set(): return
            url = item['url_dl']
            title_fixed = item['title']
            
            self.after(0, lambda: self.write_log(f"Started: {title_fixed[:40]}..."))
            self.after(0, lambda: self.send_status_to_card(url, "Starting...", 0, color="#ffffff"))
            
            def cb_wrapper(prog_val, prog_text):
                progress_manager(url, prog_val, prog_text)

            used_cookie = cookie_path_global
            
            domain_detect = "unknown"
            if "facebook.com" in url: domain_detect = "facebook_com"
            elif "bilibili.com" in url: domain_detect = "bilibili_com"
            elif "tiktok.com" in url: domain_detect = "tiktok_com"
            elif "youtube.com" in url: domain_detect = "youtube_com"
            
            specific_cookie = os.path.join(DATA_DIR, f"cookies_{domain_detect}.txt")
            if os.path.exists(specific_cookie): used_cookie = specific_cookie
            tools_utk_ini = (yt_dlp_p, ffmpeg_p, used_cookie)
            
            try:
                downloader.run(
                    url, result_folder, False, None, tools_utk_ini, format_type, None, 
                    cb_wrapper, self.stop_event_download, proxy_string, quality_mode, None, 'abaikan', 
                    part_count=thread_count, custom_title=title_fixed, sub_langs=sub_langs 
                )
                if not self.stop_event_download.is_set():
                    progress_manager(url, 100.0, "Done.")
                    self.after(0, lambda: self.write_log(f"Completed: {title_fixed[:40]}"))
            except Exception as e:
                progress_manager(url, 0.0, f"Error: {str(e)}")
                self.after(0, lambda: self.write_log(f"Error: {str(e)}"))

        self.update_dashboard(f"Starting {parallel_count} parallel workers...", 0)
        
        with ThreadPoolExecutor(max_workers=int(parallel_count)) as executor:
            futures = [executor.submit(worker_tugas, item) for item in list_data]
            import time
            while not all(f.done() for f in futures):
                if self.stop_event_download.is_set():
                    cancelled = True
                    break 
                time.sleep(0.5)

        self.save_last_memory() 
        self.is_downloading = False
        self.after(0, lambda: self.reset_download_button(cancelled))
        
    def send_status_to_card(self, target_url, status_text, percent_value, color=None):
        for widget in self.widget_list:
            if widget.data.get('url_dl') == target_url:
                if color:
                    color = color
                else:
                    color = "#ffffff"
                    if "Error" in status_text or "ERR:" in status_text: color = "#ff5555"
                    elif "Waiting" in status_text: color = "#888888" 
                    elif percent_value >= 100: color = "#db2777"
                    elif percent_value == 0: color = "#aaaaaa"
                
                widget.set_download_status(status_text, color)
                break

    def reset_download_button(self, status_cancel):
        self.btn_download.configure(text="Download", fg_color="#db2777", hover_color="#be185d", state="normal", command=self.start_download)
        self.btn_clean_list.configure(state="normal")
        
        if status_cancel:
            self.update_dashboard("Cancelled by User.", 0)
            self.write_log("Download Stopped by User.")
            self.btn_open_folder.configure(fg_color="transparent")
            
            for item in self.scan_data:
                last_st = item.get('last_status', "")
                if "Waiting" in last_st or "Starting" in last_st:
                    item['last_status'] = "Ready."
                    self.after(0, lambda u=item['url_dl']: self.send_status_to_card(u, "Ready.", 0, color="#aaaaaa"))
        else:
            self.progress_bar.set(1.0)
            self.write_log("All Tasks Finished.")
            self.btn_open_folder.configure(fg_color="#db2777", hover_color="#be185d")
            
    def open_folder(self):
        if self.result_folder_terakhir and os.path.exists(self.result_folder_terakhir): os.startfile(self.result_folder_terakhir)

    def open_settings_popup(self):
        if self.settings_window is None or not self.settings_window.winfo_exists(): self.settings_window = settings.SettingsWindow(self)
        else: self.settings_window.focus()
    
    def open_notes_popup(self):
        if self.notes_window is None or not self.notes_window.winfo_exists():
            self.notes_window = notes.NotesWindow(self)
        else:
            self.notes_window.focus()
            self.notes_window.lift()

    def reload_initial_config(self):
        cfg = settings.load_config()
        self.custom_save_path = cfg.get("save_path", "")
        
        from datetime import datetime
        if self.custom_save_path and os.path.exists(self.custom_save_path):
            target_path = self.custom_save_path
        else:
            folder_bulan = f"{datetime.now().year}_{datetime.now().month:02d}"
            target_path = os.path.join(DATA_DIR, folder_bulan)

        self.result_folder_terakhir = os.path.abspath(target_path)
        if not os.path.exists(self.result_folder_terakhir):
            try: os.makedirs(self.result_folder_terakhir)
            except Exception as e: print(f"Error: {e}") 
        if hasattr(self, 'btn_open_folder'):
            self.btn_open_folder.configure(state="normal", fg_color="transparent")
        
    def load_last_memory(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        clean_data = [item for item in data if 'url_dl' in item and 'title' in item]
                        for item in clean_data:
                            if 'selected' not in item: item['selected'] = True
                            if 'locked' not in item: item['locked'] = False
                        self.scan_data = clean_data
                        for item in self.scan_data: self.add_one_widget(item)
                        if self.scan_data: self.btn_download.configure(state="normal")
            except Exception as e: print(f"Error: {e}")

    def save_last_memory(self):
        try:
            if not os.path.exists(os.path.dirname(HISTORY_FILE)): os.makedirs(os.path.dirname(HISTORY_FILE))
            with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(self.scan_data, f, indent=4)
        except Exception as e: print(f"Error: {e}")

    def update_dashboard(self, teks, val):
        display_text = teks[:60]+"..." if len(teks)>60 else teks
        self.lbl_status_text.configure(text=display_text)
        self.progress_bar.set(val)

    def write_log(self, teks):
        self.log_box.configure(state="normal"); self.log_box.insert("end", ">> "+teks+"\n"); self.log_box.see("end"); self.log_box.configure(state="disabled")

    def clear_input(self): self.box_link.delete("0.0", "end"); self.update_dashboard("Cleared.", 0)
    
    def action_toggle_all(self):
        # Toggle boolean state
        self.var_semua.set(not self.var_semua.get())
        status = self.var_semua.get()
        
        # Update Toggle Button UI explicitly since we are no longer using CTkSwitch
        if status:
            self.btn_select_all.configure(fg_color="#db2777", hover_color="#be185d", text_color="#ffffff", border_color="#db2777")
        else:
            self.btn_select_all.configure(fg_color="#1a1a1a", hover_color="#2b2b2b", text_color="#888888", border_color="#555555")

        for d in self.scan_data: d['selected'] = status
        for w in self.widget_list: w.var_select.set(status)

    def aksi_cek_seleksi_manual(self):
        if not self.scan_data: return
        semua_aktif = all(d.get('selected', False) for d in self.scan_data)
        if self.var_semua.get() != semua_aktif:
            self.var_semua.set(semua_aktif)
        
    def action_change_size_display(self, val):
        mode = "mp3" if "🎵" in val else "mp4"
        for w in self.widget_list: w.set_size_display(mode)
        
    def action_smart_paste(self):
        try: self.box_link.insert("end", "\n"+self.clipboard_get()) if self.box_link.get("0.0","end").strip() else self.box_link.insert("0.0", self.clipboard_get())
        except Exception as e: print(f"Error: {e}")
        
    def confirm_exit(self):
        if self.exit_window is None or not self.exit_window.winfo_exists():
            self.exit_window = ExitWindow(
                self, 
                callback_bye=lambda: (self.save_last_memory(), self.destroy())
            )
        else: self.exit_window.focus()

    def prompt_binaries_download(self):
        try:
            from xidown.gui.dialogs.setup import SetupBinariesPopup
            self.setup_popup = SetupBinariesPopup(
                self, 
                on_complete=self.on_binaries_download_complete, 
                on_cancel=self.on_binaries_download_cancel
            )
        except Exception as e:
            print(f"Error opening setup binaries popup: {e}")

    def on_binaries_download_complete(self):
        self.tools = utils.check_setup()
        if self.tools:
            self.btn_scan.configure(state="normal")
            self.btn_download.configure(state="normal")
            self.update_dashboard("Ready. System set up successfully.", 0)
            self.write_log("yt-dlp and ffmpeg successfully downloaded and set up.")
        else:
            self.update_dashboard("ERROR: Tools missing! Check bin folder.", 0)
            self.btn_scan.configure(state="disabled")
            self.btn_download.configure(state="disabled")

    def on_binaries_download_cancel(self):
        self.update_dashboard("Binary setup cancelled. Tools are missing.", 0)
        self.write_log("Binary setup cancelled by user.")

def main():
    app = CyreneApp()
    app.mainloop()

if __name__ == "__main__":
    main()