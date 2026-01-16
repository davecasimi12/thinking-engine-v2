# router/nicole_strategist_v1.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import re

from fastapi import APIRouter
from pydantic import BaseModel, Field


# =========================
# FastAPI Router (REQUIRED)
# =========================
router = APIRouter(prefix="/nicole", tags=["Nicole"])


@router.get("/ping")
def ping():
    return {
        "status": "ok",
        "role": "Nicole Strategist",
        "mode": "router-online",
    }


# =========================
# Brand profile ("Book of Truth")
# =========================
BOOK_OF_TRUTH: Dict[str, Any] = {
    "niche": "",
    "content_type": "",
    "brand_voice": "",
    "goals": [],
}


def set_brand_profile(
    niche: str,
    content_type: str,
    brand_voice: str,
    goals: List[str],
) -> Dict[str, Any]:
    BOOK_OF_TRUTH["niche"] = (niche or "").strip().lower()
    BOOK_OF_TRUTH["content_type"] = (content_type or "").strip().lower()
    BOOK_OF_TRUTH["brand_voice"] = (brand_voice or "").strip()
    BOOK_OF_TRUTH["goals"] = goals or []
    return BOOK_OF_TRUTH


# =========================
# Structured outputs for Bubble
# =========================
@dataclass
class NicoleStudioOutput:
    hooks: List[str]
    caption: str
    hashtags: str
    recommended_visual_style: str
    maya_summary: str


@dataclass
class NicoleResponse:
    message: str
    metadata: Dict[str, Any]


# =========================
# Helpers
# =========================
def _clean_lines(text: str) -> List[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _extract_field(block: str, label: str) -> Optional[str]:
    """
    Looks for: LABEL: value
    """
    pattern = re.compile(rf"^{re.escape(label)}\s*:\s*(.+)$", re.IGNORECASE)
    for ln in _clean_lines(block):
        m = pattern.match(ln)
        if m:
            return m.group(1).strip()
    return None


def _fallback_hooks(niche: str, goal: str, platform: str) -> List[str]:
    # Simple deterministic fallback so Bubble never gets empty hooks.
    niche = niche or "your niche"
    goal = goal or "your goal"
    platform = platform or "your platform"
    return [
        f"If you’re in {niche}, this is the fastest way to get {goal}.",
        f"Most {niche} creators mess this up on {platform} — don’t.",
        f"Do this once and watch your {goal} improve this week.",
    ]


def _fallback_caption(niche: str, goal: str, target_audience: str, offer: str) -> str:
    niche = niche or "your niche"
    goal = goal or "results"
    target_audience = target_audience or "your ideal customers"
    offer = offer or "your main offer"

    return (
        f"{goal.title()} doesn’t come from posting more — it comes from posting smarter.\n\n"
        f"Focus: {niche}\n"
        f"Audience: {target_audience}\n"
        f"Offer: {offer}\n\n"
        "1) Hook in the first 2 seconds\n"
        "2) Show proof or a clear step\n"
        "3) Simple CTA\n\n"
        'Comment "PLAN" and I’ll generate the next post.'
    )


def _fallback_hashtags(niche: str, platform: str) -> str:
    base = ["#smallbusiness", "#marketing", "#contentstrategy"]
    niche_tag = "#" + re.sub(r"[^a-z0-9]+", "", (niche or "niche").lower())
    plat_tag = "#" + re.sub(r"[^a-z0-9]+", "", (platform or "social").lower())
    tags = base + [niche_tag, plat_tag]
    return " ".join(tags[:8])


def _fallback_visual(style_hint: str, platform: str) -> str:
    if style_hint:
        return style_hint
    p = (platform or "").lower()
    if "tiktok" in p:
        return "caption-heavy talking head + b-roll"
    if "instagram" in p:
        return "clean aesthetic + bold headline overlay"
    return "clean high-contrast with clear headline"


# =========================
# Nicole core: bounded output
# =========================
def generate_studio_output(
    *,
    niche: str,
    platform: str,
    goal: str,
    target_audience: str = "",
    tone: str = "",
    style: str = "",
    offer: str = "",
) -> NicoleStudioOutput:
    """
    Deterministic v1 generator.
    Later we can swap internals to an LLM, but keep this same output shape.
    """
    niche = (niche or "").strip().lower()
    platform = (platform or "").strip().lower()
    goal = (goal or "").strip().lower()

    hooks = _fallback_hooks(niche=niche, goal=goal, platform=platform)
    hooks = [h.strip() for h in hooks][:3]

    caption = _fallback_caption(
        niche=niche,
        goal=goal or "results",
        target_audience=target_audience,
        offer=offer,
    )

    hashtags = _fallback_hashtags(niche=niche, platform=platform)
    visual = _fallback_visual(style_hint=style, platform=platform)

    maya_summary = (
        "This works because it matches the campaign goal, stays inside the niche, "
        "and uses a clear hook + proof + CTA structure (algorithm-friendly) and consistent."
    )

    return NicoleStudioOutput(
        hooks=hooks,
        caption=caption,
        hashtags=hashtags,
        recommended_visual_style=visual,
        maya_summary=maya_summary,
    )


def plan_campaign(prompt: str) -> NicoleResponse:
    """
    Backward compatible function your engine can call.
    If prompt includes a campaign brief, we attempt to read niche/platform/goal.
    """
    # Pull from Book of Truth as a baseline
    niche = (BOOK_OF_TRUTH.get("niche") or "").strip().lower()
    content_type = (BOOK_OF_TRUTH.get("content_type") or "").strip().lower()
    goals = BOOK_OF_TRUTH.get("goals") or []
    default_goal = (goals[0] if goals else "").strip().lower()

    # Try to extract from the prompt that engine_api builds
    p_niche = _extract_field(prompt, "Niche")
    p_platform = _extract_field(prompt, "Platform")
    p_goal = _extract_field(prompt, "Goal")
    p_aud = _extract_field(prompt, "Target audience")
    p_tone = _extract_field(prompt, "Tone")
    p_style = _extract_field(prompt, "Style")
    p_offer = _extract_field(prompt, "Offer")

    niche = (p_niche or niche or "unknown niche").strip().lower()
    platform = (p_platform or content_type or "unknown").strip().lower()
    goal = (p_goal or default_goal or "get results").strip().lower()

    studio = generate_studio_output(
        niche=niche,
        platform=platform,
        goal=goal,
        target_audience=p_aud or "",
        tone=p_tone or "",
        style=p_style or "",
        offer=p_offer or "",
    )

    msg = (
        "Plan ready.\n"
        f"- Niche: {niche}\n"
        f"- Platform: {platform}\n"
        f"- Goal: {goal}\n\n"
        "Top hooks:\n"
        f"1) {studio.hooks[0]}\n"
        f"2) {studio.hooks[1]}\n"
        f"3) {studio.hooks[2]}\n\n"
        "Next step: pick a hook + visual style, then I’ll finalize the post."
    )

    return NicoleResponse(
        message=msg,
        metadata={
            "studio": {
                "hooks": studio.hooks,
                "caption": studio.caption,
                "hashtags": studio.hashtags,
                "recommended_visual_style": studio.recommended_visual_style,
                "maya_summary": studio.maya_summary,
            }
        },
    )


# =========================
# API Models (for /docs)
# =========================
class NicoleStudioGenerateRequest(BaseModel):
    niche: str = Field(default="")
    platform: str = Field(default="")
    goal: str = Field(default="")
    target_audience: str = Field(default="")
    tone: str = Field(default="")
    style: str = Field(default="")
    offer: str = Field(default="")


class NicoleStudioGenerateResponse(BaseModel):
    hooks: List[str]
    caption: str
    hashtags: str
    recommended_visual_style: str
    maya_summary: str


class NicoleStepCardRequest(BaseModel):
    step_id: int = Field(..., ge=1, le=10)
    context: Dict[str, Any] = Field(default_factory=dict)


class NicoleStepCardResponse(BaseModel):
    message: str


# =========================
# Endpoints (what Bubble will call)
# =========================
@router.post("/studio_generate_v1", response_model=NicoleStudioGenerateResponse)
def studio_generate_v1(payload: NicoleStudioGenerateRequest):
    studio = generate_studio_output(
        niche=payload.niche,
        platform=payload.platform,
        goal=payload.goal,
        target_audience=payload.target_audience,
        tone=payload.tone,
        style=payload.style,
        offer=payload.offer,
    )
    return NicoleStudioGenerateResponse(
        hooks=studio.hooks,
        caption=studio.caption,
        hashtags=studio.hashtags,
        recommended_visual_style=studio.recommended_visual_style,
        maya_summary=studio.maya_summary,
    )


@router.post("/step_card_v1", response_model=NicoleStepCardResponse)
def step_card_v1(payload: NicoleStepCardRequest):
    # Simple bounded guidance cards (v1). We can upgrade later.
    step = payload.step_id
    if step == 1:
        msg = "Step 1: Confirm the goal + platform. Then choose 1 hook to lead with."
    elif step == 2:
        msg = "Step 2: Pick the best hook. Keep it short, direct, and specific."
    elif step == 3:
        msg = "Step 3: Choose a visual style that matches the hook (simple + clear)."
    else:
        msg = f"Step {step}: Keep it tight. One message, one action, one CTA."
    return NicoleStepCardResponse(message=msg)