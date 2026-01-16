from __future__ import annotations
from typing import Dict, Any
from bubble_campaign_contract_v1 import BubbleCampaign


def campaign_brief(c: BubbleCampaign) -> str:
    """
    Bubble Campaign -> clean brief for the AI family.
    IMPORTANT: This brief must include the same labels every time
    so parsers in Nicole/Jon/Maya/Sam stay stable.
    """
    platform = c.resolved_platform() or "unknown"

    lines = [
        "You are operating inside Nivora.",
        "Use only the campaign context below. Do not ask for DMs or private messages. No autonomous posting.",
        "",
        f"Campaign Title: {c.Title or ''}",
        f"Niche: {c.niche}",
        f"Platform: {platform}",
        f"Goal: {c.Goal}",
        f"Target audience: {c.target_audience or ''}",
        f"Tone: {c.tone or ''}",
        f"Style: {c.style or ''}",
        f"Offer: {c.main_offer or ''}",
        f"Studio theme: {c.studio_theme or ''}",
        f"Overview: {c.overview or ''}",
        f"Description: {c.Descriptions or ''}",
        "",
        "Execution prefs:",
        f"ab_test: {bool(c.ab_test)}",
        f"auto_optimize: {bool(c.auto_optimize)}",
        f"optimal_posting_time: {c.optimal_posting_time or ''}",
        "",
        "Consent flags:",
        f"allow_ai_to_post: {bool(c.allow_ai_to_post)}",
        f"approved_for_posting: {bool(c.approved_for_posting)}",
        f"content_approved: {bool(c.content_approved)}",
        "",
        "Recent metrics (if present):",
        f"Views: {c.Views if c.Views is not None else ''}",
        f"Clicks: {c.Clicks if c.Clicks is not None else ''}",
        f"Impressions: {c.Impressions if c.Impressions is not None else ''}",
        f"Engagement rate: {c.engagement_rate if c.engagement_rate is not None else ''}",
        f"Conversion: {c.conversion if c.conversion is not None else ''}",
        f"avg_post_performance: {c.avg_post_performance if c.avg_post_performance is not None else ''}",
        f"Algo health: {c.algo_health if c.algo_health is not None else ''}",
    ]
    return "\n".join(lines)


def bubble_truth_packet(c: BubbleCampaign) -> Dict[str, Any]:
    """
    Small truth packet Bubble can store/log.
    """
    return {
        "niche": c.niche,
        "platform": c.resolved_platform(),
        "goal": c.Goal,
        "tone": c.tone,
        "style": c.style,
        "target_audience": c.target_audience,
        "main_offer": c.main_offer,
        "auto_optimize": bool(c.auto_optimize),
        "ab_test": bool(c.ab_test),
        "optimal_posting_time": c.optimal_posting_time,
        "algo_health": c.algo_health,
    }