import os
import re
import sys
import subprocess
import json
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor

from xidown.core.constants import (
    DEFAULT_MAX_WORKERS,
    DEFAULT_USER_AGENT,
    DEFAULT_POPEN_KWARGS,
    FORMAT_SELECTION
)
from xidown.core.types import AnyCallable, AnyDict
from xidown.gui import settings
from xidown.core.utils import format_size, hitung_estimasi_mp3

def scan_single_url(url: str, tools: Tuple[str, ...], data_dir: str,
                    callback_log: AnyCallable,
                    callback_progress: AnyCallable,
                    callback_item_found: AnyCallable,
                    stop_event: threading.Event,
                    config: AnyDict,
                    meta_cache: AnyDict):
    yt_dlp_path, _, global_cookie_path = tools

    cached_info = meta_cache.get(url, {})
    forced_title = cached_info.get('title')
    custom_headers = cached_info.get('headers', {})
    used_cookie = Path(global_cookie_path).absolute()

    domain_detect = "unknown"
    if "facebook.com" in url:                    domain_detect = "facebook_com"
    elif "bilibili.com" in url:                  domain_detect = "bilibili_com"
    elif "tiktok.com" in url:                    domain_detect = "tiktok_com"
    elif "x.com" in url or "twitter.com" in url: domain_detect = "x_com"
    elif "youtube.com" in url:                   domain_detect = "youtube_com"

    if data_dir:
        specific_cookie = Path(data_dir) / f"cookies_{domain_detect}.txt"
        if specific_cookie.is_file():
            used_cookie = specific_cookie.absolute()

    quality_mode: str = config.get("quality", "best")
    fmt_arg = FORMAT_SELECTION[quality_mode]
    user_agent = DEFAULT_USER_AGENT

    extra_headers = []
    if custom_headers:
        for key, val in custom_headers.items():
            extra_headers.extend(['--add-header', f"{key}:{val}"])
            if key.lower() == 'user-agent':
                user_agent = val

    referer_arg = []
    if 'facebook.com' in url:   referer_arg = ['--referer', 'https://www.facebook.com/']
    elif 'bilibili.com' in url: referer_arg = ['--referer', 'https://www.bilibili.com/']
    elif 'tiktok.com' in url:   referer_arg = ['--referer', 'https://www.tiktok.com/']
    elif 'youtube.com' in url:  referer_arg = []

    # We will try with cookies first (if available), then fallback to no-cookies if it yields 0 items
    tries: List[Union[str, None]] = [str(used_cookie)] if (used_cookie and used_cookie.exists()) else [None]
    if used_cookie and used_cookie.exists():
        tries.append(None)

    # Build the commands before the loop
    prebuilt_command = [
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

    for current_cookie in tries:
        # Shallow copy the prebuilt command
        # If inside the prebuilt command has nested list, please use deep copy instead
        command = prebuilt_command.copy()

        if referer_arg: command.extend(referer_arg)
        if extra_headers: command.extend(extra_headers)
        if current_cookie: command.extend(['--cookies', current_cookie])

        popen_kwargs = DEFAULT_POPEN_KWARGS
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

        def process_json_data(line: str) -> None:
            try:
                data: AnyDict = json.loads(line)
                if 'title' in data or 'id' in data:
                    process_and_send_data(data, intercept_item_found, callback_log, forced_title)
            except json.JSONDecodeError:
                pass

        try:
            process = subprocess.Popen(command, **popen_kwargs)

            while True:
                if stop_event.is_set(): process.kill(); break
                # process.stdout can be None, should have a protection here
                line = process.stdout.readline() if process.stdout else None
                if not line and process.poll() is not None:
                    break
                elif not line:
                    continue

                clean_line = line.strip()
                if not clean_line: continue

                # Process JSON data from output line
                if clean_line.startswith('{') and clean_line.endswith('}'):
                    process_json_data(clean_line)

                # Require login authentication or cookies
                elif "Sign in" in clean_line or "login" in clean_line.lower():
                    callback_log(f"⚠ Login Required for {domain_detect}!")

                # On download progress
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

def process_and_send_data(data: AnyDict,
                          callback_item_found: AnyCallable,
                          callback_log: AnyCallable,
                          forced_title: Optional[str] = None):
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
    title = (title.replace(' - YouTube', '')   # YouTube
                  .replace(' - PikPak', '')    # PikPak
                  .replace(' | Facebook', '')  # Facebook
            )

    thumb = data.get('thumbnail', '')
    size_bytes = data.get('filesize') or data.get('filesize_approx')
    size_video_str = format_size(size_bytes) if size_bytes else "Unknown"

    raw_duration = data.get('duration') or 0
    m, d = divmod(int(raw_duration), 60)
    if m >= 60:
        h, m = divmod(m, 60)
        duration_str = f"{h}:{m:02d}:{d:02d}"
    else:
        duration_str = f"{m}:{d:02d}"

    size_mp3_str = hitung_estimasi_mp3(raw_duration)
    height = data.get('height')
    resolution_str = f"{height}p" if height else "??p"

    # Extract Subtitles
    available_subs: Dict[str, str] = {}
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
        'title': title,
        'size_video': size_video_str,
        'size_audio': size_mp3_str,
        'size': size_video_str,
        'duration': duration_str,
        'thumb_url': thumb,
        'url_dl': original_url,
        'res': resolution_str,
        'selected': True,
        'locked': False,
        'subs': available_subs
    }
    callback_item_found(data_item)
    callback_log(f"Found: {title[:20]}...")

def run_scan(links: Iterable[str], tools: Tuple[str, ...], data_dir: str,
             scan_data: Iterable[AnyDict],
             stop_event: threading.Event,
             callback_log: AnyCallable,
             callback_progress: AnyCallable,
             callback_item_found: AnyCallable,
             callback_done: AnyCallable,
             meta_cache: Optional[AnyDict] = None):
    if meta_cache is None: meta_cache = {}
    config = settings.load_config()
    total_found = 0
    lock = threading.Lock()

    def safe_item_found(item):
        nonlocal total_found
        nonlocal lock
        is_dup = False

        with lock:
            for existing in scan_data:
                if existing['url_dl'] == item['url_dl']: is_dup = True; break
            if not is_dup: total_found += 1
        if not is_dup: callback_item_found(item)
        else: callback_log(f"Skip Duplicate: {item['title'][:15]}...")

    max_workers = DEFAULT_MAX_WORKERS  # Change this if want to use non-heavy processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for url in links:
            if stop_event.is_set(): break
            futures.append(executor.submit(
                scan_single_url,
                url, tools, data_dir,
                callback_log, callback_progress,
                safe_item_found, stop_event, config,
                meta_cache
            ))
        for f in futures:
            if stop_event.is_set(): break
            f.result()
    callback_done(total_found)
