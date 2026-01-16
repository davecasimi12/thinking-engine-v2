# router/kai_creative_v1.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import re
import base64

router = APIRouter(prefix="/kai", tags=["Kai"])


# -------------------------
# Utilities
# -------------------------
def _clean(s: str) -> str:
    return (s or "").strip()


def _platform_defaults(platform: str) -> Dict[str, str]:
    p = (platform or "").lower().strip()
    if p in {"tiktok", "reels", "instagram reels", "youtube shorts"}:
        return {"aspect_ratio": "9:16"}
    if p in {"youtube"}:
        return {"aspect_ratio": "16:9"}
    return {"aspect_ratio": "1:1"}


def _safe_negative_prompt() -> str:
    return (
        "low quality, blurry, pixelated, watermark, signature, logo, brand marks, "
        "too much text, illegible text, clutter, distorted faces, extra fingers, "
        "gore, violence, hate symbols, sexual content"
    )


def _build_prompt(
    platform: str,
    niche: str,
    offer: str,
    audience: str,
    selected_hook: str,
    visual_style: str,
    brand_colors: Optional[List[str]] = None,
    brand_font_hint: str = "",
    include_logo: bool = False,
) -> Dict[str, Any]:
    defaults = _platform_defaults(platform)
    aspect_ratio = defaults["aspect_ratio"]

    hook = _clean(selected_hook) or "A bold, clear headline matching the campaign goal"
    if len(hook) > 72:
        hook = hook[:69].rstrip() + "..."

    color_hint = ""
    if brand_colors:
        color_hint = "Brand colors: " + ", ".join([c for c in brand_colors if _clean(c)]) + "."

    font_hint = f"Typography: {brand_font_hint}." if _clean(brand_font_hint) else ""
    logo_rule = (
        "Logo: include ONLY if user provided a logo in-session. If not provided, do not invent a logo."
        if include_logo
        else "Logo: do not include any logos."
    )

    niche = _clean(niche) or "general niche"
    audience = _clean(audience) or "general audience"
    offer = _clean(offer) or "the offer"
    style = _clean(visual_style) or "clean, high-contrast, premium, readable headline"

    prompt = (
        f"Create a professional social media image for {platform}.\n"
        f"Aspect ratio: {aspect_ratio}.\n"
        f"Niche: {niche}.\n"
        f"Audience: {audience}.\n"
        f"Offer: {offer}.\n"
        f"Visual style: {style}.\n\n"
        f"Headline text (must be readable): {hook}\n\n"
        f"{color_hint}\n{font_hint}\n{logo_rule}\n"
        "Rules: premium design, minimal clutter, readable typography, strong contrast, brand-safe.\n"
        "Output: one high-quality final image."
    ).strip()

    return {
        "prompt": prompt,
        "negative_prompt": _safe_negative_prompt(),
        "aspect_ratio": aspect_ratio,
    }


# -------------------------
# Models
# -------------------------
@router.get("/ping")
def ping():
    return {"status": "ok", "role": "Kai Creative", "mode": "router-online"}


class KaiImageBriefRequest(BaseModel):
    platform: str = Field(default="instagram")
    niche: str = Field(default="")
    offer: str = Field(default="")
    audience: str = Field(default="")
    selected_hook: str = Field(default="")
    visual_style: str = Field(default="")
    brand_colors: List[str] = Field(default_factory=list)
    brand_font_hint: str = Field(default="")
    include_logo: bool = Field(default=False)
    context: Dict[str, Any] = Field(default_factory=dict)


class KaiImageBriefResponse(BaseModel):
    prompt: str
    negative_prompt: str
    aspect_ratio: str


@router.post("/image_brief_v1", response_model=KaiImageBriefResponse)
def image_brief_v1(req: KaiImageBriefRequest):
    out = _build_prompt(
        platform=req.platform,
        niche=req.niche,
        offer=req.offer,
        audience=req.audience,
        selected_hook=req.selected_hook,
        visual_style=req.visual_style,
        brand_colors=req.brand_colors,
        brand_font_hint=req.brand_font_hint,
        include_logo=req.include_logo,
    )
    return KaiImageBriefResponse(
        prompt=out["prompt"],
        negative_prompt=out["negative_prompt"],
        aspect_ratio=out["aspect_ratio"],
    )


# -------------------------
# GENERATION (on-demand only)
# -------------------------
class KaiGenerateImageRequest(KaiImageBriefRequest):
    # optional override: if Bubble already has a prompt, pass it
    prompt_override: str = Field(default="")


class KaiGenerateImageResponse(BaseModel):
    ok: bool
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    provider: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


def _try_generate_with_local_provider(prompt: str, negative_prompt: str, aspect_ratio: str) -> KaiGenerateImageResponse:
    """
    This function tries to call YOUR generator implementation if it exists.
    You plug it in by creating: engine_image_generator.py with a function:
        generate_image(prompt: str, negative_prompt: str, aspect_ratio: str) -> dict
    Return dict can include: {"image_url": "..."} OR {"image_bytes": b"..."} OR {"image_base64": "..."}
    """
    try:
        import engine_image_generator  # you create this file later
    except Exception as e:
        raise HTTPException(
            status_code=501,
            detail=(
                "Kai image generation is not wired yet. "
                "Create engine_image_generator.py with generate_image(prompt, negative_prompt, aspect_ratio). "
                f"Import error: {e}"
            ),
        )

    fn = getattr(engine_image_generator, "generate_image", None)
    if not callable(fn):
        raise HTTPException(
            status_code=501,
            detail="engine_image_generator.generate_image(...) not found. Please implement it.",
        )

    result = fn(prompt=prompt, negative_prompt=negative_prompt, aspect_ratio=aspect_ratio)

    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="generate_image() must return a dict.")

    if result.get("image_url"):
        return KaiGenerateImageResponse(
            ok=True,
            image_url=str(result["image_url"]),
            provider=str(result.get("provider", "local_provider")),
            meta={k: v for k, v in result.items() if k not in {"image_url", "image_bytes", "image_base64"}},
        )

    if result.get("image_base64"):
        return KaiGenerateImageResponse(
            ok=True,
            image_base64=str(result["image_base64"]),
            provider=str(result.get("provider", "local_provider")),
            meta={k: v for k, v in result.items() if k not in {"image_url", "image_bytes", "image_base64"}},
        )

    if result.get("image_bytes"):
        b = result["image_bytes"]
        if isinstance(b, bytes):
            b64 = base64.b64encode(b).decode("utf-8")
            return KaiGenerateImageResponse(
                ok=True,
                image_base64=b64,
                provider=str(result.get("provider", "local_provider")),
                meta={k: v for k, v in result.items() if k not in {"image_url", "image_bytes", "image_base64"}},
            )

    raise HTTPException(status_code=500, detail="generate_image() returned no image_url/image_base64/image_bytes.")


@router.post("/generate_image_v1", response_model=KaiGenerateImageResponse)
def generate_image_v1(req: KaiGenerateImageRequest):
    # Build prompt unless Bubble provides override
    if _clean(req.prompt_override):
        prompt = _clean(req.prompt_override)
        out = _build_prompt(
            platform=req.platform,
            niche=req.niche,
            offer=req.offer,
            audience=req.audience,
            selected_hook=req.selected_hook,
            visual_style=req.visual_style,
            brand_colors=req.brand_colors,
            brand_font_hint=req.brand_font_hint,
            include_logo=req.include_logo,
        )
        negative_prompt = out["negative_prompt"]
        aspect_ratio = out["aspect_ratio"]
    else:
        out = _build_prompt(
            platform=req.platform,
            niche=req.niche,
            offer=req.offer,
            audience=req.audience,
            selected_hook=req.selected_hook,
            visual_style=req.visual_style,
            brand_colors=req.brand_colors,
            brand_font_hint=req.brand_font_hint,
            include_logo=req.include_logo,
        )
        prompt = out["prompt"]
        negative_prompt = out["negative_prompt"]
        aspect_ratio = out["aspect_ratio"]

    # On-demand generation only
    return _try_generate_with_local_provider(prompt, negative_prompt, aspect_ratio)