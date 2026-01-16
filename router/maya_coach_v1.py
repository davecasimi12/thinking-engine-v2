from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, Callable, Optional

router = APIRouter(prefix="/maya", tags=["Maya"])


@router.get("/ping")
def ping():
    return {"status": "ok", "role": "Maya Coach", "mode": "router-online"}


class MayaExplainRequest(BaseModel):
    topic: str = Field(default="why_this_works")
    payload: Dict[str, Any] = Field(default_factory=dict)


class MayaExplainResponse(BaseModel):
    ok: bool
    explanation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _load_legacy():
    try:
        import router.maya_coach_v1_legacy as legacy  # type: ignore
        return legacy
    except Exception:
        return None


def _first_callable(mod: Any, names: list[str]) -> Optional[Callable]:
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            return fn
    return None


@router.post("/explain_v1", response_model=MayaExplainResponse)
def explain_v1(req: MayaExplainRequest):
    legacy = _load_legacy()
    if legacy:
        fn = _first_callable(legacy, ["explain_v1", "explain", "coach"])
        if fn:
            out = fn(req.topic, req.payload)
            if isinstance(out, dict):
                return MayaExplainResponse(
                    ok=bool(out.get("ok", True)),
                    explanation=str(out.get("explanation", "")),
                    metadata=dict(out.get("metadata", {})),
                )

    return MayaExplainResponse(
        ok=True,
        explanation="This works because it stays on-niche, uses a clear hook → proof → CTA, and avoids spam patterns.",
        metadata={"fallback": True, "topic": req.topic},
    )