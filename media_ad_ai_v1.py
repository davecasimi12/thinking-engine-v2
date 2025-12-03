"""
media_ad_ai_v1.py

Nivora Thinking Engine - Media Ad AI (v1.0)
- Generates image prompts and 15–30 second video ad scripts
  for a given campaign brief.
- Standalone module: safe to plug into the main Thinking Engine later.

Usage (CLI quick test):
    python media_ad_ai_v1.py
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import textwrap
import json
import datetime


# ---------- Data models ----------

@dataclass
class CampaignBrief:
    brand_name: str
    offer: str              # what are we promoting
    target_audience: str
    goal: str               # e.g. "get leads", "sell product", "book calls"
    platform: str           # e.g. "tiktok", "instagram", "facebook", "youtube"
    tone: str = "friendly"  # default tone


@dataclass
class MediaAdResult:
    image_prompt: str
    thumbnail_caption: str
    hook_line: str
    video_script: str
    estimated_duration_seconds: int
    scenes: List[str]


# ---------- Core media brain ----------

class MediaAdAI:
    """
    MediaAdAI:
    - Takes a CampaignBrief
    - Designs 1 strong image prompt
    - Writes a short 15–30 second script
    - Breaks script into simple scenes for video tools
    """

    def __init__(self, max_duration_seconds: int = 30) -> None:
        self.max_duration = max_duration_seconds

    # ---- Public API ----

    def generate_media_ad(self, brief: CampaignBrief) -> MediaAdResult:
        image_prompt = self._build_image_prompt(brief)
        hook = self._build_hook_line(brief)
        script = self._build_video_script(brief, hook)
        scenes = self._split_into_scenes(script)
        duration = self._estimate_duration(script)

        # Clamp to our 15–30 sec window
        if duration < 15:
            duration = 15
        if duration > self.max_duration:
            duration = self.max_duration

        thumbnail_caption = self._build_thumbnail_caption(brief, hook)

        return MediaAdResult(
            image_prompt=image_prompt,
            thumbnail_caption=thumbnail_caption,
            hook_line=hook,
            video_script=script,
            estimated_duration_seconds=duration,
            scenes=scenes,
        )

    # ---- Internal helpers ----

    def _build_image_prompt(self, brief: CampaignBrief) -> str:
        """
        This is the text you would send to an image model
        (DALL·E, Midjourney, etc.).
        """
        platform_style = self._platform_visual_style(brief.platform)

        prompt = (
            f"Ultra-clean {platform_style} style ad for the brand '{brief.brand_name}'. "
            f"Show a confident small business owner looking at their phone while "
            f"analytics and social media icons glow around them. Highlight the idea: "
            f"'{brief.offer}'. Color palette: modern purples, blues, and white. "
            f"Composition optimized for vertical video thumbnail / story format."
        )

        return prompt

    def _build_hook_line(self, brief: CampaignBrief) -> str:
        goal_phrase = self._goal_phrase(brief.goal)
        return f"Stop wasting money on dead ads — let {brief.brand_name} do the heavy lifting {goal_phrase}."

    def _build_video_script(self, brief: CampaignBrief, hook_line: str) -> str:
        """
        Simple 4-part structure:
        1) Hook
        2) Pain
        3) Solution (Nivora / client)
        4) CTA
        """

        lines: List[str] = []

        # 1) Hook
        lines.append(f"[Hook / 0–3s]\n{hook_line}")

        # 2) Pain
        lines.append(
            "[Pain / 3–8s]\n"
            f"You're posting nonstop, but your {brief.platform} views are flat. "
            f"No clicks, no sales, just noise."
        )

        # 3) Solution
        lines.append(
            "[Solution / 8–18s]\n"
            f"{brief.brand_name} builds smart campaigns for you. "
            f"Nicole designs the content, Sam tracks performance, "
            f"Jon handles posting, and Maya coaches you on what’s working. "
            f"Every ad is tested, improved, and never blindly reposted."
        )

        # 4) CTA
        lines.append(
            "[CTA / 18–25s]\n"
            f"Tap the link to launch your first campaign: '{brief.offer}'. "
            f"Let {brief.brand_name} turn your content into real {brief.goal}."
        )

        script = "\n\n".join(lines)
        return textwrap.dedent(script).strip()

    def _split_into_scenes(self, script: str) -> List[str]:
        """
        Very simple split: each [Section] becomes a scene.
        """
        parts = script.split("\n\n")
        scenes: List[str] = []
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                scenes.append(cleaned)
        return scenes

    def _estimate_duration(self, script: str) -> int:
        """
        Crude estimate: 2.5–3 words per second.
        """
        words = script.split()
        word_count = len(words)
        if word_count == 0:
            return 15
        seconds = int(round(word_count / 2.7))
        return max(10, seconds)

    def _build_thumbnail_caption(self, brief: CampaignBrief, hook_line: str) -> str:
        """
        Short text overlay for the thumbnail.
        """
        if len(hook_line) > 45:
            return "Killer ads. Zero guesswork."
        return hook_line

    # ---- Small mapping helpers ----

    @staticmethod
    def _platform_visual_style(platform: str) -> str:
        p = (platform or "").lower()
        if "tiktok" in p:
            return "TikTok-style vertical video"
        if "instagram" in p:
            return "Instagram Reels / Stories"
        if "facebook" in p:
            return "Facebook feed and Stories"
        if "youtube" in p:
            return "YouTube Shorts"
        return "social media"

    @staticmethod
    def _goal_phrase(goal: str) -> str:
        g = (goal or "").lower()
        if "lead" in g:
            return "and bring you qualified leads"
        if "sale" in g or "sell" in g:
            return "and convert views into sales"
        if "book" in g or "call" in g:
            return "and fill your calendar with booked calls"
        return "and turn views into real results"


# ---------- Convenience wrapper ----------

def generate_media_package(brief_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper so other parts of the Thinking Engine can call this
    using a plain dict instead of the dataclasses.
    """
    brief = CampaignBrief(
        brand_name=brief_dict.get("brand_name", "Nivora"),
        offer=brief_dict.get("offer", "Launch your first smart campaign"),
        target_audience=brief_dict.get("target_audience", "small business owners"),
        goal=brief_dict.get("goal", "get more sales"),
        platform=brief_dict.get("platform", "tiktok"),
        tone=brief_dict.get("tone", "friendly"),
    )

    media_ai = MediaAdAI()
    result = media_ai.generate_media_ad(brief)
    data = asdict(result)
    data["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    return data


# ---------- CLI test ----------

def _demo_nivora_self_promo() -> None:
    brief = {
        "brand_name": "Nivora",
        "offer": "Done-for-you AI campaign system",
        "target_audience": "small business owners and creators",
        "goal": "get more sales",
        "platform": "tiktok",
        "tone": "confident",
    }
    package = generate_media_package(brief)
    print("=== Nivora Media Ad Package ===")
    print(json.dumps(package, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _demo_nivora_self_promo()