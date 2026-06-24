import subprocess
import sys
import re
import os
import ctypes
import threading
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

from xidown.core.constants import (
    DEFAULT_OUTPUT_TEMPLATE,
    DEFAULT_POPEN_KWARGS,
    DOWNLOAD_MAX_RETRIES,
    FRAGMENT_MAX_RETRIES,
    FORMAT_SELECTION,
    SOCKET_TIMEOUT,
)
from xidown.core.types import AnyCallable, AnyDict, PathLike
from xidown.core.utils import sanitize_filename, safe_rmdir

def run(url: str, result_folder: PathLike,
        audio_only: bool,
        playlist_items,
        tools_paths: Tuple[str, ...],
        format_type: str,
        video_quality: str,
        callback_progress: AnyCallable,
        stop_event: threading.Event,
        proxy_url: str,
        quality_setting: str,
        time_range: Iterable[Union[int, None]],
        duplicate_option: Optional[AnyDict] = None,
        part_count: int = 2,
        custom_title: Optional[str] = None,
        sub_langs: Optional[Union[str, List[str]]] = None):
    yt_dlp_path, ffmpeg_dir, cookie_path = tools_paths

    # 1. Ensure primary output directory exists
    result_folder = Path(result_folder).absolute()
    if not result_folder.exists():
        result_folder.mkdir(parents=True)

    # 1.b. Create temporary processing folder
    folder_temp = result_folder / "process"
    if not folder_temp.exists():
        folder_temp.mkdir()
        if os.name == 'nt':
            try:
                ctypes.windll.kernel32.SetFileAttributesW(str(folder_temp), 0x02) # Attribute Hidden
            except: pass

    # 2. Determine output filename template
    if custom_title:
        clean_title = sanitize_filename(custom_title)
        if len(clean_title) > 200: 
            clean_title = clean_title[:200]
        output_template = f"{clean_title}.%(ext)s"
    else:
        output_template = DEFAULT_OUTPUT_TEMPLATE

    # 3. Build shell command
    base_cmd: List[str] = [
        yt_dlp_path,
        url,
        '--newline',
        '--no-warnings',
        '--ffmpeg-location', ffmpeg_dir,
        '--socket-timeout', str(SOCKET_TIMEOUT),
        '--retries', str(DOWNLOAD_MAX_RETRIES),
        '--fragment-retries', str(FRAGMENT_MAX_RETRIES),
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
        selected_format = FORMAT_SELECTION.get(quality_setting) or FORMAT_SELECTION['medium']
        base_cmd.extend(['-f', selected_format])

        if quality_setting == 'excellent' or quality_setting == 'best':
            base_cmd.extend(['--merge-output-format', 'mp4'])

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
            section = f"*{start_t}-{end_t}" if (start_t and end_t) else (f"*{start_t}-inf" if start_t else f"*0-{end_t}")
            base_cmd.extend([
                '--downloader', 'ffmpeg',
                '--force-keyframes-at-cuts',
                '--download-sections', section
            ])

    # 6. Execute Process with cookie fallback support
    popen_kwargs = DEFAULT_POPEN_KWARGS

    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        popen_kwargs["startupinfo"] = startupinfo
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    tries: List[Union[str, None]] = [cookie_path] if (cookie_path and os.path.exists(cookie_path)) else [None]
    if cookie_path and os.path.exists(cookie_path):
        tries.append(None)

    for attempt_cookie in tries:
        cmd = base_cmd.copy()
        if attempt_cookie:
            cmd.extend(['--cookies', attempt_cookie])

        try:
            process = subprocess.Popen(cmd, **popen_kwargs)

            pattern_percent_simple = re.compile(r'(\d{1,3}\.\d|\d{1,3})%') 
            pattern_detail = re.compile(r'of\s+~?(\S+)\s+at\s+(\S+)\s+ETA\s+(\S+)')
            pattern_fragment = re.compile(r'fragment\s+(\d+)\s+of\s+(\d+)')

            file_exists = False
            is_done = False 
            error_captured = None

            while True:
                if stop_event.is_set():
                    process.kill()
                    if callback_progress:
                        callback_progress(0, "Cancelled by User.")
                    break

                # process.stdout can be None, should have a protection here
                line = process.stdout.readline() if process.stdout else None
                if not line and process.poll() is not None:
                    break
                elif not line:
                    continue

                line = line.strip()

                # >> Already downloaded
                if "has already been downloaded" in line.lower():
                    file_exists = True
                    is_done = True
                    if callback_progress:
                        callback_progress(100, "File already exists!")

                # >> On progress (fragment)
                elif "fragment" in line.lower() and "of" in line.lower():
                    match_frag = pattern_fragment.search(line)
                    if not match_frag: continue

                    try:
                        curr_frag = int(match_frag.group(1))
                        total_frag = int(match_frag.group(2))

                        if total_frag > 0: percent = (curr_frag / total_frag) * 100
                        else: percent = 0
                        msg = f"Part {curr_frag}/{total_frag} • Gathering pieces..."

                        if callback_progress:
                            callback_progress(percent, msg)
                    except Exception: pass

                # >> On progress (download)
                elif "%" in line and "[download]" in line:
                    match_percent = pattern_percent_simple.search(line)
                    if not match_percent: continue

                    try:
                        percent_str = match_percent.group(1)
                        percent = float(percent_str)
                        is_done = percent >= 100

                        match_detail = pattern_detail.search(line)
                        if match_detail:
                            size_str = match_detail.group(1)
                            speed_str = match_detail.group(2)
                            eta_str = match_detail.group(3)
                            msg = f"{size_str} • {speed_str} • ETA {eta_str}"
                        else:
                            msg = "Downloading..."

                        if callback_progress:
                            callback_progress(percent, msg)
                    except Exception: pass

                # >> On progress (ffmpeg)
                elif "[ffmpeg]" in line or "Merger" in line:
                    is_done = True
                    if callback_progress: callback_progress(99, "Processing & Merging...")
                elif "Metadata" in line:
                    if callback_progress: callback_progress(99, "Writing Tags...")
                elif "ERROR:" in line.upper():
                    err_msg = line.replace("[youtube]", "").replace("ERROR:", "").strip()
                    error_captured = err_msg
                    if not (attempt_cookie and (None in tries)):
                        if callback_progress: callback_progress(0, f"ERR: {err_msg[:40]}")

            rc = process.poll()
            is_success = (rc == 0) or is_done or file_exists

            if is_success:
                if folder_temp.exists():
                    safe_rmdir(folder_temp)

                if stop_event.is_set(): return

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
