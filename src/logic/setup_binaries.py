import os
import sys
import zipfile
import urllib.request
import shutil
import tempfile
import threading

def download_binary(url, dest_path, progress_callback=None, cancel_event=None):
    """
    Downloads a file with progress reporting and cancellation support.
    """
    # Ensure destination directory exists
    dest_dir = os.path.dirname(dest_path)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 1024 * 64  # 64KB chunks
            downloaded = 0
            
            with open(dest_path, 'wb') as f:
                while True:
                    if cancel_event and cancel_event.is_set():
                        return False
                    
                    block = response.read(block_size)
                    if not block:
                        break
                    
                    f.write(block)
                    downloaded += len(block)
                    if total_size > 0 and progress_callback:
                        percent = downloaded / total_size
                        progress_callback(percent, downloaded, total_size)
            return True
    except Exception as e:
        print(f"[SetupBinaries] Error downloading {url}: {e}")
        return False

def extract_ffmpeg_binaries(zip_path, bin_dir, cancel_event=None):
    """
    Extracts ffmpeg.exe and ffprobe.exe from the downloaded zip file and places them in bin_dir.
    """
    try:
        if cancel_event and cancel_event.is_set():
            return False
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Look for ffmpeg.exe and ffprobe.exe inside the zip file
            ffmpeg_member = None
            ffprobe_member = None
            for member in zip_ref.namelist():
                if member.endswith("ffmpeg.exe"):
                    ffmpeg_member = member
                elif member.endswith("ffprobe.exe"):
                    ffprobe_member = member
            
            if not ffmpeg_member:
                print("[SetupBinaries] ffmpeg.exe not found in zip archive.")
                return False
                
            # Extract to temporary directory and move to bin_dir
            with tempfile.TemporaryDirectory() as tmpdir:
                if cancel_event and cancel_event.is_set():
                    return False
                
                # Extract ffmpeg.exe
                zip_ref.extract(ffmpeg_member, tmpdir)
                extracted_path = os.path.join(tmpdir, ffmpeg_member)
                dest_path = os.path.join(bin_dir, "ffmpeg.exe")
                
                if not os.path.exists(bin_dir):
                    os.makedirs(bin_dir)
                    
                if os.path.exists(dest_path):
                    try: os.remove(dest_path)
                    except: pass
                shutil.move(extracted_path, dest_path)
                
                # Extract ffprobe.exe if available
                if ffprobe_member:
                    zip_ref.extract(ffprobe_member, tmpdir)
                    extracted_probe_path = os.path.join(tmpdir, ffprobe_member)
                    dest_probe_path = os.path.join(bin_dir, "ffprobe.exe")
                    if os.path.exists(dest_probe_path):
                        try: os.remove(dest_probe_path)
                        except: pass
                    shutil.move(extracted_probe_path, dest_probe_path)
                    
            return True
    except Exception as e:
        print(f"[SetupBinaries] Error extracting ffmpeg: {e}")
        return False
