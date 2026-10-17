"""
Reviva entrypoint for Hugging Face Spaces (free ZeroGPU tier).

Why this file exists
--------------------
Docker Spaces need a paid plan and free accounts cannot downgrade a Space to
cpu-basic, so the free route is a Gradio-SDK Space on ZeroGPU.

ZeroGPU rules that shape this file:
  * a GPU only exists inside a function decorated with @spaces.GPU;
  * that decorated function must be the one registered as a Gradio event
    handler, otherwise startup fails with "No @spaces.GPU function detected".

So `enhance_photo` below is both the Gradio handler and the single place any
enhancement happens - the REST endpoint is routed through it too.

    /           the built React UI            (web/)
    /api/...    the FastAPI endpoints         (backend/main.py)
    /gradio     the Gradio UI                 (also a free auto-generated API)
    /health     liveness probe

Mount order matters: the React UI is a catch-all mount at "/", so it has to go
on last - hence REVIVA_SKIP_FRONTEND_MOUNT below.
"""
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

# ---- Space defaults (override them in Space Settings > Variables) ----------
# /dev/shm is only 64 MB inside the container, so keep scratch space in /tmp.
os.environ.setdefault("REVIVA_WORK_DIR", os.path.join(tempfile.gettempdir(), "reviva"))
os.environ.setdefault("REVIVA_WEIGHTS_DIR", os.path.join(_HERE, "weights"))
# "auto" is important: CUDA only exists inside a @spaces.GPU call, so the
# device has to be decided per call, not once at import.
os.environ.setdefault("REVIVA_USE_GPU", "auto")
os.environ.setdefault("UPSCALE", "2")
os.environ.setdefault("RATE_LIMIT_PHOTO", "6/minute")
# We mount the React build ourselves, after Gradio.
os.environ["REVIVA_SKIP_FRONTEND_MOUNT"] = "1"

import gradio as gr  # noqa: E402
import spaces  # noqa: E402
import uvicorn  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

import backend.main as backend_main  # noqa: E402
import backend.video as backend_video  # noqa: E402
from backend.main import app as api  # noqa: E402

_WEB = os.getenv("REVIVA_FRONTEND_DIR") or os.path.join(_HERE, "web")


@spaces.GPU(duration=120)
def enhance_photo(image_path: str, restore_faces: bool = True) -> str:
    """The Gradio handler AND the only place a GPU exists.

    Models load lazily on the first call, which happens inside the GPU
    context, so they land on CUDA.
    """
    if not image_path:
        raise gr.Error("Upload a photo first.")

    from backend.enhance import enhance_image_bytes

    with open(image_path, "rb") as fh:
        data = fh.read()
    result = enhance_image_bytes(data, restore_faces=restore_faces)

    out_path = os.path.join(tempfile.mkdtemp(prefix="reviva_out_"), "reviva.png")
    with open(out_path, "wb") as fh:
        fh.write(result)
    return out_path


def _api_enhance_bytes(data: bytes, restore_faces: bool = True) -> bytes:
    """Bytes-in/bytes-out shim so /api/enhance/photo uses the same GPU call."""
    work = tempfile.mkdtemp(prefix="reviva_api_")
    src = os.path.join(work, "input")
    with open(src, "wb") as fh:
        fh.write(data)
    out_path = enhance_photo(src, restore_faces)
    with open(out_path, "rb") as fh:
        return fh.read()


def _video_unavailable(*_args, **_kwargs):
    raise ValueError(
        "Video enhancement is disabled on this free Space: per-frame "
        "enhancement would exhaust the daily GPU quota in one clip. "
        "Run Reviva locally for video - github.com/CodeWithYeasin/Reviva"
    )


backend_main.enhance_image_bytes = _api_enhance_bytes
backend_video.enhance_video = _video_unavailable


with gr.Blocks(title="Reviva", analytics_enabled=False) as demo:
    gr.Markdown(
        "## Reviva - AI photo enhancer\n"
        "Real-ESRGAN upscaling + GFPGAN face restoration. Nothing is stored: "
        "your upload is processed in memory and discarded.\n\n"
        "*The first photo also downloads the model weights, so give it a "
        "minute. Video is local-only - see the repo.*"
    )
    with gr.Row():
        src = gr.Image(type="filepath", label="Original", sources=["upload"])
        dst = gr.Image(label="Enhanced", format="png")
    faces = gr.Checkbox(value=True, label="Restore faces (GFPGAN)")
    gr.Button("Enhance", variant="primary").click(
        enhance_photo, inputs=[src, faces], outputs=dst
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
