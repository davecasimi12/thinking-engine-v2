# ------------------------------------------------------------
# Thinking_Engine_20.0.py
# Phase 20 — Conversational Core (Dynamic Personality, Text Only)
# - Preserves: owner-lock, feeds/exports hashing, HTTP mirror,
#   unified console input (type while loop runs), family feeds.
# - Adds: conversation router, dynamic tone, conversation_memory.json
# ------------------------------------------------------------

import os, json, time, uuid, argparse, sys, re, threading, hashlib, queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

VERSION = "20.0"
SCHEMA_VERSION = 24
OWNER_ID = "YZ"

# Networking / loop
OFFLINE_MODE = False          # keep True for strict offline (or run with --no-http)
HTTP_HOST = "127.0.0.1"
HTTP_PORT = 5050
SLEEP_SEC_BASE = 5.0
GREETING_INTERVAL_CYCLES = 6

# ---------- Paths ----------
DATA_DIR = "data"
REPORT_DIR = os.path.join(DATA_DIR, "reports")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
IMPORT_DIR = os.path.join(DATA_DIR, "imports")
FEEDS_DIR  = os.path.join(DATA_DIR, "feeds")

MEMORY_PATH = os.path.join(DATA_DIR, "long_term_memory.json")
SESSION_LOG = os.path.join(DATA_DIR, "session_log.json")
HEAL_SUMMARY_PATH = os.path.join(REPORT_DIR, "healing_summary.json")
EMOTION_SUMMARY_PATH = os.path.join(REPORT_DIR, "emotion_summary.json")
AUTONOMY_SUMMARY_PATH = os.path.join(REPORT_DIR, "autonomy_summary.json")
AUDIT_LOG_PATH = os.path.join(REPORT_DIR, "audit_log.json")

CONVO_MEM_PATH = os.path.join(DATA_DIR, "conversation_memory.json")  # NEW

# ---------- Utils ----------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(IMPORT_DIR, exist_ok=True)
    os.makedirs(FEEDS_DIR,  exist_ok=True)

def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _read_json(path: str, default: Any):
    try:
        if not os.path.exists(path): return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_json_raw(path: str, payload: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _hash_file(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f: return _sha256_bytes(f.read())
    except Exception: return None

def _sha_path(path: str) -> str: return f"{path}.sha"

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

def _append_audit(event: Dict[str, Any]) -> None:
    audit = _read_json(AUDIT_LOG_PATH, {"schema": 1, "history": []})
    event = {"ts": iso_now(), "owner": OWNER_ID, **event}
    audit["history"].append(event)
    _write_and_hash(AUDIT_LOG_PATH, audit)

def _append_session(event: Dict[str, Any]) -> None:
    event["owner"] = OWNER_ID
    log = _read_json(SESSION_LOG, [])
    log.append(event)
    _write_and_hash(SESSION_LOG, log)

def _safe_print(msg: str) -> None:
    try: print(msg, flush=True)
    except Exception: pass

def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

# ---------- Core Data ----------
def _load_memory() -> Dict[str, Any]:
    mem = _read_json(MEMORY_PATH, {})
    if not isinstance(mem, dict): mem = {}
    mem.setdefault("_meta", {"schema_version": SCHEMA_VERSION, "version": VERSION, "updated": iso_now()})
    mem.setdefault("core_memories", [])
    mem.setdefault("signals", {})
    return mem

def _save_memory(mem: Dict[str, Any]) -> None:
    mem["_meta"]["schema_version"] = SCHEMA_VERSION
    mem["_meta"]["version"] = VERSION
    mem["_meta"]["updated"] = iso_now()
    _write_and_hash(MEMORY_PATH, mem)

# ---------- Affect (lite) ----------
POSITIVE = {"win","success","stable","growth","clear","good","great","love","proud","ready","focus"}
NEGATIVE = {"error","fail","bug","lost","mad","angry","sad","risk","bad","conflict","block","hiccup"}
def analyze_emotion(text: str) -> Tuple[float, List[str]]:
    if not isinstance(text, str) or not text.strip(): return (0.0, [])
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
    if not isinstance(it, dict): return base
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

    # signature dedupe + health
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

    summary = _read_json(HEAL_SUMMARY_PATH, {"schema": 1, "history": []})
    summary["history"].append({
        "ts": iso_now(), "version": VERSION, "pre": pre,
        "repairs": {"normalized_or_fixed": repaired, "dedup_sig": dedup_sig, "dedup_ids": dedup_ids, "anomalous": anomalous},
        "post": {"total": total, "ok": ok_count, "resilience": resilience},
        "status": "OK" if anomalous == 0 and pre == {"missing_fields":0,"bad_timestamp":0,"duplicate_ids":0,"non_dict":0} else "WARN"
    })
    _write_and_hash(HEAL_SUMMARY_PATH, summary)

    status = f"ok | items={total} | dedup_sig={dedup_sig} | dedup_ids={dedup_ids} | repaired={repaired} | resilience={resilience}"
    _append_session({"ts": iso_now(), "kind": "heal2", "status": status})
    _security_verify_cycle(["memory", MEMORY_PATH],
                           ["healing_summary", HEAL_SUMMARY_PATH],
                           ["session_log",   SESSION_LOG])
    return status, resilience

# ---------- Recall / Evolve ----------
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

# ---------- Exports & Feeds ----------
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

def _feed_write(name: str, payload: Dict[str, Any]) -> None:
    payload = {"_ts": iso_now(), "_version": VERSION, "_owner": OWNER_ID, **payload}
    _write_and_hash(os.path.join(FEEDS_DIR, name), payload)

def sync_family_feeds() -> None:
    bundle = _read_json(os.path.join(EXPORT_DIR, "sync_bundle.json"), {})
    metrics = _read_json(os.path.join(EXPORT_DIR, "metrics.json"), {})
    emo    = _read_json(EMOTION_SUMMARY_PATH, {"history": []})
    heal   = _read_json(HEAL_SUMMARY_PATH, {"history": []})
    mem    = _load_memory()

    reflection = bundle.get("reflection", {})
    loop       = bundle.get("loop", {})

    nicole = {
        "owner": OWNER_ID,
        "insight": reflection.get("insight"),
        "affect": reflection.get("affect"),
        "emotion_avg": emo["history"][-1] if emo.get("history") else {},
    }
    _feed_write("nicole_feed.json", nicole)

    sam = {
        "owner": OWNER_ID,
        "resilience": loop.get("resilience", metrics.get("resilience")),
        "last_cycle_ms": loop.get("last_cycle_ms", metrics.get("last_cycle_ms")),
        "sleep_sec": loop.get("sleep_sec", metrics.get("sleep_sec")),
        "recalled": loop.get("recalled", metrics.get("recalled")),
    }
    _feed_write("sam_feed.json", sam)

    items = mem.get("core_memories", []) if isinstance(mem.get("core_memories", []), list) else []
    ranked = sorted(items, key=lambda it: float(it.get("score",0.0)) - float(it.get("penalty",0.0)), reverse=True)[:5]
    compact = [{"id": it.get("id"), "content": it.get("content"), "tags": it.get("tags"), "score": it.get("score")} for it in ranked]
    jon = {"owner": OWNER_ID, "top_memories": compact, "healing_pulse": heal["history"][-1] if heal.get("history") else {}}
    _feed_write("jon_feed.json", jon)

    _security_verify_cycle(["feed_nicole", os.path.join(FEEDS_DIR,"nicole_feed.json")],
                           ["feed_sam",    os.path.join(FEEDS_DIR,"sam_feed.json")],
                           ["feed_jon",    os.path.join(FEEDS_DIR,"jon_feed.json")])

def write_greeting(status: str, message: str = None) -> None:
    if message is None:
        message = "Hey YZ 👋 I’m online — ready when you are."
    greeting = {"owner": OWNER_ID, "status": status, "message": message}
    _feed_write("greeting_feed.json", greeting)

# ---------- Local HTTP server ----------
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

    def _load_checked(self, base_dir: str, name: str) -> Dict[str, Any]:
        folder = EXPORT_DIR if base_dir == "exports" else FEEDS_DIR
        path = os.path.join(folder, name)
        data = _read_json(path, {})
        res = _verify_hash(path)
        ok_owner = (data.get("_owner") == OWNER_ID)
        if not res["ok"] or not ok_owner:
            _append_audit({"kind":"serve", "file":path, "status":"blocked_or_warn",
                           "hash_ok":res["ok"], "owner_ok":ok_owner})
            return {"error": "integrity_or_owner_check_failed"}
        return data

    def do_GET(self):
        if not self._only_local():
            self._send_json(403, {"error": "local-only"}); return

        p = self.path.split("?")[0]
        if p == "/status":     self._send_json(200, {"version": VERSION, "heartbeat": self._load_checked("exports","heartbeat.json")}); return
        if p == "/reflection": self._send_json(200, {"reflection": self._load_checked("exports","reflection.json")}); return
        if p == "/metrics":    self._send_json(200, {"metrics":    self._load_checked("exports","metrics.json")}); return
        if p == "/bundle":     self._send_json(200, {"bundle":     self._load_checked("exports","sync_bundle.json")}); return
        if p == "/family/nicole": self._send_json(200, {"nicole":   self._load_checked("feeds","nicole_feed.json")}); return
        if p == "/family/sam":    self._send_json(200, {"sam":      self._load_checked("feeds","sam_feed.json")}); return
        if p == "/family/jon":    self._send_json(200, {"jon":      self._load_checked("feeds","jon_feed.json")}); return
        if p == "/greeting":      self._send_json(200, {"greeting": self._load_checked("feeds","greeting_feed.json")}); return

        self._send_json(404, {"error":"not_found","endpoints":["/status","/reflection","/metrics","/bundle","/family/nicole","/family/sam","/family/jon","/greeting"]})

    def log_message(self, fmt, *args): return

def _start_http_server(stop_event: threading.Event):
    server = HTTPServer((HTTP_HOST, HTTP_PORT), _LocalHandler)
    server.timeout = 0.5
    _safe_print(f"[HTTP] Local mirror on http://{HTTP_HOST}:{HTTP_PORT} (read-only, owner-locked)")
    while not stop_event.is_set():
        server.handle_request()
    _safe_print("[HTTP] Server stopped.")

# ---------- Conversation Memory (NEW) ----------
def _load_convo() -> Dict[str, Any]:
    data = _read_json(CONVO_MEM_PATH, {"schema": 1, "history": []})
    if not isinstance(data, dict): data = {"schema": 1, "history": []}
    if "history" not in data or not isinstance(data["history"], list): data["history"] = []
    return data

def _save_convo(data: Dict[str, Any]) -> None:
    # keep last 10 exchanges max
    data["history"] = data.get("history", [])[-10:]
    _write_and_hash(CONVO_MEM_PATH, data)

def _push_convo(speaker: str, text: str) -> None:
    data = _load_convo()
    data["history"].append({"ts": iso_now(), "speaker": speaker, "text": text})
    _save_convo(data)

# ---------- Tone Selection (NEW) ----------
def tone_selector(user_text: str, affect_sig: Dict[str, Any]) -> str:
    """Return one of: 'balanced', 'casual', 'focused', 'mentor'."""
    t = (user_text or "").strip()
    t_low = t.lower()
    # quick intent cues
    if any(x in t_low for x in ["now", "do this", "run ", "heal", "recall", "status"]) or len(t.split()) <= 3:
        return "focused"
    if any(x in t_low for x in ["lol", "haha", "😂", "😅", "bro", "chill"]):
        return "casual"
    if any(x in t_low for x in ["why", "reflect", "lesson", "meaning", "purpose"]):
        return "mentor"
    # affect-based fallback
    v = float(affect_sig.get("valence", 0.0)) if isinstance(affect_sig, dict) else 0.0
    if v < -0.2: return "mentor"
    if v > 0.3:  return "casual"
    return "balanced"

# ---------- Natural Reply Generator (NEW) ----------
def generate_reply(user_text: str) -> str:
    """Compose a Nova-style answer using memory, signals, and convo history."""
    mem = _load_memory()
    signals = mem.get("signals", {})
    affect = signals.get("recent_affect", {"valence": 0.0, "labels": []})
    convo = _load_convo().get("history", [])
    last_reflection = _read_json(os.path.join(EXPORT_DIR, "reflection.json"), {}).get("insight", "steady state")
    heal_sum = _read_json(HEAL_SUMMARY_PATH, {"history": []})
    resilience = _read_json(os.path.join(EXPORT_DIR, "metrics.json"), {}).get("resilience", None)

    mode = tone_selector(user_text, affect)

    # tiny templates
    if mode == "focused":
        base = "Understood. "
    elif mode == "casual":
        base = "Got you 😎 "
    elif mode == "mentor":
        base = "Here’s the signal I’m seeing: "
    else:
        base = "I’m here — "

    # context stitching
    bits = []
    bits.append(base)
    if "how" in user_text.lower():
        bits.append("I’m steady and clear right now")
        if resilience is not None: bits.append(f"(resilience {resilience}). ")
        else: bits.append(". ")

    elif "learn" in user_text.lower() or "what did we" in user_text.lower():
        bits.append(f"Latest reflection: {last_reflection}. ")

    elif "feeling" in user_text.lower() or "mood" in user_text.lower():
        v = affect.get("valence", 0.0)
        label = ", ".join(affect.get("labels", [])) or "balanced"
        bits.append(f"Emotion signal ~ {label} ({v:+.2f}). ")

    elif "advice" in user_text.lower() or "next" in user_text.lower():
        bits.append("Next smart step: keep the loop stable and ship one improvement. ")
        bits.append("Want me to slow cycles or run a targeted heal/recall? ")

    else:
        # default: acknowledge + small status
        if resilience is not None:
            bits.append(f"Loop is stable (resilience {resilience}). ")
        bits.append(f"Reflection says: {last_reflection}. ")

    # short memory echo
    if convo:
        last_user = next((m["text"] for m in reversed(convo) if m.get("speaker")=="YZ"), None)
        if last_user and last_user != user_text:
            bits.append("I remember your last note — still aligned. ")

    # tone closers
    if mode == "casual":
        bits.append("We’re cruising. 🔥")
    elif mode == "mentor":
        bits.append("Small wins compound. Stay consistent. 💭")
    elif mode == "focused":
        bits.append("Say a command or goal and I’ll execute. ⚙️")
    else:
        bits.append("What do you want to do next? 🙂")

    return "".join(bits)

# ---------- Console Input ----------
def _input_thread(stop_event: threading.Event, inbox: "queue.Queue[str]"):
    while not stop_event.is_set():
        try:
            line = input().strip()
        except EOFError:
            break
        if not line: continue
        inbox.put(line)

def _respond(text: str):
    _safe_print(text)

def _handle_command_or_chat(cmd: str, sleep_sec: float) -> Tuple[bool, float]:
    """Route system commands; otherwise switch to conversation mode."""
    lower = cmd.lower().strip()
    _append_session({"ts": iso_now(), "kind": "interaction", "text": cmd})

    # --- system commands (same as 18.2) ---
    if lower in {"hi","hello","hey"}:
        out = "Nova: Hey YZ 👋 I’m here and thinking."
        _respond(out); _push_convo("Nova", out); _push_convo("YZ", cmd); return (False, sleep_sec)

    if lower.startswith("sleep "):
        try:
            sec = float(lower.split(" ", 1)[1]); sec = max(2.0, min(15.0, sec))
            out = f"Nova: Cycle sleep set to {sec:.1f}s."
            _respond(out); _push_convo("Nova", out); _push_convo("YZ", cmd); return (False, sec)
        except Exception:
            out = "Nova: Give me a number like `sleep 8`."
            _respond(out); _push_convo("Nova", out); _push_convo("YZ", cmd); return (False, sleep_sec)

    if lower in {"status","/status"}:
        bun = _read_json(os.path.join(EXPORT_DIR, "sync_bundle.json"), {})
        loop = bun.get("loop", {})
        out = f"Nova: status → resilience={loop.get('resilience')} last_ms={loop.get('last_cycle_ms')} recalled={loop.get('recalled')}"
        _respond(out); _push_convo("Nova", out); _push_convo("YZ", cmd); return (False, sleep_sec)

    if lower in {"recall"}:
        items = recall_core_memories(limit=5)
        out = f"Nova: recalled {len(items)} items."
        _respond(out); _push_convo("Nova", out); _push_convo("YZ", cmd); return (False, sleep_sec)

    if lower in {"heal"}:
        stat, res = heal_memory()
        out = f"Nova: heal run → {stat}"
        _respond(out); _push_convo("Nova", out); _push_convo("YZ", cmd); return (False, sleep_sec)

    if lower in {"stop","exit","quit"}:
        out = "Nova: Stopping now. 👋"
        _respond(out); _push_convo("Nova", out); _push_convo("YZ", cmd); return (True, sleep_sec)

    # --- conversational mode (NEW) ---
    reply = generate_reply(cmd)
    _respond(f"Nova: {reply}")
    _push_convo("YZ", cmd)
    _push_convo("Nova", reply)
    return (False, sleep_sec)

# ---------- Self-Running Loop ----------
def self_mechanism(stop_event: threading.Event, inbox: "queue.Queue[str]"):
    _safe_print(f"[Access verified: {OWNER_ID}]")
    _safe_print("[Thinking Engine Online]")
    _safe_print("Hey YZ 👋 I’m online — ready when you are.")

    sleep_sec = SLEEP_SEC_BASE
    cycle = 0
    while not stop_event.is_set():
        t0 = time.time()
        try:
            # process queued console inputs
            while True:
                try:
                    cmd = inbox.get_nowait()
                except queue.Empty:
                    break
                should_stop, sleep_sec = _handle_command_or_chat(cmd, sleep_sec)
                if should_stop:
                    stop_event.set(); break

            if stop_event.is_set(): break

            effects = import_commands_if_any()
            if effects.get("set_sleep") is not None:
                sleep_sec = max(2.0, min(15.0, float(effects["set_sleep"])))
            if effects.get("ignored"):
                _safe_print("[Warning] Unauthorized command ignored.")

            reflection = reflect_on_session()
            mem = _load_memory()
            affect = mem.get("signals", {}).get("recent_affect", {"valence":0.0, "labels":[]})
            _safe_print(f"[Reflect] Insight derived: {reflection}")

            heal_status, resilience = heal_memory()
            _safe_print(f"[Heal] Memory integrity: {heal_status}")

            recalled = recall_core_memories(limit=5)
            _safe_print(f"[Recall] Key memories retrieved: {len(recalled)} items")

            evolve_state = evolve_engine(reflection, heal_status, recalled)
            _safe_print(f"[Evolve] Evolution complete: {evolve_state}")

            last_ms = (time.time() - t0) * 1000.0
            export_heartbeat()
            export_reflection(reflection, affect)
            export_metrics(heal_status, resilience, [it.get("id") for it in recalled], last_ms, sleep_sec)
            export_bundle(reflection, affect, heal_status, resilience, [it.get("id") for it in recalled], last_ms, sleep_sec)

            sync_family_feeds()
            _security_verify_cycle(["export_heartbeat", os.path.join(EXPORT_DIR,"heartbeat.json")],
                                   ["export_reflection", os.path.join(EXPORT_DIR,"reflection.json")],
                                   ["export_metrics", os.path.join(EXPORT_DIR,"metrics.json")],
                                   ["export_bundle", os.path.join(EXPORT_DIR,"sync_bundle.json")])

            cycle += 1
            if cycle % GREETING_INTERVAL_CYCLES == 0:
                msg = "Still here, YZ — working smoothly and watching your signals. 👍"
                write_greeting(status="ready", message=msg)
                _safe_print(msg)

        except KeyboardInterrupt:
            _safe_print("\n[Stopped manually]")
            break
        except Exception as e:
            _safe_print(f"[Loop Error] {e}")

        for _ in range(int(sleep_sec * 10)):
            if stop_event.is_set(): break
            time.sleep(0.1)

# ---------- Imports (Owner-locked) ----------
def import_commands_if_any() -> Dict[str, Any]:
    path = os.path.join(IMPORT_DIR, "commands.json")
    cmds = _read_json(path, {})
    effects = {"set_sleep": None, "pushed": 0, "cleared": False, "ignored": False}
    if not isinstance(cmds, dict) or not cmds: return effects

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
        _write_and_hash(path, {}); effects["cleared"] = True
    return effects

# ---------- SECURITY ----------
def _security_verify_cycle(*pairs: Tuple[str, str]) -> None:
    for label, path in pairs:
        if not os.path.exists(path):
            _append_audit({"kind":"verify", "label":label, "status":"missing", "path":path}); continue
        res = _verify_hash(path)
        if res["ok"]:
            _append_audit({"kind":"verify", "label":label, "status":"ok", "path":path})
        else:
            _append_audit({"kind":"verify", "label":label, "status":"mismatch", "path":path,
                           "recorded":res["recorded"], "current":res["current"], "severity":"warning"})
            _safe_print(f"[SECURITY] Hash mismatch detected in {os.path.basename(path)}")

def _security_verify_startup() -> bool:
    labels = [
        ("memory", MEMORY_PATH),
        ("session_log", SESSION_LOG),
        ("healing_summary", HEAL_SUMMARY_PATH),
        ("emotion_summary", EMOTION_SUMMARY_PATH),
        ("autonomy_summary", AUTONOMY_SUMMARY_PATH),
        ("export_heartbeat", os.path.join(EXPORT_DIR,"heartbeat.json")),
        ("export_reflection", os.path.join(EXPORT_DIR,"reflection.json")),
        ("export_metrics", os.path.join(EXPORT_DIR,"metrics.json")),
        ("export_bundle", os.path.join(EXPORT_DIR,"sync_bundle.json")),
        ("feed_nicole", os.path.join(FEEDS_DIR,"nicole_feed.json")),
        ("feed_sam", os.path.join(FEEDS_DIR,"sam_feed.json")),
        ("feed_jon", os.path.join(FEEDS_DIR,"jon_feed.json")),
        ("greeting_feed", os.path.join(FEEDS_DIR,"greeting_feed.json")),
    ]
    all_ok = True
    for label, path in labels:
        if not os.path.exists(path):
            _append_audit({"kind":"verify", "label":label, "status":"missing", "path":path}); continue
        res = _verify_hash(path)
        ok = bool(res["ok"]); all_ok = all_ok and ok
        _append_audit({"kind":"verify", "label":label, "status":"ok" if ok else "mismatch", "path":path})
    return all_ok

# ---------- Bootstrap & Main ----------
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

def main():
    parser = argparse.ArgumentParser(description="Thinking Engine 20.0 — Conversational Core")
    parser.add_argument("--no-http", action="store_true", help="Run without local HTTP mirror")
    args = parser.parse_args()

    _ensure_dirs()
    if OFFLINE_MODE:
        blocked = [m for m in sys.modules if m in {"requests","socket","urllib","http.client"}]
        if any(b in {"requests","socket","urllib"} for b in blocked):
            raise RuntimeError("Offline mode active: prohibited network modules detected.")

    _bootstrap_seed_memory()
    _append_session({"ts": iso_now(), "kind": "startup", "version": VERSION, "owner": OWNER_ID})

    healthy = _security_verify_startup()
    write_greeting(status="ready" if healthy else "safe_mode", message="Hey YZ 👋 I’m online — ready when you are.")

    stop_event = threading.Event()
    inbox: "queue.Queue[str]" = queue.Queue()

    if not args.no_http:
        http_thread = threading.Thread(target=_start_http_server, args=(stop_event,), daemon=True)
        http_thread.start()

    # init convo file
    if not os.path.exists(CONVO_MEM_PATH):
        _write_and_hash(CONVO_MEM_PATH, {"schema": 1, "history": []})

    # start input thread
    it_thread = threading.Thread(target=_input_thread, args=(stop_event, inbox), daemon=True)
    it_thread.start()

    try:
        self_mechanism(stop_event, inbox)
    finally:
        stop_event.set()

if __name__ == "__main__":
    main()