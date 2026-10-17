"""
Dependency compatibility shims.

basicsr 1.4.2 (pulled in by both realesrgan and gfpgan) imports
`torchvision.transforms.functional_tensor`, a private module that was removed
in torchvision >= 0.17. Without a shim, importing the models fails with:

    ModuleNotFoundError: No module named 'torchvision.transforms.functional_tensor'

Rather than vendoring a patched basicsr or pinning an ancient torchvision, we
register a tiny stand-in module *before* basicsr is ever imported.
"""
import sys
import types


def patch_torchvision_functional_tensor() -> None:
    """Make `torchvision.transforms.functional_tensor` importable again."""
    name = "torchvision.transforms.functional_tensor"

    if name in sys.modules:
        return

    try:
        # Old torchvision: the real module still exists, nothing to do.
        __import__(name)
        return
    except Exception:
        pass

    try:
        import torchvision.transforms.functional as F
    except Exception:
        # No torchvision at all — let the real import error surface later.
        return

    shim = types.ModuleType(name)
    for attr in (
        "rgb_to_grayscale",
        "normalize",
        "resize",
        "rotate",
        "crop",
        "center_crop",
        "hflip",
        "vflip",
        "adjust_brightness",
        "adjust_contrast",
        "adjust_saturation",
        "adjust_hue",
    ):
        if hasattr(F, attr):
            setattr(shim, attr, getattr(F, attr))

    sys.modules[name] = shim
