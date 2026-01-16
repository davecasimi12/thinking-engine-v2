from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/nicole", tags=["Nicole"])


class StepCardRequest(BaseModel):
    step_id: str = Field(..., description="step_1_goal, step_2_hooks, step_3_visual")
    campaign_id: Optional[str] = None
    platform: Optional[str] = None


class StepCardResponse(BaseModel):
    title: str
    message: str
    next_action: str


@router.post("/step_card_v1", response_model=StepCardResponse)
def step_card_v1(payload: StepCardRequest):
    sid = (payload.step_id or "").lower().strip()

    if "goal" in sid or sid in {"step_1", "step1"}:
        return StepCardResponse(
            title="Step 1 — Confirm the goal",
            message="Pick ONE outcome. No mixing goals. Keeps strategy and analytics clean.",
            next_action="Select the goal → Continue to hooks.",
        )

    if "hook" in sid or sid in {"step_2", "step2"}:
        return StepCardResponse(
            title="Step 2 — Choose a hook",
            message="Pick the hook that hits pain + promise. Everything builds from this choice.",
            next_action="Pick 1 hook → Continue to visuals.",
        )

    if "visual" in sid or sid in {"step_3", "step3"}:
        return StepCardResponse(
            title="Step 3 — Visual direction",
            message="Make the hook obvious in 1 second. Minimal text. Strong contrast.",
            next_action="Pick a visual style → Generate in Studio.",
        )

    return StepCardResponse(
        title="Studio Step",
        message="Follow the guided flow step-by-step.",
        next_action="Continue.",
    )