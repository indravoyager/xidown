import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Literal, Tuple, Optional, overload

from xidown.core.constants import FAVICON_PATH
from xidown.core.types import PathLike

# --------- Simple Utilities ---------- #
def is_windows() -> bool:
    """Returns true if the current system is Windows"""
    return sys.platform == 'win32'

@overload
def sanitize_filename(name: str) -> str: ...
@overload
def sanitize_filename(name: Path) -> Path: ...

def sanitize_filename(name: PathLike) -> PathLike:
    """
    Sanitize filename to be used by system files.

    Returns a filename with type consistent to the given input type.
    """
    _name = str(name)
    sanitized = re.sub(r'[\\/*?:"<>|]', "", _name).strip()
    return Path(sanitized) if isinstance(name, Path) else sanitized

def safe_rm(path: PathLike) -> bool:
    """
    Safely remove a regular file.

    This function does not perform validation to ensure that ``path``
    refers to an existing regular file.

    Args
    ----
    path : str or Path
        Input path.

    Returns
    -------
    bool
        True if the removal operation completed without raising an
        exception, False otherwise.
    """
    try: os.remove(str(path))
    except Exception: return False
    # If succeed, return True
    return True

def safe_rmdir(path: PathLike) -> bool:
    """
    Safely remove a directory tree recursively.

    All files and subdirectories contained within the target directory are
    removed as part of the operation.

    Any exception raised by ``shutil.rmtree()`` is suppressed and causes the
    function to return ``False``. No validation is performed to ensure that
    ``path`` refers to an existing directory.

    Args
    ----
    path : str or Path
        Input path.

    Returns
    -------
    bool
        True if the removal operation completed without raising an
        exception, False otherwise.
    """
    try: shutil.rmtree(path)
    except Exception: return False
    # If succeed, return True
    return True

@overload
def get_rootdir() -> str: ...
@overload
def get_rootdir(as_path: Literal[False]) -> str: ...
@overload
def get_rootdir(as_path: Literal[True]) -> Path: ...
@overload
def get_rootdir(as_path: bool) -> PathLike: ...

def get_rootdir(as_path: bool = False) -> PathLike:
    """
    Get the project's root directory.

    Args
    ----
    as_path : bool, optional
        Whether to return the path as ``pathlib.Path``.
    """
    base_path: Path
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        # Current file location: .../xidown/xidown/core/utils.py
        base_path = Path(__file__).absolute().parent.parent.parent
    return base_path if as_path else str(base_path)

@overload
def get_bin_folder() -> str: ...
@overload
def get_bin_folder(as_path: Literal[True]) -> Path: ...
@overload
def get_bin_folder(as_path: Literal[False]) -> str: ...
@overload
def get_bin_folder(as_path: bool) -> PathLike: ...

def get_bin_folder(as_path: bool = False) -> PathLike:
    """
    Get the project's binary directory, relative to project's root directory.

    Args
    ----
    as_path : bool, optional
        Whether to return the path as ``pathlib.Path``.
    """
    bin_path = get_rootdir(True) / 'bin'
    return bin_path if as_path else str(bin_path)

def check_setup() -> Optional[Tuple[str, str, str]]:
    """
    Verify the existence of external binaries (ffmpeg & yt-dlp).
    Checks system PATH first, then falls back to local bin directory.
    Supports both the new directory structure and compiled executable (.exe) modes.

    Returns
    -------
    Tuple[str, str, str]
        A tuple containing, yt-dlp path, ffmpeg path, and cookies path. Otherwise,
        returns None if cannot find neither ffmpeg nor yt-dlp binary.
    """
    # Expected executable names based on OS
    is_win = is_windows()
    yt_dlp_name = "yt-dlp.exe" if is_win else "yt-dlp"
    ffmpeg_name = "ffmpeg.exe" if is_win else "ffmpeg"

    bin_folder = get_bin_folder(True)

    # Prioritize local bin folder first (standalone portability)
    local_yt = bin_folder / yt_dlp_name
    path_yt_dlp = local_yt if local_yt.is_file() else None

    local_ff = bin_folder / ffmpeg_name
    path_ffmpeg = local_ff if local_ff.is_file() else None

    # Fallback to system PATH if not found in local bin folder
    if not path_yt_dlp:
        _temp = shutil.which(yt_dlp_name)
        path_yt_dlp = Path(_temp) if _temp else None

    if not path_ffmpeg:
        _temp = shutil.which(ffmpeg_name)
        path_ffmpeg = Path(_temp) if _temp else None

    # Optional Cookie file path
    path_cookies = bin_folder / "cookies.txt"

    missing = []
    if not path_yt_dlp: missing.append(yt_dlp_name)
    if not path_ffmpeg: missing.append(ffmpeg_name)

    # Optional config: Default cookies path might not exist, ignore if missing
    if not path_cookies.is_file():
        pass

    if missing:
        # Enhanced error message for debugging paths
        print(f"[Utils] Searching binaries in System PATH and: {bin_folder}", file=sys.stderr)
        print(f"[Utils] ERROR: Missing: {', '.join(missing)}", file=sys.stderr)
        return None

    # yt-dlp expects the directory containing ffmpeg, not the executable file itself, or it can accept the executable path.
    # Returning dirname is safer for yt-dlp's --ffmpeg-location if it's in the system path.
    ffmpeg_dir = path_ffmpeg.parent if path_ffmpeg else bin_folder

    return str(path_yt_dlp), str(ffmpeg_dir), str(path_cookies)

# --- SIZE FORMATTING UTILITIES ---
def format_size(bytes_size: float) -> str:
    if not bytes_size: return "Unknown"
    power = 1024
    n = 0
    power_labels = {0 : '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while bytes_size > power:
        bytes_size /= power
        n += 1
    return f"{bytes_size:.2f} {power_labels[n]}"

def hitung_estimasi_mp3(duration_detik: int) -> str:
    if not duration_detik: return "Unknown"
    try:
        total_bytes = int(duration_detik) * 16 * 1024 
        return format_size(total_bytes)
    except Exception:
        return "Unknown"

def get_icon_path() -> Optional[str]:
    """
    Retrieve the safe absolute path to assets/favicon.ico.

    Returns
    -------
    str
        A string path refers to the image, or None if cannot be found.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = get_rootdir(True)
        
    favicon_path = base_path.joinpath(*FAVICON_PATH.split('/'))

    if favicon_path.is_file():
        return str(favicon_path)

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

    exe_path = Path(sys.executable).absolute()
    base_path = exe_path.parent
    data_dir = base_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    flag_file = data_dir / ".shortcut_created"
    if flag_file.exists(): return

    try:
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

        creation_flags = 0x08000000  # CREATE_NO_WINDOW
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
