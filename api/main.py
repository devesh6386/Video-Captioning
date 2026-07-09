"""
main.py

FastAPI backend for the AI Video Caption Generator.

Endpoints:
  POST /api/caption  — Upload a video, extract frames, call Gemini, return captions.
  GET  /api/health   — Readiness check.

Environment Variables:
  GEMINI_API_KEY     — API key for Gemini
  GEMINI_MODEL       — Model name (default: gemini-2.5-flash)
  FRAME_COUNT        — Number of frames to extract (default: 5)
  CORS_ORIGINS       — Comma-separated list of allowed CORS origins (default: localhost origins)
  ENVIRONMENT        — Deployment environment: development, staging, production (default: development)
"""

import json
import logging
import os
import tempfile
from datetime import datetime

import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from frame_extractor import extract_frames
from gemini_service import generate_captions

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CaptionAI API",
    description="AI-powered multi-style video caption generator",
    version="1.0.0",
)

# ── CORS Configuration ──────────────────────────────────────────────────────
# Parse CORS origins from environment or use defaults
def get_allowed_origins():
    """Get allowed CORS origins from environment or use sensible defaults."""
    cors_env = os.getenv("CORS_ORIGINS", "")
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    # Default origins based on environment
    if environment == "production":
        # Production: Allow Vercel deployment and common domains
        default_origins = [
            "https://video-captioning.vercel.app",
            "https://video-captioning-two.vercel.app",  # Your actual Vercel domain
            "https://captionai.example.com",
        ]
    elif environment == "staging":
        default_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]
    else:  # development
        default_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]
    
    # If explicitly set, use those
    if cors_env.strip():
        explicit_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
        logger.info(f"Using explicit CORS origins from environment: {explicit_origins}")
        return explicit_origins
    
    logger.info(f"Using default CORS origins for {environment}: {default_origins}")
    return default_origins

allowed_origins = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS configured for origins: {allowed_origins}")

# Config
FRAME_COUNT = int(os.getenv("FRAME_COUNT", "5"))
MAX_UPLOAD_MB = 100
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "outputs")
STYLES = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]


@app.get("/api/health")
async def health():
    """
    Readiness check endpoint.
    
    Returns diagnostic information about the backend:
    - status: ok/error
    - model: Gemini model being used
    - environment: deployment environment
    - timestamp: server time
    - api_key_configured: whether GEMINI_API_KEY is set (not the actual key)
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    has_api_key = bool(api_key and len(api_key) > 4)
    
    return {
        "status": "ok",
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.utcnow().isoformat(),
        "api_key_configured": has_api_key,
        "cors_origins": allowed_origins,
    }


@app.post("/api/caption")
async def caption_video(video: UploadFile = File(...)):
    """
    Upload a video file, extract frames, call Gemini for multi-style
    caption generation, save results, and return JSON.
    
    Request:
      - video: video file (multipart/form-data)
    
    Response:
      {
        "captions": {
          "formal": "...",
          "sarcastic": "...",
          "humorous_tech": "...",
          "humorous_non_tech": "..."
        },
        "video_understanding": {...},
        "filename": "...",
        "timestamp": "..."
      }
    
    Errors:
      - 400: Unsupported video format
      - 413: File too large
      - 500: Processing failed (Gemini call, frame extraction, etc.)
    """
    logger.info(f"Received caption request for: {video.filename}")
    
    # ── Validate file type ────────────────────────────────────────────
    allowed_types = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
    if video.content_type and video.content_type not in allowed_types:
        logger.warning(f"Rejected unsupported format: {video.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format: {video.content_type}. Accepted: MP4, WebM, MOV.",
        )

    # ── Save uploaded file to temp location using aiofiles ────────────
    suffix = ".mp4"
    if video.filename:
        _, ext = os.path.splitext(video.filename)
        if ext:
            suffix = ext

    video_path = None
    frame_paths: list[str] = []

    try:
        # Write upload to temp file asynchronously (non-blocking)
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        video_path = tmp.name
        tmp.close()

        total_bytes = 0
        async with aiofiles.open(video_path, "wb") as f:
            while True:
                chunk = await video.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    logger.error(f"Upload rejected: {total_bytes / 1024 / 1024:.1f}MB exceeds limit")
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_UPLOAD_MB}MB.",
                    )
                await f.write(chunk)

        logger.info(f"✓ Uploaded {total_bytes / 1024 / 1024:.1f}MB to {video_path}")

        # ── Extract frames (runs in thread pool) ─────────────────────
        logger.info(f"⏳ Extracting {FRAME_COUNT} frames...")
        frame_paths = await extract_frames(video_path, n=FRAME_COUNT)
        logger.info(f"✓ Extracted {len(frame_paths)} frame(s)")

        # ── Call Gemini for captions ──────────────────────────────────
        logger.info("⏳ Calling Gemini for caption generation...")
        result = generate_captions(frame_paths, styles=STYLES)

        captions = result.get("captions", {})
        video_understanding = result.get("video_understanding", {})
        
        logger.info(f"✓ Gemini response received with {len(captions)} styles")

        # ── Save to results.json ─────────────────────────────────────
        try:
            os.makedirs(RESULTS_DIR, exist_ok=True)
            results_path = os.path.join(RESULTS_DIR, "results.json")

            result_entry = {
                "task_id": video.filename or "web_upload",
                "captions": captions,
                "video_understanding": video_understanding,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Append to or create results file
            existing = []
            if os.path.exists(results_path):
                try:
                    with open(results_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not read existing results.json: {e}")
                    existing = []

            existing.append(result_entry)

            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ Results saved to {results_path}")
        except Exception as save_err:
            logger.warning(f"Failed to save results.json: {save_err}")

        # ── Return to frontend ───────────────────────────────────────
        response = {
            "captions": captions,
            "video_understanding": video_understanding,
            "filename": video.filename,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info(f"✓ Returning response for {video.filename}")
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"✗ Caption generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Processing failed: {str(exc)}"
        )

    finally:
        # ── Cleanup temp files ───────────────────────────────────────
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                logger.debug(f"Cleaned up temp video: {video_path}")
            except OSError as e:
                logger.warning(f"Failed to cleanup video: {e}")
        for fp in frame_paths:
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                except OSError as e:
                    logger.warning(f"Failed to cleanup frame: {e}")
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_UPLOAD_MB}MB.",
                    )
                await f.write(chunk)

        logger.info(f"Uploaded {total_bytes / 1024 / 1024:.1f}MB to {video_path}")

        # ── Extract frames (runs in thread pool) ─────────────────────
        logger.info(f"Extracting {FRAME_COUNT} frames...")
        frame_paths = await extract_frames(video_path, n=FRAME_COUNT)
        logger.info(f"Extracted {len(frame_paths)} frame(s)")

        # ── Call Gemini for captions ──────────────────────────────────
        logger.info("Calling Gemini for caption generation...")
        result = generate_captions(frame_paths, styles=STYLES)

        captions = result.get("captions", {})
        video_understanding = result.get("video_understanding", {})

        # ── Save to results.json ─────────────────────────────────────
        try:
            os.makedirs(RESULTS_DIR, exist_ok=True)
            results_path = os.path.join(RESULTS_DIR, "results.json")

            result_entry = {
                "task_id": video.filename or "web_upload",
                "captions": captions,
                "video_understanding": video_understanding,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Append to or create results file
            existing = []
            if os.path.exists(results_path):
                try:
                    with open(results_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, IOError):
                    existing = []

            existing.append(result_entry)

            with open(results_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)

            logger.info(f"Results saved to {results_path}")
        except Exception as save_err:
            logger.warning(f"Failed to save results.json: {save_err}")

        # ── Return to frontend ───────────────────────────────────────
        return {
            "captions": captions,
            "video_understanding": video_understanding,
            "filename": video.filename,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Caption generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    finally:
        # ── Cleanup temp files ───────────────────────────────────────
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass
        for fp in frame_paths:
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                except OSError:
                    pass
