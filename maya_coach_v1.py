from typing import Any, Dict

from engine_campaign_brain_v1 import (
    BrainRequest,
    BrainResponse,
    get_book_of_truth,
    process_brain_request,
)


class MayaCoach:
    """
    Maya = Coach / Explainer / Mindset.
    She explains what Nicole, Sam, and Jon are doing. She never edits the plan.
    """

    def __init__(self) -> None:
        self.role: str = "maya"

    # -----------------------------------------------------
    # General coaching / explanation
    # -----------------------------------------------------

    def coach_user(self, user_message: str) -> BrainResponse:
        """
        Ask Maya to explain what's going on or give gentle guidance.
        """
        req = BrainRequest(
            role="maya",
            message=user_message,
            context={"intent": "coach_user"},
        )
        return process_brain_request(req)

    # -----------------------------------------------------
    # Explain results in a simple way (built on Book of Truth)
    # -----------------------------------------------------

    def explain_results_brief(self) -> str:
        """
        Very simple text-only explanation that Maya can give,
        based on the Book of Truth. Real versions will use
        Sam's real metrics later.
        """
        truth = get_book_of_truth()
        niche = truth.get("niche") or "unknown niche"
        content_type = truth.get("content_type") or "unspecified content type"
        goals = truth.get("goals") or []
        goals_str = ", ".join(goals) if goals else "no specific goals yet"

        return (
            "Maya: Here's the simple version.\n"
            f"We're helping a '{niche}' brand with '{content_type}'. "
            f"Our main goals are: {goals_str}. "
            "Nicole chooses the strategy, Jon runs tests, and Sam reads the numbers. "
            "My job is to keep you clear and confident while they do the heavy lifting."
        )


# ---------------------------------------------------------
# Simple helper so other files can use Maya easily
# ---------------------------------------------------------

def run_maya_coach(user_message: str) -> BrainResponse:
    maya = MayaCoach()
    return maya.coach_user(user_message)


# ---------------------------------------------------------
# CLI demo
# ---------------------------------------------------------

if __name__ == "__main__":
    maya = MayaCoach()

    print("--- Maya coach_user demo ---")
    resp = maya.coach_user(
        "I'm confused about what Nivora is doing for me this week."
    )
    print(resp.message)

    print("\n--- Maya explain_results_brief demo ---")
    print(maya.explain_results_brief())