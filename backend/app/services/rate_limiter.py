"""
Lightweight in-memory rate limiter for authentication endpoints.

Storage: a plain in-memory dict, matching every other piece of
short-lived server state already in this codebase (PersonalityAnalyzer
.sessions, WhatsAppImportService.pending, TextChatService.sessions,
auth.py's own _pending_signups). This app runs as a single uvicorn
process with no Redis or other shared store anywhere — so an in-memory
structure is the right-sized tool here, not an added dependency. If
this backend is ever horizontally scaled to multiple processes/
instances, this state would need to move to a shared store (e.g.
Redis) since each process would otherwise track its own separate
counters; noted here so that isn't a surprise later.

Algorithm: a fixed window per key — a key gets up to `max_events`
countable events (e.g. failed login attempts) within `window_seconds`
of the first one; once the window elapses with no further check, it
resets. Simple and easy to reason about, matching what was asked for.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Optional, Tuple


class RateLimitExceeded(Exception):
    """Raised by RateLimiter.guard() when `key` is currently blocked."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded — retry after {retry_after_seconds}s")


class RateLimiter:
    """
    Usage (see app/routers/auth.py):

        try:
            with limiter.guard(key):
                ... do the protected work ...
                if it_failed:
                    limiter.record_failure(key)
                else:
                    limiter.reset(key)
        except RateLimitExceeded as e:
            ... return 429, e.retry_after_seconds ...

    `guard(key)` raises immediately (before the `with` body runs) if
    `key` is already blocked, so a blocked client never reaches the
    expensive part of the request (a DB lookup + bcrypt check, in
    login's case).

    Concurrency: one re-entrant lock per key, not a single global lock.
    FastAPI dispatches these routes (plain `def`, not `async def`) to a
    real thread pool, so concurrent requests can genuinely race on a
    plain dict read-modify-write — but the lock only needs to be held
    per-key, since only requests sharing the *same* key (the same
    client) can race against each other's counter. Different keys never
    wait on each other, so this adds no contention for unrelated
    traffic. It's an RLock (not a plain Lock) because record_failure()/
    reset() are called from inside the same thread's `with guard(key):`
    block and need to re-acquire the lock they're already holding.
    """

    def __init__(self, max_events: int, window_seconds: int):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._state: Dict[str, Tuple[int, datetime]] = {}
        self._locks: Dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    def _lock_for(self, key: str) -> threading.RLock:
        with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.RLock()
                self._locks[key] = lock
            return lock

    def _seconds_until_allowed(self, key: str) -> Optional[int]:
        entry = self._state.get(key)
        if entry is None:
            return None
        count, window_start = entry
        elapsed = (datetime.now() - window_start).total_seconds()
        if elapsed >= self.window_seconds:
            del self._state[key]
            return None
        if count >= self.max_events:
            return max(1, int(self.window_seconds - elapsed))
        return None

    @contextmanager
    def guard(self, key: str):
        lock = self._lock_for(key)
        with lock:
            retry_after = self._seconds_until_allowed(key)
            if retry_after is not None:
                raise RateLimitExceeded(retry_after)
            yield

    def record_failure(self, key: str) -> None:
        """Counts one failed attempt for `key`. Must be called from
        inside an active `with guard(key):` block."""
        with self._lock_for(key):
            now = datetime.now()
            entry = self._state.get(key)
            if entry is None or (now - entry[1]).total_seconds() >= self.window_seconds:
                self._state[key] = (1, now)
            else:
                count, window_start = entry
                self._state[key] = (count + 1, window_start)

    # Same behavior as record_failure() — separate name for endpoints
    # where every call counts (e.g. sending an OTP email), not just
    # failures, so a call site reads correctly either way.
    record_event = record_failure

    def reset(self, key: str) -> None:
        """Clears any tracked events for `key` — call on success so a
        legitimate login right after some failed attempts is never
        blocked by them. Must be called from inside an active
        `with guard(key):` block."""
        with self._lock_for(key):
            self._state.pop(key, None)


def client_ip(request) -> str:
    """
    The rate-limit key: the raw TCP peer address Starlette/uvicorn saw
    for this connection (`request.client.host`) — never a client-
    supplied header. This app runs uvicorn directly with no reverse
    proxy trust configured anywhere in this codebase (no
    `--proxy-headers`/`--forwarded-allow-ips`, no ProxyHeadersMiddleware
    — see backend/run.py and app/main.py), so an `X-Forwarded-For`-style
    header is not validated or stripped by anything in front of this
    process; trusting it here would let any client simply set it to
    bypass the limiter. If this app is later deployed behind a real
    reverse proxy, uvicorn's own trusted-proxy support should be
    configured explicitly first — this should not be switched to trust
    a forwarded header without that.
    """
    if request.client is None:
        return "unknown"
    return request.client.host
