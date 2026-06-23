import os
import sys
import threading
import customtkinter as ctk
import xidown.core.utils as utils
import xidown.core.setup as setup

class SetupBinariesPopup(ctk.CTkToplevel):
    def __init__(self, parent, on_complete, on_cancel=None):
        super().__init__(parent)
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.cancel_event = threading.Event()

        self.withdraw()
        self.title("Setup Binaries")
        
        # Center the window
        w_width, w_height = 360, 220
        if parent.winfo_viewable():
            p_x = parent.winfo_x(); p_y = parent.winfo_y()
            p_w = parent.winfo_width(); p_h = parent.winfo_height()
            pos_x = p_x + (p_w // 2) - (w_width // 2)
            pos_y = p_y + (p_h // 2) - (w_height // 2)
        else:
            s_w = parent.winfo_screenwidth()
            s_h = parent.winfo_screenheight()
            pos_x = (s_w // 2) - (w_width // 2)
            pos_y = (s_h // 2) - (w_height // 2)
        self.geometry(f"{w_width}x{w_height}+{int(pos_x)}+{int(pos_y)}")

        self.resizable(False, False)
        self.configure(fg_color="#121212")
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        def force_icon():
            try:
                icon_path = utils.get_icon_path()
                if icon_path and os.path.exists(icon_path):
                    self.iconbitmap(icon_path)
            except Exception: pass
            
        force_icon()
        self.after(200, force_icon)
        self.after(1000, force_icon)

        self.protocol("WM_DELETE_WINDOW", self.action_cancel)

        # UI elements
        self.lbl_title = ctk.CTkLabel(self, text="Downloading Dependencies", font=("Terminal", 15, "bold"), text_color="#db2777")
        self.lbl_title.pack(pady=(15, 5))

        self.lbl_desc = ctk.CTkLabel(self, text="Preparing to download yt-dlp & ffmpeg...", font=("Terminal", 11), text_color="#aaaaaa", wraplength=320)
        self.lbl_desc.pack(pady=(0, 15))

        self.progress_bar = ctk.CTkProgressBar(self, width=280, height=8, corner_radius=0, progress_color="#db2777", fg_color="#2b2b2b")
        self.progress_bar.pack(pady=(0, 15))
        self.progress_bar.set(0)

        self.lbl_speed = ctk.CTkLabel(self, text="", font=("Terminal", 10, "italic"), text_color="#00ffcc")
        self.lbl_speed.pack(pady=(0, 10))

        # Bottom Button
        self.btn_cancel = ctk.CTkButton(self, text="Cancel", height=32, fg_color="#2b2b2b", hover_color="#3a3a3a", font=("Terminal", 12, "bold"), corner_radius=0, command=self.action_cancel)
        self.btn_cancel.pack(pady=(5, 15))

        # Start downloading in a background thread
        self.after(200, self.start_download_thread)
        self.after(50, self.deiconify)

    def start_download_thread(self):
        threading.Thread(target=self.run_download_process, daemon=True).start()

    def run_download_process(self):
        # Resolve bin path
        bin_dir = utils.get_bin_folder()
        if not os.path.exists(bin_dir):
            os.makedirs(bin_dir)

        if sys.platform != "win32":
            install_cmd = "sudo apt update && sudo apt install ffmpeg yt-dlp" if sys.platform.startswith("linux") else "brew install ffmpeg yt-dlp"
            instructions = (
                f"Please install dependencies via your package manager:\n\n"
                f"{install_cmd}\n\n"
                f"After installation, click 'Close' to verify."
            )
            self.update_ui_state("Manual installation required.", 0.5, "Check terminal instructions...")
            self.show_error(instructions)
            self.btn_cancel.configure(text="Close", fg_color="#db2777", hover_color="#be185d", command=self.action_success_close)
            return

        path_yt_dlp = os.path.join(bin_dir, "yt-dlp.exe")
        path_ffmpeg_zip = os.path.join(bin_dir, "ffmpeg_temp.zip")

        # ----------------------------------------------------
        # Step 1: Download yt-dlp.exe
        # ----------------------------------------------------
        if not os.path.exists(path_yt_dlp):
            self.update_ui_state("Step 1/3: Downloading yt-dlp.exe...", 0.0, "")
            
            yt_dlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            
            def yt_dlp_progress(percent, downloaded, total):
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                status_text = f"{mb_downloaded:.1f} MB / {mb_total:.1f} MB"
                self.update_ui_state(f"Step 1/3: Downloading yt-dlp.exe ({status_text})", percent, "")

            success = setup.download_binary(yt_dlp_url, path_yt_dlp, yt_dlp_progress, self.cancel_event)
            
            if self.cancel_event.is_set():
                self.cleanup_temp_files(path_yt_dlp, path_ffmpeg_zip)
                return
                
            if not success:
                self.show_error("Failed to download yt-dlp.exe. Check internet connection.")
                return
        else:
            self.update_ui_state("Step 1/3: yt-dlp.exe already present.", 0.33, "")

        # ----------------------------------------------------
        # Step 2: Download ffmpeg-release-essentials.zip
        # ----------------------------------------------------
        path_ffmpeg_exe = os.path.join(bin_dir, "ffmpeg.exe")
        if not os.path.exists(path_ffmpeg_exe):
            self.update_ui_state("Step 2/3: Downloading ffmpeg package...", 0.33, "")
            
            ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            
            def ffmpeg_progress(percent, downloaded, total):
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                status_text = f"{mb_downloaded:.1f} MB / {mb_total:.1f} MB"
                # Map 0.0 - 1.0 download progress to 0.33 - 0.90 of total progress
                mapped_percent = 0.33 + (percent * 0.57)
                self.update_ui_state(f"Step 2/3: Downloading ffmpeg ({status_text})", mapped_percent, "")

            success = setup.download_binary(ffmpeg_url, path_ffmpeg_zip, ffmpeg_progress, self.cancel_event)
            
            if self.cancel_event.is_set():
                self.cleanup_temp_files(path_yt_dlp, path_ffmpeg_zip)
                return
                
            if not success:
                self.show_error("Failed to download FFmpeg package. Check internet connection.")
                return

            # ----------------------------------------------------
            # Step 3: Extract ffmpeg.exe
            # ----------------------------------------------------
            self.update_ui_state("Step 3/3: Extracting ffmpeg.exe...", 0.92, "Please wait, extracting...")
            
            success = setup.extract_ffmpeg_binaries(path_ffmpeg_zip, bin_dir, self.cancel_event)
            
            # Clean up zip file immediately
            if os.path.exists(path_ffmpeg_zip):
                try: os.remove(path_ffmpeg_zip)
                except: pass

            if self.cancel_event.is_set():
                return
                
            if not success:
                self.show_error("Failed to extract ffmpeg.exe from archive.")
                return
        else:
            self.update_ui_state("Step 2/3: ffmpeg.exe already present.", 0.90, "")

        # ----------------------------------------------------
        # Finish Setup
        # ----------------------------------------------------
        self.update_ui_state("All binaries set up successfully!", 1.0, "Ready!")
        self.btn_cancel.configure(text="Close", fg_color="#db2777", hover_color="#be185d", command=self.action_success_close)

    def update_ui_state(self, desc, progress, speed_text):
        def _update():
            if self.winfo_exists():
                self.lbl_desc.configure(text=desc)
                self.progress_bar.set(progress)
                self.lbl_speed.configure(text=speed_text)
        self.after(0, _update)

    def show_error(self, err_msg):
        def _update():
            if self.winfo_exists():
                self.lbl_title.configure(text="Error", text_color="#FF3333")
                self.lbl_desc.configure(text=err_msg)
                self.progress_bar.set(0)
                self.lbl_speed.configure(text="")
                self.btn_cancel.configure(text="Retry", fg_color="#db2777", hover_color="#be185d", command=self.action_retry)
        self.after(0, _update)

    def cleanup_temp_files(self, path_yt_dlp, path_ffmpeg_zip):
        # Delete incomplete downloads if canceled
        for p in [path_yt_dlp, path_ffmpeg_zip]:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass

    def action_cancel(self):
        self.cancel_event.set()
        self.destroy()
        if self.on_cancel:
            self.on_cancel()

    def action_retry(self):
        self.cancel_event.clear()
        self.lbl_title.configure(text="Downloading Dependencies", text_color="#db2777")
        self.btn_cancel.configure(text="Cancel", fg_color="#2b2b2b", hover_color="#3a3a3a", command=self.action_cancel)
        self.start_download_thread()

    def action_success_close(self):
        self.destroy()
        if self.on_complete:
            self.on_complete()
