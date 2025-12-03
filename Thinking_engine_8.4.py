# Thinking_Engine_8.4.py
# ------------------------------------------------------------
# Version: 8.4 | Multi-Cycle AutoLoop + Emotion Carryover (fixed banner)
# ------------------------------------------------------------
import json, os, argparse, time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

VERSION = "8.4"
SCHEMA_VERSION = 8

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

# ---------- Memory ----------
class Memory:
    def __init__(self, path: str):
        self.path = path
        _ensure_dirs()
        self.data: Dict[str, Any] = {}

    def load(self):
        raw = _read_json(self.path, default={})
        base = {
            "last_priority": None,
            "reflections": [],
            "facts": [],
            "goals": [],
            "open_tasks": [],
            "completed_tasks": [],
            "task_scores": {},
            "errors": [],
            "insights": [],
            "confidence_scores": {},
            "insight_weights": {},
            "emotion_history": [],
            "schema_version": SCHEMA_VERSION,
            "last_run": None,
            "extras": {},
        }
        # quarantine unknowns
        for k, v in raw.items():
            if k not in base:
                base["extras"][k] = v
        # fill defaults
        for k, v in base.items():
            if k not in raw:
                raw[k] = v
        self.data = raw

    def save(self): _write_json(self.path, self.data)
    def touch_run(self): self.data["last_run"] = iso_now()

    def push_emotion(self, e: str, cap: int = 12):
        self.data["emotion_history"].append(e)
        self.data["emotion_history"] = self.data["emotion_history"][-cap:]

    def add_task(self, t: str, s: float):
        if t not in self.data["open_tasks"]:
            self.data["open_tasks"].append(t)
        prev = float(self.data["task_scores"].get(t, 0))
        self.data["task_scores"][t] = round(max(prev, s), 3)

    def get_top_task(self) -> Tuple[str | None, float]:
        if not self.data["open_tasks"]:
            return None, 0.0
        top = max(self.data["open_tasks"], key=lambda x: self.data["task_scores"].get(x, 0.1))
        return top, float(self.data["task_scores"].get(top, 0.1))

    def complete_task(self, t: str | None = None) -> Dict[str, Any]:
        if not self.data["open_tasks"]:
            return {"ok": False, "msg": "No open tasks."}
        if t is None:
            t, _ = self.get_top_task()
        if t not in self.data["open_tasks"]:
            return {"ok": False, "msg": "Task not found."}
        self.data["open_tasks"] = [x for x in self.data["open_tasks"] if x != t]
        self.data["completed_tasks"].append(t)
        # Reinforce insights
        for k in list(self.data["insight_weights"].keys()):
            w = float(self.data["insight_weights"][k])
            self.data["insight_weights"][k] = round(min(1.0, w + 0.02), 3)
        self.data["last_priority"] = None
        return {"ok": True, "msg": f"Completed: {t}"}

# ---------- Engine ----------
class Engine:
    def __init__(self, memory: Memory):
        self.mem = memory

    def analyze_emotion(self, text: str) -> str:
        t = (text or "").lower()
        if any(x in t for x in ["why", "doubt", "uncertain"]): return "curious"
        if any(x in t for x in ["fail", "hard", "struggle"]): return "reflective"
        if any(x in t for x in ["goal", "achieve", "plan", "let's", "move"]): return "motivated"
        return "neutral"

    def compute_confidence(self, text: str) -> int:
        b = 3
        if "!" in text: b += 1
        if "?" in text: b -= 1
        return max(1, min(5, b))

    def chain_next_priority(self, base: str | None) -> str:
        hist = self.mem.data.get("emotion_history", [])
        last3 = hist[-3:]
        if last3.count("reflective") >= 2: return "Plan: Convert reflection to a concrete next step."
        if last3.count("curious") >= 2: return "Plan: Formulate a testable question and act."
        if last3.count("motivated") >= 2: return "Plan: Execute a high-confidence action now."
        return base or "Plan: Define a clear goal and first task."

    def score_task(self, base: float, e: str, c: int) -> float:
        s = base
        if e == "motivated": s += 0.1
        elif e == "reflective": s += 0.05
        elif e == "curious": s -= 0.05
        s += (c - 3) * 0.05
        return round(max(0.1, min(1.0, s)), 2)

    def generate_tasks(self, src: str, w: float, e: str, c: int) -> List[Tuple[str, float]]:
        base = src or "the current goal"
        templates = [
            f"Define the objective for: {base} (1 sentence).",
            f"List 3 concrete steps toward: {base}.",
            f"Do a 5-minute starter action for: {base}.",
        ]
        return [(t, self.score_task(w, e, c)) for t in templates]

    def reflect_once(self) -> Dict[str, Any]:
        m = self.mem
        prev = m.data.get("reflections", [])
        last = prev[-1] if prev else ""
        e = self.analyze_emotion(last)
        c = self.compute_confidence(last)
        m.push_emotion(e)

        hint = self.chain_next_priority(m.data.get("last_priority"))
        thought = f"[{iso_now()}] Emotion={e} | Next={hint}"
        m.data["reflections"].append(thought)
        m.data["confidence_scores"][str(len(prev))] = c

        # Every 3 reflections → new insight + tasks
        new_tasks = []
        if len(m.data["reflections"]) % 3 == 0:
            weight = round(min(1.0, c / 5 + (0.2 if e == 'motivated' else 0.1 if e == 'reflective' else 0)), 2)
            ins = f"Insight: derived from {e} state — {hint}"
            m.data["insights"].append(ins)
            m.data["insight_weights"][str(len(m.data['insights']))] = weight
            new_tasks = self.generate_tasks(ins, weight, e, c)
            for t, s in new_tasks:
                m.add_task(t, s)

        top, sc = m.get_top_task()
        if top:
            m.data["last_priority"] = top
        return {"emotion": e, "confidence": c, "next": hint, "top": top, "score": sc, "new_tasks": len(new_tasks)}

# ---------- Display ----------
def banner(mem: Memory, r: Dict[str, Any]) -> str:
    weights = mem.data.get("insight_weights", {})
    avg = round(sum(float(v) for v in weights.values()) / max(len(weights), 1), 2) if weights else 0.0
    em = ", ".join(mem.data.get("emotion_history", [])[-5:])
    top = r.get("top") or "None"
    return (
        f"Thinking Engine {VERSION} Online\n"
        f"- Emotion: {r.get('emotion')} | Confidence: {r.get('confidence')}/5\n"
        f"- Reflections: {len(mem.data['reflections'])} | Insights: {len(mem.data['insights'])} (avg {avg})\n"
        f"- Tasks: {len(mem.data['open_tasks'])} | Completed: {len(mem.data['completed_tasks'])}\n"
        f"- Top: {top}\n"
        f"- Next: {r.get('next')}\n"
        f"- Recent Emotions: [{em}]\n"
        f"- Goals: {len(mem.data['goals'])}\n"
    )

def print_task_list(mem: Memory):
    print("---- OPEN TASKS ----")
    for i, t in enumerate(mem.data.get("open_tasks", []), start=1):
        sc = mem.data.get("task_scores", {}).get(t, 0.0)
        print(f"{i}. {t}  [score {round(float(sc),2)}]")
    print("---- COMPLETED TASKS ----")
    for i, t in enumerate(mem.data.get("completed_tasks", []), start=1):
        print(f"{i}. {t}")

# ---------- Logging ----------
def log(entry: Dict[str, Any]):
    lg = _read_json(SESSION_LOG, default=[])
    if not isinstance(lg, list): lg = []
    lg.append(entry)
    lg = lg[-500:]
    _write_json(SESSION_LOG, lg)

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Thinking Engine 8.4")
    parser.add_argument("--cycles", type=int, default=1, help="Number of reasoning cycles to run.")
    parser.add_argument("--list", action="store_true", help="List tasks and exit.")
    parser.add_argument("--do", action="store_true", help="Complete the current top task and exit.")
    args = parser.parse_args()

    _ensure_dirs()
    mem = Memory(MEMORY_PATH)
    mem.load()
    eng = Engine(mem)

    if args.list:
        print_task_list(mem)
        top, sc = mem.get_top_task()
        print(f"\nTop task: {top or 'None'} (score {round(sc,2)})")
        return

    if args.do:
        top, _ = mem.get_top_task()
        result = mem.complete_task(top)
        mem.touch_run(); mem.save()
        log({"ts": iso_now(), "version": VERSION, "action": "complete", "result": result})
        print(f"Task action → {result.get('msg')}")
        # show status after action
        r = {"emotion": (mem.data.get("emotion_history") or ["neutral"])[-1], "confidence": 3,
             "next": mem.data.get("last_priority"), "top": mem.get_top_task()[0]}
        print(banner(mem, r))
        return

    last_report = {}
    for i in range(max(1, args.cycles)):
        r = eng.reflect_once()
        mem.touch_run()
        mem.save()
        log({"ts": iso_now(), "version": VERSION, "mode": "cycle", "cycle": i+1, "report": r})
        print(f"[cycle {i+1}/{args.cycles}] emotion={r['emotion']} conf={r['confidence']} top={r.get('top') or 'None'} tasks={len(mem.data['open_tasks'])}")
        last_report = r
        # tiny pause so you can watch the loop
        time.sleep(0.05)

    print("\n" + banner(mem, last_report))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _ensure_dirs()
        mem = Memory(MEMORY_PATH)
        mem.load()
        mem.data.setdefault("errors", []).append(f"{iso_now()} :: Fatal: {repr(e)}")
        mem.save()
        raise