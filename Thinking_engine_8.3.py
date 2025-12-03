# Thinking_Engine_8.3.py
# ------------------------------------------------------------
# Version: 8.3 | Task Generator + Priority Scoring + Auto-Progress
# ------------------------------------------------------------
import json, os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

VERSION = "8.3"
SCHEMA_VERSION = 7

# ---------- Schema ----------
SCHEMA_KEYS = {
    "last_priority": None,          # str | None (top task to focus)
    "reflections": [],              # List[str]
    "facts": [],                    # List[str]
    "goals": [],                    # List[str]
    "open_tasks": [],               # List[str] (task texts)
    "completed_tasks": [],          # List[str]
    "task_scores": {},              # Dict[str, float] -> priority score (0.1..1.0)
    "errors": [],                   # List[str]
    "insights": [],                 # List[str]
    "confidence_scores": {},        # Dict[str, int] reflection_id -> confidence
    "insight_weights": {},          # Dict[str, float] insight_id -> weight
    "emotion_history": [],          # List[str] recent emotions (max 12)
    "schema_version": SCHEMA_VERSION,
    "last_run": None,               # ISO timestamp
    "extras": {},                   # quarantine for unknown keys
}

DATA_DIR = "data"
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")

# ---------- Utilities ----------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def iso_now() -> str:
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
        # quarantine unknown keys
        for k, v in raw.items():
            if k not in SCHEMA_KEYS: extras[k] = v
        # fill with defaults
        for k, v in SCHEMA_KEYS.items():
            healed[k] = raw.get(k, v)
        healed["extras"] = extras
        healed["schema_version"] = SCHEMA_VERSION

        # guards
        for key, typ in [
            ("open_tasks", list), ("completed_tasks", list), ("reflections", list),
            ("goals", list), ("errors", list), ("insights", list), ("emotion_history", list),
        ]:
            if not isinstance(healed.get(key), typ): healed[key] = typ()
        for key, typ in [("task_scores", dict), ("confidence_scores", dict), ("insight_weights", dict)]:
            if not isinstance(healed.get(key), typ): healed[key] = typ()

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
    def add_task(self, task: str, score: float):
        if not task: return
        if task not in self.data["open_tasks"]:
            self.data["open_tasks"].append(task)
        # always keep highest score seen for the task
        prev = float(self.data["task_scores"].get(task, 0.0))
        self.data["task_scores"][task] = round(max(prev, score), 3)

# ---------- Reflection + Task Engine ----------
class Engine:
    def __init__(self, memory: Memory):
        self.mem = memory

    # --- Emotion & confidence ---
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

    # --- Priority chaining from emotion history ---
    def chain_next_priority(self, base_priority: str | None) -> str:
        hist = self.mem.data.get("emotion_history", [])
        last3 = hist[-3:]
        if last3.count("reflective") >= 2:
            return "Plan: Convert reflection to a concrete, motivating next step."
        if last3.count("curious") >= 2:
            return "Plan: Formulate one testable question and act on it."
        if last3.count("motivated") >= 2:
            return "Plan: Execute a small, high-confidence task now."
        return base_priority or "Plan: Define a clear goal and first task."

    # --- Weight nudging for insights ---
    def nudge_insight_weights(self, emotion: str):
        delta = 0.0
        if emotion == "motivated": delta = 0.03
        elif emotion == "reflective": delta = 0.02
        elif emotion == "curious": delta = -0.01
        weights = self.mem.data.get("insight_weights", {})
        if not weights: return
        for k in list(weights.keys()):
            old = float(weights[k])
            new = max(0.1, min(1.0, round(old + delta, 3)))
            weights[k] = new
        self.mem.data["insight_weights"] = weights

    # --- Reflection compression ---
    def compress_insight(self, reflections: List[str]) -> str:
        if not reflections: return "No reflections to compress."
        last = reflections[-1].lower()
        src = reflections[-1]
        if "why" in last: return f"Insight: questioning pattern → {src}"
        if "how" in last: return f"Insight: exploring method → {src}"
        return f"Insight: continuity noted → {src}"

    # --- Task scoring helper ---
    def score_task(self, base_weight: float, emotion: str, confidence: int) -> float:
        score = base_weight
        if emotion == "motivated": score += 0.10
        elif emotion == "reflective": score += 0.05
        elif emotion == "curious": score -= 0.05
        score += (confidence - 3) * 0.05   # +/- for punctuation confidence
        return round(max(0.1, min(1.0, score)), 2)

    # --- Task generation from an insight or priority hint ---
    def generate_tasks_from(self, source: str, base_weight: float, emotion: str, confidence: int) -> List[Tuple[str, float]]:
        src = (source or "the current priority").strip()
        tasks = [
            (f"Define the objective for: {src} (1 sentence).", None),
            (f"List 3 concrete steps toward: {src}.", None),
            (f"Do a 5-minute starter action for: {src}.", None),
        ]
        out: List[Tuple[str, float]] = []
        for t, _ in tasks:
            out.append((t, self.score_task(base_weight, emotion, confidence)))
        return out

    # --- Main reasoning step ---
    def step(self) -> Dict[str, Any]:
        mem = self.mem
        prev = mem.data.get("reflections", [])
        last_text = prev[-1] if prev else ""

        emotion = self.analyze_emotion(last_text)
        confidence = self.compute_confidence(last_text)
        mem.push_emotion(emotion)

        next_hint = self.chain_next_priority(mem.data.get("last_priority"))
        thought = f"[{iso_now()}] Emotion={emotion} | Next={next_hint}"
        mem.add_reflection(thought)
        mem.data["confidence_scores"][str(len(prev))] = confidence

        # nudge insight weights a little each run
        self.nudge_insight_weights(emotion)

        # Every 3 reflections -> compress to insight and possibly generate tasks
        maybe_tasks: List[Tuple[str, float]] = []
        if len(mem.data["reflections"]) % 3 == 0:
            compressed = self.compress_insight(mem.data["reflections"])
            base_weight = confidence / 5.0
            if emotion == "motivated": base_weight += 0.20
            elif emotion == "reflective": base_weight += 0.10
            elif emotion == "curious": base_weight -= 0.05
            base_weight = max(0.1, min(1.0, round(base_weight, 2)))
            mem.add_insight(compressed, base_weight)
            # Generate tasks if strong enough or if no tasks exist
            if base_weight >= 0.70 or not mem.data["open_tasks"]:
                maybe_tasks = self.generate_tasks_from(compressed, base_weight, emotion, confidence)

        # If still no tasks at all, seed from next_hint so queue never stays empty
        if not maybe_tasks and not mem.data["open_tasks"]:
            maybe_tasks = self.generate_tasks_from(next_hint, 0.6, emotion, confidence)

        # Merge tasks into memory and pick the top one
        for task, score in maybe_tasks:
            mem.add_task(task, score)

        top_task = None
        if mem.data["open_tasks"]:
            # choose highest scoring task
            top_task = max(mem.data["open_tasks"], key=lambda t: mem.data["task_scores"].get(t, 0.1))
            mem.data["last_priority"] = top_task

        return {
            "emotion": emotion,
            "confidence": confidence,
            "next_priority": mem.data.get("last_priority") or next_hint,
            "task_count": len(mem.data["open_tasks"]),
            "top_task": top_task,
            "top_score": mem.data["task_scores"].get(top_task, 0.0) if top_task else 0.0,
        }

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
    top_task = report.get("top_task") or "None"
    top_score = round(float(report.get("top_score", 0.0)), 2)
    return (
        f"Thinking Engine {VERSION} Online\n"
        f"- Schema v{SCHEMA_VERSION} OK | Memory healed & loaded\n"
        f"- Emotion: {report.get('emotion')} | Confidence: {report.get('confidence')}/5\n"
        f"- Insights: {len(mem.data.get('insights', []))} | Avg Weight: {avg_w}\n"
        f"- Reflections: {len(mem.data.get('reflections', []))}\n"
        f"- Tasks: {len(mem.data.get('open_tasks', []))} | Top: {top_task} (score {top_score})\n"
        f"- Next: {report.get('next_priority')}\n"
        f"- Recent Emotions: [{recent_emotions}]\n"
        f"- Goals: {len(mem.data.get('goals', []))}\n"
    )

# ---------- Main ----------
def main():
    _ensure_dirs()
    mem = Memory(MEMORY_PATH)
    mem.load()

    engine = Engine(mem)
    report = engine.step()
    mem.touch_run()
    mem.save()

    append_session_log({
        "ts": iso_now(),
        "version": VERSION,
        "report": report,
        "reflections": len(mem.data["reflections"]),
        "insights": len(mem.data["insights"]),
        "tasks": len(mem.data["open_tasks"]),
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