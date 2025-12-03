# engine_api_v1.py
#
# Simple HTTP API to expose Nicole (and later Sam/Jon/Maya) to Nivora.
# Start it with:
#   uvicorn engine_api_v1:app --reload

from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from nicole_strategist_v1 import NicoleStrategist
from sam_analytics_v1 import SamAnalytics
from jon_executor_v1 import JonExecutor
from maya_coach_v1 import MayaCoach

# ---------------------------------------------------------
# Pydantic models (request / response shapes)
# ---------------------------------------------------------


class NicolePlanRequest(BaseModel):
    niche: str
    content_type: str
    brand_voice: str
    goals: List[str]
    prompt: str


class NicolePlanResponse(BaseModel):
    nicole_message: str
    niche: str
    content_type: str
    brand_voice: str
    goals: List[str]


class SimplePromptRequest(BaseModel):
    prompt: str


class SimpleMessageResponse(BaseModel):
    role: str
    message: str


# ---------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------

app = FastAPI(title="Thinking Engine API v1")


# Shared instances of the family
nicole = NicoleStrategist()
sam = SamAnalytics()
jon = JonExecutor()
maya = MayaCoach()


# ---------------------------------------------------------
# Nicole endpoint: set BookOfTruth + plan campaign
# ---------------------------------------------------------


@app.post("/nicole/plan_campaign", response_model=NicolePlanResponse)
def nicole_plan_campaign(payload: NicolePlanRequest) -> NicolePlanResponse:
    """
    Main endpoint for Nivora's Nicole page.

    Bubble (or any client) sends:
    - niche
    - content_type
    - brand_voice
    - goals
    - prompt  (what the user typed / what Nicole should plan)

    We:
    - update the BookOfTruth
    - call Nicole to plan a campaign
    - return her message + the truth fields
    """
    profile = nicole.set_brand_profile(
        niche=payload.niche,
        content_type=payload.content_type,
        brand_voice=payload.brand_voice,
        goals=payload.goals,
    )

    resp = nicole.plan_campaign(payload.prompt)

    return NicolePlanResponse(
        nicole_message=resp.message,
        niche=profile["niche"],
        content_type=profile["content_type"],
        brand_voice=profile["brand_voice"],
        goals=profile["goals"],
    )


# ---------------------------------------------------------
# Extra: simple endpoints for Sam / Jon / Maya
# (nice for later or testing from Bubble's API connector)
# ---------------------------------------------------------


@app.post("/sam/overview", response_model=SimpleMessageResponse)
def sam_overview(payload: SimplePromptRequest) -> SimpleMessageResponse:
    resp = sam.analytics_overview(payload.prompt)
    return SimpleMessageResponse(role="sam", message=resp.message)


@app.post("/jon/experiment", response_model=SimpleMessageResponse)
def jon_experiment(payload: SimplePromptRequest) -> SimpleMessageResponse:
    resp = jon.design_experiment(payload.prompt)
    return SimpleMessageResponse(role="jon", message=resp.message)


@app.post("/maya/coach", response_model=SimpleMessageResponse)
def maya_coach(payload: SimplePromptRequest) -> SimpleMessageResponse:
    resp = maya.coach_user(payload.prompt)
    return SimpleMessageResponse(role="maya", message=resp.message)


# ---------------------------------------------------------
# Small root route (optional)
# ---------------------------------------------------------


@app.get("/")
def root() -> dict:
    return {"status": "ok", "message": "Thinking Engine API v1 is running"}