"""
engine_media_bridge_v1.py

Nivora Thinking Engine - Media Bridge (v1.0)

Thin wrapper so the main Thinking Engine can talk to the Media Ad AI
without worrying about the internal details.

Main entrypoint for other modules:
    get_media_package_for_campaign(raw_campaign: dict) -> dict
"""

from typing import Dict, Any
from media_ad_ai_v1 import generate_media_package


# ---------- Normalization helpers ----------

def _normalize_platform(raw: str) -> str:
    """
    Map messy platform strings into a clean label that MediaAdAI understands.
    """
    if not raw:
        return "tiktok"

    p = raw.lower()
    if "tok" in p:
        return "tiktok"
    if "insta" in p or "ig" in p:
        return "instagram"
    if "fb" in p or "face" in p:
        return "facebook"
    if "yt" in p or "short" in p:
        return "youtube"
    return raw


def _normalize_goal(raw: str) -> str:
    """
    Simple cleanup so the goal text is clear.
    """
    if not raw:
        return "get more sales"

    g = raw.lower()
    if "lead" in g:
        return "get more leads"
    if "sale" in g or "sell" in g:
        return "get more sales"
    if "book" in g or "call" in g or "appointment" in g:
        return "book more calls"
    return raw


def _build_brief_from_campaign(raw_campaign: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a generic campaign dict from the Thinking Engine
    into the brief dict expected by generate_media_package().
    """

    brand_name = (
        raw_campaign.get("brand_name")
        or raw_campaign.get("business_name")
        or "Nivora"
    )

    offer = (
        raw_campaign.get("offer")
        or raw_campaign.get("headline")
        or raw_campaign.get("campaign_promise")
        or "Launch your first smart campaign"
    )

    target_audience = (
        raw_campaign.get("target_audience")
        or raw_campaign.get("audience")
        or "small business owners"
    )

    goal = _normalize_goal(
        raw_campaign.get("goal") or raw_campaign.get("primary_goal") or ""
    )

    platform = _normalize_platform(
        raw_campaign.get("platform") or raw_campaign.get("primary_platform") or "tiktok"
    )

    tone = (
        raw_campaign.get("tone")
        or raw_campaign.get("voice")
        or "friendly"
    )

    brief = {
        "brand_name": brand_name,
        "offer": offer,
        "target_audience": target_audience,
        "goal": goal,
        "platform": platform,
        "tone": tone,
    }

    return brief


# ---------- Public API ----------

def get_media_package_for_campaign(raw_campaign: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function the Thinking Engine should call.

    Input:
        raw_campaign: dict containing at least some of:
            - brand_name / business_name
            - offer / headline / campaign_promise
            - target_audience / audience
            - goal / primary_goal
            - platform / primary_platform
            - tone / voice

    Output:
        dict with keys:
            - image_prompt
            - thumbnail_caption
            - hook_line
            - video_script
            - estimated_duration_seconds
            - scenes (list of scene strings)
            - generated_at (ISO timestamp)
    """
    brief = _build_brief_from_campaign(raw_campaign)
    media_package = generate_media_package(brief)
    return media_package


# ---------- CLI demo for quick manual testing ----------

if __name__ == "__main__":
    import json

    demo_campaign = {
        "brand_name": "Nivora",
        "offer": "Done-for-you AI campaign system",
        "target_audience": "small business owners and creators",
        "goal": "get more sales",
        "platform": "tiktok",
        "tone": "confident",
    }

    print("=== Engine Media Bridge Demo ===")
    package = get_media_package_for_campaign(demo_campaign)
    print(json.dumps(package, indent=2, ensure_ascii=False))