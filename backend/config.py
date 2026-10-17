"""
Central configuration. Everything privacy/security sensitive is tuned here.
All limits are intentionally conservative — raise them only if your GPU can take it.
"""
import os

# ---- Upload limits (bytes) ----
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", 15 * 1024 * 1024))   # 15 MB
MAX_VIDEO_BYTES = int(os.getenv("MAX_VIDEO_BYTES", 60 * 1024 * 1024))   # 60 MB

# ---- Allowed input types ----
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}

# ---- Video safety caps (keep processing time + memory sane) ----
MAX_VIDEO_SECONDS = int(os.getenv("MAX_VIDEO_SECONDS", 15))   # reject clips longer than this
MAX_VIDEO_WIDTH = int(os.getenv("MAX_VIDEO_WIDTH", 1280))     # downscale wider inputs before enhance

# ---- Upscale factor ----
UPSCALE = int(os.getenv("UPSCALE", 2))   # 2x is a good balance; 4x is heavy

# ---- Rate limiting (per client IP) ----
RATE_LIMIT_PHOTO = os.getenv("RATE_LIMIT_PHOTO", "20/minute")
RATE_LIMIT_VIDEO = os.getenv("RATE_LIMIT_VIDEO", "4/minute")

# ---- CORS ----
# Lock this to your real domain in production, e.g. ["https://reviva.example.com"].
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ---- Where temp files live during a single request.
# They are deleted the instant the response is sent. Point this at a tmpfs
# (RAM-backed, e.g. /dev/shm) for true no-disk processing.
WORK_DIR = os.getenv("REVIVA_WORK_DIR", "/dev/shm/reviva" if os.path.isdir("/dev/shm") else None)

# ---- Device ----
USE_GPU = os.getenv("REVIVA_USE_GPU", "auto")   # "auto" | "1" | "0"
