from dataclasses import asdict
from typing import Any, Dict

from engine_campaign_brain_v1 import (
    BrainRequest,
    BrainResponse,
    get_book_of_truth,
    process_brain_request,
)


class SamAnalytics:
    """
    Sam = Analytics / Performance Brain / Risk Radar.
    He NEVER changes the strategy. He reads data and raises insights + alerts.
    """

    def __init__(self) -> None:
        self.role: str = "sam"

    # -----------------------------------------------------
    # High-level analytics overview
    # -----------------------------------------------------

    def analytics_overview(self, user_message: str) -> BrainResponse:
        """
        Ask Sam for a general performance overview.

        user_message example:
        - "How did we do this week?"
        - "Summarize performance for October."
        """
        req = BrainRequest(
            role="sam",
            message=user_message,
            context={"intent": "analytics_overview"},
        )
        return process_brain_request(req)

    # -----------------------------------------------------
    # Experiment / A/B test analysis
    # -----------------------------------------------------

    def analyze_experiment(self, user_message: str) -> BrainResponse:
        """
        Ask Sam to analyze an A/B test or experiment
        that Jon has already run.
        """
        req = BrainRequest(
            role="sam",
            message=user_message,
            context={"intent": "analyze_experiment"},
        )
        return process_brain_request(req)

    # -----------------------------------------------------
    # Simple human-readable explanation of metrics input
    # (Maya can later build on this)
    # -----------------------------------------------------

    def explain_metrics(self, metrics: Dict[str, Any]) -> str:
        """
        Turn a metrics dict into a simple text summary.
        This does NOT call the brain; it's just a helper.
        """
        truth = get_book_of_truth()
        niche = truth.get("niche") or "unknown niche"
        content_type = truth.get("content_type") or "unspecified content type"

        parts = [
            f"Sam: Here's how your '{niche}' {content_type} content is doing:",
        ]

        for key, value in metrics.items():
            parts.append(f"- {key}: {value}")

        return "\n".join(parts)


# ---------------------------------------------------------
# Simple helper so other files can use Sam easily
# ---------------------------------------------------------

def run_sam_overview(user_message: str) -> BrainResponse:
    sam = SamAnalytics()
    return sam.analytics_overview(user_message)


# ---------------------------------------------------------
# CLI demo
# ---------------------------------------------------------

if __name__ == "__main__":
    sam = SamAnalytics()

    print("--- Sam overview demo ---")
    resp = sam.analytics_overview("Give me a monthly performance summary.")
    print(resp.message)

    print("\n--- Sam experiment demo ---")
    resp2 = sam.analyze_experiment("Compare variant A vs B for the last campaign.")
    print(resp2.message)

    print("\n--- Sam explain_metrics helper demo ---")
    text = sam.explain_metrics(
        {
            "impressions": 12000,
            "click_through_rate": "3.5%",
            "cost_per_result": "$1.20",
            "conversions": 140,
        }
    )
    print(text)