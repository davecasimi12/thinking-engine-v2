# Thinking_Engine_8.0.py
# ------------------------------------------------------------
# Version: 8.0  |  Adaptive Reflection + Insight Pooling
# ------------------------------------------------------------
import json, os, time
from datetime import datetime
from typing import Any, Dict, List

VERSION = "8.0"
SCHEMA_VERSION = 4

# ---------- Schema ----------
SCHEMA_KEYS = {
    "last_priority": None,
    "reflections": [],
    "facts": [],
    "goals": [],
    "open_tasks": [],
    "errors": [],
    "insights": [],                # new compressed reflections
    "confidence_scores": {},       # {reflection_id: score}
    "schema_version": SCHEMA_VERSION,
    "last_run": None,
    "extras": {},
}

DATA_DIR = "data"
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")

# ---------- Utilities ----------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def iso_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _read_json(path: str, default: Any) -> Any:
    try:
        if not os.path.isfile(path): return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_json(path: str, data: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

# ---------- Memory Core ----------
class Memory:
    def __init__(self, path: str):
        self.path = path
        _ensure_dirs()
        self.data: Dict[str, Any] = {}

    def load(self):
        raw = _read_json(self.path, default={})
        healed = {}
        extras = raw.get("extras", {})
        if not isinstance(extras, dict): extras = {}
        for k, v in raw.items():
            if k not in SCHEMA_KEYS: extras[k] = v
        for k, v in SCHEMA_KEYS.items():
            healed[k] = raw.get(k, v)
        healed["extras"] = extras
        healed["schema_version"] = SCHEMA_VERSION
        self.data = healed

    def save(self): _write_json(self.path, self.data)
    def touch_run(self): self.data["last_run"] = iso_now()
    def add_reflection(self, txt): self.data["reflections"].append(txt)
    def add_insight(self, txt): self.data["insights"].append(txt)
    def add_error(self, msg):
        self.data["errors"].append(f"{iso_now()} :: {msg}")
        self.data["errors"] = self.data["errors"][-50:]

# ---------- Adaptive Reflection Engine ----------
class ReflectionEngine:
    def __init__(self, memory: Memory):
        self.memory = memory

    def analyze_emotion(self, text: str) -> str:
        text = text.lower()
        if any(x in text for x in ["why", "doubt", "uncertain"]): return "curious"
        if any(x in text for x in ["fail", "hard", "struggle"]): return "reflective"
        if any(x in text for x in ["goal", "achieve", "plan"]): return "motivated"
        return "neutral"

    def compute_confidence(self, text: str) -> int:
        base = 3
        if "!" in text: base += 1
        if "?" in text: base -= 1
        return max(1, min(5, base))

    def compress_insight(self, reflections: List[str]) -> str:
        if not reflections: return "No reflections to compress."
        last = reflections[-1]
        if "why" in last.lower(): return f"Insight: questioning pattern → {last}"
        if "how" in last.lower(): return f"Insight: exploring method → {last}"
        return f"Insight: continuity noted → {last}"

    def reflect(self) -> Dict[str, Any]:
        mem = self.memory
        prev = mem.data.get("reflections", [])
        last = prev[-1] if prev else ""
        emotion = self.analyze_emotion(last)
        confidence = self.compute_confidence(last)
        next_p = mem.data.get("last_priority") or "Plan: Define next objective."

        thought = f"[{iso_now()}] Building on prior reflection. Emotion={emotion}. Priority={next_p}"
        mem.add_reflection(thought)
        mem.data["confidence_scores"][str(len(prev))] = confidence

        # compress reflections every 3 runs
        if len(mem.data["reflections"]) % 3 == 0:
            compressed = self.compress_insight(mem.data["reflections"])
            mem.add_insight(compressed)

        return {"emotion": emotion, "confidence": confidence, "thought": thought}

# ---------- Logging ----------
def append_session_log(entry: Dict[str, Any]):
    log = _read_json(SESSION_LOG, default=[])
    if not isinstance(log, list): log = []
    log.append(entry)
    log = log[-500:]
    _write_json(SESSION_LOG, log)

# ---------- Boot Display ----------
def boot_banner(mem: Memory, report: Dict[str, Any]) -> str:
    return (
        f"Thinking Engine {VERSION} Online\n"
        f"- Schema v{SCHEMA_VERSION} OK | Memory healed & loaded\n"
        f"- Emotion: {report.get('emotion')} | Confidence: {report.get('confidence')}/5\n"
        f"- Insights: {len(mem.data.get('insights', []))}\n"
        f"- Reflections: {len(mem.data.get('reflections', []))}\n"
        f"- Goals: {len(mem.data.get('goals', []))} | Tasks: {len(mem.data.get('open_tasks', []))}\n"
    )

# ---------- Main ----------
def main():
    _ensure_dirs()
    mem = Memory(MEMORY_PATH)
    mem.load()

    engine = ReflectionEngine(mem)
    report = engine.reflect()
    mem.touch_run()
    mem.save()

    append_session_log({
        "ts": iso_now(),
        "version": VERSION,
        "report": report,
        "reflections": len(mem.data["reflections"]),
        "insights": len(mem.data["insights"]),
    })
    print(boot_banner(mem, report))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _ensure_dirs()
        mem = Memory(MEMORY_PATH)
        mem.load()
        mem.add_error(f"Fatal: {repr(e)}")
        mem.save()
        raise