"""
api_campaign_brain_v1.py

Nivora Thinking Engine - Campaign Brain API (v1.0)

Exposes the full campaign brain orchestration over HTTP so Bubble (or
any client) can send a base campaign and receive:

- Ranked scenarios
- Media bundles (with language analysis + file paths)
- Optional dead-campaign check
- Optional algo health snapshot

Endpoint:

    POST /campaign-brain
"""

from typing import Optional, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel

from engine_campaign_brain_v1 import run_campaign_brain


# ---------- Request models ----------

class BaseCampaign(BaseModel):
    brand_name: Optional[str] = None
    offer: Optional[str] = None
    target_audience: Optional[str] = None
    goal: Optional[str] = None
    platform: Optional[str] = None
    tone: Optional[str] = None


class PerformanceMetrics(BaseModel):
    impressions: Optional[int] = 0
    clicks: Optional[int] = 0
    conversions: Optional[int] = 0
    spend: Optional[float] = 0.0


class AlgoMetrics(BaseModel):
    avg_engagement_rate: Optional[float] = 0.0
    post_frequency_per_week: Optional[float] = 0.0
    recent_violations_count: Optional[int] = 0
    shadowban_suspected: Optional[bool] = False


class CampaignBrainRequest(BaseModel):
    base_campaign: BaseCampaign
    performance_metrics: Optional[PerformanceMetrics] = None
    algo_metrics: Optional[AlgoMetrics] = None
    max_scenarios: Optional[int] = 10
    top_n: Optional[int] = 3


# ---------- FastAPI app ----------

app = FastAPI(
    title="Nivora Campaign Brain API",
    description="Full campaign brain (scenarios + media + safety) for Nivora.",
    version="1.0.0",
)


@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "message": "Nivora Campaign Brain API is running"}


@app.post("/campaign-brain")
def campaign_brain_endpoint(payload: CampaignBrainRequest) -> Dict[str, Any]:
    """
    Run the campaign brain orchestration.
    """
    base_campaign_dict = {
        k: v for k, v in payload.base_campaign.dict().items() if v is not None
    }

    perf = payload.performance_metrics.dict() if payload.performance_metrics else None
    algo = payload.algo_metrics.dict() if payload.algo_metrics else None

    result = run_campaign_brain(
        base_campaign=base_campaign_dict,
        performance_metrics=perf,
        algo_metrics=algo,
        max_scenarios=payload.max_scenarios or 10,
        top_n=payload.top_n or 3,
    )
    return result