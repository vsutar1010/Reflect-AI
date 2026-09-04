"""
ASGI middleware for request-level protections that don't belong in any
single router.
"""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class MaxUploadSizeMiddleware:
    """
    Rejects a request to `path` outright, based on its declared
    Content-Length, before Starlette starts reading/parsing the request
    body at all — for a multipart file upload, that parsing step writes
    incoming bytes straight to a temp file (spooled through ~1MB of RAM,
    then to disk) with no size limit of its own, so without this an
    oversized upload would already be sitting on disk before the route
    handler's own (authoritative) size check ever runs.

    This is a fast, best-effort first line of defense, not the
    authoritative check — Content-Length can be absent or wrong (e.g. a
    lying or chunked-transfer client). The route handler must still
    verify the actual bytes it reads regardless of what this allows
    through. Scoped to a single `path` so no other endpoint is affected.
    """

    def __init__(self, app: ASGIApp, path: str, max_bytes: int, max_mb: int):
        self.app = app
        self.path = path
        self.max_bytes = max_bytes
        self.max_mb = max_mb

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"] == self.path:
            content_length = Headers(scope=scope).get("content-length")
            if content_length is not None:
                try:
                    declared_size = int(content_length)
                except ValueError:
                    declared_size = None
                if declared_size is not None and declared_size > self.max_bytes:
                    response = JSONResponse(
                        {
                            "detail": (
                                f"WhatsApp export is too large. Maximum allowed size is {self.max_mb} MB."
                            )
                        },
                        status_code=413,
                    )
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)
