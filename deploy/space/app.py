"""
Reviva entrypoint for Hugging Face Spaces (free CPU tier).

Why this file exists
--------------------
Docker Spaces now require a paid plan, so the free route is the Gradio SDK.
A Gradio Space simply runs `python app.py`, which means we can still serve the
real Reviva app — React UI and FastAPI endpoints — and keep a small Gradio UI
alongside it:

    /           the built React UI            (web/)
    /api/...    the FastAPI endpoints         (backend/main.py)
    /gradio     a minimal Gradio fallback UI  (also gives a free auto API)
    /health     liveness probe

Mount order matters: the React UI is a catch-all mount at "/", so it has to go
on last — hence REVIVA_SKIP_FRONTEND_MOUNT below.
"""
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

# ---- Space-specific defaults (override them in Space Settings > Variables) --
# /dev/shm is only 64 MB inside the container, so keep scratch space in /tmp.
os.environ.setdefault("REVIVA_WORK_DIR", os.path.join(tempfile.gettempdir(), "reviva"))
os.environ.setdefault("REVIVA_WEIGHTS_DIR", os.path.join(_HERE, "weights"))
os.environ.setdefault("REVIVA_USE_GPU", "0")          # free tier is CPU-only
os.environ.setdefault("UPSCALE", "2")                 # 4x is far too slow on CPU
os.environ.setdefault("MAX_VIDEO_SECONDS", "3")       # per-frame enhance on CPU
os.environ.setdefault("MAX_VIDEO_BYTES", str(12 * 1024 * 1024))
os.environ.setdefault("RATE_LIMIT_PHOTO", "6/minute")
os.environ.setdefault("RATE_LIMIT_VIDEO", "1/minute")
# We mount the React build ourselves, after Gradio.
os.environ["REVIVA_SKIP_FRONTEND_MOUNT"] = "1"

import gradio as gr  # noqa: E402
import uvicorn  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from backend.main import app as api  # noqa: E402
from backend.enhance import enhance_image_bytes  # noqa: E402

_WEB = os.getenv("REVIVA_FRONTEND_DIR") or os.path.join(_HERE, "web")


def _enhance(image_path: str, restore_faces: bool) -> str:
    """Gradio handler: path in, path out (Gradio manages its own temp files)."""
    if not image_path:
        raise gr.Error("Upload a photo first.")
    with open(image_path, "rb") as fh:
        data = fh.read()
    result = enhance_image_bytes(data, restore_faces=restore_faces)
    out_path = os.path.join(tempfile.mkdtemp(prefix="reviva_gr_"), "reviva.png")
    with open(out_path, "wb") as fh:
        fh.write(result)
    return out_path


with gr.Blocks(title="Reviva", analytics_enabled=False) as demo:
    gr.Markdown(
        "## Reviva - AI photo enhancer\n"
        "Real-ESRGAN upscaling + GFPGAN face restoration. Nothing is stored: "
        "your upload is processed in memory and discarded.\n\n"
        "*Running on free CPU hardware - the first photo also downloads the "
        "model weights, so give it a minute.*"
    )
    with gr.Row():
        src = gr.Image(type="filepath", label="Original", sources=["upload"])
        dst = gr.Image(label="Enhanced", format="png")
    faces = gr.Checkbox(value=True, label="Restore faces (GFPGAN)")
    gr.Button("Enhance", variant="primary").click(
        _enhance, inputs=[src, faces], outputs=dst
    )

app = gr.mount_gradio_app(api, demo, path="/gradio")

# React UI last: it is a catch-all mount.
if os.path.isdir(_WEB):
    app.mount("/", StaticFiles(directory=_WEB, html=True), name="frontend")
else:
    @app.get("/")
    async def _no_build():
        return {"detail": "React build missing - open /gradio instead."}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("GRADIO_SERVER_PORT", os.getenv("PORT", "7860"))),
    )
