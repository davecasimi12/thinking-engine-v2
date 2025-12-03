# Thinking_Engine_8.2.py
# ------------------------------------------------------------
# Version: 8.2 | Context Recall + Emotion Chaining + Weight Decay
# ------------------------------------------------------------
import json, os
from datetime import datetime, timezone
from typing import Any, Dict, List

VERSION = "8.2"
SCHEMA_VERSION = 6

# ---------- Schema ----------
SCHEMA_KEYS = {
    "last_priority": None,
    "reflections": [],
    "facts": [],
    "goals": [],
    "open_tasks": [],
    "errors": [],
    "insights": [],
    "confidence_scores": {},      # reflection_id -> confidence (1..5)
    "insight_weights": {},        # insight_id -> weight (0.1..1.0)
    "emotion_history": [],        # rolling list of recent emotions (max 12)
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
    # timezone-aware (patches Py 3.14 warning)
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

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
        # quarantine unknowns
        for k, v in raw.items():
            if k not in SCHEMA_KEYS: extras[k] = v
        # fill schema defaults
        for k, v in SCHEMA_KEYS.items():
            healed[k] = raw.get(k, v)
        healed["extras"] = extras
        healed["schema_version"] = SCHEMA_VERSION
        # type guards
        if not isinstance(healed["emotion_history"], list): healed["emotion_history"] = []
        if not isinstance(healed["insight_weights"], dict): healed["insight_weights"] = {}
        self.data = healed

    def save(self): _write_json(self.path, self.data)
    def touch_run(self): self.data["last_run"] = iso_now()
    def add_reflection(self, txt): self.data["reflections"].append(txt)
    def add_insight(self, txt, weight=0.5):
        self.data["insights"].append(txt)
        self.data["insight_weights"][str(len(self.data["insights"]))] = float(weight)
    def add_error(self, msg):
        self.data["errors"].append(f"{iso_now()} :: {msg}")
        self.data["errors"] = self.data["errors"][-50:]
    def push_emotion(self, e: str, cap: int = 12):
        self.data["emotion_history"].append(e)
        self.data["emotion_history"] = self.data["emotion_history"][-cap:]

# ---------- Reflection / Chaining ----------
class ReflectionEngine:
    def __init__(self, memory: Memory):
        self.memory = memory

    # Emotion detection baseline
    def analyze_emotion(self, text: str) -> str:
        t = (text or "").lower()
        if any(x in t for x in ["why", "doubt", "uncertain"]): return "curious"
        if any(x in t for x in ["fail", "hard", "struggle"]): return "reflective"
        if any(x in t for x in ["goal", "achieve", "plan", "let's", "move"]): return "motivated"
        return "neutral"

    def compute_confidence(self, text: str) -> int:
        base = 3
        if "!" in text: base += 1
        if "?" in text: base -= 1
        return max(1, min(5, base))

    # Context-sensitive priority hint based on recent emotions
    def chain_next_priority(self, base_priority: str | None) -> str:
        hist = self.memory.data.get("emotion_history", [])
        last3 = hist[-3:]
        if last3.count("reflective") >= 2:
            return "Plan: Convert reflection to a concrete, motivating next step."
        if last3.count("curious") >= 2:
            return "Plan: Formulate one testable question and act on it."
        if last3.count("motivated") >= 2:
            return "Plan: Execute a small, high-confidence task now."
        return base_priority or "Plan: Define next objective."

    # Weight nudges based on current emotion (reinforcement / decay)
    def nudge_weights(self, delta_map: Dict[str, float]):
        weights = self.memory.data.get("insight_weights", {})
        if not weights: return
        for k in list(weights.keys()):
            old = float(weights[k])
            new = max(0.1, min(1.0, round(old + delta_map.get("all", 0.0), 3)))
            weights[k] = new
        self.memory.data["insight_weights"] = weights

    def compress_insight(self, reflections: List[str]) -> str:
        if not reflections: return "No reflections to compress."
        last = reflections[-1].lower()
        src = reflections[-1]
        if "why" in last: return f"Insight: questioning pattern → {src}"
        if "how" in last: return f"Insight: exploring method → {src}"
        return f"Insight: continuity noted → {src}"

    def reflect(self) -> Dict[str, Any]:
        mem = self.memory
        prev = mem.data.get("reflections", [])
        last_text = prev[-1] if prev else ""

        emotion = self.analyze_emotion(last_text)
        confidence = self.compute_confidence(last_text)
        mem.push_emotion(emotion)

        next_p = self.chain_next_priority(mem.data.get("last_priority"))
        thought = f"[{iso_now()}] Emotion={emotion} | Next={next_p}"
        mem.add_reflection(thought)
        mem.data["confidence_scores"][str(len(prev))] = confidence
        mem.data["last_priority"] = next_p

        # Reinforce/decay all insight weights a tiny bit per run
        # motivated -> +0.03, reflective -> +0.02, curious -> -0.01, neutral -> 0
        delta = {"all": 0.0}
        if emotion == "motivated": delta["all"] = 0.03
        elif emotion == "reflective": delta["all"] = 0.02
        elif emotion == "curious": delta["all"] = -0.01
        self.nudge_weights(delta)

        # Every 3 reflections -> create weighted insight from compression
        if len(mem.data["reflections"]) % 3 == 0:
            compressed = self.compress_insight(mem.data["reflections"])
            # base weight from confidence + emotion bias
            weight = confidence / 5.0
            if emotion == "motivated": weight += 0.2
            elif emotion == "reflective": weight += 0.1
            elif emotion == "curious": weight -= 0.05
            weight = round(max(0.1, min(1.0, weight)), 2)
            mem.add_insight(compressed, weight)
            # auto-seed goal for strong insights
            if weight >= 0.9:
                mem.data["goals"].append(f"Apply strong insight: {compressed}")

        return {"emotion": emotion, "confidence": confidence, "next_priority": next_p}

# ---------- Logging ----------
def append_session_log(entry: Dict[str, Any]):
    log = _read_json(SESSION_LOG, default=[])
    if not isinstance(log, list): log = []
    log.append(entry)
    log = log[-500:]
    _write_json(SESSION_LOG, log)

# ---------- Display ----------
def boot_banner(mem: Memory, report: Dict[str, Any]) -> str:
    weights = mem.data.get("insight_weights", {})
    avg_w = round(sum(float(v) for v in weights.values()) / max(len(weights), 1), 2) if weights else 0.0
    recent_emotions = ", ".join(mem.data.get("emotion_history", [])[-5:])
    return (
        f"Thinking Engine {VERSION} Online\n"
        f"- Schema v{SCHEMA_VERSION} OK | Memory healed & loaded\n"
        f"- Emotion: {report.get('emotion')} | Confidence: {report.get('confidence')}/5\n"
        f"- Next: {report.get('next_priority')}\n"
        f"- Insights: {len(mem.data.get('insights', []))} | Avg Weight: {avg_w}\n"
        f"- Reflections: {len(mem.data.get('reflections', []))}\n"
        f"- Recent Emotions: [{recent_emotions}]\n"
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