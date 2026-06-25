import os
import sys

import shutil

def get_bin_folder():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        # Current file location: .../xidown/xidown/core/utils.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        xidown_dir = os.path.dirname(current_dir)
        base_path = os.path.dirname(xidown_dir)
    return os.path.join(base_path, "bin")

def check_setup():
    """
    Verify the existence of external binaries (ffmpeg & yt-dlp).
    Checks system PATH first, then falls back to local bin directory.
    Supports both the new directory structure and compiled executable (.exe) modes.
    """
    # Expected executable names based on OS
    is_win = sys.platform == "win32"
    yt_dlp_name = "yt-dlp.exe" if is_win else "yt-dlp"
    ffmpeg_name = "ffmpeg.exe" if is_win else "ffmpeg"

    bin_folder = get_bin_folder()

    # 1. Prioritize local bin folder first (standalone portability)
    local_yt = os.path.join(bin_folder, yt_dlp_name)
    path_yt_dlp = local_yt if os.path.exists(local_yt) else None

    local_ff = os.path.join(bin_folder, ffmpeg_name)
    path_ffmpeg = local_ff if os.path.exists(local_ff) else None

    # 2. Fallback to System PATH if not found in local bin folder
    if not path_yt_dlp:
        path_yt_dlp = shutil.which("yt-dlp")
            
    if not path_ffmpeg:
        path_ffmpeg = shutil.which("ffmpeg")

    # Optional Cookie file path
    path_cookies = os.path.join(bin_folder, "cookies.txt")

    missing = []
    if not path_yt_dlp: missing.append(yt_dlp_name)
    if not path_ffmpeg: missing.append(ffmpeg_name)

    # Optional config: Default cookies path might not exist, ignore if missing
    if not os.path.exists(path_cookies):
        pass 

    if missing:
        # Enhanced error message for debugging paths
        print(f"[Utils] Searching binaries in System PATH and: {bin_folder}")
        print(f"[Utils] ERROR: Missing: {', '.join(missing)}")
        return None
    
    # yt-dlp expects the directory containing ffmpeg, not the executable file itself, or it can accept the executable path.
    # Returning dirname is safer for yt-dlp's --ffmpeg-location if it's in the system path.
    ffmpeg_dir = os.path.dirname(path_ffmpeg) if path_ffmpeg else bin_folder
    
    return path_yt_dlp, ffmpeg_dir, path_cookies
 
# --- SIZE FORMATTING UTILITIES ---
def format_size(bytes_size):
    if not bytes_size: return "Unknown"
    power = 1024
    n = 0
    power_labels = {0 : '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while bytes_size > power:
        bytes_size /= power
        n += 1
    return f"{bytes_size:.2f} {power_labels[n]}"
 
def hitung_estimasi_mp3(duration_detik):
    if not duration_detik: return "Unknown"
    try:
        total_bytes = int(duration_detik) * 16 * 1024 
        return format_size(total_bytes)
    except:
        return "Unknown"
 
def get_icon_path():
    """
    Retrieve the safe absolute path to assets/favicon.ico.
    """
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        package_dir = os.path.dirname(current_dir)
        base_path = os.path.dirname(package_dir)
        
    path_assets = os.path.join(base_path, "assets", "favicon.ico")
    if os.path.exists(path_assets):
        return path_assets
    
    # Fallback in case resources are placed in img/
    path_img = os.path.join(base_path, "img", "favicon.ico")
    if os.path.exists(path_img):
        return path_img
        
    return None

def create_shortcut_if_first_run():
    """
    Automatically creates a Windows desktop shortcut on the first run of the application.
    Does nothing on non-Windows platforms or in development mode.
    """
    if sys.platform != "win32":
        return

    if not getattr(sys, 'frozen', False):
        return

    base_path = os.path.dirname(sys.executable)
    data_dir = os.path.join(base_path, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    flag_file = os.path.join(data_dir, ".shortcut_created")
    if os.path.exists(flag_file):
        return
        
    try:
        exe_path = sys.executable
        working_dir = base_path
        
        # PowerShell script to create shortcut pointing to the exe and setting its icon
        ps_cmd = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Shortcut = $WshShell.CreateShortcut(([Environment]::GetFolderPath('Desktop') + '\\xidown.lnk')); "
            f"$Shortcut.TargetPath = '{exe_path}'; "
            f"$Shortcut.WorkingDirectory = '{working_dir}'; "
            f"$Shortcut.IconLocation = '{exe_path}'; "
            f"$Shortcut.Save()"
        )
        
        import subprocess
        creation_flags = 0x08000000 # CREATE_NO_WINDOW
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            creationflags=creation_flags,
            check=True
        )
        
        with open(flag_file, "w") as f:
            f.write("created")
            
        print("[Utils] Desktop shortcut successfully created.")
    except Exception as e:
        print(f"[Utils] Failed to create desktop shortcut: {e}")