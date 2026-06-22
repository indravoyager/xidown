# xidown

xidown is a powerful, GUI-based video and audio downloading application built with Python. Designed with an aesthetic dark-themed UI (CustomTkinter), xidown enables users to effortlessly scan, preview, and download media using `yt-dlp` and `ffmpeg`.

## Features

- **Modern & Premium UI:** Built with CustomTkinter for a sleek, dark-themed experience.
- **Batch Processing:** Scan playlists or multiple links, and download them simultaneously with multithreading support.
- **Browser Extension Integration:** Built-in Maribel Server (Flask-based) on port 3000 to instantly catch download links from browser extensions.
- **Subtitle Selection:** Choose specific subtitle languages before downloading.
- **Video Preview Cache:** Quickly preview videos directly from the UI before fully downloading them.
- **Cookie Sync:** Import and use cookies for downloading content from protected sites (like Bilibili or Facebook).
- **History Tracking & Session Recovery:** Easily undo/redo actions in your scan list, and remember previously scanned items across sessions.

## Prerequisites

- Python 3.8+
- `ffmpeg` and `yt-dlp` executables must be present in the `bin` directory for processing media formats.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/indravoyager/xidown.git
   cd xidown
   ```

2. **Install the required Python packages:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure you have packages like `customtkinter`, `Flask`, `flask-cors`, and `Pillow` installed).*

3. **Set up binaries:**
   Place `yt-dlp.exe` and `ffmpeg.exe` inside the `bin` folder. The application checks this directory on startup.

## Browser Extension Setup

To enable seamless download link catching directly from your browser, you will need the companion browser extension:

1. Download or clone the extension from its repository: [xidown_ext](https://github.com/indravoyager/xidown_ext)
2. Open your Chromium-based browser (Chrome, Edge, Brave).
3. Navigate to the extensions page: `chrome://extensions/` or `edge://extensions/`.
4. Enable **Developer mode** in the top right corner.
5. Click **"Load unpacked"** and select the folder where you extracted the `xidown_ext` files.
6. Once loaded, the extension will automatically send detected video links to xidown's Maribel server (port 3000) whenever xidown is running.

## Usage

Run the main application using Python:

```bash
python main.py
```

- **Scan:** Paste your video link(s) and click **Scan** to retrieve metadata.
- **Download:** Select the desired format (Video/Audio) and click **Download**.
- **Settings:** Configure threads, proxy, download quality, and default save paths from the settings panel.

## Project Structure

```text
xidown/
├── bin/                 # yt-dlp and ffmpeg executables (User-provided)
├── data/                # History, caches, and thumb previews
├── scripts/             # Development scripts and utilities
├── src/                 # Core source code
│   ├── logic/           # Download logic, scanning algorithms, and versioning
│   └── ui/              # CustomTkinter UI layouts, popups, and components
├── assets/              # Icons and image resources
└── main.py              # Main application entry point
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
