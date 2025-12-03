"""
language_guard_v1.py

Nivora Thinking Engine - Language Guard (v1.0)

Goal:
- Provide a STABLE INTERFACE for language detection and basic content flagging
  so we can later plug in real translation / detection APIs without changing
  the rest of the engine.

v1 is intentionally simple and heuristic-based, but the function signatures
are meant to be future-proof.

Public API:

    LanguageAnalysis (dataclass)
    analyze_text_language(text: str, preferred_lang: str = "en") -> LanguageAnalysis
    analysis_to_dict(analysis: LanguageAnalysis) -> dict
"""

from dataclasses import dataclass, asdict
from typing import List, Dict


@dataclass
class LanguageAnalysis:
    language_code: str          # e.g. "en", "es", "fr"
    confidence: float           # 0.0 - 1.0
    needs_translation: bool     # True if language != preferred_lang
    flagged: bool               # True if content looks risky
    flags: List[str]            # Reasons / tags for the flag


def _simple_detect_language(text: str) -> str:
    """
    Very naive language detection stub.

    This is just a placeholder until we plug in a real model or API.
    Basic rules:
      - If mostly ASCII and contains a lot of common English words -> "en"
      - If contains many non-ASCII characters -> "unknown" (to be safe)
    """
    if not text:
        return "unknown"

    # Count non-ASCII characters
    total_chars = len(text)
    non_ascii = sum(1 for c in text if ord(c) > 127)

    if total_chars == 0:
        return "unknown"

    ratio_non_ascii = non_ascii / total_chars

    # Heuristic: if mostly ASCII, treat as English for now
    if ratio_non_ascii < 0.1:
        return "en"

    # Otherwise we don't guess for now
    return "unknown"


def _simple_flag_content(text: str) -> List[str]:
    """
    Very basic content flagging stub.

    v1 approach:
      - Looks for a small list of generic risky patterns:
        - obvious profanity placeholders
        - threats / violence keywords
        - spammy callouts like "buy now!!!" in all caps

    NOTE: This is intentionally conservative and minimal.
    You can customize this list later or replace this function entirely.
    """
    if not text:
        return []

    lowered = text.lower()
    flags: List[str] = []

    # Tiny placeholder lists (no explicit examples to keep it generic)
    profanity_markers = ["badword"]  # replace with real internal list later
    violence_markers = ["kill", "hurt", "attack"]
    spam_markers = ["buy now", "limited time", "click here"]

    if any(marker in lowered for marker in profanity_markers):
        flags.append("possible_profanity")

    if any(marker in lowered for marker in violence_markers):
        flags.append("possible_violence")

    if any(marker in lowered for marker in spam_markers):
        flags.append("possible_spammy_language")

    # Caps / shouting check (crude)
    if len(text) > 15:
        upper_chars = sum(1 for c in text if c.isupper())
        if upper_chars > 0 and upper_chars / len(text) > 0.4:
            flags.append("too_much_caps_shouting")

    return flags


def analyze_text_language(text: str, preferred_lang: str = "en") -> LanguageAnalysis:
    """
    Main entrypoint.

    Returns a LanguageAnalysis object with:
      - language_code
      - confidence (very rough in v1)
      - needs_translation (True if language != preferred_lang)
      - flagged (True if content looks risky)
      - flags (list of reasons)
    """
    language = _simple_detect_language(text)
    flags = _simple_flag_content(text)

    # Confidence: optimistic if we guessed "en" with ASCII,
    # otherwise low since v1 is basic.
    if language == "en":
        confidence = 0.8
    elif language == "unknown":
        confidence = 0.3
    else:
        confidence = 0.5

    needs_translation = language != preferred_lang and language != "unknown"

    analysis = LanguageAnalysis(
        language_code=language,
        confidence=confidence,
        needs_translation=needs_translation,
        flagged=bool(flags),
        flags=flags,
    )
    return analysis


def analysis_to_dict(analysis: LanguageAnalysis) -> Dict:
    """
    Convert a LanguageAnalysis dataclass to a plain dict, so we can
    safely attach it inside media_kit or other JSON structures.
    """
    return asdict(analysis)