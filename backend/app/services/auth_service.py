"""
Password hashing, session JWTs, and Google ID token verification.

Kept as one small stateless module (no DB access here) — routers/auth.py
owns looking users up and deciding what to do with the results.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict

import bcrypt
import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app import config


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(days=config.JWT_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expires_at}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Returns the user id encoded in `token`, or None if missing/expired/invalid."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")


class GoogleIdentity(TypedDict):
    sub: str
    email: str
    name: str


def verify_google_id_token(credential: str) -> GoogleIdentity:
    """
    Verifies a Google Identity Services ID token (the `credential` the
    frontend's Google Sign-In button hands back) and returns the claims we
    care about. Raises ValueError on anything invalid/expired/wrong-audience.
    """
    if not config.GOOGLE_CLIENT_ID:
        raise ValueError("Google Sign-In is not configured on this server.")

    try:
        claims = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), config.GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        raise ValueError(f"Invalid Google credential: {e}") from e

    return {
        "sub": claims["sub"],
        "email": claims.get("email", ""),
        "name": claims.get("name") or claims.get("email", "").split("@")[0],
    }
