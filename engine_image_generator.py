# engine_image_generator.py
"""
Kai Image Generator Provider (stub)

Purpose:
- Satisfy Kai router imports (no more Pylance missing import error)
- Provide a single function: generate_image(...)
- Later we can swap this stub to a real provider (Replicate / Stability / OpenAI / Local SD)

IMPORTANT:
- This file does NOT generate images yet.
- It returns a clear, safe response shape so your API doesn't crash.
"""

from __future__ import annotations

from typing import Any, Dict


def generate_image(prompt: str, negative_prompt: str = "", aspect_ratio: str = "1:1") -> Dict[str, Any]:
    """
    Expected return keys (one of these):
      - {"image_url": "...", "provider": "..."}
      - {"image_base64": "...", "provider": "..."}
      - {"image_bytes": b"...", "provider": "..."}
    """

    # Stub mode — no real provider connected yet
    # This keeps everything stable and prevents runtime crashes.
    return {
        "provider": "stub",
        "error": "No image provider wired yet. Replace engine_image_generator.generate_image() with a real generator call.",
        "prompt_used": prompt,
        "negative_prompt_used": negative_prompt,
        "aspect_ratio_used": aspect_ratio,
    }