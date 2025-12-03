from dataclasses import asdict
from typing import Any, Dict, List

from engine_campaign_brain_v1 import (
    BrainRequest,
    BrainResponse,
    get_book_of_truth,
    process_brain_request,
    update_book_of_truth,
)


class NicoleStrategist:
    """
    Nicole = Head Master / Chief Strategist.
    She is the only one allowed to override or change the Book of Truth.
    Everyone else just reads from it.
    """

    def __init__(self) -> None:
        # role must match the Role type used in engine_campaign_brain_v1
        self.role: str = "nicole"

    # -----------------------------------------------------
    # Book of Truth control (only Nicole can do this)
    # -----------------------------------------------------

    def set_brand_profile(
        self,
        niche: str,
        content_type: str,
        brand_voice: str,
        goals: List[str],
    ) -> Dict[str, Any]:
        """
        Update the Book of Truth with the core brand settings.
        Only Nicole is allowed to call this.
        """
        updated = update_book_of_truth(
            role=self.role,
            updates={
                "niche": niche,
                "content_type": content_type,
                "brand_voice": brand_voice,
                "goals": goals,
            },
        )
        return asdict(updated)

    # -----------------------------------------------------
    # Planning – Nicole sets direction, Brain supports
    # -----------------------------------------------------

    def plan_campaign(self, user_message: str) -> BrainResponse:
        """
        High-level planner. Nicole sets direction and delegates details
        to the brain and other roles under the hood.
        """
        request = BrainRequest(
            role="nicole",
            message=user_message,
            context={"intent": "plan_campaign"},
        )
        return process_brain_request(request)

    # -----------------------------------------------------
    # Explanation – Nicole describing current strategy
    # (Maya can later use this as input to coach the user)
    # -----------------------------------------------------

    def explain_current_strategy(self) -> str:
        """
        Human-readable explanation of the current strategy,
        based on the Book of Truth.
        """
        truth = get_book_of_truth()
        niche = truth.get("niche") or "unknown niche"
        content_type = truth.get("content_type") or "unspecified content type"
        goals = truth.get("goals") or []
        goals_str = ", ".join(goals) if goals else "no specific goals yet"

        explanation = (
            f"Nicole: Right now, we're focused on helping a '{niche}' brand using "
            f"'{content_type}'. Our main goals are: {goals_str}. "
            "From here, I will choose scenarios for Jon to test and Sam to measure."
        )
        return explanation


# ---------------------------------------------------------
# Optional helper used by other files
# ---------------------------------------------------------

def run_nicole_strategy(user_message: str) -> BrainResponse:
    """
    Simple helper so other files can do:
    from nicole_strategist_v1 import run_nicole_strategy
    """
    nicole = NicoleStrategist()
    return nicole.plan_campaign(user_message)


# ---------------------------------------------------------
# Simple CLI demo
# ---------------------------------------------------------

if __name__ == "__main__":
    nicole = NicoleStrategist()

    profile = nicole.set_brand_profile(
        niche="barbershop owners",
        content_type="short TikTok videos",
        brand_voice="confident, casual, motivating",
        goals=["get more local clients", "increase weekly bookings"],
    )
    print("Book of Truth after Nicole update:")
    print(profile)

    print("\n--- Nicole planning a campaign ---")
    resp = nicole.plan_campaign(
        "Create a 7-day content plan to promote a new haircut style."
    )
    print(resp.message)

    print("\n--- Nicole explaining current strategy ---")
    print(nicole.explain_current_strategy())