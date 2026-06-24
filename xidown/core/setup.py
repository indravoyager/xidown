import os
import sys
import zipfile
from urllib import request
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Union, Optional
from threading import Event

from xidown.core.constants import MAX_CHUNK_SIZE, DEFAULT_USER_AGENT
from xidown.core.types import AnyCallable
from xidown.core.utils import get_bin_folder, safe_rm, safe_rmdir

def download_binary(url: str, dest_path: str,
                    progress_callback: Optional[AnyCallable] = None,
                    cancel_event: Optional[Event] = None) -> bool:
    """
    Downloads a file with progress reporting and cancellation support.
    """
    # Ensure destination directory exists
    dest_dir = Path(dest_path).absolute().parent if dest_path else None
    if dest_dir and not dest_dir.exists():
        dest_dir.mkdir(parents=True)

    req = request.Request(url, headers={ 'User-Agent': DEFAULT_USER_AGENT })
    try:
        with request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = MAX_CHUNK_SIZE
            downloaded = 0

            with open(dest_path, 'wb') as f:
                while True:
                    if cancel_event and cancel_event.is_set():
                        return False

                    block = response.read(block_size)
                    if not block: break

                    f.write(block)
                    downloaded += len(block)
                    if total_size > 0 and progress_callback:
                        percent = downloaded / total_size
                        progress_callback(percent, downloaded, total_size)
            return True
    except Exception as e:
        print(f"[SetupBinaries] Error downloading {url}: {e}", file=sys.stderr)
        return False

def extract_ffmpeg_binaries(zip_path: str, bin_dir: Optional[Union[str, Path]] = None,
                            cancel_event: Optional[Event] = None) -> bool:
    """
    Extracts ffmpeg.exe and ffprobe.exe from the downloaded zip file and places them in bin_dir.
    """
    try:
        if cancel_event and cancel_event.is_set():
            return False

        extracted_members: Dict[str, Union[str, None]] = {
            'ffmpeg': None,
            'ffprobe': None
        }

        # Fallback if bin directory is not provided
        bin_dir = Path(bin_dir) if bin_dir else get_bin_folder(True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Look for ffmpeg.exe and ffprobe.exe inside the zip file
            for member in zip_ref.namelist():
                if member.endswith("ffmpeg.exe"):
                    extracted_members['ffmpeg'] = member
                elif member.endswith("ffprobe.exe"):
                    extracted_members['ffprobe'] = member

                # Break once both ffmpeg and ffprobe has been found
                if extracted_members['ffmpeg'] and extracted_members['ffprobe']:
                    break

        # If the ffmpeg binary file does not exist, then also for ffprobe is not exist
        if not extracted_members['ffmpeg']:
            print("[SetupBinaries] ffmpeg.exe not found in zip archive.", file=sys.stderr)
            return False

        # Extract to temporary directory and move to bin_dir
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_p = Path(tmpdir)
            if cancel_event and cancel_event.is_set():
                return False

            # Extract ffmpeg.exe
            zip_ref.extract(extracted_members['ffmpeg'], tmpdir)
            extracted_path = tmpdir_p / extracted_members['ffmpeg']
            dest_path = bin_dir / "ffmpeg.exe"

            if not bin_dir.exists():
                bin_dir.mkdir(parents=True)

            # Remove any existing ffmpeg file
            if dest_path.exists():
                safe_rm(dest_path)

            shutil.move(extracted_path, dest_path)

            # Extract ffprobe.exe if available
            ffprobe_path = extracted_members['ffprobe']
            if ffprobe_path:
                zip_ref.extract(ffprobe_path, tmpdir)
                extracted_probe_path = tmpdir_p / ffprobe_path
                dest_probe_path = bin_dir / "ffprobe.exe"

                if dest_probe_path.exists():
                    safe_rm(dest_probe_path)

                shutil.move(extracted_probe_path, dest_probe_path)

            # Python <3.11 support, remove the temp directory manually
            safe_rmdir(tmpdir)
        return True
    except Exception as e:
        print(f"[SetupBinaries] Error extracting ffmpeg: {e}", file=sys.stderr)
        return False
