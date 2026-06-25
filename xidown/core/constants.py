# Use import aliases to prevent naming pollution
import os as _os
import subprocess as _subproc

FORMAT_SELECTION = {
    # [MARIBEL FIX] Logic to detect Excellent quality
    'excellent': 'bestvideo+bestaudio/best',
    'best': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best',
    'best_mp4': 'bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'medium': 'bestvideo[vcodec^=avc1][height<=720]+bestaudio[acodec^=mp4a]/best[height<=720]',
    'worst': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst',
    'bad': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst',

    # Fallback value similar to best
    '_fallback': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best'
}

# User Agent Chrome 120; released in 2023
# ---
# For web scraping, it is better to stay using this old user agent,
# due to many anti-bot systems may actually find a very old UA suspicious
# if other browser fingerprints look modern.
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Use all CPU threads but prevent from using entire threads on high-core machines
DEFAULT_MAX_WORKERS = min(16, (_os.cpu_count() or 1))

# Used for subprocess creation using `subprocess.Popen()`
# These arguments will:
#   - Capture any incoming logs from standard output (stdout)
#   - Redirect standard error (stderr) to stdout (it means this will be captured too)
#   - Redirect standard input (stdin) to "/dev/null" (Linux black hole) or NUL (Windows black hole)
#   - Replace any invalid bytes when decoding fails
#   - Enable text instead bytes with encoding UTF-8 and flushed one-by-one line (bufsize: 1)
DEFAULT_POPEN_KWARGS = {
    "stdout": _subproc.PIPE,
    "stderr": _subproc.STDOUT,
    "stdin": _subproc.DEVNULL,
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
    "bufsize": 1
}

# =========================================== #
#             SETUP CONFIGURATION             #
# =========================================== #

# Maximum chunk size for downloading FFmpeg
MAX_CHUNK_SIZE = 64 * 1024  # 64 KB

# FFmpeg download URL (via GitHub releases)
# Using gyan.dev was really slow and is likely to have download speed limitation
FFMPEG_DOWNLOAD_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

# yt-dlp binary (EXE) download URL (via GitHub releases)
YT_DLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

# =========================================== #
#          DOWNLOADER CONFIGURATION           #
# =========================================== #

# Socket timeout in seconds
SOCKET_TIMEOUT = 30
# Download max retries
DOWNLOAD_MAX_RETRIES = 10
# Fragment max retries
FRAGMENT_MAX_RETRIES = 10

# Default output template if user does not provide custom title
DEFAULT_OUTPUT_TEMPLATE = "%(title)s.%(ext)s"

# =========================================== #
#              MISC CONFIGURATION             #
# =========================================== #

# Path refers to favicon.ico, relative from project's root directory
# Please use Linux path separator ("/") and NOT Windows separator ("\\")
FAVICON_PATH = "assets/favicon.ico"
