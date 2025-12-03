from nicole_strategist_v1 import NicoleStrategist
from sam_analytics_v1 import SamAnalytics
from jon_executor_v1 import JonExecutor
from maya_coach_v1 import MayaCoach


def main() -> None:
    # Instantiate the family
    nicole = NicoleStrategist()
    sam = SamAnalytics()
    jon = JonExecutor()
    maya = MayaCoach()

    print("=== Step 1: Nicole sets the brand profile (Book of Truth) ===")
    profile = nicole.set_brand_profile(
        niche="barbershop owners",
        content_type="short-form TikTok videos",
        brand_voice="confident, street-smart, supportive",
        goals=["get more local clients", "increase weekly bookings"],
    )
    print(profile)

    print("\n=== Step 2: Nicole plans a campaign ===")
    plan_resp = nicole.plan_campaign(
        "Create a 7-day content plan to promote a new haircut style."
    )
    print(plan_resp.message)

    print("\n=== Step 3: Sam gives an analytics-style overview ===")
    sam_resp = sam.analytics_overview("How are we performing this month?")
    print(sam_resp.message)

    print("\n=== Step 4: Jon designs an experiment inside Nicole's strategy ===")
    jon_resp = jon.design_experiment(
        "Set up a small A/B test comparing 3 hooks for our next TikTok."
    )
    print(jon_resp.message)

    print("\n=== Step 5: Maya explains everything in simple language ===")
    maya_resp = maya.coach_user(
        "Explain what Nivora is doing for me right now in simple terms."
    )
    print(maya_resp.message)

    print("\n=== Step 6: Maya quick summary using Book of Truth ===")
    print(maya.explain_results_brief())


if __name__ == "__main__":
    main()