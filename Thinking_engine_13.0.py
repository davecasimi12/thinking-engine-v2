# ------------------------------------------------------------
# Thinking_Engine_13.0.py
# Phase 13 — System Autonomy Layer
# Self-tuning loop: adaptive cycle timing, health-aware pruning,
# autonomy metrics & summaries. Carries forward 12.0 features
# (Healing 2.0 + Emotion Fusion 2.0). Interactive: DISABLED.
# ------------------------------------------------------------

import os, json, time, uuid, argparse, sys, re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Optional

VERSION = "13.0"
SCHEMA_VERSION = 16  # bump for autonomy signals

# ---------- Paths ----------
DATA_DIR = "data"
REPORT_DIR = os.path.join(DATA_DIR, "reports")
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")
HEAL_SUMMARY_PATH = os.path.join(REPORT_DIR, "healing_summary.json")
EMOTION_SUMMARY_PATH = os.path.join(REPORT_DIR, "emotion_summary.json")
AUTONOMY_SUMMARY_PATH = os.path.join(REPORT_DIR, "autonomy_summary.json")

# ---------- Utils ----------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

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

# ---------- Core Data ----------
def _load_memory() -> Dict[str, Any]:
    mem = _read_json(MEMORY_PATH, {})
    if not isinstance(mem, dict):
        mem = {}
    mem.setdefault("_meta", {"schema_version": SCHEMA_VERSION, "version": VERSION, "updated": iso_now()})
    mem.setdefault("core_memories", [])
    mem.setdefault("signals", {})  # holds affect & autonomy signals
    return mem

def _save_memory(mem: Dict[str, Any]) -> None:
    mem["_meta"]["schema_version"] = SCHEMA_VERSION
    mem["_meta"]["version"] = VERSION
    mem["_meta"]["updated"] = iso_now()
    _write_json(MEMORY_PATH, mem)

# ---------- Emotion Fusion 2.0 (from Phase 12) ----------
POSITIVE = {"win","success","stable","growth","clear","good","great","love","proud","ready","focus"}
NEGATIVE = {"error","fail","bug","lost","mad","angry","sad","risk","bad","conflict","block","hiccup"}
HIGH_AROUSAL = {"alert","urgent","now","fast","hot","fire","launch","pressure","intense","crash"}
LOW_AROUSAL  = {"calm","steady","chill","slow","idle","rest"}

def analyze_emotion(text: str) -> Tuple[float, float, List[str]]:
    if not isinstance(text, str) or not text.strip():
        return (0.0, 0.2, [])
    t = text.lower()
    val = 0.2 * sum(1 for w in POSITIVE if w in t) - 0.25 * sum(1 for w in NEGATIVE if w in t)
    aro = 0.2 + 0.15 * sum(1 for w in HIGH_AROUSAL if w in t) - 0.1 * sum(1 for w in LOW_AROUSAL if w in t)
    labels = []
    if any(w in t for w in POSITIVE): labels.append("positive")
    if any(w in t for w in NEGATIVE): labels.append("negative")
    if any(w in t for w in HIGH_AROUSAL): labels.append("high_arousal")
    if any(w in t for w in LOW_AROUSAL): labels.append("low_arousal")
    return (_clip(val, -1.0, 1.0), _clip(aro, 0.0, 1.0), labels)

def _ensure_affect_fields(it: Dict[str, Any]) -> None:
    aff = it.get("affect")
    if not isinstance(aff, dict):
        aff = {}
    aff.setdefault("valence", 0.0)
    aff.setdefault("arousal", 0.3)
    aff.setdefault("labels", [])
    it["affect"] = aff

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
    val, aro, labels = analyze_emotion(insight)
    _append_session({"ts": iso_now(), "kind": "reflection", "insight": insight, "affect": {"valence": val, "arousal": aro, "labels": labels}})
    mem = _load_memory()
    signals = mem.get("signals", {})
    signals["recent_affect"] = {"valence": val, "arousal": aro, "labels": labels, "ts": iso_now()}
    mem["signals"] = signals
    _save_memory(mem)
    return insight

# ---------- Healing 2.0 ----------
REQUIRED_FIELDS = {"id": str, "content": str, "tags": list, "score": float, "last_seen": str}
DEFAULT_ITEM = lambda: {
    "id": str(uuid.uuid4()),
    "content": "",
    "tags": [],
    "score": 0.0,
    "last_seen": iso_now(),
    "health": "ok",  # ok | healed | anomalous
    "penalty": 0.0,
    "affect": {"valence": 0.0, "arousal": 0.3, "labels": []},
}

def _is_iso8601_z(s: str) -> bool:
    return isinstance(s, str) and bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", s))

def _normalize_item(it: Any) -> Dict[str, Any]:
    base = DEFAULT_ITEM()
    if not isinstance(it, dict):
        return base
    out = {}
    out["id"] = str(it.get("id") or base["id"])
    out["content"] = str(it.get("content") or "")
    out["tags"] = it.get("tags") if isinstance(it.get("tags"), list) else []
    try: out["score"] = float(it.get("score", 0.0))
    except Exception: out["score"] = 0.0
    out["last_seen"] = it.get("last_seen") if _is_iso8601_z(it.get("last_seen","")) else iso_now()
    out["health"] = it.get("health") if it.get("health") in {"ok","healed","anomalous"} else "ok"
    try: out["penalty"] = float(it.get("penalty", 0.0))
    except Exception: out["penalty"] = 0.0
    aff = it.get("affect")
    if not isinstance(aff, dict): aff = base["affect"]
    out["affect"] = {
        "valence": _clip(float(aff.get("valence", 0.0)), -1.0, 1.0),
        "arousal": _clip(float(aff.get("arousal", 0.3)), 0.0, 1.0),
        "labels": aff.get("labels") if isinstance(aff.get("labels"), list) else [],
    }
    return out

def _detect_anomalies(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    anomalies = {"missing_fields": 0, "bad_timestamp": 0, "duplicate_ids": 0, "non_dict": 0}
    id_seen = set(); dup_ids = set()
    for it in items:
        if not isinstance(it, dict):
            anomalies["non_dict"] += 1; continue
        for k in REQUIRED_FIELDS:
            if k not in it: anomalies["missing_fields"] += 1; break
        if not _is_iso8601_z(it.get("last_seen","")): anomalies["bad_timestamp"] += 1
        _id = str(it.get("id"))
        if _id in id_seen: dup_ids.add(_id)
        else: id_seen.add(_id)
    anomalies["duplicate_ids"] = len(dup_ids)
    return anomalies

def heal_memory() -> Tuple[str, float]:
    """
    Returns (status_str, resilience_float)
    """
    mem = _load_memory()
    raw_items = mem.get("core_memories", [])
    if not isinstance(raw_items, list): raw_items = []

    pre_stats = _detect_anomalies(raw_items)

    seen_sig = set(); seen_ids = set()
    healed: List[Dict[str, Any]] = []
    dedup_sig = dedup_ids = repaired = anomalous_marked = 0

    for it in raw_items:
        was_dict = isinstance(it, dict)
        norm = _normalize_item(it)
        repaired += int((not was_dict) or it != norm)

        sig = (norm.get("content",""), tuple(sorted(norm.get("tags",[]))))
        if sig in seen_sig:
            dedup_sig += 1
            norm["health"] = "healed"
            norm["penalty"] = max(norm.get("penalty", 0.0), 0.1)
            continue
        seen_sig.add(sig)

        _id = norm.get("id")
        if _id in seen_ids:
            dedup_ids += 1
            norm["id"] = str(uuid.uuid4())
            norm["health"] = "healed"
            norm["penalty"] = max(norm.get("penalty", 0.0), 0.15)
        seen_ids.add(norm["id"])

        if not norm.get("content"):
            norm["health"] = "anomalous"
            norm["penalty"] = max(norm.get("penalty", 0.0), 0.2)
            anomalous_marked += 1

        _ensure_affect_fields(norm)
        healed.append(norm)

    mem["core_memories"] = healed
    _save_memory(mem)

    total = len(healed)
    ok_count = sum(1 for it in healed if it.get("health") == "ok")
    healed_count = sum(1 for it in healed if it.get("health") == "healed")
    anomalous_count = sum(1 for it in healed if it.get("health") == "anomalous")
    resilience = 0.0 if total == 0 else round(ok_count / total, 3)

    summary = _read_json(HEAL_SUMMARY_PATH, {"schema": 1, "history": []})
    pulse = {
        "ts": iso_now(), "version": VERSION,
        "pre_anomalies": pre_stats,
        "repairs": {"normalized_or_fixed": repaired, "dedup_signature": dedup_sig, "dedup_ids": dedup_ids, "anomalous_marked": anomalous_marked},
        "post_health": {"total": total, "ok": ok_count, "healed": healed_count, "anomalous": anomalous_count, "resilience": resilience},
        "status": "OK" if anomalous_count == 0 and pre_stats == {"missing_fields":0,"bad_timestamp":0,"duplicate_ids":0,"non_dict":0} else "WARN"
    }
    summary["history"].append(pulse)
    _write_json(HEAL_SUMMARY_PATH, summary)

    status = f"ok | items={total} | dedup_sig={dedup_sig} | dedup_ids={dedup_ids} | repaired={repaired} | resilience={resilience}"
    _append_session({"ts": iso_now(), "kind": "heal2", "status": status})
    return status, resilience

# ---------- Recall with Emotion Bias ----------
def recall_core_memories(limit: int = 5) -> List[Dict[str, Any]]:
    mem = _load_memory()
    items = mem.get("core_memories", [])
    if not isinstance(items, list) or not items:
        _append_session({"ts": iso_now(), "kind": "recall", "count": 0})
        return []
    signals = mem.get("signals", {})
    r_aff = signals.get("recent_affect", {"valence": 0.0, "arousal": 0.3})

    def _eff_score(it: Dict[str, Any]) -> Tuple[float, str]:
        base = float(it.get("score", 0.0))
        penalty = float(it.get("penalty", 0.0))
        health = it.get("health", "ok")
        health_bonus = 0.02 if health == "ok" else (0.0 if health == "healed" else -0.05)
        aff = it.get("affect", {})
        val = float(aff.get("valence", 0.0)); aro = float(aff.get("arousal", 0.3))
        valence_bonus = 0.03 * val
        arousal_bonus = 0.04 * (1 - abs(0.55 - _clip(aro, 0.0, 1.0)) * 2)
        align_bonus = 0.02 * (val * float(r_aff.get("valence", 0.0)))
        eff = base - penalty + health_bonus + valence_bonus + arousal_bonus + align_bonus
        return (eff, it.get("last_seen","1970-01-01T00:00:00Z"))

    ranked = sorted(items, key=_eff_score, reverse=True)
    take = ranked[: max(1, int(limit))]
    _append_session({"ts": iso_now(), "kind": "recall", "count": len(take)})
    return take

# ---------- Evolution ----------
def evolve_engine(reflection: str, heal_status: str, recalled: List[Dict[str, Any]]) -> str:
    mem = _load_memory()
    id_set = {it.get("id") for it in recalled}
    changed = 0
    for it in mem.get("core_memories", []):
        if it.get("id") in id_set:
            it["score"] = float(it.get("score", 0.0)) + 0.1
            p = float(it.get("penalty", 0.0))
            if p > 0.0: it["penalty"] = max(0.0, round(p - 0.02, 3))
            if it.get("health") in {"healed","anomalous"} and it.get("penalty",0.0) == 0.0:
                it["health"] = "ok"
            _ensure_affect_fields(it)
            val = float(it["affect"]["valence"])
            if abs(val) > 0.8: it["affect"]["valence"] = round(val * 0.95, 3)
            aro = float(it["affect"]["arousal"])
            it["affect"]["arousal"] = round(aro + (0.55 - aro) * 0.05, 3)
            it["last_seen"] = iso_now()
            changed += 1
    _save_memory(mem)

    # Emotion summary pulse
    aff_vals = [float(m.get("affect",{}).get("valence",0.0)) for m in mem.get("core_memories",[])]
    aff_aros = [float(m.get("affect",{}).get("arousal",0.3)) for m in mem.get("core_memories",[])]
    emo_summary = _read_json(EMOTION_SUMMARY_PATH, {"schema": 1, "history": []})
    emo_summary["history"].append({
        "ts": iso_now(), "version": VERSION,
        "avg_valence": round(sum(aff_vals)/len(aff_vals), 3) if aff_vals else 0.0,
        "avg_arousal": round(sum(aff_aros)/len(aff_aros), 3) if aff_aros else 0.0,
        "recalled": [it.get("id") for it in recalled],
    })
    _write_json(EMOTION_SUMMARY_PATH, emo_summary)

    report = {"ts": iso_now(), "version": VERSION, "reflection": reflection, "heal_status": heal_status, "recalled": [it.get("id") for it in recalled], "changed": changed}
    _append_session({"ts": report["ts"], "kind": "evolve", "changed": changed})
    _write_json(os.path.join(REPORT_DIR, f"cycle_{int(time.time())}.json"), report)
    return f"score_updates={changed}"

# ---------- Autonomy Layer ----------
AUTONOMY_DEFAULTS = {
    "sleep_sec_base": 5.0,
    "sleep_sec_min": 2.0,
    "sleep_sec_max": 15.0,
    "target_compute_ms": 800.0,   # desired compute time per cycle (excl. sleep)
    "error_backoff_sec": 3.0,
    "prune_max_items": 1000,
    "prune_floor_keep": 50,
    "prune_if_score_lt": 0.05,
    "prune_if_penalty_gt": 0.2,
    "prune_if_last_seen_days_gt": 7,
}

def _autonomy_state() -> Dict[str, Any]:
    mem = _load_memory()
    signals = mem.get("signals", {})
    auto = signals.get("autonomy", {})
    if not isinstance(auto, dict): auto = {}
    # rolling stats
    auto.setdefault("sleep_sec", AUTONOMY_DEFAULTS["sleep_sec_base"])
    auto.setdefault("rolling_ms", [])  # last N compute durations
    auto.setdefault("rolling_errors", [])  # last N (0/1)
    auto.setdefault("last_prune", None)
    signals["autonomy"] = auto
    mem["signals"] = signals
    _save_memory(mem)
    return auto

def _save_autonomy_state(state: Dict[str, Any]) -> None:
    mem = _load_memory()
    signals = mem.get("signals", {})
    signals["autonomy"] = state
    mem["signals"] = signals
    _save_memory(mem)

def _maybe_prune_memories(resilience: float) -> Dict[str, int]:
    """
    Prune when memory count exceeds max, or resilience is high but store is bloated.
    Returns stats dict.
    """
    mem = _load_memory()
    items = mem.get("core_memories", [])
    total_before = len(items)
    stats = {"pruned": 0, "kept": total_before}

    if total_before <= AUTONOMY_DEFAULTS["prune_max_items"]:
        return stats

    # prune criteria
    cutoff_days = AUTONOMY_DEFAULTS["prune_if_last_seen_days_gt"]
    cutoff_ts = datetime.now(timezone.utc) - timedelta(days=cutoff_days)

    def _eligible(it: Dict[str, Any]) -> bool:
        try:
            last_seen = datetime.strptime(it.get("last_seen","1970-01-01T00:00:00Z"), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except Exception:
            last_seen = datetime(1970,1,1,tzinfo=timezone.utc)
        score = float(it.get("score", 0.0))
        penalty = float(it.get("penalty", 0.0))
        health = it.get("health","ok")
        old_enough = last_seen < cutoff_ts
        weak = (score < AUTONOMY_DEFAULTS["prune_if_score_lt"] and penalty > AUTONOMY_DEFAULTS["prune_if_penalty_gt"]) or health == "anomalous"
        return old_enough and weak

    # keep healthiest/highest score first, but drop eligible ones
    survivors = [it for it in items if not _eligible(it)]
    # ensure a floor of items kept
    if len(survivors) < AUTONOMY_DEFAULTS["prune_floor_keep"]:
        # keep top by score if we fell below floor
        ranked = sorted(items, key=lambda it: float(it.get("score",0.0)), reverse=True)
        survivors = ranked[:AUTONOMY_DEFAULTS["prune_floor_keep"]]

    stats["pruned"] = total_before - len(survivors)
    stats["kept"] = len(survivors)
    mem["core_memories"] = survivors
    _save_memory(mem)
    return stats

def autonomy_controller(last_ms: float, had_error: bool, recalled_count: int, resilience: float) -> Tuple[float, Dict[str,int]]:
    """
    Adjusts sleep seconds based on compute time and errors; may prune memory.
    Returns (next_sleep_sec, prune_stats)
    """
    state = _autonomy_state()
    # track rolling metrics
    rm = state.get("rolling_ms", []); rm.append(last_ms); state["rolling_ms"] = rm[-20:]
    re = state.get("rolling_errors", []); re.append(1 if had_error else 0); state["rolling_errors"] = re[-50:]

    # base sleep adjust
    sleep_sec = float(state.get("sleep_sec", AUTONOMY_DEFAULTS["sleep_sec_base"]))
    target_ms = AUTONOMY_DEFAULTS["target_compute_ms"]

    # if compute is very fast (< 0.5 * target) and healthy, speed up slightly
    if last_ms < 0.5 * target_ms and resilience >= 0.9 and recalled_count >= 1:
        sleep_sec = max(AUTONOMY_DEFAULTS["sleep_sec_min"], round(sleep_sec - 0.5, 2))
    # if compute is heavy (> 1.5 * target) or resilience is low, slow down
    if last_ms > 1.5 * target_ms or resilience < 0.6:
        sleep_sec = min(AUTONOMY_DEFAULTS["sleep_sec_max"], round(sleep_sec + 0.5, 2))
    # error backoff
    if had_error:
        sleep_sec = min(AUTONOMY_DEFAULTS["sleep_sec_max"], round(sleep_sec + AUTONOMY_DEFAULTS["error_backoff_sec"], 2))

    state["sleep_sec"] = sleep_sec

    # decide pruning if store is large; prefer to prune when resilience is decent
    prune_stats = {"pruned": 0, "kept": 0}
    mem = _read_json(MEMORY_PATH, {})
    total_items = len(mem.get("core_memories", [])) if isinstance(mem.get("core_memories", []), list) else 0
    if total_items > AUTONOMY_DEFAULTS["prune_max_items"] and resilience >= 0.7:
        prune_stats = _maybe_prune_memories(resilience)
        state["last_prune"] = {"ts": iso_now(), **prune_stats}

    _save_autonomy_state(state)

    # write autonomy pulse
    auto_summary = _read_json(AUTONOMY_SUMMARY_PATH, {"schema": 1, "history": []})
    auto_summary["history"].append({
        "ts": iso_now(),
        "version": VERSION,
        "last_ms": round(last_ms, 2),
        "sleep_sec": sleep_sec,
        "had_error": had_error,
        "recalled_count": recalled_count,
        "resilience": resilience,
        "prune": prune_stats
    })
    _write_json(AUTONOMY_SUMMARY_PATH, auto_summary)

    return sleep_sec, prune_stats

# ------------------------------------------------------------
# Self-Running Loop: Reflect • Heal • Recall • Evolve • Autonomy
# (AUTOSTARTS ON LAUNCH)
# ------------------------------------------------------------
def self_mechanism():
    _safe_print("\n[Self Mechanism Activated — Autonomous Cycle Running Forever]")
    sleep_sec = AUTONOMY_DEFAULTS["sleep_sec_base"]
    while True:
        cycle_error = False
        t0 = time.time()
        try:
            reflection = reflect_on_session()
            _safe_print(f"[Reflect] Insight derived: {reflection}")

            heal_status, resilience = heal_memory()
            _safe_print(f"[Heal] Memory integrity: {heal_status}")

            recalled_data = recall_core_memories(limit=5)
            _safe_print(f"[Recall] Key memories retrieved: {len(recalled_data)} items")

            evolve_state = evolve_engine(reflection, heal_status, recalled_data)
            _safe_print(f"[Evolve] Evolution complete: {evolve_state}")

        except KeyboardInterrupt:
            _safe_print("\n[Self Mechanism Deactivated — Manual Stop Detected]")
            break
        except Exception as e:
            _safe_print(f"[Self Mechanism Error] {e}")
            cycle_error = True

        # Autonomy adjust (even after error)
        last_ms = (time.time() - t0) * 1000.0
        sleep_sec, prune_stats = autonomy_controller(last_ms, cycle_error, len(recalled_data) if not cycle_error else 0, resilience if not cycle_error else 0.0)

        # Cooldown before next cycle
        time.sleep(sleep_sec)

# ---------- Bootstrap ----------
def _bootstrap_seed_memory():
    mem = _load_memory()
    if not mem.get("core_memories"):
        mem["core_memories"] = [{
            "id": str(uuid.uuid4()),
            "content": "Engine initialized and stable. Ready to win.",
            "tags": ["system","init","ready"],
            "score": 0.6,
            "last_seen": iso_now(),
            "health": "ok",
            "penalty": 0.0,
            "affect": {"valence": 0.2, "arousal": 0.5, "labels": ["positive"]}
        }]
        _save_memory(mem)

def main():
    parser = argparse.ArgumentParser(description="Thinking Engine 13.0")
    parser.add_argument("--cycles", type=int, default=None,
                        help="(Optional) For compatibility only; self_mechanism runs forever.")
    args = parser.parse_args()

    _ensure_dirs()
    _bootstrap_seed_memory()
    _append_session({"ts": iso_now(), "kind": "startup", "version": VERSION})

    self_mechanism()

if __name__ == "__main__":
    main()