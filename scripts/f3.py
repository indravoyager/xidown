import threading
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
sys.path.append(os.path.join(os.path.dirname(__file__), "src", "ui"))
import logic.logic_scanner as scanner
import logic.utils as utils

tools = utils.check_setup()
if not tools:
    print("Tools not found")
    sys.exit()

stop_event = threading.Event()
config = {"quality": "best"}
meta_cache = {}

def callback_log(msg):
    print("LOG:", msg)

def callback_progress(msg, p):
    print("PROG:", msg)

def callback_item_found(data):
    print("\n--- ITEM FOUND ---")
    print("Title:", data.get('title'))
    subs = data.get('subs', {})
    print("Subtitles count:", len(subs))
    for k, v in subs.items():
        print(f" - {k}: {v}")

scanner.scan_single_url(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    tools,
    None,
    callback_log,
    callback_progress,
    callback_item_found,
    stop_event,
    config,
    meta_cache
)
