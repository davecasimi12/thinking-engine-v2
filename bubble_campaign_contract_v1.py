from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class BubbleCampaign(BaseModel):
    """
    Canonical Bubble Campaign payload (aligned to your Bubble data type fields).
    Send this to every AI endpoint so everyone speaks the same language.
    """

    # Identity / Strategy
    campaign_id: Optional[str] = None
    Title: Optional[str] = None
    niche: str
    Goal: str

    platform: Optional[str] = None
    social_media: Optional[str] = None

    target_audience: Optional[str] = None
    tone: Optional[str] = None
    style: Optional[str] = None
    studio_theme: Optional[str] = None
    main_offer: Optional[str] = None
    overview: Optional[str] = None
    Descriptions: Optional[str] = None

    # Creative selections (Bubble fields you already have)
    selected_hook_title: Optional[str] = None
    selected_tag: Optional[str] = None
    selected_visual_style: Optional[str] = None
    selected_visual_slot: Optional[int] = None

    # Consent / workflow flags
    allow_ai_to_post: Optional[bool] = False
    approved_for_posting: Optional[bool] = False
    content_approved: Optional[bool] = False
    auto_optimize: Optional[bool] = False
    ab_test: Optional[bool] = False

    # Metrics (Sam)
    algo_health: Optional[float] = None
    Views: Optional[float] = None
    Clicks: Optional[float] = None
    Impressions: Optional[float] = None
    engagement_rate: Optional[float] = None
    conversion: Optional[float] = None
    avg_post_performance: Optional[float] = None
    Growth: Optional[float] = None
    new_customers: Optional[float] = None
    jobs_completed: Optional[float] = None

    # Optional scheduling field you have
    optimal_posting_time: Optional[str] = None

    def resolved_platform(self) -> str:
        return (self.platform or self.social_media or "").strip().lower()