"""
scenario_brain_v1.py

Nivora Thinking Engine - Scenario Brain (v1.0)

Goal:
- Given a base campaign, generate multiple "scenario" variants
  (different angles, tones, platforms, goals).
- Assign each scenario a rough score and risk flags.
- Provide a ranked list so higher layers can pick the top few.

This is a STRUCTURE-FIRST implementation:
- v1 uses simple heuristics for scoring and variant creation.
- Later, Sam + real stats will feed into the scoring function.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class ScenarioIdea:
    id: str
    label: str
    campaign: Dict[str, Any]
    score: float
    risk_flags: List[str]


# ---------- Helpers ----------


def _clone_campaign(base: Dict[str, Any]) -> Dict[str, Any]:
    return dict(base) if base else {}


def _base_scenario_set(base: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate a simple set of scenario campaign variants
    based on common changes we want to test.
    """

    brand = base.get("brand_name", "Brand")
    offer = base.get("offer", "Your offer")
    audience = base.get("target_audience", "your audience")

    scenarios: List[Dict[str, Any]] = []

    # 1) Original as-is
    s0 = _clone_campaign(base)
    s0["scenario_label"] = "Base angle"
    scenarios.append(s0)

    # 2) Stronger pain-focused angle
    s1 = _clone_campaign(base)
    s1["campaign_promise"] = f"Stop wasting money on dead ads — let {brand} fix it."
    s1["tone"] = "bold"
    s1["scenario_label"] = "Pain-first bold angle"
    scenarios.append(s1)

    # 3) Results-focused (sales)
    s2 = _clone_campaign(base)
    s2["goal"] = "get more sales"
    s2["campaign_promise"] = f"Turn your content into real sales with {brand}."
    s2["scenario_label"] = "Sales-focused"
    scenarios.append(s2)

    # 4) Leads-focused (for B2B)
    s3 = _clone_campaign(base)
    s3["goal"] = "get more leads"
    s3["scenario_label"] = "Leads-focused B2B style"
    scenarios.append(s3)

    # 5) Safer, calm / pro tone
    s4 = _clone_campaign(base)
    s4["tone"] = "calm"
    s4["scenario_label"] = "Calm professional angle"
    scenarios.append(s4)

    # 6) Platform tweak: TikTok
    s5 = _clone_campaign(base)
    s5["platform"] = "tiktok"
    s5["scenario_label"] = "TikTok short-form"
    scenarios.append(s5)

    # 7) Platform tweak: Instagram
    s6 = _clone_campaign(base)
    s6["platform"] = "instagram"
    s6["scenario_label"] = "Instagram Reels / Stories"
    scenarios.append(s6)

    # 8) Platform tweak: YouTube Shorts
    s7 = _clone_campaign(base)
    s7["platform"] = "youtube"
    s7["scenario_label"] = "YouTube Shorts"
    scenarios.append(s7)

    # 9) Audience tweak: niche creators
    s8 = _clone_campaign(base)
    s8["target_audience"] = f"content creators in {audience}"
    s8["scenario_label"] = "Creator-focused"
    scenarios.append(s8)

    # 10) Audience tweak: local businesses
    s9 = _clone_campaign(base)
    s9["target_audience"] = "local small business owners"
    s9["scenario_label"] = "Local business angle"
    scenarios.append(s9)

    return scenarios


def _score_scenario(campaign: Dict[str, Any]) -> float:
    """
    Very simple scoring heuristic.

    Later, this will use:
      - Sam's performance data
      - historical CTR / CPM / CPC
      - engagement metrics

    For now we:
      - reward TikTok / Reels / Shorts
      - reward clear goals
      - lightly reward bold / confident tones
    """
    score = 5.0  # base

    platform = (campaign.get("platform") or "").lower()
    tone = (campaign.get("tone") or "").lower()
    goal = (campaign.get("goal") or "").lower()

    if "tiktok" in platform or "instagram" in platform or "short" in platform:
        score += 1.5

    if "sale" in goal or "sell" in goal:
        score += 1.0
    elif "lead" in goal:
        score += 0.8
    elif "book" in goal or "call" in goal:
        score += 0.7

    if "bold" in tone or "confident" in tone:
        score += 0.5
    elif "calm" in tone or "professional" in tone:
        score += 0.3

    return round(score, 2)


def _risk_flags_for_scenario(campaign: Dict[str, Any]) -> List[str]:
    """
    Placeholder risk flags.

    Later, this will look at:
      - language guard output
      - past performance (dead campaigns)
      - platform policy risks

    For now, we just add small hints.
    """
    flags: List[str] = []
    tone = (campaign.get("tone") or "").lower()

    if "bold" in tone:
        flags.append("tone_bold_check_copy_for_overpromising")

    # This can be extended later based on language guard, etc.
    return flags


# ---------- Public API ----------


def generate_scenario_ideas(
    base_campaign: Dict[str, Any],
    max_scenarios: int = 10,
) -> List[ScenarioIdea]:
    """
    Generate a list of ScenarioIdea objects for the given base campaign.
    """
    raw_scenarios = _base_scenario_set(base_campaign)
    ideas: List[ScenarioIdea] = []

    for idx, c in enumerate(raw_scenarios[:max_scenarios]):
        label = c.get("scenario_label", f"Scenario {idx + 1}")
        score = _score_scenario(c)
        risks = _risk_flags_for_scenario(c)
        idea = ScenarioIdea(
            id=f"scenario_{idx + 1}",
            label=label,
            campaign=c,
            score=score,
            risk_flags=risks,
        )
        ideas.append(idea)

    return ideas


def rank_scenarios(
    base_campaign: Dict[str, Any],
    max_scenarios: int = 10,
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    """
    High-level helper:
      - Generate scenario ideas
      - Sort by score (DESC)
      - Return top_n as plain dicts
    """
    ideas = generate_scenario_ideas(base_campaign, max_scenarios=max_scenarios)
    ideas_sorted = sorted(ideas, key=lambda s: s.score, reverse=True)
    top = ideas_sorted[:top_n]
    return [asdict(s) for s in top]


if __name__ == "__main__":
    # Simple manual demo
    demo = {
        "brand_name": "Nivora",
        "offer": "Done-for-you AI campaign system",
        "target_audience": "small business owners and content creators",
        "goal": "get more sales",
        "platform": "tiktok",
        "tone": "confident",
    }

    ranked = rank_scenarios(demo, max_scenarios=10, top_n=3)
    import json

    print(json.dumps(ranked, indent=2, ensure_ascii=False))