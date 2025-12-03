# ------------------------------------------------------------
# Thinking_Engine_11.0.py
# Phase 11 — Self-Correction & Healing 2.0
# Carries forward 10.0 + adds anomaly detection, auto-repair,
# adaptive memory health, resilience metrics, healing summary.
# Interactive mode: DISABLED (autostarts self_mechanism)
# ------------------------------------------------------------

import os, json, time, uuid, argparse, sys, re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

VERSION = "11.0"
SCHEMA_VERSION = 14  # bumped for Healing 2.0 fields

# ---------- Paths ----------
DATA_DIR = "data"
REPORT_DIR = os.path.join(DATA_DIR, "reports")
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")
HEAL_SUMMARY_PATH = os.path.join(REPORT_DIR, "healing_summary.json")

# ---------- Utils ----------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

def iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

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
        pass

# ---------- Core Data ----------
def _load_memory() -> Dict[str, Any]:
    mem = _read_json(MEMORY_PATH, {})
    if not isinstance(mem, dict):
        mem = {}
    mem.setdefault("_meta", {"schema_version": SCHEMA_VERSION, "version": VERSION, "updated": iso_now()})
    mem.setdefault("core_memories", [])
    mem.setdefault("signals", {})
    return mem

def _save_memory(mem: Dict[str, Any]) -> None:
    mem["_meta"]["schema_version"] = SCHEMA_VERSION
    mem["_meta"]["version"] = VERSION
    mem["_meta"]["updated"] = iso_now()
    _write_json(MEMORY_PATH, mem)

# ---------- Reflection ----------
def reflect_on_session() -> str:
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
        insight = f"Recent focus: {top[0][0]} ({top[0][1]} events)." if top else "Activity observed; distribution unclear."
    _append_session({"ts": iso_now(), "kind": "reflection", "insight": insight})
    return insight

# ---------- Healing 2.0 (Anomaly Detection + Auto-Repair) ----------
REQUIRED_FIELDS = {"id": str, "content": str, "tags": list, "score": float, "last_seen": str}
DEFAULT_ITEM = lambda: {
    "id": str(uuid.uuid4()),
    "content": "",
    "tags": [],
    "score": 0.0,
    "last_seen": iso_now(),
    # Healing 2.0 fields:
    "health": "ok",         # ok | healed | anomalous
    "penalty": 0.0,         # adaptive penalty after repair/anomaly
}

def _is_iso8601_z(s: str) -> bool:
    return isinstance(s, str) and bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", s))

def _normalize_item(it: Any) -> Dict[str, Any]:
    """Bring arbitrary input into a valid memory item shape."""
    base = DEFAULT_ITEM()
    if not isinstance(it, dict):
        return base
    out = {}
    out["id"] = str(it.get("id") or base["id"])
    out["content"] = str(it.get("content") or "")
    out["tags"] = it.get("tags")
    if not isinstance(out["tags"], list):
        out["tags"] = []
    try:
        out["score"] = float(it.get("score", 0.0))
    except Exception:
        out["score"] = 0.0
    out["last_seen"] = it.get("last_seen") if _is_iso8601_z(it.get("last_seen", "")) else iso_now()
    # Healing 2.0 fields
    out["health"] = it.get("health") if it.get("health") in {"ok", "healed", "anomalous"} else "ok"
    try:
        out["penalty"] = float(it.get("penalty", 0.0))
    except Exception:
        out["penalty"] = 0.0
    return out

def _detect_anomalies(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return stats & indices of anomalies before repair."""
    anomalies = {
        "missing_fields": 0,
        "bad_timestamp": 0,
        "duplicate_ids": 0,
        "non_dict": 0,
    }
    id_seen = set()
    dup_ids = set()
    for it in items:
        if not isinstance(it, dict):
            anomalies["non_dict"] += 1
            continue
        # missing fields
        for k in REQUIRED_FIELDS:
            if k not in it:
                anomalies["missing_fields"] += 1
                break
        # timestamp format
        if isinstance(it, dict) and not _is_iso8601_z(it.get("last_seen", "")):
            anomalies["bad_timestamp"] += 1
        # duplicate ids
        _id = str(it.get("id"))
        if _id in id_seen:
            dup_ids.add(_id)
        else:
            id_seen.add(_id)
    anomalies["duplicate_ids"] = len(dup_ids)
    return anomalies

def heal_memory() -> str:
    """
    Healing 2.0:
      - Detect anomalies
      - Normalize/repair items
      - Deduplicate by (content, tags) AND by duplicate id
      - Apply adaptive penalties
      - Compute resilience metrics
      - Persist per-cycle healing summary
    """
    mem = _load_memory()
    raw_items = mem.get("core_memories", [])
    if not isinstance(raw_items, list):
        raw_items = []

    # 1) Pre-repair anomaly scan
    pre_stats = _detect_anomalies(raw_items)

    # 2) Normalize/repair + de-duplication
    seen_sig = set()
    seen_ids = set()
    healed: List[Dict[str, Any]] = []
    dedup_sig = 0
    dedup_ids = 0
    repaired = 0
    anomalous_marked = 0

    for it in raw_items:
        was_dict = isinstance(it, dict)
        norm = _normalize_item(it)
        repaired += int((not was_dict) or it != norm)

        # de-dup signature by content+tags
        sig = (norm.get("content", ""), tuple(sorted(norm.get("tags", []))))
        if sig in seen_sig:
            dedup_sig += 1
            # penalty if duplicates detected
            norm["health"] = "healed"
            norm["penalty"] = max(norm.get("penalty", 0.0), 0.1)
            continue
        seen_sig.add(sig)

        # de-dup by duplicate IDs (rare but possible)
        _id = norm.get("id")
        if _id in seen_ids:
            dedup_ids += 1
            # regenerate a new id and mark healed
            norm["id"] = str(uuid.uuid4())
            norm["health"] = "healed"
            norm["penalty"] = max(norm.get("penalty", 0.0), 0.15)
        seen_ids.add(norm["id"])

        # mark items with empty content as anomalous but keep (engine can evolve them later)
        if not norm.get("content"):
            norm["health"] = "anomalous"
            norm["penalty"] = max(norm.get("penalty", 0.0), 0.2)
            anomalous_marked += 1

        healed.append(norm)

    # 3) Save repaired state
    mem["core_memories"] = healed
    _save_memory(mem)

    # 4) Resilience metrics
    total = len(healed)
    ok_count = sum(1 for it in healed if it.get("health") == "ok")
    healed_count = sum(1 for it in healed if it.get("health") == "healed")
    anomalous_count = sum(1 for it in healed if it.get("health") == "anomalous")
    resilience = 0.0 if total == 0 else round(ok_count / total, 3)

    # 5) Healing summary (persist & append)
    summary = _read_json(HEAL_SUMMARY_PATH, {
        "schema": 1,
        "history": []  # append per cycle
    })
    pulse = {
        "ts": iso_now(),
        "version": VERSION,
        "pre_anomalies": pre_stats,
        "repairs": {
            "normalized_or_fixed": repaired,
            "dedup_signature": dedup_sig,
            "dedup_ids": dedup_ids,
            "anomalous_marked": anomalous_marked
        },
        "post_health": {
            "total": total,
            "ok": ok_count,
            "healed": healed_count,
            "anomalous": anomalous_count,
            "resilience": resilience
        },
        "status": "OK" if anomalous_count == 0 and pre_stats == {"missing_fields": 0, "bad_timestamp": 0, "duplicate_ids": 0, "non_dict": 0} else "WARN"
    }
    summary["history"].append(pulse)
    _write_json(HEAL_SUMMARY_PATH, summary)

    # 6) Session event
    status = f"ok | items={total} | dedup_sig={dedup_sig} | dedup_ids={dedup_ids} | repaired={repaired} | resilience={resilience}"
    _append_session({"ts": iso_now(), "kind": "heal2", "status": status})
    return status

# ---------- Recall (score minus penalty; prioritize healthy) ----------
def recall_core_memories(limit: int = 5) -> List[Dict[str, Any]]:
    mem = _load_memory()
    items = mem.get("core_memories", [])
    if not isinstance(items, list) or not items:
        _append_session({"ts": iso_now(), "kind": "recall", "count": 0})
        return []

    def _eff_score(it: Dict[str, Any]) -> Tuple[float, str, str]:
        base = float(it.get("score", 0.0))
        penalty = float(it.get("penalty", 0.0))
        health = it.get("health", "ok")
        # slight priority boost for healthy over healed, and healed over anomalous
        health_bonus = 0.02 if health == "ok" else (0.0 if health == "healed" else -0.05)
        eff = base - penalty + health_bonus
        ls = it.get("last_seen", "1970-01-01T00:00:00Z")
        return (eff, ls, health)

    ranked = sorted(items, key=_eff_score, reverse=True)
    take = ranked[: max(1, int(limit))]
    _append_session({"ts": iso_now(), "kind": "recall", "count": len(take)})
    return take

# ---------- Evolution (respect penalties; reward stability) ----------
def evolve_engine(reflection: str, heal_status: str, recalled: List[Dict[str, Any]]) -> str:
    mem = _load_memory()
    id_set = {it.get("id") for it in recalled}
    changed = 0
    for it in mem.get("core_memories", []):
        if it.get("id") in id_set:
            it["score"] = float(it.get("score", 0.0)) + 0.1
            # If an item is repeatedly recalled, gradually reduce penalty and move it toward "ok"
            current_penalty = float(it.get("penalty", 0.0))
            if current_penalty > 0.0:
                it["penalty"] = max(0.0, round(current_penalty - 0.02, 3))
            if it.get("health") in {"healed", "anomalous"} and it.get("penalty", 0.0) == 0.0:
                it["health"] = "ok"
            it["last_seen"] = iso_now()
            changed += 1
    _save_memory(mem)

    report = {
        "ts": iso_now(),
        "version": VERSION,
        "reflection": reflection,
        "heal_status": heal_status,
        "recalled": [it.get("id") for it in recalled],
        "changed": changed,
    }
    _append_session({"ts": report["ts"], "kind": "evolve", "changed": changed})
    _write_json(os.path.join(REPORT_DIR, f"cycle_{int(time.time())}.json"), report)
    return f"score_updates={changed}"

# ------------------------------------------------------------
# Self-Running Loop: Reflect • Heal • Recall • Evolve
# (AUTOSTARTS ON LAUNCH)
# ------------------------------------------------------------
def self_mechanism():
    _safe_print("\n[Self Mechanism Activated — Autonomous Cycle Running Forever]")
    while True:
        try:
            # 1) REFLECT
            reflection = reflect_on_session()
            _safe_print(f"[Reflect] Insight derived: {reflection}")

            # 2) HEAL 2.0
            heal_status = heal_memory()
            _safe_print(f"[Heal] Memory integrity: {heal_status}")

            # 3) RECALL (healthy-first, score-minus-penalty)
            recalled_data = recall_core_memories(limit=5)
            _safe_print(f"[Recall] Key memories retrieved: {len(recalled_data)} items")

            # 4) EVOLVE (reduce penalties on stable recalls)
            evolve_state = evolve_engine(reflection, heal_status, recalled_data)
            _safe_print(f"[Evolve] Evolution complete: {evolve_state}")

            # 5) Wait before next cycle
            time.sleep(5)

        except KeyboardInterrupt:
            _safe_print("\n[Self Mechanism Deactivated — Manual Stop Detected]")
            break
        except Exception as e:
            _safe_print(f"[Self Mechanism Error] {e}")
            time.sleep(3)

# ---------- Bootstrap ----------
def _bootstrap_seed_memory():
    mem = _load_memory()
    if not mem.get("core_memories"):
        mem["core_memories"] = [{
            "id": str(uuid.uuid4()),
            "content": "Engine initialized and stable.",
            "tags": ["system", "init"],
            "score": 0.6,
            "last_seen": iso_now(),
            "health": "ok",
            "penalty": 0.0,
        }]
        _save_memory(mem)

def main():
    parser = argparse.ArgumentParser(description="Thinking Engine 11.0")
    parser.add_argument("--cycles", type=int, default=None,
                        help="(Optional) For compatibility only; self_mechanism runs forever.")
    args = parser.parse_args()

    _ensure_dirs()
    _bootstrap_seed_memory()
    _append_session({"ts": iso_now(), "kind": "startup", "version": VERSION})

    # AUTOSTART self mechanism
    self_mechanism()

if __name__ == "__main__":
    main()