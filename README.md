# xidown

xidown is a powerful, cross-platform GUI-based video and audio downloader built with Python. Designed with a premium, dark-themed CustomTkinter UI, xidown lets you effortlessly scan, queue, and download media using `yt-dlp` and `ffmpeg`.

![xidown Interface](xidownv0.2516.png)

---

## What's New

- **Zero Antivirus Warnings:** Recompiled natively with Nuitka to completely eliminate false positive virus detections (like Wacatac) and improve performance.
- **Setup Wizard Installer:** Replaced manual zip extraction with a professional, easy-to-use Windows Installer (`setup.exe`).
- **Smart Portable Mode:** Download the `.zip` version and run it directly from a USB drive! It automatically detects portable mode and saves all data locally without touching the host PC.
- **Organized Downloads:** Automatically stores all downloads, caches, and history cleanly inside your OS's native `Videos/xidown` folder.
- **Premium Aesthetics:** Features perfect layout symmetry, flat square scrollbars, and tactile CustomTkinter interfaces.

---

## Key Features

- **Modern & Premium UI:** Built with CustomTkinter featuring custom color palettes, fluid animations, and a high-contrast dark aesthetic.
- **Interactive Queue (Drag & Drop):** Easily reorder scanned videos by dragging and dropping the cards.
- **Advanced Context Menus:** Right-click cards to **Pin/Unpin** items, **Test Play (15s)** to preview, **Download Item** instantly, or **Delete** from queue.
- **Intelligent Playlist Guard:** Prompts a confirmation dialog when pasting large playlists to prevent UI overload.
- **Browser Extension Integration:** Built-in Flask server (Maribel Server) runs silently on port 3000 to catch download links instantly from the companion browser extension.
- **Smart Cookie Management:** Easily import Netscape cookies per domain to bypass age restrictions and login walls, with built-in YouTube API spoofing.
- **Caching & Cleaner Manager:** Caches thumbnails and includes a one-click manager to clear temporary files and broken downloads.
- **History & Session Recovery:** Undo/redo actions in the scan list and recover previously scanned sessions on startup.

---

## Prerequisites

- Python 3.8+
- **ffmpeg and yt-dlp:** Required for scanning and downloading.
  - **Windows:** Automatically prompted to download to the local `bin/` folder on first run if missing from system PATH.
  - **Linux / macOS:** Can be installed manually via package managers (e.g., `sudo apt update && sudo apt install ffmpeg yt-dlp` or `brew install ffmpeg yt-dlp`).

---

## Installation & Setup

### Option 1: Standalone Release (Recommended)
Download the pre-compiled package for your OS from the [Releases](https://github.com/indravoyager/xidown/releases) page.
1. Download the release for your platform.
2. Run the application:
   - **Windows:** Download the `-setup.exe` installer for an automated, User-Level installation (no admin rights needed), or grab the `-portable.zip` version to run it directly from a USB drive.
   - **Linux:** Download the `.zip`, extract it, open a terminal in the folder, make it executable, and run:
     ```bash
     chmod +x xidown
     ./xidown
     ```
   - **macOS:** Download the `.zip`, extract it, and simply double-click **`xidown.app`** (or run `open xidown.app` in your terminal).

### Option 2: Run from Source (For Developers)
1. **Clone the repo:**
   ```bash
   git clone https://github.com/indravoyager/xidown.git
   cd xidown
   ```
2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   # Activate:
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows (CMD)
   ```
3. **Install in editable mode:**
   ```bash
   pip install -e .
   ```
4. **Run the application:**
   Once installed, you can launch the app from any directory:
   ```bash
   xidown
   ```
   Or run it directly as a module from the project root:
   ```bash
   python -m xidown
   ```

### Option 3: Build from Source
xidown uses [Nuitka](https://nuitka.net/) to compile Python into native C binaries.

**Requirements:**
- Python 3.8+
- C compiler: **MSVC** (Windows), **GCC** (Linux), or **Xcode CLT** (macOS)

**Steps:**
```bash
pip install -e .
pip install nuitka ordered-set
python build.py
```
The compiled output will be in `dist/app.dist/` and a release `.zip` in `releases/`.

---

## Browser Extension Setup
To catch download links directly from your browser:
1. Clone or download the extension: [xidown_ext](https://github.com/indravoyager/xidown_ext)
2. Open your Chromium browser and go to `chrome://extensions/`.
3. Enable **Developer mode** (top-right toggle).
4. Click **"Load unpacked"** and select the extension folder.
5. The extension will now automatically send links to xidown whenever the app is running!

---

## Project Structure

```text
xidown/
├── assets/              # Icons and image resources
├── bin/                 # Auto-downloaded yt-dlp and ffmpeg executables
├── xidown/              # Core Python package
│   ├── app.py           # Main application entry point & Flask Server
│   ├── core/            # Download logic, scanning algorithms, and system utilities
│   └── gui/             # CustomTkinter UI layouts, popups, and components
├── build.py             # Nuitka build script for standalone compilation
├── pyproject.toml       # Python package configuration and dependencies
└── README.md
```

---

## License
[MIT](LICENSE)
