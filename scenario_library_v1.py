from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def jdump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def jload(s: Optional[str]) -> Any:
    if not s:
        return None
    return json.loads(s)


@dataclass
class ScenarioPattern:
    """
    A reusable scenario pattern (template) Nicole can pick from.
    Stored in SQLite.
    """
    pattern_id: str
    name: str
    niche: str
    platform: str
    goal: str  # Bubble field is "Goal" (text) — we mirror that label

    angle: str = ""
    format: str = ""
    audience: str = ""
    offer_type: str = ""

    hook_templates: List[str] = None
    cta_templates: List[str] = None
    script_skeleton: Dict[str, Any] = None
    creative_notes: Dict[str, Any] = None
    constraints: Dict[str, Any] = None
    tags: List[str] = None

    created_at: str = ""
    updated_at: str = ""

    times_used: int = 0
    wins: int = 0
    losses: int = 0

    score_public: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class ScenarioLibrary:
    """
    v1: SQLite-backed pattern library
    - exact-match search on (niche, platform, goal) for speed & clarity
    - simple scoring that can evolve later
    """

    def __init__(self, db_path: str = "data/scenario_library.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS scenario_patterns (
                  pattern_id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  niche TEXT NOT NULL,
                  platform TEXT NOT NULL,
                  goal TEXT NOT NULL,
                  angle TEXT NOT NULL,
                  format TEXT NOT NULL,
                  audience TEXT NOT NULL,
                  offer_type TEXT NOT NULL,
                  hook_templates_json TEXT NOT NULL,
                  cta_templates_json TEXT NOT NULL,
                  script_skeleton_json TEXT NOT NULL,
                  creative_notes_json TEXT NOT NULL,
                  constraints_json TEXT NOT NULL,
                  tags_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  times_used INTEGER NOT NULL,
                  wins INTEGER NOT NULL,
                  losses INTEGER NOT NULL,
                  score_public REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_patterns_lookup
                ON scenario_patterns (niche, platform, goal, score_public, updated_at);
                """
            )

    # ---------- Scoring (v1) ----------

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    def _score(self, p: ScenarioPattern) -> float:
        """
        0..10 score
        v1 scoring:
        - evidence: win rate (light weight)
        - clarity: presence of hooks/cta/script
        - novelty: not overused
        """
        used = max(0, p.times_used)
        wins = max(0, p.wins)
        losses = max(0, p.losses)

        if used == 0:
            evidence = 0.45
        else:
            win_rate = wins / max(1, wins + losses)
            evidence = self._clamp(0.25 + 0.75 * win_rate, 0.0, 1.0)

        clarity = 0.0
        clarity += 0.35 if (p.hook_templates and len(p.hook_templates) > 0) else 0.0
        clarity += 0.35 if (p.cta_templates and len(p.cta_templates) > 0) else 0.0
        clarity += 0.30 if (p.script_skeleton and len(p.script_skeleton) > 0) else 0.0
        clarity = self._clamp(clarity, 0.0, 1.0)

        novelty = 1.0 - self._clamp((used / 30.0), 0.0, 0.65)

        total = 10.0 * (0.55 * evidence + 0.30 * clarity + 0.15 * novelty)
        return round(self._clamp(total, 0.0, 10.0), 2)

    # ---------- CRUD ----------

    def upsert_pattern(self, p: ScenarioPattern) -> ScenarioPattern:
        now = utc_now_iso()
        if not p.created_at:
            p.created_at = now
        p.updated_at = now

        # defaults
        p.hook_templates = p.hook_templates or []
        p.cta_templates = p.cta_templates or []
        p.script_skeleton = p.script_skeleton or {}
        p.creative_notes = p.creative_notes or {}
        p.constraints = p.constraints or {}
        p.tags = p.tags or []

        p.score_public = self._score(p)

        with self._connect() as con:
            con.execute(
                """
                INSERT INTO scenario_patterns (
                  pattern_id, name, niche, platform, goal,
                  angle, format, audience, offer_type,
                  hook_templates_json, cta_templates_json,
                  script_skeleton_json, creative_notes_json,
                  constraints_json, tags_json,
                  created_at, updated_at,
                  times_used, wins, losses,
                  score_public
                ) VALUES (
                  ?, ?, ?, ?, ?,
                  ?, ?, ?, ?,
                  ?, ?,
                  ?, ?,
                  ?, ?,
                  ?, ?,
                  ?, ?, ?,
                  ?
                )
                ON CONFLICT(pattern_id) DO UPDATE SET
                  name=excluded.name,
                  niche=excluded.niche,
                  platform=excluded.platform,
                  goal=excluded.goal,
                  angle=excluded.angle,
                  format=excluded.format,
                  audience=excluded.audience,
                  offer_type=excluded.offer_type,
                  hook_templates_json=excluded.hook_templates_json,
                  cta_templates_json=excluded.cta_templates_json,
                  script_skeleton_json=excluded.script_skeleton_json,
                  creative_notes_json=excluded.creative_notes_json,
                  constraints_json=excluded.constraints_json,
                  tags_json=excluded.tags_json,
                  updated_at=excluded.updated_at,
                  times_used=excluded.times_used,
                  wins=excluded.wins,
                  losses=excluded.losses,
                  score_public=excluded.score_public
                """,
                (
                    p.pattern_id, p.name, p.niche, p.platform, p.goal,
                    p.angle, p.format, p.audience, p.offer_type,
                    jdump(p.hook_templates), jdump(p.cta_templates),
                    jdump(p.script_skeleton), jdump(p.creative_notes),
                    jdump(p.constraints), jdump(p.tags),
                    p.created_at, p.updated_at,
                    int(p.times_used), int(p.wins), int(p.losses),
                    float(p.score_public),
                ),
            )
        return p

    def top_patterns(self, niche: str, platform: str, goal: str, limit: int = 5) -> List[ScenarioPattern]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM scenario_patterns
                WHERE niche = ? AND platform = ? AND goal = ?
                ORDER BY score_public DESC, updated_at DESC
                LIMIT ?
                """,
                (niche, platform, goal, int(limit)),
            ).fetchall()

        return [self._row_to_pattern(r) for r in rows]

    def record_outcome(self, pattern_id: str, won: bool) -> Optional[ScenarioPattern]:
        p = self.get(pattern_id)
        if not p:
            return None

        p.times_used += 1
        if won:
            p.wins += 1
        else:
            p.losses += 1

        return self.upsert_pattern(p)

    def get(self, pattern_id: str) -> Optional[ScenarioPattern]:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM scenario_patterns WHERE pattern_id = ?",
                (pattern_id,),
            ).fetchone()
        return self._row_to_pattern(row) if row else None

    def seed_if_empty(self) -> None:
        """
        Adds a couple starter patterns so your /top_scenarios endpoint returns results immediately.
        You can delete these later — they’re just to prove the pipe works.
        """
        with self._connect() as con:
            row = con.execute("SELECT COUNT(1) AS c FROM scenario_patterns").fetchone()
            if int(row["c"]) > 0:
                return

        starters = [
            ScenarioPattern(
                pattern_id="pat_barber_001",
                name="Before/After Proof Reel",
                niche="barbershop owners",
                platform="tiktok",
                goal="increase bookings",
                angle="before_after",
                format="short-form",
                audience="local men 18-35",
                offer_type="service",
                hook_templates=[
                    "If your barber never gets you right… watch this.",
                    "This is why your fade doesn’t hit.",
                    "Barbers hate when I show this transformation…",
                ],
                cta_templates=[
                    "Book this week — link in bio.",
                    "Comment 'BOOK' for the next slots.",
                ],
                script_skeleton={
                    "hook": "1 line curiosity",
                    "body": ["show before", "process clips", "one micro-tip"],
                    "proof": "after reveal",
                    "cta": "booking push",
                },
                creative_notes={"visuals": ["tight before shot", "mirror reveal", "caption-heavy"]},
                constraints={"no_autopost": True, "user_consent_required": True},
                tags=["proof", "transformation", "local"],
            ),
            ScenarioPattern(
                pattern_id="pat_barber_002",
                name="Myth Bust: Haircut Mistake",
                niche="barbershop owners",
                platform="tiktok",
                goal="get more local clients",
                angle="myth_bust",
                format="short-form",
                audience="men who want clean cuts",
                offer_type="service",
                hook_templates=[
                    "Stop asking for this cut if you don’t want to look uneven.",
                    "One thing ruining your lineup (and nobody tells you).",
                ],
                cta_templates=[
                    "Follow for more barber truth.",
                    "Book now — link in bio.",
                ],
                script_skeleton={
                    "hook": "myth statement",
                    "body": ["why it’s wrong", "what to ask for instead", "quick example"],
                    "cta": "follow/book",
                },
                creative_notes={"visuals": ["talking head", "overlay text", "quick b-roll"]},
                constraints={"no_autopost": True, "user_consent_required": True},
                tags=["education", "local"],
            ),
        ]

        for s in starters:
            self.upsert_pattern(s)

    # ---------- internal ----------

    def _row_to_pattern(self, r: sqlite3.Row) -> ScenarioPattern:
        return ScenarioPattern(
            pattern_id=r["pattern_id"],
            name=r["name"],
            niche=r["niche"],
            platform=r["platform"],
            goal=r["goal"],
            angle=r["angle"],
            format=r["format"],
            audience=r["audience"],
            offer_type=r["offer_type"],
            hook_templates=jload(r["hook_templates_json"]) or [],
            cta_templates=jload(r["cta_templates_json"]) or [],
            script_skeleton=jload(r["script_skeleton_json"]) or {},
            creative_notes=jload(r["creative_notes_json"]) or {},
            constraints=jload(r["constraints_json"]) or {},
            tags=jload(r["tags_json"]) or [],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            times_used=int(r["times_used"]),
            wins=int(r["wins"]),
            losses=int(r["losses"]),
            score_public=float(r["score_public"]),
        )