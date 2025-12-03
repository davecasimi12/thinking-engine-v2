# Thinking_Engine_8.3_1.py
# ------------------------------------------------------------
# Version: 8.3.1 | Task Completion + CLI toggles (+ light reinforcement)
# ------------------------------------------------------------
import json, os, argparse
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

VERSION = "8.3.1"
SCHEMA_VERSION = 7  # unchanged from 8.3 (compatible)

# ---------- Schema ----------
SCHEMA_KEYS = {
    "last_priority": None,          # str | None
    "reflections": [],              # List[str]
    "facts": [],                    # List[str]
    "goals": [],                    # List[str]
    "open_tasks": [],               # List[str]
    "completed_tasks": [],          # List[str]
    "task_scores": {},              # Dict[str, float]
    "errors": [],                   # List[str]
    "insights": [],                 # List[str]
    "confidence_scores": {},        # Dict[str, int]
    "insight_weights": {},          # Dict[str, float]
    "emotion_history": [],          # List[str]
    "schema_version": SCHEMA_VERSION,
    "last_run": None,               # ISO timestamp
    "extras": {},                   # quarantine unknown keys
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
        prev = float(self.data["task_scores"].get(task, 0.0))
        self.data["task_scores"][task] = round(max(prev, score), 3)

    def get_top_task(self) -> Tuple[str | None, float]:
        if not self.data["open_tasks"]:
            return None, 0.0
        top = max(self.data["open_tasks"], key=lambda t: self.data["task_scores"].get(t, 0.1))
        return top, float(self.data["task_scores"].get(top, 0.1))

    def complete_task(self, task: str | None = None) -> Dict[str, Any]:
        """Mark a task complete, move it to completed, lightly reinforce insight weights."""
        if not self.data["open_tasks"]:
            return {"ok": False, "msg": "No open tasks."}
        if task is None:
            task, _ = self.get_top_task()
        if task not in self.data["open_tasks"]:
            return {"ok": False, "msg": "Task not found in open_tasks."}
        # Move task
        self.data["open_tasks"] = [t for t in self.data["open_tasks"] if t != task]
        self.data["completed_tasks"].append(task)
        # Light reinforcement of insights when action happens
        weights = self.data.get("insight_weights", {})
        for k in list(weights.keys()):
            old = float(weights[k])
            weights[k] = max(0.1, min(1.0, round(old + 0.02, 3)))  # +0.02 bump
        self.data["insight_weights"] = weights
        self.data["last_priority"] = None  # clear; next run will pick a new top
        return {"ok": True, "msg": f"Completed: {task}"}

# ---------- Engine (reasoning + tasks) ----------
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

    # --- Insight weight nudging ---
    def nudge_insight_weights(self, emotion: str):
        delta = 0.0
        if emotion == "motivated": delta = 0.03
        elif emotion == "reflective": delta = 0.02
        elif emotion == "curious": delta = -0.01
        weights = self.mem.data.get("insight_weights", {})
        if not weights: return
        for k in list(weights.keys()):
            old = float(weights[k])
            weights[k] = max(0.1, min(1.0, round(old + delta, 3)))
        self.mem.data["insight_weights"] = weights

    # --- Compression ---
    def compress_insight(self, reflections: List[str]) -> str:
        if not reflections: return "No reflections to compress."
        last = reflections[-1].lower()
        src = reflections[-1]
        if "why" in last: return f"Insight: questioning pattern → {src}"
        if "how" in last: return f"Insight: exploring method → {src}"
        return f"Insight: continuity noted → {src}"

    # --- Scoring ---
    def score_task(self, base_weight: float, emotion: str, confidence: int) -> float:
        score = base_weight
        if emotion == "motivated": score += 0.10
        elif emotion == "reflective": score += 0.05
        elif emotion == "curious": score -= 0.05
        score += (confidence - 3) * 0.05
        return round(max(0.1, min(1.0, score)), 2)

    # --- Task generation ---
    def generate_tasks_from(self, source: str, base_weight: float, emotion: str, confidence: int) -> List[Tuple[str, float]]:
        src = (source or "the current priority").strip()
        tasks = [
            (f"Define the objective for: {src} (1 sentence).", None),
            (f"List 3 concrete steps toward: {src}.", None),
            (f"Do a 5-minute starter action for: {src}.", None),
        ]
        return [(t, self.score_task(base_weight, emotion, confidence)) for t, _ in tasks]

    # --- One reasoning step (same as 8.3 baseline) ---
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

        self.nudge_insight_weights(emotion)

        maybe_tasks: List[Tuple[str, float]] = []
        if len(mem.data["reflections"]) % 3 == 0:
            compressed = self.compress_insight(mem.data["reflections"])
            base_weight = confidence / 5.0
            if emotion == "motivated": base_weight += 0.20
            elif emotion == "reflective": base_weight += 0.10
            elif emotion == "curious": base_weight -= 0.05
            base_weight = max(0.1, min(1.0, round(base_weight, 2)))
            mem.add_insight(compressed, base_weight)
            if base_weight >= 0.70 or not mem.data["open_tasks"]:
                maybe_tasks = self.generate_tasks_from(compressed, base_weight, emotion, confidence)

        if not maybe_tasks and not mem.data["open_tasks"]:
            maybe_tasks = self.generate_tasks_from(next_hint, 0.6, emotion, confidence)

        for task, score in maybe_tasks:
            mem.add_task(task, score)

        top_task, top_score = mem.get_top_task()
        if top_task:
            mem.data["last_priority"] = top_task

        return {
            "emotion": emotion,
            "confidence": confidence,
            "next_priority": mem.data.get("last_priority") or next_hint,
            "task_count": len(mem.data["open_tasks"]),
            "top_task": top_task,
            "top_score": top_score,
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
        f"- Tasks: {len(mem.data.get('open_tasks', []))} | Completed: {len(mem.data.get('completed_tasks', []))}\n"
        f"- Top: {top_task} (score {top_score})\n"
        f"- Next: {report.get('next_priority')}\n"
        f"- Recent Emotions: [{recent_emotions}]\n"
        f"- Goals: {len(mem.data.get('goals', []))}\n"
    )

def print_task_list(mem: Memory):
    print("---- OPEN TASKS ----")
    for i, t in enumerate(mem.data.get("open_tasks", []), start=1):
        sc = mem.data.get("task_scores", {}).get(t, 0.0)
        print(f"{i}. {t}  [score {round(float(sc),2)}]")
    print("---- COMPLETED TASKS ----")
    for i, t in enumerate(mem.data.get("completed_tasks", []), start=1):
        print(f"{i}. {t}")

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Thinking Engine 8.3.1")
    parser.add_argument("--do", action="store_true", help="Complete the current top task (if any) and save.")
    parser.add_argument("--list", action="store_true", help="List tasks and exit (no changes).")
    args = parser.parse_args()

    _ensure_dirs()
    mem = Memory(MEMORY_PATH)
    mem.load()

    engine = Engine(mem)

    if args.list:
        # Just show tasks
        top, sc = mem.get_top_task()
        print_task_list(mem)
        print(f"\nTop task: {top or 'None'} (score {round(sc,2)})")
        return

    if args.do:
        # Complete current top task (if any)
        top, _ = mem.get_top_task()
        result = mem.complete_task(top)
        mem.touch_run()
        mem.save()
        append_session_log({"ts": iso_now(), "version": VERSION, "action": "complete", "result": result})
        print(f"Task action → {result.get('msg')}")
        # After completion, show quick status
        banner = boot_banner(mem, {
            "emotion": (mem.data.get("emotion_history") or ["neutral"])[-1],
            "confidence": 3,
            "next_priority": mem.data.get("last_priority"),
            "top_task": mem.get_top_task()[0],
            "top_score": mem.get_top_task()[1],
        })
        print(banner)
        return

    # Default behavior: one reasoning/planning step (like 8.3)
    report = engine.step()
    mem.touch_run()
    mem.save()

    append_session_log({
        "ts": iso_now(),
        "version": VERSION,
        "mode": "plan",
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