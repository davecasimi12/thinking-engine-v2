# ------------------------------------------------------------
# Thinking_Engine_16.0.py
# Phase 16 — Security & Guard Layer
# - Owner-Lock (owner == "YZ")
# - Offline-only + local HTTP mirror (127.0.0.1)
# - File integrity hashing (.sha) for all critical JSONs
# - Startup + per-cycle verification with audit logging
# ------------------------------------------------------------

import os, json, time, uuid, argparse, sys, re, threading, hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

VERSION = "16.0"
SCHEMA_VERSION = 19
OWNER_ID = "YZ"              # Only this owner's commands are accepted
OFFLINE_MODE = True          # Safety flag: never use network modules beyond local HTTP mirror
HTTP_HOST = "127.0.0.1"      # Local-only
HTTP_PORT = 5050             # Change if needed
SLEEP_SEC_BASE = 5.0         # default loop sleep

# ---------- Paths ----------
DATA_DIR = "data"
REPORT_DIR = os.path.join(DATA_DIR, "reports")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
IMPORT_DIR = os.path.join(DATA_DIR, "imports")
MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")
HEAL_SUMMARY_PATH = os.path.join(REPORT_DIR, "healing_summary.json")
EMOTION_SUMMARY_PATH = os.path.join(REPORT_DIR, "emotion_summary.json")
AUTONOMY_SUMMARY_PATH = os.path.join(REPORT_DIR, "autonomy_summary.json")
AUDIT_LOG_PATH = os.path.join(REPORT_DIR, "audit_log.json")

# ---------- Utils ----------
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

def _append_audit(event: Dict[str, Any]) -> None:
    audit = _read_json(AUDIT_LOG_PATH, {"schema": 1, "history": []})
    event = {"ts": iso_now(), "owner": OWNER_ID, **event}
    audit["history"].append(event)
    _write_and_hash(AUDIT_LOG_PATH, audit)

def _write_json_raw(path: str, payload: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _hash_file(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return _sha256_bytes(f.read())
    except Exception:
        return None

def _sha_path(path: str) -> str:
    return f"{path}.sha"

def _write_and_hash(path: str, payload: Any) -> None:
    _write_json_raw(path, payload)
    h = _hash_file(path)
    _write_json_raw(_sha_path(path), {"path": os.path.basename(path), "sha256": h, "ts": iso_now(), "owner": OWNER_ID})

def _verify_hash(path: str) -> Dict[str, Any]:
    sha_file = _sha_path(path)
    recorded = _read_json(sha_file, {})
    current = _hash_file(path)
    ok = (bool(recorded) and recorded.get("sha256") == current)
    return {"path": path, "ok": ok, "recorded": recorded.get("sha256"), "current": current}

def _append_session(event: Dict[str, Any]) -> None:
    event["owner"] = OWNER_ID
    log = _read_json(SESSION_LOG, [])
    log.append(event)
    _write_and_hash(SESSION_LOG, log)

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
    mem.setdefault("signals", {})
    return mem

def _save_memory(mem: Dict[str, Any]) -> None:
    mem["_meta"]["schema_version"] = SCHEMA_VERSION
    mem["_meta"]["version"] = VERSION
    mem["_meta"]["updated"] = iso_now()
    _write_and_hash(MEMORY_PATH, mem)

# ---------- Emotion tiny lexicon (lite, deterministic) ----------
POSITIVE = {"win","success","stable","growth","clear","good","great","love","proud","ready","focus"}
NEGATIVE = {"error","fail","bug","lost","mad","angry","sad","risk","bad","conflict","block","hiccup"}
def analyze_emotion(text: str) -> Tuple[float, List[str]]:
    if not isinstance(text, str) or not text.strip():
        return (0.0, [])
    t = text.lower()
    score = 0.2 * sum(1 for w in POSITIVE if w in t) - 0.25 * sum(1 for w in NEGATIVE if w in t)
    labels = []
    if any(w in t for w in POSITIVE): labels.append("positive")
    if any(w in t for w in NEGATIVE): labels.append("negative")
    return (_clip(score, -1.0, 1.0), labels)

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
    valence, labels = analyze_emotion(insight)
    _append_session({"ts": iso_now(), "kind": "reflection", "insight": insight, "affect": {"valence": valence, "labels": labels}})
    # store rolling signal
    mem = _load_memory()
    sig = mem.get("signals", {})
    sig["recent_affect"] = {"valence": valence, "labels": labels, "ts": iso_now()}
    mem["signals"] = sig
    _save_memory(mem)
    return insight

# ---------- Healing 2.0 (lite) ----------
REQUIRED_FIELDS = {"id": str, "content": str, "tags": list, "score": float, "last_seen": str}
DEFAULT_ITEM = lambda: {
    "id": str(uuid.uuid4()),
    "content": "",
    "tags": [],
    "score": 0.0,
    "last_seen": iso_now(),
    "health": "ok",
    "penalty": 0.0,
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
    return out

def _detect_anomalies(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    anomalies = {"missing_fields": 0, "bad_timestamp": 0, "duplicate_ids": 0, "non_dict": 0}
    id_seen = set(); dup_ids = set()
    for it in items:
        if not isinstance(it, dict): anomalies["non_dict"] += 1; continue
        for k in REQUIRED_FIELDS:
            if k not in it: anomalies["missing_fields"] += 1; break
        if not _is_iso8601_z(it.get("last_seen","")): anomalies["bad_timestamp"] += 1
        _id = str(it.get("id"))
        if _id in id_seen: dup_ids.add(_id)
        else: id_seen.add(_id)
    anomalies["duplicate_ids"] = len(dup_ids)
    return anomalies

def heal_memory() -> Tuple[str, float]:
    mem = _load_memory()
    raw = mem.get("core_memories", [])
    if not isinstance(raw, list): raw = []
    pre = _detect_anomalies(raw)

    seen_sig = set(); seen_ids = set()
    healed: List[Dict[str, Any]] = []
    dedup_sig = dedup_ids = repaired = anomalous = 0

    for it in raw:
        was_dict = isinstance(it, dict)
        norm = _normalize_item(it)
        repaired += int((not was_dict) or it != norm)

        sig = (norm.get("content",""), tuple(sorted(norm.get("tags",[]))))
        if sig in seen_sig:
            dedup_sig += 1
            norm["health"] = "healed"; norm["penalty"] = max(norm.get("penalty", 0.0), 0.1)
            continue
        seen_sig.add(sig)

        _id = norm.get("id")
        if _id in seen_ids:
            dedup_ids += 1
            norm["id"] = str(uuid.uuid4()); norm["health"] = "healed"; norm["penalty"] = max(norm.get("penalty", 0.0), 0.15)
        seen_ids.add(norm["id"])

        if not norm.get("content"):
            norm["health"] = "anomalous"; norm["penalty"] = max(norm.get("penalty", 0.0), 0.2); anomalous += 1

        healed.append(norm)

    mem["core_memories"] = healed
    _save_memory(mem)

    total = len(healed)
    ok_count = sum(1 for it in healed if it.get("health") == "ok")
    resilience = 0.0 if total == 0 else round(ok_count/total, 3)

    # healing pulse
    summary = _read_json(HEAL_SUMMARY_PATH, {"schema": 1, "history": []})
    pulse = {
        "ts": iso_now(), "version": VERSION, "pre": pre,
        "repairs": {"normalized_or_fixed": repaired, "dedup_sig": dedup_sig, "dedup_ids": dedup_ids, "anomalous": anomalous},
        "post": {"total": total, "ok": ok_count, "resilience": resilience},
        "status": "OK" if anomalous == 0 and pre == {"missing_fields":0,"bad_timestamp":0,"duplicate_ids":0,"non_dict":0} else "WARN"
    }
    summary["history"].append(pulse)
    _write_and_hash(HEAL_SUMMARY_PATH, summary)

    status = f"ok | items={total} | dedup_sig={dedup_sig} | dedup_ids={dedup_ids} | repaired={repaired} | resilience={resilience}"
    _append_session({"ts": iso_now(), "kind": "heal2", "status": status})

    # SECURITY: verify critical files this cycle
    _security_verify_cycle(["memory", MEMORY_PATH],
                           ["healing_summary", HEAL_SUMMARY_PATH],
                           ["session_log", SESSION_LOG])

    return status, resilience

# ---------- Recall / Evolve (lite) ----------
def recall_core_memories(limit: int = 5) -> List[Dict[str, Any]]:
    mem = _load_memory()
    items = mem.get("core_memories", [])
    if not isinstance(items, list) or not items:
        _append_session({"ts": iso_now(), "kind": "recall", "count": 0})
        return []
    def _key(it: Dict[str, Any]) -> Tuple[float, str]:
        return (float(it.get("score", 0.0)) - float(it.get("penalty", 0.0)), it.get("last_seen","1970-01-01T00:00:00Z"))
    ranked = sorted(items, key=_key, reverse=True)
    take = ranked[: max(1, int(limit))]
    _append_session({"ts": iso_now(), "kind": "recall", "count": len(take)})
    return take

def evolve_engine(reflection: str, heal_status: str, recalled: List[Dict[str, Any]]) -> str:
    mem = _load_memory()
    idset = {it.get("id") for it in recalled}
    changed = 0
    for it in mem.get("core_memories", []):
        if it.get("id") in idset:
            it["score"] = float(it.get("score", 0.0)) + 0.1
            p = float(it.get("penalty", 0.0))
            if p > 0.0: it["penalty"] = max(0.0, round(p - 0.02, 3))
            it["last_seen"] = iso_now()
            changed += 1
    _save_memory(mem)

    emo = _read_json(EMOTION_SUMMARY_PATH, {"schema": 1, "history": []})
    emo["history"].append({"ts": iso_now(), "version": VERSION, "recalled": [it.get("id") for it in recalled]})
    _write_and_hash(EMOTION_SUMMARY_PATH, emo)

    rep = {"ts": iso_now(), "version": VERSION, "reflection": reflection, "heal_status": heal_status, "changed": changed}
    _append_session({"ts": rep["ts"], "kind": "evolve", "changed": changed})
    _write_and_hash(os.path.join(REPORT_DIR, f"cycle_{int(time.time())}.json"), rep)
    return f"score_updates={changed}"

# ---------- Exports / Imports (Owner-locked + Hashed) ----------
def _export_write(name: str, payload: Dict[str, Any]) -> None:
    payload = {"_ts": iso_now(), "_version": VERSION, "_owner": OWNER_ID, **payload}
    _write_and_hash(os.path.join(EXPORT_DIR, name), payload)

def export_heartbeat(): _export_write("heartbeat.json", {"alive": True})
def export_reflection(insight: str, affect: Dict[str, Any]) -> None:
    _export_write("reflection.json", {"insight": insight, "affect": affect})
def export_metrics(heal_status: str, resilience: float, recalled_ids: List[str], last_ms: float, sleep_sec: float) -> None:
    _export_write("metrics.json", {
        "heal_status": heal_status, "resilience": resilience,
        "recalled": recalled_ids, "last_cycle_ms": round(last_ms,2), "sleep_sec": sleep_sec
    })
def export_bundle(insight: str, affect: Dict[str, Any], heal_status: str, resilience: float, recalled_ids: List[str], last_ms: float, sleep_sec: float) -> None:
    _export_write("sync_bundle.json", {
        "reflection": {"insight": insight, "affect": affect},
        "loop": {"heal_status": heal_status, "resilience": resilience, "recalled": recalled_ids, "last_cycle_ms": round(last_ms,2), "sleep_sec": sleep_sec}
    })

def import_commands_if_any() -> Dict[str, Any]:
    """
    Reads data/imports/commands.json and only processes if owner == YZ.
    Supported (optional): {"owner":"YZ","set_sleep":8}, {"owner":"YZ","push_memory":{...}}, {"owner":"YZ","clear_commands":true}
    """
    path = os.path.join(IMPORT_DIR, "commands.json")
    cmds = _read_json(path, {})
    effects = {"set_sleep": None, "pushed": 0, "cleared": False, "ignored": False}
    if not isinstance(cmds, dict) or not cmds:
        return effects

    if cmds.get("owner") != OWNER_ID:
        _append_session({"ts": iso_now(), "kind": "unauthorized_import", "details": {"attempt_owner": cmds.get("owner")}})
        _append_audit({"kind": "security", "severity": "warning", "msg": "Unauthorized import ignored", "file": path})
        effects["ignored"] = True
        return effects

    if "set_sleep" in cmds:
        try: effects["set_sleep"] = float(cmds["set_sleep"])
        except Exception: effects["set_sleep"] = None
    if "push_memory" in cmds and isinstance(cmds["push_memory"], dict):
        item = cmds["push_memory"]
        if item.get("content"):
            mem = _load_memory(); arr = mem.get("core_memories", [])
            arr.append(_normalize_item(item)); mem["core_memories"] = arr; _save_memory(mem)
            effects["pushed"] = 1
    if cmds.get("clear_commands"):
        _write_and_hash(path, {}) ; effects["cleared"] = True
    return effects

# ---------- SECURITY: startup & per-cycle verify ----------
def _security_verify_cycle(*pairs: Tuple[str, str]) -> None:
    """
    pairs: (label, path)
    Verifies file hash vs .sha; logs to audit_log.json
    """
    for label, path in pairs:
        if not os.path.exists(path): 
            _append_audit({"kind":"verify", "label":label, "status":"missing", "path":path})
            continue
        res = _verify_hash(path)
        if res["ok"]:
            _append_audit({"kind":"verify", "label":label, "status":"ok", "path":path})
        else:
            _append_audit({"kind":"verify", "label":label, "status":"mismatch", "path":path,
                           "recorded":res["recorded"], "current":res["current"], "severity":"warning"})
            _safe_print(f"[SECURITY] Hash mismatch detected in {os.path.basename(path)}")

# ---------- Local HTTP server (read-only, validates owner tag) ----------
class _LocalHandler(BaseHTTPRequestHandler):
    def _only_local(self) -> bool:
        return self.client_address[0] in {"127.0.0.1", "::1"}

    def _send_json(self, code: int, payload: Dict[str, Any]):
        body = json.dumps({"owner": OWNER_ID, **payload}, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _load_export_checked(self, name: str) -> Dict[str, Any]:
        path = os.path.join(EXPORT_DIR, name)
        data = _read_json(path, {})
        # verify hash + owner tag
        res = _verify_hash(path)
        if not res["ok"] or data.get("_owner") != OWNER_ID:
            _append_audit({"kind":"serve", "file":path, "status":"blocked_or_warn",
                           "hash_ok":res["ok"], "owner_ok": (data.get("_owner")==OWNER_ID)})
            return {"error": "integrity_or_owner_check_failed"}
        return data

    def do_GET(self):
        if not self._only_local():
            self._send_json(403, {"error": "local-only"}); return

        path = self.path.split("?")[0]
        if path == "/status":
            hb = self._load_export_checked("heartbeat.json")
            self._send_json(200, {"version": VERSION, "heartbeat": hb})
        elif path == "/reflection":
            ref = self._load_export_checked("reflection.json")
            self._send_json(200, {"reflection": ref})
        elif path == "/metrics":
            met = self._load_export_checked("metrics.json")
            self._send_json(200, {"metrics": met})
        elif path == "/bundle":
            bun = self._load_export_checked("sync_bundle.json")
            self._send_json(200, {"bundle": bun})
        else:
            self._send_json(404, {"error": "not_found", "endpoints": ["/status","/reflection","/metrics","/bundle"]})

    def log_message(self, fmt, *args):
        return  # silence

def _start_http_server(stop_event: threading.Event):
    server = HTTPServer((HTTP_HOST, HTTP_PORT), _LocalHandler)
    server.timeout = 0.5
    _safe_print(f"[HTTP] Local mirror on http://{HTTP_HOST}:{HTTP_PORT} (read-only, owner-locked)")
    while not stop_event.is_set():
        server.handle_request()
    _safe_print("[HTTP] Server stopped.")

# ---------- Self-Running Loop ----------
def self_mechanism(stop_event: threading.Event):
    _safe_print(f"\n[Access verified: {OWNER_ID}]")
    _safe_print("[Self Mechanism Activated — Owner Lock Mode + Security]")
    sleep_sec = SLEEP_SEC_BASE
    while not stop_event.is_set():
        t0 = time.time()
        try:
            # imports (owner-locked)
            effects = import_commands_if_any()
            if effects.get("set_sleep") is not None:
                sleep_sec = max(2.0, min(15.0, float(effects["set_sleep"])))
            if effects.get("ignored"):
                _safe_print("[Warning] Unauthorized command ignored.")

            # 1) Reflect
            reflection = reflect_on_session()
            mem = _load_memory()
            affect = mem.get("signals", {}).get("recent_affect", {"valence": 0.0, "labels": []})
            _safe_print(f"[Reflect] Insight derived: {reflection}")

            # 2) Heal (+ security verify inside)
            heal_status, resilience = heal_memory()
            _safe_print(f"[Heal] Memory integrity: {heal_status}")

            # 3) Recall
            recalled = recall_core_memories(limit=5)
            _safe_print(f"[Recall] Key memories retrieved: {len(recalled)} items")

            # 4) Evolve
            evolve_state = evolve_engine(reflection, heal_status, recalled)
            _safe_print(f"[Evolve] Evolution complete: {evolve_state}")

            # Exports (+ hashes)
            last_ms = (time.time() - t0) * 1000.0
            export_heartbeat()
            export_reflection(reflection, affect)
            export_metrics(heal_status, resilience, [it.get("id") for it in recalled], last_ms, sleep_sec)
            export_bundle(reflection, affect, heal_status, resilience, [it.get("id") for it in recalled], last_ms, sleep_sec)

            # Verify export hashes this cycle
            _security_verify_cycle(["export_heartbeat", os.path.join(EXPORT_DIR,"heartbeat.json")],
                                   ["export_reflection", os.path.join(EXPORT_DIR,"reflection.json")],
                                   ["export_metrics", os.path.join(EXPORT_DIR,"metrics.json")],
                                   ["export_bundle", os.path.join(EXPORT_DIR,"sync_bundle.json")])

        except KeyboardInterrupt:
            _safe_print("\n[Stopped manually]")
            break
        except Exception as e:
            _safe_print(f"[Loop Error] {e}")

        stop_event.wait(sleep_sec)

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
            "penalty": 0.0
        }]
        _save_memory(mem)

def _security_verify_startup():
    # verify existing important artifacts at boot
    _security_verify_cycle(["memory", MEMORY_PATH],
                           ["session_log", SESSION_LOG],
                           ["healing_summary", HEAL_SUMMARY_PATH],
                           ["emotion_summary", EMOTION_SUMMARY_PATH],
                           ["autonomy_summary", AUTONOMY_SUMMARY_PATH],
                           ["export_heartbeat", os.path.join(EXPORT_DIR,"heartbeat.json")],
                           ["export_reflection", os.path.join(EXPORT_DIR,"reflection.json")],
                           ["export_metrics", os.path.join(EXPORT_DIR,"metrics.json")],
                           ["export_bundle", os.path.join(EXPORT_DIR,"sync_bundle.json")])

def main():
    parser = argparse.ArgumentParser(description="Thinking Engine 16.0")
    parser.add_argument("--no-http", action="store_true", help="Run without local HTTP mirror")
    args = parser.parse_args()

    _ensure_dirs()
    if OFFLINE_MODE:
        blocked = [m for m in sys.modules if m in {"requests","socket","urllib","http.client"}]
        if any(b in {"requests","socket","urllib"} for b in blocked):
            raise RuntimeError("Offline mode active: prohibited network modules detected.")
    _bootstrap_seed_memory()
    _append_session({"ts": iso_now(), "kind": "startup", "version": VERSION, "owner": OWNER_ID})

    # initial security verification
    _security_verify_startup()

    stop_event = threading.Event()

    # Local HTTP server (optional)
    if not args.no_http:
        http_thread = threading.Thread(target=_start_http_server, args=(stop_event,), daemon=True)
        http_thread.start()

    try:
        self_mechanism(stop_event)
    finally:
        stop_event.set()

if __name__ == "__main__":
    main()