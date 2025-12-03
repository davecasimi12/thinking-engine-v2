# ------------------------------------------------------------
# Thinking_Engine_10.0.py
# Phase 10.0 — Stable Core + Autonomous Self Mechanism
# Carries forward: reflection, healing, recall, evolution, reports
# Interactive mode: DISABLED (autostarts self_mechanism)
# ------------------------------------------------------------

import os, json, time, uuid, argparse, sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

VERSION = "10.0"
SCHEMA_VERSION = 13  # safe migration

# ---------- Paths ----------
DATA_DIR = "data"
REPORT_DIR = os.path.join(DATA_DIR, "reports")
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")

# ---------- Utils ----------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

def iso_now() -> str:
    # UTC ISO8601 Z
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
    log = _read_json(SESSION_LOG, [])
    log.append(event)
    _write_json(SESSION_LOG, log)

def _safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except Exception:
        # Never crash on print
        pass

# ---------- Core Data Access ----------
def _load_memory() -> Dict[str, Any]:
    mem = _read_json(MEMORY_PATH, {})
    if not isinstance(mem, dict):
        mem = {}
    # bootstrap root keys
    mem.setdefault("_meta", {"schema_version": SCHEMA_VERSION, "version": VERSION, "updated": iso_now()})
    mem.setdefault("core_memories", [])  # list of dict items
    mem.setdefault("signals", {})        # misc signals
    return mem

def _save_memory(mem: Dict[str, Any]) -> None:
    mem["_meta"]["schema_version"] = SCHEMA_VERSION
    mem["_meta"]["version"] = VERSION
    mem["_meta"]["updated"] = iso_now()
    _write_json(MEMORY_PATH, mem)

# ---------- Reflection ----------
def reflect_on_session() -> str:
    """
    Quick heuristic reflection over the last N session events.
    Produces a short insight string.
    """
    log = _read_json(SESSION_LOG, [])
    window = log[-10:] if len(log) > 10 else log
    if not window:
        insight = "No recent events; baseline stable."
    else:
        kinds = {}
        for e in window:
            k = e.get("kind", "unknown")
            kinds[k] = kinds.get(k, 0) + 1
        top = sorted(kinds.items(), key=lambda x: x[1], reverse=True)
        if top:
            insight = f"Recent focus: {top[0][0]} ({top[0][1]} events)."
        else:
            insight = "Activity observed; distribution unclear."
    _append_session({"ts": iso_now(), "kind": "reflection", "insight": insight})
    return insight

# ---------- Healing ----------
def heal_memory() -> str:
    """
    Validates memory structure, removes obvious duplicates, and normalizes fields.
    Returns a status string.
    """
    mem = _load_memory()
    items = mem.get("core_memories", [])
    if not isinstance(items, list):
        items = []
    seen = set()
    healed: List[Dict[str, Any]] = []
    dedup = 0

    for it in items:
        if not isinstance(it, dict):
            continue
        # Normalize fields
        it.setdefault("id", str(uuid.uuid4()))
        it.setdefault("content", "")
        it.setdefault("tags", [])
        it.setdefault("score", 0.0)
        it.setdefault("last_seen", iso_now())

        # Deduplicate by (content, tuple(tags))
        sig = (it.get("content", ""), tuple(sorted(it.get("tags", []))))
        if sig in seen:
            dedup += 1
            continue
        seen.add(sig)
        healed.append(it)

    mem["core_memories"] = healed
    _save_memory(mem)

    status = f"ok | items={len(healed)} | dedup={dedup}"
    _append_session({"ts": iso_now(), "kind": "heal", "status": status})
    return status

# ---------- Recall ----------
def recall_core_memories(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Returns up to `limit` top memories, ranked by score then recency.
    """
    mem = _load_memory()
    items = mem.get("core_memories", [])
    if not isinstance(items, list) or not items:
        return []
    def _key(it):
        # higher score first, then newer last_seen first
        ls = it.get("last_seen", "1970-01-01T00:00:00Z")
        return (it.get("score", 0.0), ls)
    ranked = sorted(items, key=_key, reverse=True)
    take = ranked[: max(1, int(limit))]
    # log recall event
    _append_session({"ts": iso_now(), "kind": "recall", "count": len(take)})
    return take

# ---------- Evolution ----------
def evolve_engine(reflection: str, heal_status: str, recalled: List[Dict[str, Any]]) -> str:
    """
    Simple adaptive tweak: bump scores for recalled memories and log a pulse report.
    """
    mem = _load_memory()
    id_set = {it.get("id") for it in recalled}
    changed = 0
    for it in mem.get("core_memories", []):
        if it.get("id") in id_set:
            it["score"] = float(it.get("score", 0.0)) + 0.1
            it["last_seen"] = iso_now()
            changed += 1
    _save_memory(mem)

    # Emit a small cycle report
    report = {
        "ts": iso_now(),
        "version": VERSION,
        "reflection": reflection,
        "heal": heal_status,
        "recalled": [it.get("id") for it in recalled],
        "changed": changed,
    }
    _append_session({"ts": report["ts"], "kind": "evolve", "changed": changed})
    _write_json(os.path.join(REPORT_DIR, f"cycle_{int(time.time())}.json"), report)
    return f"score_updates={changed}"

# ------------------------------------------------------------
# Self-Running Loop: Reflect • Heal • Recall • Evolve
# Triggered by the Self Mechanism (AUTOSTARTS ON LAUNCH)
# ------------------------------------------------------------
def self_mechanism():
    _safe_print("\n[Self Mechanism Activated — Autonomous Cycle Running Forever]")
    while True:
        try:
            # 1) REFLECT
            reflection = reflect_on_session()
            _safe_print(f"[Reflect] Insight derived: {reflection}")

            # 2) HEAL
            heal_status = heal_memory()
            _safe_print(f"[Heal] Memory integrity: {heal_status}")

            # 3) RECALL
            recalled_data = recall_core_memories(limit=5)
            _safe_print(f"[Recall] Key memories retrieved: {len(recalled_data)} items")

            # 4) EVOLVE
            evolve_state = evolve_engine(reflection, heal_status, recalled_data)
            _safe_print(f"[Evolve] Evolution complete: {evolve_state}")

            # 5) Wait before next cycle (adjustable)
            time.sleep(5)

        except KeyboardInterrupt:
            _safe_print("\n[Self Mechanism Deactivated — Manual Stop Detected]")
            break
        except Exception as e:
            _safe_print(f"[Self Mechanism Error] {e}")
            time.sleep(3)

# ---------- Bootstrap ----------
def _bootstrap_seed_memory():
    """
    Ensure memory exists; if empty, insert a small seed so evolution has material.
    """
    mem = _load_memory()
    if not mem.get("core_memories"):
        mem["core_memories"] = [{
            "id": str(uuid.uuid4()),
            "content": "Engine initialized and stable.",
            "tags": ["system", "init"],
            "score": 0.5,
            "last_seen": iso_now(),
        }]
        _save_memory(mem)

def main():
    parser = argparse.ArgumentParser(description="Thinking Engine 10.0")
    parser.add_argument("--cycles", type=int, default=None,
                        help="(Optional) For compatibility only; self_mechanism runs forever.")
    args = parser.parse_args()

    _ensure_dirs()
    _bootstrap_seed_memory()

    # Log startup
    _append_session({"ts": iso_now(), "kind": "startup", "version": VERSION})

    # AUTOSTART self mechanism (interactive disabled)
    self_mechanism()

if __name__ == "__main__":
    main()