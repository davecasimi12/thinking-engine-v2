from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, Callable, Optional

router = APIRouter(prefix="/sam", tags=["Sam"])


@router.get("/ping")
def ping():
    return {"status": "ok", "role": "Sam Analytics", "mode": "router-online"}


class SamAnalyzeRequest(BaseModel):
    campaign: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class SamAnalyzeResponse(BaseModel):
    ok: bool
    insights: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _load_legacy():
    try:
        import router.sam_analytics_v1_legacy as legacy  # type: ignore
        return legacy
    except Exception:
        return None


def _first_callable(mod: Any, names: list[str]) -> Optional[Callable]:
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            return fn
    return None


@router.post("/analyze_v1", response_model=SamAnalyzeResponse)
def analyze_v1(req: SamAnalyzeRequest):
    legacy = _load_legacy()
    if legacy:
        fn = _first_callable(legacy, ["analyze_v1", "analyze", "score"])
        if fn:
            out = fn(req.campaign, req.metrics)
            if isinstance(out, dict):
                return SamAnalyzeResponse(
                    ok=bool(out.get("ok", True)),
                    insights=dict(out.get("insights", out)),
                    metadata=dict(out.get("metadata", {})),
                )

    return SamAnalyzeResponse(
        ok=True,
        insights={
            "algo_health_hint": "stable",
            "signal": "needs more proof content",
            "next_move": "post 3 times this week staying in the same niche + format",
        },
        metadata={"fallback": True},
    )