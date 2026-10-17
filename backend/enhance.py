"""
Photo enhancement pipeline.

- Real-ESRGAN  -> general super-resolution / upscaling (whole image)
- GFPGAN       -> face restoration (fixes blurry / degraded faces)

Models are loaded lazily and cached, so the first request is slow and the
rest are fast. Weights download automatically on first use into ./weights.
"""
import os
import cv2
import numpy as np

from . import compat, config

# Must run before basicsr / realesrgan / gfpgan are imported anywhere.
compat.patch_torchvision_functional_tensor()

# Where downloaded model weights land. Override with REVIVA_WEIGHTS_DIR on
# hosts where the app directory is read-only (most free PaaS containers).
_WEIGHTS_DIR = os.getenv(
    "REVIVA_WEIGHTS_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "weights"),
)
try:
    os.makedirs(_WEIGHTS_DIR, exist_ok=True)
except OSError:
    # Read-only filesystem: fall back to a temp dir so import still succeeds.
    import tempfile

    _WEIGHTS_DIR = os.path.join(tempfile.gettempdir(), "reviva-weights")
    os.makedirs(_WEIGHTS_DIR, exist_ok=True)

_upsampler = None
_face_enhancer = None


def _pick_device() -> bool:
    """Return True if CUDA should be used."""
    if config.USE_GPU == "0":
        return False
    if config.USE_GPU == "1":
        return True
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def _get_upsampler():
    global _upsampler
    if _upsampler is not None:
        return _upsampler

    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet

    use_gpu = _pick_device()
    model = RRDBNet(
        num_in_ch=3, num_out_ch=3, num_feat=64,
        num_block=23, num_grow_ch=32, scale=4,
    )
    _upsampler = RealESRGANer(
        scale=4,
        model_path="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        model=model,
        tile=400,          # tiling keeps VRAM bounded on big images
        tile_pad=10,
        pre_pad=0,
        half=use_gpu,      # fp16 only helps on GPU
        gpu_id=0 if use_gpu else None,
    )
    return _upsampler


def _get_face_enhancer():
    global _face_enhancer
    if _face_enhancer is not None:
        return _face_enhancer

    from gfpgan import GFPGANer

    _face_enhancer = GFPGANer(
        model_path="https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth",
        upscale=config.UPSCALE,
        arch="clean",
        channel_multiplier=2,
        bg_upsampler=_get_upsampler(),
    )
    return _face_enhancer


def enhance_image_bytes(data: bytes, restore_faces: bool = True) -> bytes:
    """
    Take raw image bytes, return enhanced PNG bytes.
    Pure in-memory: nothing is written to disk.
    """
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")

    if restore_faces:
        enhancer = _get_face_enhancer()
        # GFPGAN returns (cropped_faces, restored_faces, restored_whole_image)
        _, _, output = enhancer.enhance(
            img, has_aligned=False, only_center_face=False, paste_back=True
        )
    else:
        upsampler = _get_upsampler()
        output, _ = upsampler.enhance(img, outscale=config.UPSCALE)

    ok, buf = cv2.imencode(".png", output)
    if not ok:
        raise ValueError("Could not encode result.")
    return buf.tobytes()


def enhance_frame(img: np.ndarray, restore_faces: bool) -> np.ndarray:
    """Enhance a single decoded video frame (BGR ndarray)."""
    if restore_faces:
        enhancer = _get_face_enhancer()
        _, _, output = enhancer.enhance(
            img, has_aligned=False, only_center_face=False, paste_back=True
        )
        return output
    upsampler = _get_upsampler()
    output, _ = upsampler.enhance(img, outscale=config.UPSCALE)
    return output
