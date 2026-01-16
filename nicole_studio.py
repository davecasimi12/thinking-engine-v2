from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/nicole", tags=["Nicole"])


class StudioGenerateRequest(BaseModel):
    campaign_id: str = Field(..., description="Bubble campaign unique id")
    platform: str = Field(..., description="instagram, tiktok, youtube, facebook")
    goal_id: str = Field(..., description="canonical goal id from dropdown")

    niche: Optional[str] = None
    offer: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None


class StudioGenerateResponse(BaseModel):
    hooks: List[str]
    caption: str
    hashtags: List[str]
    recommended_visual_style: str
    next_step: str


@router.post("/studio_generate_v1", response_model=StudioGenerateResponse)
def studio_generate_v1(payload: StudioGenerateRequest):
    audience = payload.audience or "your ideal customer"
    niche = payload.niche or "your niche"
    offer = payload.offer or "your offer"

    hooks = [
        f"Stop scrolling — {audience}, this is for you.",
        f"If you’re in {niche}, do THIS before you waste another week.",
        "Most people get this wrong… here’s the fix in 20 seconds.",
    ]

    caption = (
        f"Quick win for {payload.platform}.\n\n"
        f"Goal: {payload.goal_id}\n"
        f"Offer: {offer}\n\n"
        "1) One clear promise\n"
        "2) One proof point\n"
        "3) One call-to-action\n\n"
        "Comment 'PLAN' and I’ll send the steps."
    )

    hashtags = ["#marketing", "#smallbusiness", "#contentstrategy", "#growth"]

    return StudioGenerateResponse(
        hooks=hooks,
        caption=caption,
        hashtags=hashtags,
        recommended_visual_style="Clean, high-contrast, minimal text overlay, brand colors",
        next_step="Pick a hook → then proceed to Visual step.",
    )