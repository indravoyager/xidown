import subprocess
import sys
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from xidown.gui import settings
from xidown.core.utils import format_size, hitung_estimasi_mp3
import os
import re

def scan_single_url(url, tools, data_dir, callback_log, callback_progress, callback_item_found, stop_event, config, meta_cache):
    yt_dlp_path, ffmpeg_dir, global_cookie_path = tools
    
    cached_info = meta_cache.get(url, {})
    forced_title = cached_info.get('title')
    custom_headers = cached_info.get('headers', {})

    used_cookie = global_cookie_path
    domain_detect = "unknown"
    if "facebook.com" in url: domain_detect = "facebook_com"
    elif "bilibili.com" in url: domain_detect = "bilibili_com"
    elif "tiktok.com" in url: domain_detect = "tiktok_com"
    elif "x.com" in url or "twitter.com" in url: domain_detect = "x_com"
    elif "youtube.com" in url: domain_detect = "youtube_com"
    
    if data_dir:
        specific_cookie = os.path.join(data_dir, f"cookies_{domain_detect}.txt")
        if os.path.exists(specific_cookie):
            used_cookie = specific_cookie

    quality_mode = config.get("quality", "best")
    
    # [MARIBEL FIX] Logic to detect Excellent quality
    if quality_mode == 'excellent':
        # Singularity: Take the strongest, ignore the limitations of the mortal format
        fmt_arg = "bestvideo+bestaudio/best"
    elif quality_mode == 'medium':
        fmt_arg = "bestvideo[vcodec^=avc1][height<=720]+bestaudio[acodec^=mp4a]/best[height<=720]"
    else: 
        # Fallback to standard 'best' to maintain legacy MP4 compatibility
        fmt_arg = "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best"

    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    extra_headers = []
    if custom_headers:
        for key, val in custom_headers.items():
            extra_headers.extend(['--add-header', f"{key}:{val}"])
            if key.lower() == 'user-agent':
                user_agent = val

    referer_arg = []
    if 'facebook.com' in url: referer_arg = ['--referer', 'https://www.facebook.com/']
    elif 'bilibili.com' in url: referer_arg = ['--referer', 'https://www.bilibili.com/']
    elif 'tiktok.com' in url: referer_arg = ['--referer', 'https://www.tiktok.com/']
    elif 'youtube.com' in url: referer_arg = []

    # We will try with cookies first (if available), then fallback to no-cookies if it yields 0 items
    tries = [used_cookie] if (used_cookie and os.path.exists(used_cookie)) else [None]
    if used_cookie and os.path.exists(used_cookie):
        tries.append(None)

    for current_cookie in tries:
        command = [
            yt_dlp_path, 
            '--dump-json', 
            '--format', fmt_arg, 
            '--yes-playlist', 
            '--ignore-errors',
            '--no-warnings',
            '--write-subs',
            '--sub-langs', 'all',
            '--user-agent', user_agent, 
            url
        ]
        
        if referer_arg: command.extend(referer_arg)
        if extra_headers: command.extend(extra_headers) 
        if current_cookie: command.extend(['--cookies', current_cookie])

        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "bufsize": 1
        }
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            popen_kwargs["startupinfo"] = startupinfo
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        items_found = []
        def intercept_item_found(item):
            items_found.append(item)
            callback_item_found(item)

        try:
            process = subprocess.Popen(command, **popen_kwargs)

            while True:
                if stop_event.is_set(): process.kill(); break
                line = process.stdout.readline()
                if not line and process.poll() is not None: break

                if line:
                    clean_line = line.strip()
                    if not clean_line: continue

                    if clean_line.startswith('{') and clean_line.endswith('}'):
                        try:
                            data = json.loads(clean_line)
                            if 'title' in data or 'id' in data:
                                process_and_send_data(data, intercept_item_found, callback_log, forced_title)
                        except json.JSONDecodeError: pass
                    
                    elif "Sign in" in clean_line or "login" in clean_line.lower():
                        callback_log(f"⚠ Login Required for {domain_detect}!")
                    
                    elif clean_line.startswith('[') or "Downloading" in clean_line:
                        short_message = clean_line
                        if len(short_message) > 50: short_message = short_message[:47] + "..."
                        callback_progress(f"🔍 {short_message}", 0)

            # If items were successfully parsed, stop trying other options (like no-cookies)
            if items_found:
                break
            
            # If we used cookies and failed (0 items), warn and fallback
            if current_cookie:
                callback_log(f"⚠️ Cookie scan failed for {domain_detect}. Retrying without cookies...")

        except Exception as e:
            if not current_cookie: # Only log error on the final retry
                callback_log(f"Error Scan {url}: {str(e)}")

def process_and_send_data(data, callback_item_found, callback_log, forced_title=None):
    original_url = data.get('webpage_url') or data.get('url')
    title_raw = data.get('title', 'Unknown Video')
    
    if forced_title:
        title = forced_title
    else:
        title_jelek = ["video", "facebook video", "unknown video", "watch", "live", "master"]
        is_numeric = str(title_raw).replace(" ", "").isdigit()
        
        if not title_raw or str(title_raw).lower() in title_jelek or is_numeric or len(title_raw) < 3:
            description = data.get('description') or data.get('uploader') or "Video Result"
            title_baru = description.split('\n')[0].strip()
            if len(title_baru) > 80: title_baru = title_baru[:77] + "..."
            title = title_baru if title_baru else title_raw
        else:
            title = title_raw

    title = re.sub(r'^\(\d+\)\s*', '', title)
    title = title.replace(' - YouTube', '').replace(' - PikPak', '').replace(' | Facebook', '')

    thumb = data.get('thumbnail', '')
    size_bytes = data.get('filesize') or data.get('filesize_approx')
    size_video_str = format_size(size_bytes) if size_bytes else "Unknown"
    
    raw_duration = data.get('duration') or 0
    m, d = divmod(int(raw_duration), 60)
    if m >= 60: h, m = divmod(m, 60); duration_str = f"{h}:{m:02d}:{d:02d}"
    else: duration_str = f"{m}:{d:02d}"

    size_mp3_str = hitung_estimasi_mp3(raw_duration)
    height = data.get('height')
    resolution_str = f"{height}p" if height else "??p"

    # Extract Subtitles
    available_subs = {}
    subs = data.get('subtitles') or {}
    auto_subs = data.get('automatic_captions') or {}
    for lang_code in subs.keys():
        name_list = subs[lang_code]
        lang_name = lang_code
        if name_list and isinstance(name_list, list) and 'name' in name_list[0]:
            lang_name = name_list[0]['name']
        available_subs[lang_code] = lang_name
        
    for lang_code in auto_subs.keys():
        if lang_code not in available_subs:
            name_list = auto_subs[lang_code]
            lang_name = f"{lang_code} (Auto)"
            if name_list and isinstance(name_list, list) and 'name' in name_list[0]:
                lang_name = f"{name_list[0]['name']} (Auto)"
            available_subs[lang_code] = lang_name

    data_item = {
        'title': title, 'size_video': size_video_str, 'size_audio': size_mp3_str, 
        'size': size_video_str, 'duration': duration_str, 'thumb_url': thumb, 
        'url_dl': original_url, 'res': resolution_str, 'selected': True, 'locked': False,
        'subs': available_subs
    }
    callback_item_found(data_item)
    callback_log(f"Found: {title[:20]}...")

def run_scan(links, tools, data_dir, scan_data, stop_event, callback_log, callback_progress, callback_item_found, callback_done, meta_cache=None):
    if meta_cache is None: meta_cache = {}
    config = settings.load_config()
    total_found = 0
    lock = threading.Lock() 

    def safe_item_found(item):
        nonlocal total_found
        is_dup = False
        with lock:
            for existing in scan_data:
                if existing['url_dl'] == item['url_dl']: is_dup = True; break
            if not is_dup: total_found += 1
        if not is_dup: callback_item_found(item) 
        else: callback_log(f"Skip Duplicate: {item['title'][:15]}...")

    max_workers = 3 
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for url in links:
            if stop_event.is_set(): break
            
            futures.append(
                executor.submit(
                    scan_single_url, 
                    url, tools, data_dir, 
                    callback_log, callback_progress, safe_item_found, stop_event, config, meta_cache
                )
            )
        for f in futures:
            if stop_event.is_set(): break
            f.result()
    callback_done(total_found)