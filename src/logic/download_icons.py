import os
import urllib.request
import sys

def download_icons():
    # Setup path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icon_dir = os.path.join(base_dir, "assets", "icons")
    
    if not os.path.exists(icon_dir):
        os.makedirs(icon_dir)

    # Dictionary of icons (name: icon8_id)
    # Using 'fluency-systems-regular' which is very clean and resembles Tailwind/Heroicons
    icons = {
        "settings.png": "settings",
        "notes.png": "document",
        "folder.png": "opened-folder",
        "delete.png": "trash",
        "video.png": "video",
        "audio.png": "musical-notes",
        "clear.png": "broom",
        "paste.png": "paste",
        "search.png": "search"
    }

    print("Downloading modern icons...")
    for filename, icon_id in icons.items():
        url = f"https://img.icons8.com/fluency-systems-regular/32/ffffff/{icon_id}.png"
        filepath = os.path.join(icon_dir, filename)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
            print(f"[OK] {filename}")
        except Exception as e:
            print(f"[FAIL] {filename}: {e}")

if __name__ == "__main__":
    download_icons()
