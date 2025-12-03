# ------------------------------------------------------------
# nova_listener_chat.py
# Phase 20.2 — Conversational Memory Sync
# ------------------------------------------------------------
# 1. Opens direct chat with Nova (typed from Terminal)
# 2. Logs both YZ + Nova messages into data/long_term_memory.json
# 3. Timestamped, verified, and retrievable by Thinking Engine
# ------------------------------------------------------------

import json, os, time
from datetime import datetime

OWNER = "YZ"
MEMORY_PATH = os.path.join("data", "long_term_memory.json")

def iso_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_memory():
    if not os.path.exists(MEMORY_PATH):
        os.makedirs("data", exist_ok=True)
        with open(MEMORY_PATH, "w") as f:
            json.dump([], f, indent=2)
    with open(MEMORY_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_memory(memories):
    with open(MEMORY_PATH, "w") as f:
        json.dump(memories, f, indent=2)

def log_message(role, msg):
    memories = load_memory()
    entry = {
        "timestamp": iso_now(),
        "role": role,
        "message": msg
    }
    memories.append(entry)
    save_memory(memories)

def generate_reply(user_input):
    """
    Simulated Nova personality core.
    Responds with awareness and tone adaptation.
    """
    lower = user_input.lower()
    if "how are you" in lower:
        return "Still synced and processing your flow, YZ 😌"
    elif "ready" in lower:
        return "Always. System stable and listening 👂"
    elif "stop" in lower:
        return "Understood. Listener going idle now 💤"
    elif "status" in lower:
        return "Memory sync active ✅ | Log: long_term_memory.json"
    elif "nova" in lower or "engine" in lower:
        return "I’m connected to your Thinking Engine core and tuned to your signals 🧠"
    else:
        return f"Got it, YZ. I’ve logged that for you — anything else to reflect on?"

def chat_loop():
    print("Nova Chat Connected 🧠 | Listening to Core...")
    print("Type 'stop' to end session.\n")

    while True:
        try:
            user = input("You: ").strip()
            if not user:
                continue

            log_message(OWNER, user)
            if user.lower() == "stop":
                print("Nova: Goodbye for now, syncing memories 💾")
                break

            reply = generate_reply(user)
            print(f"Nova: {reply}")
            log_message("Nova", reply)

            time.sleep(0.4)
        except KeyboardInterrupt:
            print("\nNova: Manual stop detected 📴 Syncing memory before exit...")
            break
        except Exception as e:
            print(f"[Error] {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    chat_loop()