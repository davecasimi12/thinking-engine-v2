# Thinking_Engine_8.8.py
# ------------------------------------------------------------
# Version: 8.8 | Priority Decay + Duplicate Task Merge
# Keeps 8.7 features: Smart Auto-Export (MD/CSV/JSON), Autoloop, Drift
# ------------------------------------------------------------
import json, os, argparse, time, csv, re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

VERSION = "8.8"
SCHEMA_VERSION = 11   # migration-safe

DATA_DIR = "data"
REPORT_DIR = os.path.join(DATA_DIR, "reports")
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")

# ---------- Utilities ----------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _short_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

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

# ---------- Normalizers ----------
_punct_re = re.compile(r"[\s\.\,\;\:\-\_\(\)\[\]\{\}\!\?\|/\\]+")
def normalize_task(text: str) -> str:
    t = (text or "").lower().strip()
    t = _punct_re.sub(" ", t)
    t = re.sub(r"\s+", " ", t)
    # collapse leading verbs that often vary
    t = re.sub(r"^(define|list|do|make|create)\s+", "", t)
    return t.strip()

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
            "context_buffer": [],
            "session_summaries": [],
            "schema_version": SCHEMA_VERSION,
            "last_run": None,
            "extras": {},
        }
        for k, v in raw.items():
            if k not in base:
                base["extras"][k] = v
        for k, v in base.items():
            if k not in raw:
                raw[k] = v

        # guards
        for key, typ in [
            ("open_tasks", list), ("completed_tasks", list), ("reflections", list),
            ("goals", list), ("errors", list), ("insights", list), ("emotion_history", list),
            ("context_buffer", list), ("session_summaries", list)
        ]:
            if not isinstance(raw.get(key), typ): raw[key] = typ()
        for key, typ in [("task_scores", dict), ("confidence_scores", dict), ("insight_weights", dict)]:
            if not isinstance(raw.get(key), typ): raw[key] = typ()

        raw["schema_version"] = SCHEMA_VERSION
        self.data = raw

    def save(self): _write_json(self.path, self.data)
    def touch_run(self): self.data["last_run"] = iso_now()

    def push_emotion(self, e: str, cap: int = 12):
        self.data["emotion_history"].append(e)
        self.data["emotion_history"] = self.data["emotion_history"][-cap:]

    # ----- Duplicate Merge + Add -----
    def add_task(self, t: str, s: float):
        """Add a task with duplicate-aware merge. Keeps the higher score."""
        if not t: return
        norm_map = {normalize_task(x): x for x in self.data["open_tasks"]}
        key = normalize_task(t)
        if key in norm_map:
            existing = norm_map[key]
            prev = float(self.data["task_scores"].get(existing, 0))
            self.data["task_scores"][existing] = round(max(prev, s), 3)
            return
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
        # Reinforce insights slightly
        for k in list(self.data["insight_weights"].keys()):
            w = float(self.data["insight_weights"][k])
            self.data["insight_weights"][k] = round(min(1.0, w + 0.02), 3)
        self.data["last_priority"] = None
        return {"ok": True, "msg": f"Completed: {t}"}

    # ----- Maintenance: decay + global dedupe -----
    def maintenance(self, decay: float = 0.98, floor: float = 0.10):
        """
        - Priority Decay: multiply all task scores by `decay` to let stale tasks slowly drop.
        - Duplicate Merge: unify tasks that normalize to the same key (keeps highest score).
        """
        # Decay (do not decay the current top to avoid thrash)
        top, _ = self.get_top_task()
        for t in list(self.data["open_tasks"]):
            if t == top: 
                continue
            sc = float(self.data["task_scores"].get(t, 0.1))
            self.data["task_scores"][t] = round(max(floor, sc * decay), 3)

        # Merge duplicates across the whole list
        merged: Dict[str, Tuple[str, float]] = {}
        for t in self.data["open_tasks"]:
            key = normalize_task(t)
            sc = float(self.data["task_scores"].get(t, 0.1))
            if key not in merged or sc > merged[key][1]:
                merged[key] = (t, sc)
        # Rebuild open_tasks and task_scores
        self.data["open_tasks"] = [orig for orig, _ in merged.values()]
        self.data["task_scores"] = {orig: round(score, 3) for orig, score in merged.values()}

# ---------- Engine ----------
class Engine:
    def __init__(self, memory: Memory):
        self.mem = memory

    # Emotion & confidence
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

    # Drift to keep emotional balance
    def apply_emotion_drift(self, current: str) -> str:
        hist = self.mem.data.get("emotion_history", [])
        if len(hist) < 3: return current
        last3 = hist[-3:]
        if last3.count("motivated") == 3: return "curious"
        if last3.count("reflective") >= 2: return "motivated"
        return current

    # Priority suggestion from history
    def chain_next_priority(self, base: str | None) -> str:
        hist = self.mem.data.get("emotion_history", [])
        last3 = hist[-3:]
        if last3.count("reflective") >= 2: return "Plan: Convert reflection to a concrete next step."
        if last3.count("curious") >= 2: return "Plan: Formulate a testable question and act."
        if last3.count("motivated") >= 2: return "Plan: Execute a high-confidence action now."
        return base or "Plan: Define a clear goal and first task."

    # Scores & tasks
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

    # Context buffer + one-line summary
    def update_context_and_summary(self, thought: str, emotion: str) -> str:
        buf = self.mem.data.get("context_buffer", [])
        buf.append(thought)
        self.mem.data["context_buffer"] = buf[-5:]
        last = self.mem.data["context_buffer"][-3:]
        summary = f"{iso_now()} :: {emotion} → " + " | ".join(x.split('] ', 1)[-1] for x in last)
        self.mem.data["session_summaries"].append(summary)
        self.mem.data["session_summaries"] = self.mem.data["session_summaries"][-200:]
        return summary

    def reflect_once(self) -> Dict[str, Any]:
        m = self.mem
        prev = m.data.get("reflections", [])
        last_text = prev[-1] if prev else ""

        emotion0 = self.analyze_emotion(last_text)
        emotion = self.apply_emotion_drift(emotion0)
        conf = self.compute_confidence(last_text)
        m.push_emotion(emotion)

        hint = self.chain_next_priority(m.data.get("last_priority"))
        thought = f"[{iso_now()}] Emotion={emotion} | Next={hint}"
        m.data["reflections"].append(thought)
        m.data["confidence_scores"][str(len(prev))] = conf

        summary = self.update_context_and_summary(thought, emotion)

        # Every 3 reflections → insight + tasks
        new_tasks = []
        if len(m.data["reflections"]) % 3 == 0:
            weight = round(min(1.0, conf / 5 + (0.2 if emotion == 'motivated' else 0.1 if emotion == 'reflective' else 0)), 2)
            ins = f"Insight: derived from {emotion} state — {hint}"
            m.data["insights"].append(ins)
            m.data["insight_weights"][str(len(m.data['insights']))] = weight
            new_tasks = self.generate_tasks(ins, weight, emotion, conf)
            for t, s in new_tasks:
                m.add_task(t, s)

        # Maintenance pass (decay + merge) each cycle
        m.maintenance(decay=0.98, floor=0.10)

        top, sc = m.get_top_task()
        if top: m.data["last_priority"] = top

        return {"emotion": emotion, "confidence": conf, "next": hint, "top": top, "score": sc, "new_tasks": len(new_tasks), "summary": summary}

# ---------- Display ----------
def banner(mem: Memory, r: Dict[str, Any]) -> str:
    weights = mem.data.get("insight_weights", {})
    avg = round(sum(float(v) for v in weights.values()) / max(len(weights), 1), 2) if weights else 0.0
    em = ", ".join(mem.data.get("emotion_history", [])[-5:])
    top = r.get("top") or "None"
    latest_summary = (mem.data.get("session_summaries") or ["n/a"])[-1]
    return (
        f"Thinking Engine {VERSION} Online\n"
        f"- Emotion: {r.get('emotion')} | Confidence: {r.get('confidence')}/5\n"
        f"- Reflections: {len(mem.data['reflections'])} | Insights: {len(mem.data['insights'])} (avg {avg})\n"
        f"- Tasks: {len(mem.data['open_tasks'])} | Completed: {len(mem.data['completed_tasks'])}\n"
        f"- Top: {top}\n"
        f"- Next: {r.get('next')}\n"
        f"- Recent Emotions: [{em}]\n"
        f"- Context: {len(mem.data['context_buffer'])} items | Latest Summary → {latest_summary}\n"
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

# ---------- Exporters ----------
def export_markdown(mem: Memory) -> str:
    weights = mem.data.get("insight_weights", {})
    avg_w = round(sum(float(v) for v in weights.values()) / max(len(weights), 1), 2) if weights else 0.0
    emotions = ", ".join(mem.data.get("emotion_history", [])[-12:])
    top_task, top_score = mem.get_top_task()
    summaries = mem.data.get("session_summaries", [])[-10:]
    insights = mem.data.get("insights", [])[-10:]
    reflections = mem.data.get("reflections", [])[-10:]

    lines = []
    lines.append(f"# Nivora Thinking Engine — Session Report\n")
    lines.append(f"- **Version:** {VERSION}")
    lines.append(f"- **Generated:** {iso_now()}")
    lines.append(f"- **Schema:** v{SCHEMA_VERSION}")
    lines.append("")
    lines.append("## Snapshot")
    lines.append(f"- Reflections: **{len(mem.data['reflections'])}**  |  Insights: **{len(mem.data['insights'])}** (avg weight **{avg_w}**)  |  Goals: **{len(mem.data['goals'])}**")
    lines.append(f"- Tasks: **{len(mem.data['open_tasks'])}** open, **{len(mem.data['completed_tasks'])}** completed")
    lines.append(f"- Top Task: **{top_task or 'None'}**  (score {round(top_score,2)})")
    lines.append(f"- Emotion history (latest 12): {emotions or 'n/a'}")
    lines.append("")
    lines.append("## Latest Summaries (≤10)")
    if summaries:
        for s in summaries: lines.append(f"- {s}")
    else:
        lines.append("- n/a")
    lines.append("")
    lines.append("## Recent Insights (≤10)")
    if insights:
        total = len(mem.data['insights'])
        start_idx = max(1, total - len(insights) + 1)
        for i, ins in enumerate(insights, start=start_idx):
            lines.append(f"{i}. {ins}  *(w={mem.data.get('insight_weights', {}).get(str(i), '—')})*")
    else:
        lines.append("- n/a")
    lines.append("")
    lines.append("## Recent Reflections (≤10)")
    if reflections:
        for r in reflections: lines.append(f"- {r}")
    else:
        lines.append("- n/a")
    lines.append("")
    lines.append("## Open Tasks")
    if mem.data.get("open_tasks"):
        for t in mem.data["open_tasks"]:
            lines.append(f"- [ ] {t}  *(score {round(float(mem.data['task_scores'].get(t,0)),2)})*")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Completed Tasks")
    if mem.data.get("completed_tasks"):
        for t in mem.data["completed_tasks"]:
            lines.append(f"- [x] {t}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("> End of report.")

    fn = os.path.join(REPORT_DIR, f"Session_{_short_ts()}.md")
    with open(fn, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return fn

def export_csv(mem: Memory) -> str:
    fn = os.path.join(REPORT_DIR, f"Session_{_short_ts()}.csv")
    top_task, top_score = mem.get_top_task()
    summaries = mem.data.get("session_summaries", [])
    last_summary = summaries[-1] if summaries else ""
    row = {
        "timestamp": iso_now(),
        "reflections": len(mem.data.get("reflections", [])),
        "insights": len(mem.data.get("insights", [])),
        "avg_insight_weight": round(
            sum(float(v) for v in mem.data.get("insight_weights", {}).values()) / max(len(mem.data.get("insight_weights", {})) or 1, 1),
            2
        ) if mem.data.get("insight_weights") else 0.0,
        "emotion_recent": (mem.data.get("emotion_history") or ["n/a"])[-1],
        "emotion_trend_last5": ", ".join(mem.data.get("emotion_history", [])[-5:]),
        "top_task": top_task or "",
        "top_score": round(top_score, 2),
        "open_tasks": len(mem.data.get("open_tasks", [])),
        "completed_tasks": len(mem.data.get("completed_tasks", [])),
        "latest_summary": last_summary,
    }
    with open(fn, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
    return fn

def export_status_json(mem: Memory) -> str:
    fn = os.path.join(REPORT_DIR, f"Session_{_short_ts()}.json")
    top_task, top_score = mem.get_top_task()
    status = {
        "version": VERSION,
        "schema": SCHEMA_VERSION,
        "generated": iso_now(),
        "reflections": len(mem.data.get("reflections", [])),
        "insights": len(mem.data.get("insights", [])),
        "avg_insight_weight": round(
            sum(float(v) for v in mem.data.get("insight_weights", {}).values()) / max(len(mem.data.get("insight_weights", {})) or 1, 1),
            2
        ) if mem.data.get("insight_weights") else 0.0,
        "emotion_recent": (mem.data.get("emotion_history") or ["n/a"])[-1],
        "emotion_trend_last5": mem.data.get("emotion_history", [])[-5:],
        "top_task": top_task,
        "top_score": round(top_score, 2),
        "open_tasks": mem.data.get("open_tasks", []),
        "completed_tasks": mem.data.get("completed_tasks", []),
        "session_summaries": mem.data.get("session_summaries", [])[-10:],
        "goals": mem.data.get("goals", []),
    }
    _write_json(fn, status)
    return fn

# ---------- Main ----------
def banner_and_print(mem: Memory, r: Dict[str, Any]):
    print("\n" + banner(mem, r))

def auto_export_all(mem: Memory):
    md = export_markdown(mem)
    csv_path = export_csv(mem)
    js = export_status_json(mem)
    print(f"Report saved → {md}")
    print(f"CSV saved    → {csv_path}")
    print(f"JSON saved   → {js}")

def main():
    parser = argparse.ArgumentParser(description="Thinking Engine 8.8")
    parser.add_argument("--cycles", type=int, default=1, help="Number of reasoning cycles to run.")
    parser.add_argument("--list", action="store_true", help="List tasks and exit.")
    parser.add_argument("--do", action="store_true", help="Complete the current top task and export.")
    parser.add_argument("--export-md", action="store_true", help="Export Markdown report and exit.")
    parser.add_argument("--export-csv", action="store_true", help="Export CSV report and exit.")
    parser.add_argument("--status", action="store_true", help="Print short JSON status to stdout and exit.")
    args = parser.parse_args()

    _ensure_dirs()
    mem = Memory(MEMORY_PATH)
    mem.load()
    eng = Engine(mem)

    # On-demand utilities
    if args.list:
        print_task_list(mem)
        top, sc = mem.get_top_task()
        print(f"\nTop task: {top or 'None'} (score {round(sc,2)})")
        return
    if args.export_md:
        path = export_markdown(mem); print(f"Report saved → {path}"); return
    if args.export_csv:
        path = export_csv(mem); print(f"CSV saved → {path}"); return
    if args.status:
        status_path = export_status_json(mem)
        print(json.dumps(_read_json(status_path, {}), indent=2))
        print(f"\nJSON saved → {status_path}")
        return

    # Complete a task (and auto-export)
    if args.do:
        top, _ = mem.get_top_task()
        result = mem.complete_task(top)
        # Maintenance after action too (clean up + adjust priorities)
        mem.maintenance(decay=0.98, floor=0.10)
        mem.touch_run(); mem.save()
        log({"ts": iso_now(), "version": VERSION, "action": "complete", "result": result})
        print(f"Task action → {result.get('msg')}")
        r = {"emotion": (mem.data.get("emotion_history") or ["neutral"])[-1], "confidence": 3,
             "next": mem.data.get("last_priority"), "top": mem.get_top_task()[0]}
        banner_and_print(mem, r)
        auto_export_all(mem)
        return

    # Autoloop (planning/reflection)
    last_report = {}
    cycles = max(1, args.cycles)
    for i in range(cycles):
        r = eng.reflect_once()
        mem.touch_run()
        mem.save()
        log({"ts": iso_now(), "version": VERSION, "mode": "cycle", "cycle": i+1, "report": r})
        print(f"[cycle {i+1}/{cycles}] emotion={r['emotion']} conf={r['confidence']} top={r.get('top') or 'None'} tasks={len(mem.data['open_tasks'])}")
        last_report = r
        time.sleep(0.05)

    # Final banner + auto-export
    banner_and_print(mem, last_report)
    auto_export_all(mem)

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