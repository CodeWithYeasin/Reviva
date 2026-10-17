"""
Privacy + security helpers.

Design goal: the server is a pass-through. A file exists only for the lifetime of
one request, in a RAM-backed temp dir when available, and is wiped immediately
after the response is produced. Nothing is logged that could identify content.
"""
import os
import shutil
import tempfile
import contextlib
from typing import Iterable

from fastapi import HTTPException, UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from . import config


# ---- Magic-byte signatures: don't trust the Content-Type header alone ----
_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # followed by WEBP, checked below
}


def _sniff_is_image(head: bytes) -> bool:
    if head.startswith(b"\xff\xd8\xff"):
        return True
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return True
    return False


def _sniff_is_video(head: bytes) -> bool:
    # mp4 / mov share the ftyp box; webm starts with the EBML header 0x1A45DFA3
    if head[4:8] == b"ftyp":
        return True
    if head.startswith(b"\x1aE\xdf\xa3"):
        return True
    return False


async def read_validated(
    upload: UploadFile,
    allowed_types: set,
    max_bytes: int,
    kind: str,
) -> bytes:
    """Read an upload fully into memory, enforcing type + size. Returns raw bytes."""
    if upload.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail=f"Unsupported {kind} type.")

    data = await upload.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"{kind.capitalize()} too large.")

    head = data[:16]
    ok = _sniff_is_image(head) if kind == "image" else _sniff_is_video(head)
    if not ok:
        # Header said one thing, bytes said another -> reject.
        raise HTTPException(status_code=415, detail=f"File is not a valid {kind}.")

    return data


@contextlib.contextmanager
def ephemeral_dir():
    """A temp directory that is guaranteed to be shredded on exit."""
    base = config.WORK_DIR
    if base:
        os.makedirs(base, exist_ok=True)
    path = tempfile.mkdtemp(prefix="reviva_", dir=base)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def shred(paths: Iterable[str]) -> None:
    for p in paths:
        with contextlib.suppress(Exception):
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                os.remove(p)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds strict headers. No content ever reaches logs from here."""

    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Tell proxies/CDNs never to cache a user's image/video result.
        response.headers["Cache-Control"] = "no-store, max-age=0"
        return response
