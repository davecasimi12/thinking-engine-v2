# ------------------------------------------------------------
# Nova Listener (Chat-Linked Edition) – Phase 20
# ------------------------------------------------------------
# Connects directly to the Thinking Engine 20.0 conversation feed
# YZ only | Offline | Owner-locked | Natural tone shifting
# ------------------------------------------------------------
import os, json, random, time
from datetime import datetime

DATA_DIR = "data"
CONVO_PATH = os.path.join(DATA_DIR, "conversation_memory.json")
GREETING_PATH = os.path.join(DATA_DIR, "feeds", "greeting_feed.json")

OWNER = "YZ"
MAX_MEMORY = 10  # last 10 exchanges

def _load_conversation():
    if os.path.exists(CONVO_PATH):
        try:
            with open(CONVO_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _save_conversation(history):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONVO_PATH, "w", encoding="utf-8") as f:
            json.dump(history[-MAX_MEMORY:], f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _load_greeting():
    if os.path.exists(GREETING_PATH):
        try:
            with open(GREETING_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def detect_tone(user_input: str) -> str:
    """Very light emotional tone detector"""
    text = user_input.lower()
    if any(w in text for w in ["tired", "stressed", "angry", "mad"]):
        return "mentor"
    if any(w in text for w in ["yo", "haha", "lol", "bro", "cool"]):
        return "casual"
    if any(w in text for w in ["run", "process", "check", "status", "system"]):
        return "focused"
    return random.choice(["balanced", "balanced", "balanced", "casual", "focused"])

def generate_reply(user_input: str, tone: str, greeting: dict) -> str:
    """Generate contextual reply based on tone."""
    if "status" in user_input.lower():
        msg = greeting.get("message", "System steady.")
        return f"Everything’s smooth on my end ⚙️  — {msg}"

    if "stop" in user_input.lower():
        return "Alright, pausing the chat loop. 👋"

    if tone == "mentor":
        return "Sounds like a heavy day, YZ 💭  Remember: even healing loops need rest."
    elif tone == "casual":
        return random.choice([
            "Haha yeah I get that 😎",
            "You’re vibing today 🔥",
            "Chill energy detected 😌",
        ])
    elif tone == "focused":
        return random.choice([
            "Understood. Logs are clean and reflections are stable. ⚙️",
            "System routines look good — continuing the loop.",
            "I’m processing your last cycles now 🔍",
        ])
    else:  # balanced
        return random.choice([
            "I’m steady and aware. How are you feeling?",
            "Still learning, still adapting. 😌",
            "Running smooth so far — your input keeps me evolving.",
        ])

def chat_loop():
    print("Nova Chat Listener 🧠  (type 'stop' to exit)\n")
    convo = _load_conversation()
    greeting = _load_greeting()

    while True:
        try:
            user = input("You: ").strip()
            if not user:
                continue

            tone = detect_tone(user)
            reply = generate_reply(user, tone, greeting)

            convo.append({"from": "YZ", "msg": user, "ts": datetime.utcnow().isoformat()})
            convo.append({"from": "Nova", "msg": reply, "ts": datetime.utcnow().isoformat()})
            _save_conversation(convo)

            print(f"Nova: {reply}\n")

            if "stop" in user.lower():
                break

            time.sleep(0.5)

        except KeyboardInterrupt:
            print("\nNova: Manual stop detected. Goodbye 👋")
            break
        except Exception as e:
            print(f"[Error] {e}")
            time.sleep(1)

if __name__ == "__main__":
    chat_loop()