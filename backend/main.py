"""
Reviva — AI photo & video enhancer.

Privacy model:
  upload -> enhance in a RAM-backed temp dir -> stream result back -> shred.
  No database. No accounts. No content logging. Nothing persists after the
  response is sent.
"""
import io
import os

from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.background import BackgroundTask

from . import config, security
from .enhance import enhance_image_bytes

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Reviva", docs_url=None, redoc_url=None)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(security.SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

_FRONTEND = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "dist"
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/enhance/photo")
@limiter.limit(config.RATE_LIMIT_PHOTO)
async def enhance_photo(
    request: Request,
    file: UploadFile = File(...),
    restore_faces: bool = Form(True),
):
    data = await security.read_validated(
        file, config.ALLOWED_IMAGE_TYPES, config.MAX_IMAGE_BYTES, "image"
    )
    try:
        result = enhance_image_bytes(data, restore_faces=restore_faces)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Stream from memory; nothing touched the disk.
    return StreamingResponse(
        io.BytesIO(result),
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="reviva.png"'},
    )


@app.post("/api/enhance/video")
@limiter.limit(config.RATE_LIMIT_VIDEO)
async def enhance_video_endpoint(
    request: Request,
    file: UploadFile = File(...),
    restore_faces: bool = Form(True),
):
    # Import here so the photo path works even on boxes without ffmpeg installed.
    from .video import enhance_video

    data = await security.read_validated(
        file, config.ALLOWED_VIDEO_TYPES, config.MAX_VIDEO_BYTES, "video"
    )

    work = security.ephemeral_dir().__enter__()  # noqa: we manage teardown via BackgroundTask
    try:
        in_path = os.path.join(work, "input")
        with open(in_path, "wb") as f:
            f.write(data)

        out_path = enhance_video(in_path, work, restore_faces=restore_faces)
    except ValueError as e:
        security.shred([work])
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        security.shred([work])
        raise HTTPException(status_code=500, detail="Enhancement failed.")

    # Shred the whole ephemeral dir only AFTER the file finishes streaming.
    return FileResponse(
        out_path,
        media_type="video/mp4",
        filename="reviva.mp4",
        background=BackgroundTask(security.shred, [work]),
    )


# Serve the built frontend last so API routes win.
# `frontend/dist` only exists after `npm run build` — guard so the API still
# boots (e.g. when running the Vite dev server separately on :5173).
if os.path.isdir(_FRONTEND):
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
else:
    @app.get("/")
    async def _no_build():
        return {
            "detail": "Frontend not built yet. Run `cd frontend && npm install && npm run build`, "
                      "or use the Vite dev server (`npm run dev`) on http://localhost:5173."
        }
