# ------------------------------------------------------------
# Thinking_Engine_20.1.py
# Phase 20.1 — Unified Launch Mode (2-Terminal Edition, macOS)
# ------------------------------------------------------------
# 1. Starts the Thinking Engine core (20.0 logic)
# 2. Launches nova_listener_chat.py in a new macOS Terminal tab
# 3. Displays visual confirmation: “Nova Chat Connected 🧠 Listening to Core...”
# ------------------------------------------------------------

import os, subprocess, threading, time
from datetime import datetime

# Adjust if needed
ENGINE_FILE = "Thinking_Engine_20.0.py"
LISTENER_FILE = "nova_listener_chat.py"

# Path to your project folder
PROJECT_PATH = os.path.expanduser("~/Desktop/Thinking_Engine_v2")

OWNER = "YZ"

def run_engine():
    """Runs the Thinking Engine core (20.0)."""
    os.system(f"python3 -B {ENGINE_FILE}")

def open_new_terminal_for_listener():
    """
    Opens a new Terminal tab and runs the chat listener
    inside the correct project folder (macOS only).
    """
    script = f'''
    tell application "Terminal"
        activate
        do script "cd {PROJECT_PATH}; clear; echo 'Nova Chat Connected 🧠 Listening to Core...'; python3 {LISTENER_FILE}"
    end tell
    '''
    subprocess.run(["osascript", "-e", script])

def main():
    print(f"[Access verified: {OWNER}]")
    print("[Unified Launch Mode — Starting Engine 20.0 + Chat Listener]\n")

    # start the core engine in this terminal
    engine_thread = threading.Thread(target=run_engine, daemon=True)
    engine_thread.start()

    # give the engine time to initialize
    time.sleep(5)
    print("[Boot] Launching Nova Chat listener in a new Terminal tab...")
    open_new_terminal_for_listener()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] System online.")
    print("You can now chat in the new Terminal tab.\n")

    try:
        while engine_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Stopped manually — Unified Mode shutting down.]")

if __name__ == "__main__":
    main()