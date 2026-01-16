from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, Callable, Optional

router = APIRouter(prefix="/jon", tags=["Jon"])


@router.get("/ping")
def ping():
    return {"status": "ok", "role": "Jon Executor", "mode": "router-online"}


class JonExecuteRequest(BaseModel):
    action: str = Field(default="schedule")  # schedule | post_now | draft
    payload: Dict[str, Any] = Field(default_factory=dict)


class JonExecuteResponse(BaseModel):
    ok: bool
    message: str
    execution: Dict[str, Any] = Field(default_factory=dict)


def _load_legacy():
    try:
        import router.jon_executor_v1_legacy as legacy  # type: ignore
        return legacy
    except Exception:
        return None


def _first_callable(mod: Any, names: list[str]) -> Optional[Callable]:
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            return fn
    return None


@router.post("/execute_v1", response_model=JonExecuteResponse)
def execute_v1(req: JonExecuteRequest):
    legacy = _load_legacy()
    if legacy:
        fn = _first_callable(legacy, ["execute_v1", "execute", "run"])
        if fn:
            out = fn(req.action, req.payload)
            if isinstance(out, dict):
                return JonExecuteResponse(
                    ok=bool(out.get("ok", True)),
                    message=str(out.get("message", "Executed.")),
                    execution=dict(out.get("execution", out)),
                )

    return JonExecuteResponse(
        ok=True,
        message=f"Jon queued action='{req.action}'. (Fallback — legacy function not found.)",
        execution={"action": req.action, "payload": req.payload, "fallback": True},
    )