"""Image generation service using Google Gemini 2.5 Flash native image generation.

Calls the Generative Language API to produce images alongside text answers.
Non-blocking: returns None on any failure so the text answer is never affected.
"""

import logging
import os
from dataclasses import dataclass

import httpx

from cortexbrain.models.schemas import GeneratedImage

logger = logging.getLogger(__name__)

# Action verbs that indicate image creation intent
_ACTION_WORDS = {"generate", "create", "make", "draw", "show", "produce", "render"}

# Nouns that indicate visual output
_VISUAL_NOUNS = {
    "image", "images", "picture", "pictures", "diagram", "diagrams",
    "visual", "visuals", "visualisation", "visualization",
    "infographic", "infographics", "illustration", "illustrations",
    "chart", "graph", "flowchart", "photo",
}

# Standalone phrases that always trigger image generation
_STANDALONE_TRIGGERS = ("visualize", "visualise", "draw me", "show me")

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def should_generate_image(query: str) -> bool:
    """Check if the user's query is requesting image generation.

    Uses word-level matching so 'generate the image' and 'generate an image'
    both match, not just exact phrases.
    """
    q = query.lower()

    # Check standalone triggers first
    if any(trigger in q for trigger in _STANDALONE_TRIGGERS):
        return True

    # Word-level: check if any action word + any visual noun both appear
    words = set(q.split())
    has_action = bool(words & _ACTION_WORDS)
    has_visual = bool(words & _VISUAL_NOUNS)

    return has_action and has_visual


@dataclass
class ImageAnswerResult:
    """Combined text + image from a single gemini-2.5-flash-image call."""
    text: str
    image: GeneratedImage | None


async def generate_image_answer(
    prompt: str,
    context: str = "",
    model: str = "gemini-2.5-flash-image",
) -> ImageAnswerResult | None:
    """Generate both a text answer and an image in a single API call.

    Uses gemini-2.5-flash-image which natively returns text + image parts.

    Args:
        prompt: The user's query.
        context: Optional knowledge base context to include.
        model: Gemini model name (default: gemini-2.5-flash-image).

    Returns:
        ImageAnswerResult with text and image, or None on failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        logger.warning("Image generation skipped: no GEMINI_API_KEY or LLM_API_KEY configured")
        return None

    url = f"{_GEMINI_API_BASE}/{model}:generateContent"

    # Build the user message — include KB context if available
    if context:
        user_text = (
            f"Context from knowledge base:\n{context}\n\n"
            f"Question: {prompt}\n\n"
            "Provide a thorough text answer AND generate a relevant image."
        )
    else:
        user_text = (
            f"{prompt}\n\n"
            "Provide a thorough text answer AND generate a relevant image."
        )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": user_text},
                ],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            logger.warning("Image answer returned no candidates")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])

        # Extract text and image from response parts
        text_parts: list[str] = []
        image: GeneratedImage | None = None

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "inlineData" in part:
                inline_data = part["inlineData"]
                if inline_data.get("data") and image is None:
                    image = GeneratedImage(
                        b64_data=inline_data["data"],
                        content_type=inline_data.get("mimeType", "image/png"),
                        prompt=prompt,
                    )

        text = "\n".join(text_parts).strip()
        if not text and not image:
            logger.warning("Image answer returned neither text nor image")
            return None

        return ImageAnswerResult(text=text or "", image=image)

    except httpx.HTTPStatusError as e:
        logger.warning("Image answer API error %s: %s", e.response.status_code, e.response.text[:200])
        return None
    except Exception as e:
        logger.warning("Image answer failed: %s", e)
        return None
