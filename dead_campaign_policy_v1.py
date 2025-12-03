"""
dead_campaign_policy_v1.py

Nivora Thinking Engine - Dead Campaign Policy (v1.0)

Rule:
- We NEVER simply repost a dead campaign.
- If performance is below certain thresholds, the campaign must be improved
  or rebuilt before re-launch.

This module does NOT store history by itself; it just defines the logic.
Higher layers (Sam / storage) will provide the metrics.

Expected metrics dict can include:
    - impressions
    - clicks
    - ctr (click-through rate, 0-1)
    - conversions
    - spend
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class CampaignPerformanceCheck:
    is_dead: bool
    reasons: str
    recommendation: str


def evaluate_campaign_performance(metrics: Dict[str, Any]) -> CampaignPerformanceCheck:
    """
    Decide whether a campaign is "dead" based on simple thresholds.

    v1 thresholds (you can tune these):
      - impressions < 500 and spend > 0  -> likely dead
      - ctr < 0.5% after 1000+ impressions -> dead
      - conversions == 0 after decent spend -> dead
    """
    impressions = int(metrics.get("impressions", 0))
    clicks = int(metrics.get("clicks", 0))
    conversions = int(metrics.get("conversions", 0))
    spend = float(metrics.get("spend", 0.0))

    ctr = float(metrics.get("ctr", 0.0))
    if impressions > 0 and clicks > 0:
        ctr = clicks / impressions

    reasons = []
    is_dead = False

    # Rule 1: Very low reach with spend
    if impressions < 500 and spend > 0:
        is_dead = True
        reasons.append("Low impressions despite spend")

    # Rule 2: Very low CTR after enough impressions
    if impressions >= 1000 and ctr < 0.005:  # 0.5%
        is_dead = True
        reasons.append("CTR below 0.5% after 1000+ impressions")

    # Rule 3: No conversions after decent spend
    if conversions == 0 and spend >= 50:
        is_dead = True
        reasons.append("No conversions after significant spend")

    if not reasons:
        reasons.append("Performance is acceptable; campaign is not considered dead in v1 rules.")

    if is_dead:
        recommendation = (
            "Do NOT repost this campaign as-is. Create a new version: "
            "change hook, creative, audience, or offer before relaunch."
        )
    else:
        recommendation = "You may iterate carefully, but continue monitoring performance."

    return CampaignPerformanceCheck(
        is_dead=is_dead,
        reasons="; ".join(reasons),
        recommendation=recommendation,
    )


def performance_check_to_dict(check: CampaignPerformanceCheck) -> Dict[str, Any]:
    return asdict(check)