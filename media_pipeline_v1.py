"""
media_pipeline_v1.py

Nivora Thinking Engine - Media Pipeline (v1.1)

This module gives the main Thinking Engine ONE clean entrypoint to
generate a full media kit for any campaign AND analyze language/safety.

Public API:

    run_media_pipeline(campaign: dict) -> dict

Input:
    campaign: dict with fields like:
        - brand_name / business_name
        - offer / headline / campaign_promise
        - target_audience / audience
        - goal / primary_goal
        - platform / primary_platform
        - tone / voice

Output:
    dict:
        {
          "campaign": { ...normalized campaign... },
          "media_kit": {
             "image_prompt": ...,
             "thumbnail_caption": ...,
             "hook_line": ...,
             "video_script": ...,
             "scenes": [...],
             "estimated_duration_seconds": ...,
             "generated_at": ...,
             "language_analysis": {
                 "language_code": ...,
                 "confidence": ...,
                 "needs_translation": ...,
                 "flagged": ...,
                 "flags": [...]
             }
          },
          "file_path": "/abs/path/to/json"
        }
"""

from __future__ import annotations

from typing import Dict, Any
import json
import datetime
import os

from engine_media_bridge_v1 import get_media_package_for_campaign
from language_guard_v1 import analyze_text_language, analysis_to_dict


# ---------- Internal helpers ----------


def _normalize_campaign(raw_campaign: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make sure the campaign dict has the keys we expect.
    We don't try to be too smart here – just fill missing pieces.
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

    goal = (
        raw_campaign.get("goal")
        or raw_campaign.get("primary_goal")
        or "get more sales"
    )

    platform = (
        raw_campaign.get("platform")
        or raw_campaign.get("primary_platform")
        or "tiktok"
    )

    tone = (
        raw_campaign.get("tone")
        or raw_campaign.get("voice")
        or "friendly"
    )

    normalized = {
        "brand_name": brand_name,
        "offer": offer,
        "target_audience": target_audience,
        "goal": goal,
        "platform": platform,
        "tone": tone,
    }
    return normalized


def _build_output_filename(brand_name: str) -> str:
    brand_slug = (brand_name or "brand").replace(" ", "_")
    timestamp = datetime.datetime.utcnow().isoformat().replace(":", "-")
    return f"media_output_{brand_slug}_{timestamp}.json"


def _save_media_bundle_to_file(
    campaign: Dict[str, Any],
    media_kit: Dict[str, Any],
    filename: str | None = None,
) -> str:
    """
    Save campaign + media_kit into a JSON file.
    Returns the absolute path.
    """
    if filename is None:
        filename = _build_output_filename(campaign.get("brand_name", "brand"))

    payload = {
        "campaign": campaign,
        "media_kit": media_kit,
        "saved_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return os.path.abspath(filename)


def _attach_language_analysis(media_kit: Dict[str, Any]) -> None:
    """
    Run language guard on the combined hook + script and
    attach the result into media_kit["language_analysis"].
    """
    hook = media_kit.get("hook_line", "") or ""
    script = media_kit.get("video_script", "") or ""
    combined = f"{hook}\n{script}".strip()

    analysis = analyze_text_language(combined, preferred_lang="en")
    media_kit["language_analysis"] = analysis_to_dict(analysis)


# ---------- Public pipeline ----------


def run_media_pipeline(raw_campaign: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entrypoint for the Thinking Engine.

    Steps:
      1) Normalize the incoming campaign dict.
      2) Ask Media Ad AI (via engine_media_bridge_v1) for a media kit.
      3) Run language guard on the text.
      4) Save campaign + media kit to disk as JSON.
      5) Return everything + file path.
    """
    # 1) Normalize campaign shape
    campaign = _normalize_campaign(raw_campaign)

    # 2) Generate media kit
    media_kit = get_media_package_for_campaign(campaign)

    # 3) Attach language analysis
    _attach_language_analysis(media_kit)

    # 4) Save to JSON file
    path = _save_media_bundle_to_file(campaign, media_kit)

    # 5) Return combined result
    result = {
        "campaign": campaign,
        "media_kit": media_kit,
        "file_path": path,
    }
    return result


# ---------- Optional: quick manual demo ----------

if __name__ == "__main__":
    demo_campaign = {
        "brand_name": "Nivora",
        "offer": "Done-for-you AI campaign system",
        "target_audience": "small business owners and content creators",
        "goal": "get more sales",
        "platform": "tiktok",
        "tone": "confident",
    }

    bundle = run_media_pipeline(demo_campaign)
    print("=== Media pipeline bundle ===")
    print(json.dumps(bundle, indent=2, ensure_ascii=False))
    print("\nSaved file:", bundle["file_path"])