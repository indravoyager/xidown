import subprocess
import sys
import threading
import re
import os
import ctypes 

# [MARIBEL] Filename cleaning function
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def run(url, result_folder, audio_only, playlist_items, tools_paths, format_type, video_quality, callback_progress, stop_event, proxy_url, quality_setting, time_range, duplicate_option=None, part_count=2, custom_title=None, sub_langs=None):
    yt_dlp_path, ffmpeg_dir, cookie_path = tools_paths
    
    # 1. Ensure primary output directory exists
    result_folder = os.path.abspath(result_folder)
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)

    # 1.b. Create temporary processing folder
    folder_temp = os.path.join(result_folder, "process")
    if not os.path.exists(folder_temp):
        os.makedirs(folder_temp)
        try:
            if os.name == 'nt':
                ctypes.windll.kernel32.SetFileAttributesW(folder_temp, 0x02) # Attribute Hidden
        except: pass

    # 2. Determine output filename template
    if custom_title:
        clean_title = sanitize_filename(custom_title)
        if len(clean_title) > 200: 
            clean_title = clean_title[:200]
        output_template = f"{clean_title}.%(ext)s"
    else:
        output_template = '%(title)s.%(ext)s'

    # 3. Build shell command
    base_cmd = [
        yt_dlp_path, 
        url,
        '--newline',        
        '--no-warnings',
        '--ffmpeg-location', ffmpeg_dir,
        '--socket-timeout', '30', 
        '--retries', '10',       
        '--fragment-retries', '10',
        '-P', f"home:{result_folder}",
        '-P', f"temp:{folder_temp}",
        '--output', output_template,
        '-N', str(part_count)
    ]

    base_cmd.extend(['--postprocessor-args', 'ffmpeg:-movflags +faststart'])

    # 4. Format Settings
    if format_type == 'mp3':
        base_cmd.extend([
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '192K',
            '--embed-thumbnail',
            '--add-metadata'
        ])
    else:
        # [MARIBEL FIX] Merging logic based on quality
        if quality_setting == 'excellent':
            # God Tier: MP4 container ensures thumbnails are visible in Windows Explorer
            base_cmd.extend(['-f', 'bestvideo+bestaudio/best', '--merge-output-format', 'mp4'])
        elif quality_setting == 'medium':
            base_cmd.extend(['-f', 'bestvideo[vcodec^=avc1][height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'])
        elif quality_setting == 'worst':
            base_cmd.extend(['-f', 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst'])
        else: # For standard 'best' quality
            base_cmd.extend(['-f', 'bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'])
        
        # SUBTITLE PROCESSING
        if sub_langs:
            if isinstance(sub_langs, list):
                langs_str = ",".join(sub_langs)
            else:
                langs_str = sub_langs
            base_cmd.extend(["--write-subs", "--sub-langs", langs_str])
        
        # Add-on: Force thumbnail to jpg for correct embedding
        base_cmd.extend(['--embed-thumbnail', '--convert-thumbnails', 'jpg', '--add-metadata'])

    # 5. Proxy & Cut
    if proxy_url: base_cmd.extend(['--proxy', proxy_url])
    if time_range:
        start_t, end_t = time_range
        if start_t or end_t:
            base_cmd.extend(['--downloader', 'ffmpeg', '--force-keyframes-at-cuts'])
            section = f"*{start_t}-{end_t}" if (start_t and end_t) else (f"*{start_t}-inf" if start_t else f"*0-{end_t}")
            base_cmd.extend(['--download-sections', section])

    # 6. Execute Process with cookie fallback support
    popen_kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT, 
        "stdin": subprocess.DEVNULL, 
        "text": True,
        "encoding": 'utf-8',
        "errors": 'replace',
        "bufsize": 1
    }
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        popen_kwargs["startupinfo"] = startupinfo
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    tries = [cookie_path] if (cookie_path and os.path.exists(cookie_path)) else [None]
    if cookie_path and os.path.exists(cookie_path):
        tries.append(None)

    for attempt_cookie in tries:
        cmd = list(base_cmd)
        if attempt_cookie:
            cmd.extend(['--cookies', attempt_cookie])

        try:
            process = subprocess.Popen(cmd, **popen_kwargs)

            pattern_percent_simple = re.compile(r'(\d{1,3}\.\d|\d{1,3})%') 
            pattern_detail = re.compile(r'of\s+~?(\S+)\s+at\s+(\S+)\s+ETA\s+(\S+)')
            pattern_fragment = re.compile(r'fragment\s+(\d+)\s+of\s+(\d+)')

            file_exists = False
            is_100_percent = False 
            error_captured = None

            while True:
                if stop_event.is_set():
                    process.kill()
                    if callback_progress: callback_progress(0, "Cancelled by User.")
                    break

                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break

                if line:
                    line = line.strip()

                    if "has already been downloaded" in line:
                        file_exists = True
                        is_100_percent = True
                        if callback_progress: callback_progress(100, "File already exists!")

                    elif "fragment" in line.lower() and "of" in line.lower():
                        match_frag = pattern_fragment.search(line)
                        if match_frag:
                            try:
                                curr_frag = int(match_frag.group(1))
                                total_frag = int(match_frag.group(2))
                                if total_frag > 0: percent = (curr_frag / total_frag) * 100
                                else: percent = 0
                                msg = f"Part {curr_frag}/{total_frag} • Gathering pieces..."
                                if callback_progress: callback_progress(percent, msg)
                            except: pass
                        continue 

                    elif "%" in line and "[download]" in line:
                        match_percent = pattern_percent_simple.search(line)
                        if match_percent:
                            try:
                                percent_str = match_percent.group(1)
                                percent = float(percent_str)
                                if percent >= 100: is_100_percent = True

                                match_detail = pattern_detail.search(line)
                                if match_detail:
                                    size_str = match_detail.group(1)
                                    speed_str = match_detail.group(2)
                                    eta_str = match_detail.group(3)
                                    msg = f"{size_str} • {speed_str} • ETA {eta_str}"
                                else:
                                    msg = "Downloading..."

                                if callback_progress: callback_progress(percent, msg)
                            except: pass
                    
                    elif "[ffmpeg]" in line or "Merger" in line:
                        is_100_percent = True
                        if callback_progress: callback_progress(99, "Processing & Merging...")
                    elif "Metadata" in line:
                        if callback_progress: callback_progress(99, "Writing Tags...")
                    elif "ERROR:" in line.upper():
                        err_msg = line.replace("[youtube]", "").replace("ERROR:", "").strip()
                        error_captured = err_msg
                        if not (attempt_cookie and (None in tries)):
                            if callback_progress: callback_progress(0, f"ERR: {err_msg[:40]}")

            rc = process.poll()
            is_success = (rc == 0) or is_100_percent or file_exists

            if is_success:
                try:
                    if os.path.exists(folder_temp) and not os.listdir(folder_temp):
                        os.rmdir(folder_temp)
                except: pass

                if not stop_event.is_set():
                    if file_exists:
                        if callback_progress: callback_progress(100, "Done (Exists)!")
                    else:
                        if callback_progress: callback_progress(100, "Done!")
                return 

            else:
                if attempt_cookie:
                    if callback_progress: 
                        callback_progress(0, "Cookie error. Retrying without cookies...")
                    continue 

                if not stop_event.is_set():
                    err_lbl = error_captured if error_captured else "Failed. Check Connection."
                    if callback_progress: callback_progress(0, f"ERR: {err_lbl[:40]}")

        except Exception as e:
            if not attempt_cookie: 
                if callback_progress: callback_progress(0, f"SysErr: {str(e)[:40]}")