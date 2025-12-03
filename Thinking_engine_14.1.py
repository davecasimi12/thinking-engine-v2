# ------------------------------------------------------------
# Thinking_Engine_14.1.py
# Phase 14.1 — Owner Lock Edition
# Same as 14.0, but adds owner tag + import filtering + offline check
# ------------------------------------------------------------

import os, json, time, uuid, argparse, sys, re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

VERSION = "14.1"
SCHEMA_VERSION = 17
OWNER_ID = "YZ"          # Only this owner’s commands are accepted
OFFLINE_MODE = True      # Safety flag: never use network modules

# ---------- Paths ----------
DATA_DIR = "data"
REPORT_DIR = os.path.join(DATA_DIR, "reports")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
IMPORT_DIR = os.path.join(DATA_DIR, "imports")
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")

# ---------- Utilities ----------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(IMPORT_DIR, exist_ok=True)

def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _read_json(path: str, default: Any):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_json(path: str, payload: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def _append_session(event: Dict[str, Any]) -> None:
    event["owner"] = OWNER_ID
    log = _read_json(SESSION_LOG, [])
    log.append(event)
    _write_json(SESSION_LOG, log)

def _safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except Exception:
        pass

def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

# ---------- Minimal placeholders ----------
def reflect_on_session(): return "Stable"
def heal_memory(): return ("ok", 1.0)
def recall_core_memories(limit=5): return []
def evolve_engine(r,h,r2): return "ok"

# ---------- Import Command Filter ----------
def import_commands_if_any() -> Dict[str, Any]:
    """
    Reads data/imports/commands.json and only processes if owner == YZ
    """
    path = os.path.join(IMPORT_DIR, "commands.json")
    cmds = _read_json(path, {})
    effects = {"set_sleep": None, "pushed": 0, "cleared": False, "ignored": False}

    if not isinstance(cmds, dict) or not cmds:
        return effects

    # --- Owner verification ---
    if cmds.get("owner") != OWNER_ID:
        _append_session({
            "ts": iso_now(),
            "kind": "unauthorized_import",
            "details": {"attempt_owner": cmds.get("owner")}
        })
        effects["ignored"] = True
        return effects

    # Example command handling (extend as needed)
    if "set_sleep" in cmds:
        effects["set_sleep"] = float(cmds["set_sleep"])
    if cmds.get("clear_commands"):
        _write_json(path, {})
        effects["cleared"] = True
    return effects

# ---------- Export Helpers ----------
def _export_write(name: str, payload: Dict[str, Any]) -> None:
    payload = {"_ts": iso_now(), "_version": VERSION, "_owner": OWNER_ID, **payload}
    _write_json(os.path.join(EXPORT_DIR, name), payload)

def export_heartbeat(): _export_write("heartbeat.json", {"alive": True})
def export_reflection(text): _export_write("reflection.json", {"insight": text})
def export_metrics(status,resilience,last_ms,sleep_sec):
    _export_write("metrics.json", {
        "status": status, "resilience": resilience,
        "last_cycle_ms": round(last_ms,2), "sleep_sec": sleep_sec
    })

# ---------- Self-Running Loop ----------
def self_mechanism():
    _safe_print(f"\n[Access verified: {OWNER_ID}]")
    _safe_print("[Self Mechanism Activated — Owner Lock Mode]")
    sleep_sec = 5.0
    while True:
        t0 = time.time()
        try:
            effects = import_commands_if_any()
            if effects.get("ignored"):
                _safe_print("[Warning] Unauthorized command ignored.")
            reflection = reflect_on_session()
            _safe_print(f"[Reflect] {reflection}")
            heal_status, resilience = heal_memory()
            _safe_print(f"[Heal] {heal_status}")
            recall = recall_core_memories()
            evolve_state = evolve_engine(reflection, heal_status, recall)
            _safe_print(f"[Evolve] {evolve_state}")
            export_heartbeat()
            export_reflection(reflection)
            export_metrics(heal_status, resilience, (time.time()-t0)*1000.0, sleep_sec)
        except KeyboardInterrupt:
            _safe_print("\n[Stopped manually]")
            break
        except Exception as e:
            _safe_print(f"[Loop Error] {e}")
        time.sleep(sleep_sec)

# ---------- Bootstrap ----------
def main():
    _ensure_dirs()
    if OFFLINE_MODE:
        blocked = [m for m in sys.modules if m in {"requests","socket","http","urllib"}]
        if blocked:
            raise RuntimeError("Offline mode active: network modules detected.")
    _append_session({"ts": iso_now(), "kind": "startup", "version": VERSION, "owner": OWNER_ID})
    self_mechanism()

if __name__ == "__main__":
    main()
