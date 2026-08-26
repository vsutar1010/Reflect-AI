"""
Auth API — signup (email OTP verified) / login (email+password and Google),
logout, and "who am I".

All three sign-in routes (verify-otp/login/google) set the same httpOnly
session cookie on success; every other router in the app depends on
app.dependencies.get_current_user to read it back and scope data to that
user.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response

from app import config
from app.database import users_collection
from app.dependencies import get_current_user
from app.schemas import (
    GoogleAuthRequest,
    LoginRequest,
    SignupRequest,
    SuccessResponse,
    UserResponse,
    VerifyOtpRequest,
)
from app.services import auth_service, email_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Signups awaiting email verification, keyed by lowercased email. Mirrors
# the in-memory-pending-state pattern already used throughout this codebase
# (PersonalityAnalyzer.sessions, WhatsAppImportService.pending) — this is
# short-lived (OTP_EXPIRE_MINUTES) state, not data worth persisting.
_pending_signups: dict[str, dict] = {}


def _set_session_cookie(response: Response, user_id: str) -> None:
    token = auth_service.create_access_token(user_id)
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=config.JWT_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


def _user_response(doc: dict) -> UserResponse:
    return UserResponse(id=doc["_id"], email=doc["email"], name=doc.get("name", ""))


@router.post("/signup/request-otp", response_model=SuccessResponse)
def request_signup_otp(req: SignupRequest):
    email = req.email.lower().strip()

    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    existing = _pending_signups.get(email)
    if existing and datetime.now() < existing["created_at"] + timedelta(seconds=config.OTP_RESEND_COOLDOWN_SECONDS):
        raise HTTPException(status_code=400, detail="Please wait a bit before requesting another code.")

    otp = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now()
    _pending_signups[email] = {
        "name": req.name.strip(),
        "email": email,
        "password_hash": auth_service.hash_password(req.password),
        "otp": otp,
        "expires_at": now + timedelta(minutes=config.OTP_EXPIRE_MINUTES),
        "attempts": 0,
        "created_at": now,
    }

    try:
        email_service.send_otp_email(email, req.name.strip(), otp)
    except RuntimeError as e:
        del _pending_signups[email]
        raise HTTPException(status_code=503, detail=str(e))

    return SuccessResponse(success=True, message=f"Verification code sent to {email}.")


@router.post("/signup/verify-otp", response_model=UserResponse)
def verify_signup_otp(req: VerifyOtpRequest, response: Response):
    email = req.email.lower().strip()
    pending = _pending_signups.get(email)

    if not pending or datetime.now() > pending["expires_at"]:
        _pending_signups.pop(email, None)
        raise HTTPException(status_code=400, detail="No pending signup for this email — request a new code.")

    pending["attempts"] += 1
    if pending["attempts"] > config.OTP_MAX_ATTEMPTS:
        del _pending_signups[email]
        raise HTTPException(status_code=400, detail="Too many incorrect attempts — request a new code.")

    if req.otp != pending["otp"]:
        raise HTTPException(status_code=400, detail="Incorrect code.")

    del _pending_signups[email]

    user_doc = {
        "_id": str(uuid.uuid4()),
        "email": email,
        "name": pending["name"],
        "password_hash": pending["password_hash"],
        # No `google_sub` key at all (not even null) — the sparse unique
        # index on that field only excludes documents where it's absent;
        # an explicit null on every password account would still collide.
        "created_at": datetime.now().isoformat(),
    }
    users_collection.insert_one(user_doc)

    _set_session_cookie(response, user_doc["_id"])
    return _user_response(user_doc)


@router.post("/login", response_model=UserResponse)
def login(req: LoginRequest, response: Response):
    email = req.email.lower().strip()
    user_doc = users_collection.find_one({"email": email})

    if not user_doc or not user_doc.get("password_hash"):
        detail = (
            "This account uses Google Sign-In — use the Google button instead."
            if user_doc
            else "Invalid email or password."
        )
        raise HTTPException(status_code=400 if user_doc else 401, detail=detail)

    if not auth_service.verify_password(req.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    _set_session_cookie(response, user_doc["_id"])
    return _user_response(user_doc)


@router.post("/google", response_model=UserResponse)
def login_with_google(req: GoogleAuthRequest, response: Response):
    try:
        identity = auth_service.verify_google_id_token(req.credential)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    email = identity["email"].lower().strip()
    user_doc = users_collection.find_one({"google_sub": identity["sub"]})

    if not user_doc:
        # Link to an existing password account with the same email instead
        # of creating a duplicate user.
        user_doc = users_collection.find_one({"email": email})
        if user_doc:
            users_collection.update_one({"_id": user_doc["_id"]}, {"$set": {"google_sub": identity["sub"]}})
        else:
            user_doc = {
                "_id": str(uuid.uuid4()),
                "email": email,
                "name": identity["name"],
                "password_hash": None,
                "google_sub": identity["sub"],
                "created_at": datetime.now().isoformat(),
            }
            users_collection.insert_one(user_doc)

    _set_session_cookie(response, user_doc["_id"])
    return _user_response(user_doc)


@router.post("/logout", response_model=SuccessResponse)
def logout(response: Response):
    response.delete_cookie(key=config.SESSION_COOKIE_NAME, path="/")
    return SuccessResponse(success=True, message="Logged out.")


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)
