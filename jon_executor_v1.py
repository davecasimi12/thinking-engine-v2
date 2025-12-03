from typing import Any, Dict

from engine_campaign_brain_v1 import (
    BrainRequest,
    BrainResponse,
    get_book_of_truth,
    process_brain_request,
)


class JonExecutor:
    """
    Jon = Executor / Launcher / Tester.
    He runs experiments INSIDE Nicole's strategy. He never changes the strategy.
    """

    def __init__(self) -> None:
        self.role: str = "jon"

    # -----------------------------------------------------
    # Design / run a small experiment
    # -----------------------------------------------------

    def design_experiment(self, user_message: str) -> BrainResponse:
        """
        Ask Jon to outline a small test to run
        (different hooks, thumbnails, times, etc.).
        """
        req = BrainRequest(
            role="jon",
            message=user_message,
            context={"intent": "design_experiment"},
        )
        return process_brain_request(req)

    # -----------------------------------------------------
    # Launch-style request (still just talks to brain for now)
    # -----------------------------------------------------

    def plan_launch_steps(self, user_message: str) -> BrainResponse:
        """
        Ask Jon to outline the concrete steps to execute a campaign plan.
        """
        req = BrainRequest(
            role="jon",
            message=user_message,
            context={"intent": "plan_launch"},
        )
        return process_brain_request(req)

    # -----------------------------------------------------
    # Simple text description of what Jon is focusing on
    # -----------------------------------------------------

    def describe_current_focus(self) -> str:
        truth = get_book_of_truth()
        niche = truth.get("niche") or "unknown niche"
        content_type = truth.get("content_type") or "unspecified content type"

        return (
            "Jon: My job is to execute Nicole's plan without changing it. "
            f"Right now I'm running tests for a '{niche}' brand using "
            f"'{content_type}' content, and I report results back to Sam and Nicole."
        )


# ---------------------------------------------------------
# Simple helper so other files can use Jon easily
# ---------------------------------------------------------

def run_jon_experiment(user_message: str) -> BrainResponse:
    jon = JonExecutor()
    return jon.design_experiment(user_message)


# ---------------------------------------------------------
# CLI demo
# ---------------------------------------------------------

if __name__ == "__main__":
    jon = JonExecutor()

    print("--- Jon design_experiment demo ---")
    resp = jon.design_experiment(
        "Set up a small A/B test comparing 3 hooks for our next TikTok."
    )
    print(resp.message)

    print("\n--- Jon plan_launch_steps demo ---")
    resp2 = jon.plan_launch_steps(
        "Outline steps to launch a 7-day promo campaign."
    )
    print(resp2.message)

    print("\n--- Jon describe_current_focus demo ---")
    print(jon.describe_current_focus())