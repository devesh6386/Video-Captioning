"""
gemini_service.py

Calls Gemini 2.5 Flash with sampled video frames to produce a structured JSON
response containing video understanding metadata and all 4 caption styles
in a single API call.

Uses the responseSchema feature to guarantee structured JSON output.
Includes exponential backoff retry on 429/5xx.
"""

import base64
import json
import logging
import os
import re
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("TOP_P", "0.8"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))

# Retry config
MAX_ATTEMPTS = 4
INITIAL_DELAY = 2.0
RATE_LIMIT_DELAY = 30.0
REQUEST_TIMEOUT = 60.0

RETRYABLE_CODES = frozenset({429, 500, 502, 503, 504})

# Camera motion allowed values
CAMERA_MOTION_VALUES = "static | pan | tilt | zoom | tracking | handheld | unknown"

# Caption styles
STYLES = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]

# Response schema for structured JSON output
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "video_understanding": {
            "type": "object",
            "properties": {
                "main_action": {"type": "string"},
                "subjects": {"type": "array", "items": {"type": "string"}},
                "objects": {"type": "array", "items": {"type": "string"}},
                "setting": {"type": "string"},
                "background": {"type": "string"},
                "apparent_emotion": {"type": "string"},
                "camera_motion": {"type": "string"},
                "visible_text": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": [
                "main_action", "subjects", "objects", "setting",
                "background", "apparent_emotion", "camera_motion",
                "visible_text", "summary",
            ],
        },
        "captions": {
            "type": "object",
            "properties": {
                "formal": {"type": "string"},
                "sarcastic": {"type": "string"},
                "humorous_tech": {"type": "string"},
                "humorous_non_tech": {"type": "string"},
            },
            "required": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
        },
    },
    "required": ["video_understanding", "captions"],
}


def _build_prompt(styles: list[str]) -> str:
    """Build the unified Gemini prompt for video analysis + caption generation."""
    return (
        "You are an expert video analyst and factual caption writer. "
        "Analyze the provided video frames chronologically and produce "
        "a structured JSON response. "
        "This analysis must work for any domain — sports, food, tech, nature, etc.\n\n"

        "STRICT OBSERVATION RULES:\n"
        "• Only describe what is directly visible in the frames.\n"
        "• Never invent details, objects, people, actions, or settings.\n"
        "• Never infer intentions or internal thoughts.\n"
        "• If any element is uncertain, describe it as \"unknown\".\n\n"

        f"For camera_motion, return exactly one of: {CAMERA_MOTION_VALUES}.\n"
        "For apparent_emotion, describe ONLY visible facial expressions or body language.\n\n"

        "CAPTION RULES (apply to ALL styles):\n"
        "• Each caption MUST be exactly ONE sentence.\n"
        "• Raw caption text ONLY. No markdown, quotes, bullets, emojis, numbering.\n"
        "• Every caption must mention at least one visible object or action.\n"
        "• ALL captions describe the SAME scene. Only tone differs.\n\n"

        "PER-STYLE RULES:\n"
        "• formal: Objective, factual. 12–16 words, max 18. Professional tone.\n"
        "• sarcastic: Witty, dry sarcasm. Max 16 words. No offensive jokes.\n"
        "• humorous_tech: Use a software engineering metaphor tied to a visible object. Max 16 words.\n"
        "• humorous_non_tech: Relatable everyday humor tied to a visible object. No tech references. Max 16 words.\n\n"

        "Return ONLY a valid JSON object matching the required schema."
    )


def _encode_frame(path: str) -> dict[str, Any] | None:
    """Read a JPEG frame and encode it as Gemini inlineData."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("utf-8")
        return {"inlineData": {"mimeType": "image/jpeg", "data": b64}}
    except OSError as exc:
        logger.error(f"Could not read frame file {path}: {exc}")
        return None


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json … ``` fences that Gemini sometimes emits."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_text(data: dict) -> str:
    """Extract text from Gemini response envelope."""
    try:
        candidates = data.get("candidates") or []
        if not candidates:
            raise KeyError("candidates list is empty")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        if not parts:
            raise KeyError("parts list is empty")
        return parts[0].get("text", "")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {exc}") from exc


def _validate_and_patch(parsed: dict, styles: list[str]) -> dict:
    """Ensure all required keys exist with safe defaults."""
    # Captions
    if not isinstance(parsed.get("captions"), dict):
        parsed["captions"] = {}
    for style in styles:
        if not isinstance(parsed["captions"].get(style), str):
            parsed["captions"][style] = ""

    # Video understanding
    defaults = {
        "main_action": "unknown", "subjects": [], "objects": [],
        "setting": "unknown", "background": "unknown",
        "apparent_emotion": "unknown", "camera_motion": "unknown",
        "visible_text": "none", "summary": "",
    }
    if not isinstance(parsed.get("video_understanding"), dict):
        parsed["video_understanding"] = dict(defaults)
    else:
        vu = parsed["video_understanding"]
        if "apparent_emotion" not in vu:
            vu["apparent_emotion"] = str(vu.pop("emotion", "unknown"))
        for key, default in defaults.items():
            if key not in vu:
                vu[key] = default
        allowed_cam = {"static", "pan", "tilt", "zoom", "tracking", "handheld", "unknown"}
        if vu.get("camera_motion", "unknown") not in allowed_cam:
            vu["camera_motion"] = "unknown"

    return parsed


def generate_captions(frame_paths: list[str], styles: list[str] | None = None) -> dict:
    """
    Call Gemini to analyze frames and generate all requested captions
    in a single API call using responseSchema for structured output.
    
    Args:
        frame_paths: List of paths to JPEG frame files
        styles: Caption styles to generate (default: all 4 styles)
    
    Returns:
        Dict with 'captions' and 'video_understanding' keys
    
    Raises:
        ValueError: If GEMINI_API_KEY is not set or no frames provided
        RuntimeError: If Gemini API fails after all retries
    """
    if styles is None:
        styles = STYLES

    if not GEMINI_API_KEY:
        error_msg = "GEMINI_API_KEY environment variable is not set"
        logger.error(f"✗ {error_msg}")
        raise ValueError(error_msg)

    if not frame_paths:
        logger.warning("No frame paths provided")
        return {"captions": {s: "" for s in styles}, "video_understanding": {}}

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    headers = {"Content-Type": "application/json"}

    # Build parts
    parts: list[dict] = [{"text": _build_prompt(styles)}]
    encoded_count = 0
    for path in frame_paths:
        part = _encode_frame(path)
        if part:
            parts.append(part)
            encoded_count += 1

    if encoded_count == 0:
        error_msg = "Could not encode any frames for Gemini"
        logger.error(f"✗ {error_msg}")
        raise ValueError(error_msg)

    logger.info(f"📤 Sending {encoded_count} frames to Gemini ({GEMINI_MODEL})")

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            "temperature": TEMPERATURE,
            "topP": TOP_P,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }

    # Retry loop
    delay = INITIAL_DELAY
    last_error = None
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logger.debug(f"Gemini API call attempt {attempt}/{MAX_ATTEMPTS}...")
            response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                raw_text = _extract_text(data)
                cleaned = _strip_markdown_fences(raw_text)
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    result = _validate_and_patch(parsed, styles)
                    logger.info(f"✓ Gemini succeeded with {len(parsed.get('captions', {}))} styles")
                    return result
                raise ValueError("Gemini returned non-dict JSON")

            if response.status_code in RETRYABLE_CODES and attempt < MAX_ATTEMPTS:
                wait = delay
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else RATE_LIMIT_DELAY
                    logger.warning(f"⏳ Rate limited (429). Waiting {wait:.0f}s before retry...")
                else:
                    logger.warning(f"⏳ Server error (HTTP {response.status_code}). Retry {attempt + 1}/{MAX_ATTEMPTS} in {wait:.1f}s...")
                time.sleep(wait)
                delay *= 2.0
                continue

            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.error(f"✗ Gemini API error: {error_msg}")
            response.raise_for_status()

        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                logger.warning(f"⏳ Connection error (attempt {attempt}/{MAX_ATTEMPTS}): {str(exc)[:100]}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2.0
            else:
                error_msg = f"Network error after {MAX_ATTEMPTS} attempts: {exc}"
                logger.error(f"✗ {error_msg}")
                raise RuntimeError(error_msg) from exc
        except json.JSONDecodeError as exc:
            last_error = exc
            logger.error(f"✗ Failed to parse Gemini response: {exc}")
            raise RuntimeError(f"Invalid JSON from Gemini: {exc}") from exc
        except Exception as exc:
            last_error = exc
            logger.error(f"✗ Unexpected error: {exc}", exc_info=True)
            raise

    error_msg = f"Gemini API failed after {MAX_ATTEMPTS} attempts"
    if last_error:
        error_msg += f": {last_error}"
    logger.error(f"✗ {error_msg}")
    raise RuntimeError(error_msg)
