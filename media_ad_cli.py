"""
media_ad_cli.py

Simple command-line wrapper around media_ad_ai_v1.MediaAdAI
so YZ can quickly generate image + video ad packages for
any brand / campaign.

Usage:
    python media_ad_cli.py
"""

from typing import Dict, Any
import json

from media_ad_ai_v1 import generate_media_package


def ask(prompt: str, default: str = "") -> str:
    """Small helper to ask for input with a default value."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    value = input(full_prompt).strip()
    return value or default


def build_brief_from_cli() -> Dict[str, Any]:
    """Ask YZ a few questions and build a campaign brief dict."""
    print("=== Media Ad Brief ===")
    brand_name = ask("Brand / platform name", "Nivora")
    offer = ask("What are you promoting?", "Done-for-you AI campaign system")
    target_audience = ask(
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

    brief = {
        "brand_name": brand_name,
        "offer": offer,
        "target_audience": target_audience,
        "goal": goal,
        "platform": platform,
        "tone": tone,
    }
    return brief


def main() -> None:
    print("=== Nivora Media Ad Generator (CLI) ===\n")
    brief = build_brief_from_cli()
    package = generate_media_package(brief)

    print("\n=== Generated Media Package ===\n")
    print(json.dumps(package, indent=2, ensure_ascii=False))

    print("\nQuick use:")
    print("- Copy 'image_prompt' into your image AI to generate the ad thumbnail.")
    print("- Use 'video_script' and 'scenes' inside your video editor or template.")
    print("- 'thumbnail_caption' is the short text overlay for the first frame.")


if __name__ == "__main__":
    main()