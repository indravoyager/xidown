import os
import sys

def check_setup():
    """
    Verify the existence of external binaries (ffmpeg & yt-dlp) in the bin directory.
    Supports both the new directory structure (src/logic) and compiled executable (.exe) modes.
    """
    if getattr(sys, 'frozen', False):
        # Execution context: .exe (Frozen)
        base_path = os.path.dirname(sys.executable)
    else:
        # --- NEW NAVIGATION LOGIC [MARIBEL FIX] ---
        # Current file location: .../xidown/src/logic/utils.py
        
        # 1. Locate the directory containing this script (src/logic)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Navigate back to 'src' directory
        src_dir = os.path.dirname(current_dir)
        
        # 3. Navigate back to the Root directory (Where the bin folder is located)
        base_path = os.path.dirname(src_dir)

    # Point to the bin directory in Root
    bin_folder = os.path.join(base_path, "bin")
    
    path_yt_dlp = os.path.join(bin_folder, "yt-dlp.exe")
    path_ffmpeg_exe = os.path.join(bin_folder, "ffmpeg.exe")
    
    # Cookie file path (Optional fallback)
    path_cookies = os.path.join(bin_folder, "cookies.txt")

    missing = []
    if not os.path.exists(path_yt_dlp): missing.append("yt-dlp.exe")
    if not os.path.exists(path_ffmpeg_exe): missing.append("ffmpeg.exe")
    
    # Optional config: Default cookies path might not exist, ignore if missing
    if not os.path.exists(path_cookies):
        pass 

    if missing:
        # Enhanced error message for debugging paths
        print(f"[Utils] Searching binaries in: {bin_folder}")
        print(f"[Utils] ERROR: Missing: {', '.join(missing)}")
        return None
    
    return path_yt_dlp, bin_folder, path_cookies
 
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
        base_path = os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(current_dir)
        base_path = os.path.dirname(src_dir)
        
    path_assets = os.path.join(base_path, "assets", "favicon.ico")
    if os.path.exists(path_assets):
        return path_assets
    
    # Fallback in case resources are placed in img/
    path_img = os.path.join(base_path, "img", "favicon.ico")
    if os.path.exists(path_img):
        return path_img
        
    return None