"""
Video enhancement.

Strategy: decode -> enhance every frame with the same models used for photos
-> re-mux with the original audio. All intermediate frames live in an ephemeral
RAM dir and are shredded when the request ends.

Kept deliberately simple and capped (see config) because per-frame enhancement
is heavy. For long/high-res video you'd move to a queue + worker; that's noted
in the README roadmap.
"""
import os
import subprocess
import cv2

from . import config
from .enhance import enhance_frame


def _probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def enhance_video(in_path: str, work_dir: str, restore_faces: bool = True) -> str:
    """
    Enhance the video at in_path. Returns the path to the enhanced mp4
    (inside work_dir). Raises ValueError if the clip violates safety caps.
    """
    duration = _probe_duration(in_path)
    if duration <= 0:
        raise ValueError("Could not read the video.")
    if duration > config.MAX_VIDEO_SECONDS:
        raise ValueError(
            f"Clip is {duration:.0f}s; max allowed is {config.MAX_VIDEO_SECONDS}s."
        )

    cap = cv2.VideoCapture(in_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0

    frames_dir = os.path.join(work_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    idx = 0
    out_size = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Downscale oversized frames before the (expensive) enhance step.
        h, w = frame.shape[:2]
        if w > config.MAX_VIDEO_WIDTH:
            scale = config.MAX_VIDEO_WIDTH / w
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

        out = enhance_frame(frame, restore_faces)
        if out_size is None:
            out_size = (out.shape[1], out.shape[0])
        cv2.imwrite(os.path.join(frames_dir, f"f_{idx:06d}.png"), out)
        idx += 1

    cap.release()
    if idx == 0:
        raise ValueError("No frames could be read from the video.")

    silent = os.path.join(work_dir, "silent.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(fps),
         "-i", os.path.join(frames_dir, "f_%06d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", silent],
        check=True, capture_output=True,
    )

    # Mux the original audio back in (ignored silently if the source had none).
    final = os.path.join(work_dir, "enhanced.mp4")
    mux = subprocess.run(
        ["ffmpeg", "-y", "-i", silent, "-i", in_path,
         "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0?",
         "-shortest", final],
        capture_output=True,
    )
    if mux.returncode != 0 or not os.path.exists(final):
        # Fall back to the silent version if muxing failed.
        return silent
    return final
