from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Literal

# ---------------------------------------------------------
# Role + capabilities config (Nivora Family Rules in code)
# ---------------------------------------------------------

Role = Literal["nicole", "sam", "jon", "maya"]

AI_ROLES: Dict[Role, Dict[str, bool]] = {
    "nicole": {
        "can_override_plan": True,
        "can_alert": False,
        "can_experiment": False,
        "can_explain": True,
    },
    "sam": {
        "can_override_plan": False,
        "can_alert": True,      # can raise warnings about performance
        "can_experiment": False,
        "can_explain": False,
    },
    "jon": {
        "can_override_plan": False,
        "can_alert": False,
        "can_experiment": True,  # sandbox tests inside Nicole’s direction
        "can_explain": False,
    },
    "maya": {
        "can_override_plan": False,
        "can_alert": False,
        "can_experiment": False,
        "can_explain": True,    # coaching / explanations
    },
}

# ---------------------------------------------------------
# Book of Truth = official niche / content / goals
# Only Nicole can change this.
# ---------------------------------------------------------


@dataclass
class BookOfTruth:
    niche: str = ""
    content_type: str = ""
    brand_voice: str = ""
    goals: List[str] = field(default_factory=list)


BOOK_OF_TRUTH = BookOfTruth()

# ---------------------------------------------------------
# Request / Response dataclasses
# ---------------------------------------------------------


@dataclass
class BrainRequest:
    role: Role
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainResponse:
    role: Role
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------
# Book of Truth helpers
# ---------------------------------------------------------


def update_book_of_truth(role: Role, updates: Dict[str, Any]) -> BookOfTruth:
    """
    Only Nicole is allowed to update the Book of Truth.
    Everyone else can read it but not change it.
    """
    if role != "nicole":
        raise PermissionError("Only Nicole can change the Book of Truth.")

    if "niche" in updates:
        BOOK_OF_TRUTH.niche = str(updates["niche"])
    if "content_type" in updates:
        BOOK_OF_TRUTH.content_type = str(updates["content_type"])
    if "brand_voice" in updates:
        BOOK_OF_TRUTH.brand_voice = str(updates["brand_voice"])
    if "goals" in updates and isinstance(updates["goals"], list):
        BOOK_OF_TRUTH.goals = [str(g) for g in updates["goals"]]

    return BOOK_OF_TRUTH


def get_book_of_truth() -> Dict[str, Any]:
    """
    Read-only view of the Book of Truth.
    Safe for any role to call.
    """
    return asdict(BOOK_OF_TRUTH)


# ---------------------------------------------------------
# Safety / positivity filter (global guardrail for everyone)
# ---------------------------------------------------------


def is_safe_content(text: str) -> bool:
    """
    VERY simple placeholder safety check.
    Later you can replace this with something smarter,
    but this enforces your "positive, safe, non-shady" rule.
    """
    unsafe_keywords = [
        "scam",
        "fraud",
        "violence",
        "weapon",
        "gun",
        "drugs",
        "porn",
        "hate",
        "terror",
    ]
    lower = text.lower()
    return not any(bad in lower for bad in unsafe_keywords)


def enforce_safety(role: Role, message: str) -> str:
    """
    If a response looks unsafe, replace it with a safe generic answer.
    """
    if is_safe_content(message):
        return message

    return (
        "Nivora can only help with positive, safe, non-controversial business content. "
        "Please adjust your request."
    )


# ---------------------------------------------------------
# Role-specific handlers (basic placeholders for now)
# These keep the hierarchy and lanes clear.
# ---------------------------------------------------------


def _handle_nicole(request: BrainRequest) -> BrainResponse:
    """
    Nicole = Head Master Strategist.
    She sets direction and locks in the plan.
    This handler should eventually call your LLM with a Nicole-style prompt.
    For now it's a structured placeholder.
    """
    truth = get_book_of_truth()

    base_reply = (
        f"Nicole: Based on the current strategy for niche '{truth.get('niche')}' "
        f"and content type '{truth.get('content_type')}', here's the plan:\n\n"
        f"{request.message}"
    )

    safe_reply = enforce_safety(request.role, base_reply)

    return BrainResponse(
        role=request.role,
        message=safe_reply,
        metadata={
            "book_of_truth": truth,
            "role_capabilities": AI_ROLES["nicole"],
            "intent": request.context.get("intent", "general"),
        },
    )


def _handle_sam(request: BrainRequest) -> BrainResponse:
    """
    Sam = analytics + risk radar.
    This is a placeholder that later connects to real metrics.
    """
    truth = get_book_of_truth()

    base_reply = (
        "Sam: I'll analyze performance for the current strategy.\n"
        "Right now, I can only return a placeholder summary. "
        "Later, this will use real metrics.\n\n"
        f"User request: {request.message}\n"
        f"Niche: {truth.get('niche')}, Content type: {truth.get('content_type')}"
    )

    safe_reply = enforce_safety(request.role, base_reply)

    return BrainResponse(
        role=request.role,
        message=safe_reply,
        metadata={
            "role_capabilities": AI_ROLES["sam"],
            "intent": request.context.get("intent", "analytics"),
        },
    )


def _handle_jon(request: BrainRequest) -> BrainResponse:
    """
    Jon = execution + sandbox tests (inside Nicole’s rules).
    """
    truth = get_book_of_truth()

    base_reply = (
        "Jon: I'll design a small experiment inside Nicole's strategy.\n"
        "For now this is a placeholder describing what I would test.\n\n"
        f"Experiment idea based on: {request.message}\n"
        f"Niche: {truth.get('niche')}, Content type: {truth.get('content_type')}"
    )

    safe_reply = enforce_safety(request.role, base_reply)

    return BrainResponse(
        role=request.role,
        message=safe_reply,
        metadata={
            "role_capabilities": AI_ROLES["jon"],
            "intent": request.context.get("intent", "execution"),
        },
    )


def _handle_maya(request: BrainRequest) -> BrainResponse:
    """
    Maya = explainer / coach.
    """
    truth = get_book_of_truth()

    base_reply = (
        "Maya: Let me explain what Nivora is doing in simple terms.\n\n"
        f"Your question: {request.message}\n"
        f"We're currently helping a '{truth.get('niche')}' brand with "
        f"'{truth.get('content_type')}' content."
    )

    safe_reply = enforce_safety(request.role, base_reply)

    return BrainResponse(
        role=request.role,
        message=safe_reply,
        metadata={
            "role_capabilities": AI_ROLES["maya"],
            "intent": request.context.get("intent", "coaching"),
        },
    )


# ---------------------------------------------------------
# Main router – all requests flow through here
# ---------------------------------------------------------


def process_brain_request(request: BrainRequest) -> BrainResponse:
    """
    Central entry point.
    You call this from Nicole / Sam / Jon / Maya code.
    """
    if request.role not in AI_ROLES:
        raise ValueError(f"Unknown role: {request.role}")

    if request.role == "nicole":
        return _handle_nicole(request)
    if request.role == "sam":
        return _handle_sam(request)
    if request.role == "jon":
        return _handle_jon(request)
    if request.role == "maya":
        return _handle_maya(request)

    # Should never reach here
    raise ValueError(f"No handler implemented for role: {request.role}")


# ---------------------------------------------------------
# Simple CLI demo (optional)
# ---------------------------------------------------------

if __name__ == "__main__":
    # Quick demo to verify wiring
    update_book_of_truth(
        role="nicole",
        updates={
            "niche": "barbershop owners",
            "content_type": "short-form TikTok videos",
            "brand_voice": "confident, street-smart, supportive",
            "goals": ["get more local clients", "increase bookings"],
        },
    )

    demo_requests = [
        BrainRequest(
            role="nicole",
            message="Draft a launch strategy for next week.",
            context={"intent": "plan_campaign"},
        ),
        BrainRequest(
            role="sam",
            message="How are we performing this month?",
            context={"intent": "analytics_overview"},
        ),
        BrainRequest(
            role="jon",
            message="Set up a small A/B test for hooks.",
            context={"intent": "run_ab_test"},
        ),
        BrainRequest(
            role="maya",
            message="Explain what Nivora is doing for me right now.",
            context={"intent": "coach_user"},
        ),
    ]

    for req in demo_requests:
        resp = process_brain_request(req)
        print("=" * 60)
        print(f"Role: {resp.role}")
        print(resp.message)
        print("Metadata:", resp.metadata)