"""
nicole_media_demo_v1.py

Nicole -> Media Ad AI demo (v1.1)

CLI helper so YZ can:
- Describe a campaign the way Nicole would,
- Send it through the engine_media_bridge,
- Get a clean, human-readable media kit
  (image prompt, hook, script, scenes),
- Save the media kit to a JSON file for later use
  (Bubble, Jon, Sam, etc).

Usage:
    python nicole_media_demo_v1.py
"""

from typing import Dict, Any
from textwrap import indent
import json
import datetime
import os

from engine_media_bridge_v1 import get_media_package_for_campaign


# ---------- Helpers ----------

def ask(prompt: str, default: str = "") -> str:
    """Ask for input with an optional default value."""
    if default:
        full = f"{prompt} [{default}]: "
    else:
        full = f"{prompt}: "
    value = input(full).strip()
    return value or default


def build_campaign_from_cli() -> Dict[str, Any]:
    """Collect a simple campaign brief like Nicole would."""
    print("=== Nicole Campaign Brief ===\n")

    brand_name = ask("Brand / business name", "Nivora")
    offer = ask("What are you promoting?", "Done-for-you AI campaign system")
    audience = ask(
        "Target audience (who is this for?)",
        "small business owners and content creators",
    )
    goal = ask(
        "Main goal (e.g. get more sales, get leads, book calls)",
        "get more sales",
    )
    platform = ask(
        "Main platform (tiktok / instagram / facebook / youtube)",
        "tiktok",
    )
    tone = ask("Tone (friendly, bold, calm, etc.)", "confident")

    campaign = {
        "brand_name": brand_name,
        "offer": offer,
        "target_audience": audience,
        "goal": goal,
        "platform": platform,
        "tone": tone,
    }
    return campaign


def print_media_package(media: Dict[str, Any]) -> None:
    """Pretty-print the media kit to the terminal."""
    print("\n=== Media Kit ===\n")

    print("Image prompt:")
    print(indent(media.get("image_prompt", ""), "  "))

    print("\nThumbnail caption:")
    print(f"  {media.get('thumbnail_caption', '')}")

    print("\nHook line:")
    print(f"  {media.get('hook_line', '')}")

    print("\nVideo script:")
    print(indent(media.get("video_script", ""), "  "))

    scenes = media.get("scenes") or []
    if scenes:
        print("\nScenes:")
        for i, scene in enumerate(scenes, start=1):
            print(f"  Scene {i}:")
            print(indent(scene, "    "))

    duration = media.get("estimated_duration_seconds")
    if duration:
        print(f"\nEstimated duration: ~{duration} seconds")

    print("\nHow to use:")
    print("  - Copy the image prompt into your image AI to generate the thumbnail.")
    print("  - Use the script and scenes inside your video editor template.")
    print("  - Add the thumbnail caption as text on the first frame.\n")


def save_media_to_file(
    media: Dict[str, Any],
    campaign: Dict[str, Any],
    filename: str | None = None,
) -> str:
    """
    Save the media kit + basic campaign info to a JSON file.

    If filename is not provided, we auto-generate one like:
        media_output_Nivora_2025-11-21T00-44-26.json
    """
    brand = (campaign.get("brand_name") or "brand").replace(" ", "_")
    timestamp = datetime.datetime.utcnow().isoformat().replace(":", "-")
    if filename is None:
        filename = f"media_output_{brand}_{timestamp}.json"

    payload = {
        "campaign": campaign,
        "media_kit": media,
        "saved_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return os.path.abspath(filename)


# ---------- Entry point ----------

def main() -> None:
    campaign = build_campaign_from_cli()
    media = get_media_package_for_campaign(campaign)

    print_media_package(media)

    path = save_media_to_file(media, campaign)
    print(f"\nMedia kit saved to:\n  {path}\n")


if __name__ == "__main__":
    main()