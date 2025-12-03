"""
algo_health_v1.py

Nivora Thinking Engine - Algorithm Health (v1.0)

Goal:
- Track an "algo health" score for a page/account based on simple metrics.
- Indicate whether we should enter a "recovery mode".
- Provide notes Maya can turn into explanations for the user.

Metrics this expects (all optional for now):
    - avg_engagement_rate (0-1)
    - post_frequency_per_week
    - recent_violations_count
    - shadowban_suspected (bool)
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class AlgoHealthSnapshot:
    score: float           # 0 - 100
    level: str             # "healthy", "warning", "danger"
    in_recovery_mode: bool
    notes: str


def estimate_algo_health(metrics: Dict[str, Any]) -> AlgoHealthSnapshot:
    """
    Very simple heuristic-based algo health estimation.

    Later, this will use real platform data and smarter models.
    """
    # Defaults
    engagement = float(metrics.get("avg_engagement_rate", 0.02))  # 2%
    frequency = float(metrics.get("post_frequency_per_week", 3.0))
    violations = int(metrics.get("recent_violations_count", 0))
    shadowban = bool(metrics.get("shadowban_suspected", False))

    score = 50.0

    # Engagement contribution
    if engagement >= 0.08:
        score += 25
    elif engagement >= 0.04:
        score += 15
    elif engagement >= 0.02:
        score += 5
    else:
        score -= 10

    # Posting frequency contribution
    if frequency >= 5:
        score += 10
    elif frequency >= 3:
        score += 5
    elif frequency < 1:
        score -= 10

    # Violations / shadowban penalties
    if violations >= 1:
        score -= 15 * violations
    if shadowban:
        score -= 25

    # Clamp 0-100
    score = max(0.0, min(100.0, score))

    # Level + recovery mode
    if score >= 70:
        level = "healthy"
        in_recovery = False
        notes = "Account looks healthy. Keep posting consistent, high-quality content."
    elif score >= 40:
        level = "warning"
        in_recovery = False
        notes = "Account is in a warning zone. Improve content quality and engagement, avoid risky behavior."
    else:
        level = "danger"
        in_recovery = True
        notes = "Account may need recovery mode: slow down risky posts, focus on safe, high-value content."

    return AlgoHealthSnapshot(
        score=round(score, 1),
        level=level,
        in_recovery_mode=in_recovery,
        notes=notes,
    )


def snapshot_to_dict(snapshot: AlgoHealthSnapshot) -> Dict[str, Any]:
    return asdict(snapshot)