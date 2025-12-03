# Thinking_Engine_7.0.py
# Full replace file — drop in as-is.
# ------------------------------------------------------------
# Version: 7.0
# Policy: Single-file, no external deps. Creates /data on first run.
# ------------------------------------------------------------

import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

VERSION = "7.0"

# ---------- Stable schema & constants (do not rename) ----------
SCHEMA_VERSION = 3
SCHEMA_KEYS = {
    "last_priority": None,                 # str | None
    "reflections": [],                     # List[str]
    "facts": [],                           # List[str]
    "goals": [],                           # List[str]
    "open_tasks": [],                      # List[str]
    "errors": [],                          # List[str] recent engine errors
    "last_run": None,                      # ISO timestamp | None
    "schema_version": SCHEMA_VERSION,      # int
    "extras": {},                          # Dict[str, Any] quarantine for unknown keys (autocorrect, etc.)
}

DATA_DIR = "data"
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")


# ---------------- Utility: safe IO ----------------
def _ensure_dirs():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


def _read_json(path: str, default: Any) -> Any:
    try:
        if not os.path.isfile(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # If file corrupt, keep a backup and return default
        try:
            bk = f"{path}.corrupt.{int(time.time())}.bak"
            if os.path.isfile(path):
                os.rename(path, bk)
        except Exception:
            pass
        return default


def _write_json(path: str, data: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def iso_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


# ---------------- Self-Healing Memory ----------------
class Memory:
    def __init__(self, path: str):
        self.path = path
        _ensure_dirs()
        self.data: Dict[str, Any] = {}

    def load(self) -> None:
        seed = {k: _clone_default(v) for k, v in SCHEMA_KEYS.items()}
        raw = _read_json(self.path, default=seed)

        # If raw isn’t dict, reset
        if not isinstance(raw, dict):
            self.data = seed
            return

        # Quarantine unknown keys to extras
        extras = raw.get("extras", {})
        if not isinstance(extras, dict):
            extras = {}

        for k, v in list(raw.items()):
            if k not in SCHEMA_KEYS:
                # Move to extras; keeps accidental/autocorrected keys without breaking engine
                extras[k] = v
                raw.pop(k, None)

        raw["extras"] = extras

        # Enforce required keys & types
        healed = {}
        for k, default_v in SCHEMA_KEYS.items():
            if k not in raw:
                healed[k] = _clone_default(default_v)
                continue

            val = raw[k]
            healed[k] = _coerce_type(key=k, value=val, default_value=default_v)

        # Lock schema version to engine SCHEMA_VERSION
        healed["schema_version"] = SCHEMA_VERSION
        self.data = healed

    def save(self) -> None:
        _write_json(self.path, self.data)

    # Convenience getters/setters (typed where useful)
    def add_reflection(self, text: str) -> None:
        if text and isinstance(text, str):
            self.data["reflections"].append(text)

    def add_error(self, text: str) -> None:
        if text and isinstance(text, str):
            self.data["errors"].append(f"{iso_now()} :: {text}")
            # Cap errors list to last 50
            self.data["errors"] = self.data["errors"][-50:]

    def set_last_priority(self, p: str | None) -> None:
        if p is None or isinstance(p, str):
            self.data["last_priority"] = p

    def touch_last_run(self) -> None:
        self.data["last_run"] = iso_now()


def _clone_default(val: Any) -> Any:
    # Return a safe clone for lists/dicts
    if isinstance(val, list):
        return list(val)
    if isinstance(val, dict):
        return dict(val)
    return val


def _coerce_type(key: str, value: Any, default_value: Any) -> Any:
    """Best-effort type enforcement with gentle coercions."""
    try:
        # None defaults pass through
        if default_value is None:
            # allow strings, None
            return value if (value is None or isinstance(value, str)) else str(value)

        # Lists
        if isinstance(default_value, list):
            if isinstance(value, list):
                # coerce all items to str for string lists
                return [str(x) for x in value]
            # single value -> list
            return [str(value)]

        # Dicts
        if isinstance(default_value, dict):
            if isinstance(value, dict):
                return value
            return {"value": value}

        # Ints
        if isinstance(default_value, int):
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            # try parse
            try:
                return int(str(value).strip())
            except Exception:
                return default_value

        # Strings
        if isinstance(default_value, str):
            return str(value)

        # Fallback
        return value
    except Exception:
        # On failure, fall back to default
        return _clone_default(default_value)


# ---------------- Reflection Engine ----------------
class ReflectionEngine:
    @staticmethod
    def reflect(memory: Memory) -> Dict[str, Any]:
        """
        Produce a simple next_action plan based on goals/open_tasks/last_priority.
        Deterministic, side-effect free (besides appending reflection text).
        """
        goals: List[str] = memory.data.get("goals", [])
        tasks: List[str] = memory.data.get("open_tasks", [])
        last_p: str | None = memory.data.get("last_priority")

        # Decide next priority
        next_priority = None
        reason = None

        if last_p and last_p in tasks:
            next_priority = last_p
            reason = "Continuing last priority in open tasks."
        elif tasks:
            next_priority = tasks[0]
            reason = "Picking first open task."
        elif goals:
            next_priority = f"Goal bootstrap: {goals[0]}"
            reason = "No open tasks; bootstrapping from first goal."
        else:
            next_priority = "Plan: Define a clear goal and first task."
            reason = "No goals or tasks available."

        # Build reflection line
        line = f"[{iso_now()}] next_priority='{next_priority}' | reason='{reason}'"
        memory.add_reflection(line)
        memory.set_last_priority(next_priority)

        return {
            "next_priority": next_priority,
            "reason": reason,
            "timestamp": iso_now(),
        }


# ---------------- Session Log (optional but helpful) ----------------
def append_session_log(entry: Dict[str, Any]) -> None:
    log = _read_json(SESSION_LOG, default=[])
    if not isinstance(log, list):
        log = []
    log.append(entry)
    # cap log length
    log = log[-500:]
    _write_json(SESSION_LOG, log)


# ---------------- Engine Boot ----------------
def boot_banner(memory: Memory, plan: Dict[str, Any]) -> str:
    """Return a concise, human-readable status line."""
    last_run = memory.data.get("last_run")
    rp = plan.get("next_priority")
    return (
        f"Thinking Engine {VERSION} Online\n"
        f"- Schema v{SCHEMA_VERSION} OK | Memory healed & loaded\n"
        f"- Last run: {last_run}\n"
        f"- Next priority: {rp}\n"
        f"- Reflections total: {len(memory.data.get('reflections', []))}\n"
        f"- Open tasks: {len(memory.data.get('open_tasks', []))} | Goals: {len(memory.data.get('goals', []))}\n"
    )


def main():
    _ensure_dirs()
    mem = Memory(MEMORY_PATH)
    mem.load()  # self-heal happens in load

    # One deterministic reflection tick per run
    plan = ReflectionEngine.reflect(mem)
    mem.touch_last_run()
    mem.save()

    # Log the session
    append_session_log({
        "ts": iso_now(),
        "version": VERSION,
        "plan": plan,
        "summary": {
            "reflections": len(mem.data.get("reflections", [])),
            "open_tasks": len(mem.data.get("open_tasks", [])),
            "goals": len(mem.data.get("goals", [])),
        }
    })

    # Console output for quick verification
    print(boot_banner(mem, plan))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Last-resort catch to keep the engine from crashing the session.
        _ensure_dirs()
        mem = Memory(MEMORY_PATH)
        try:
            mem.load()
            mem.add_error(f"Fatal: {repr(e)}")
            mem.save()
        except Exception:
            pass
        # Still raise to surface the issue in terminal for visibility.
        raise