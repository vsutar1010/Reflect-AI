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

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app import config
from app.database import users_collection
from app.dependencies import get_current_user
from app.schemas import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    SuccessResponse,
    UserResponse,
    VerifyOtpRequest,
    VerifyResetCodeRequest,
)
from app.services import auth_service, email_service
from app.services.rate_limiter import RateLimiter, RateLimitExceeded, client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Signups awaiting email verification, keyed by lowercased email. Mirrors
# the in-memory-pending-state pattern already used throughout this codebase
# (PersonalityAnalyzer.sessions, WhatsAppImportService.pending) — this is
# short-lived (OTP_EXPIRE_MINUTES) state, not data worth persisting.
_pending_signups: dict[str, dict] = {}

# Password resets awaiting code verification, keyed by lowercased email.
# Same shape/lifetime pattern as _pending_signups above — see
# request_password_reset() below.
_pending_resets: dict[str, dict] = {}

# Per-client-IP rate limiters — see app/services/rate_limiter.py.
_login_limiter = RateLimiter(config.AUTH_LOGIN_MAX_ATTEMPTS, config.AUTH_LOGIN_WINDOW_SECONDS)
_otp_request_limiter = RateLimiter(config.AUTH_OTP_REQUEST_MAX_ATTEMPTS, config.AUTH_OTP_REQUEST_WINDOW_SECONDS)
# Reuses the same limits as signup's OTP request limiter — same kind of
# endpoint (sends a real email, cost/spam is the risk being bounded).
_reset_request_limiter = RateLimiter(config.AUTH_OTP_REQUEST_MAX_ATTEMPTS, config.AUTH_OTP_REQUEST_WINDOW_SECONDS)

# A bcrypt hash of a random value nobody knows, hashed once at import
# time. login() always runs one bcrypt verification against *some*
# hash — this one when there's no real password to check against
# (nonexistent email, or an existing Google-only account with no
# password_hash) — so a nonexistent/Google-only/wrong-password account
# all cost the same bcrypt-verify time. Without this, skipping bcrypt
# for the first two cases would make them measurably faster than a
# real wrong-password attempt, letting an attacker distinguish account
# type by response time even after the response body/status were
# unified below.
_DUMMY_PASSWORD_HASH = auth_service.hash_password(secrets.token_urlsafe(32))


def _too_many_requests(message: str, retry_after_seconds: int) -> HTTPException:
    # Retry-After lets a well-behaved client wait the right amount of time
    # instead of guessing or hammering the endpoint again immediately.
    return HTTPException(status_code=429, detail=message, headers={"Retry-After": str(retry_after_seconds)})


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
def request_signup_otp(req: SignupRequest, request: Request):
    key = client_ip(request)
    try:
        with _otp_request_limiter.guard(key):
            # Every call counts here, success or not — this endpoint can
            # trigger a real email, so the thing being rate-limited is
            # request volume/cost, not "failures" the way login's is.
            _otp_request_limiter.record_event(key)

            email = req.email.lower().strip()
            name = req.name.strip()

            # The response below is identical — status, body, and (via the
            # dummy hash_password() call in the branch that skips a real
            # send) roughly the same cost — no matter which of these is
            # true, so an attacker calling this endpoint can never learn
            # which one happened. Only the real recipient, via their own
            # inbox (or the lack of a code arriving), ever finds out.
            account_exists = users_collection.find_one({"email": email}, {"_id": 1}) is not None
            pending = _pending_signups.get(email)
            resend_on_cooldown = bool(
                pending
                and datetime.now() < pending["created_at"] + timedelta(seconds=config.OTP_RESEND_COOLDOWN_SECONDS)
            )

            if account_exists or resend_on_cooldown:
                # Don't send a duplicate code, and don't send a signup code
                # to an address that's already registered — but still pay
                # the same bcrypt-hash and SMTP-connect costs the real path
                # below pays (the SMTP round trip is the dominant one — well
                # over a second against a real provider), so this branch
                # isn't measurably faster than it.
                auth_service.hash_password(req.password)
                email_service.touch_smtp_connection()
            else:
                otp = f"{secrets.randbelow(1_000_000):06d}"
                now = datetime.now()
                _pending_signups[email] = {
                    "name": name,
                    "email": email,
                    "password_hash": auth_service.hash_password(req.password),
                    "otp": otp,
                    "expires_at": now + timedelta(minutes=config.OTP_EXPIRE_MINUTES),
                    "attempts": 0,
                    "created_at": now,
                }
                try:
                    email_service.send_otp_email(email, name, otp)
                except RuntimeError as e:
                    # Don't surface this as a different status/body either —
                    # that would itself be a distinguishing signal. Log it
                    # server-side and let the response stay generic.
                    del _pending_signups[email]
                    print(f"[auth] signup OTP email failed to send: {e}")

            return SuccessResponse(
                success=True,
                message="If this email can be used to sign up, a verification code has been sent.",
            )
    except RateLimitExceeded as e:
        raise _too_many_requests(
            "Too many verification code requests. Please try again later.", e.retry_after_seconds
        )


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


@router.post("/forgot-password/request", response_model=SuccessResponse)
def request_password_reset(req: ForgotPasswordRequest, request: Request):
    """
    Step 1 of the reset flow, and also what "Resend code" calls again.
    Mirrors request_signup_otp()'s account-enumeration protections
    exactly: identical response, and identical timing cost (a real SMTP
    connect either way), regardless of whether the email is registered,
    is a Google-only account with no password to reset, or a resend is
    still on cooldown.
    """
    key = client_ip(request)
    try:
        with _reset_request_limiter.guard(key):
            _reset_request_limiter.record_event(key)

            email = req.email.lower().strip()
            user_doc = users_collection.find_one({"email": email})
            pending = _pending_resets.get(email)
            resend_on_cooldown = bool(
                pending
                and datetime.now() < pending["created_at"] + timedelta(seconds=config.OTP_RESEND_COOLDOWN_SECONDS)
            )

            # Only an account with a real password has anything to reset
            # here — a Google-only account (password_hash is None) signs
            # in via Google, not a password, so there's nothing to send.
            can_send = user_doc is not None and bool(user_doc.get("password_hash")) and not resend_on_cooldown

            if can_send:
                otp = f"{secrets.randbelow(1_000_000):06d}"
                now = datetime.now()
                _pending_resets[email] = {
                    "user_id": user_doc["_id"],
                    "otp": otp,
                    "expires_at": now + timedelta(minutes=config.OTP_EXPIRE_MINUTES),
                    "attempts": 0,
                    "created_at": now,
                }
                try:
                    email_service.send_password_reset_email(email, user_doc.get("name", ""), otp)
                except RuntimeError as e:
                    del _pending_resets[email]
                    print(f"[auth] password reset email failed to send: {e}")
            else:
                email_service.touch_smtp_connection()

            return SuccessResponse(
                success=True,
                message="If this email is registered, a password reset code has been sent.",
            )
    except RateLimitExceeded as e:
        raise _too_many_requests(
            "Too many password reset requests. Please try again later.", e.retry_after_seconds
        )


def _check_reset_code(email: str, otp: str) -> dict:
    """
    Shared validation for both /forgot-password/verify (a non-consuming
    pre-check, so the frontend can move to the next step before asking
    for a new password) and /forgot-password/reset (which re-validates
    the same way — never trusts that verify was actually called first).
    Both share one attempt counter per pending reset, so the combined
    guess budget across the two endpoints is still capped at
    OTP_MAX_ATTEMPTS. Raises HTTPException on any invalid/expired/
    exhausted case; returns the pending record on success.
    """
    pending = _pending_resets.get(email)

    if not pending or datetime.now() > pending["expires_at"]:
        _pending_resets.pop(email, None)
        raise HTTPException(status_code=400, detail="No pending reset for this email — request a new code.")

    pending["attempts"] += 1
    if pending["attempts"] > config.OTP_MAX_ATTEMPTS:
        del _pending_resets[email]
        raise HTTPException(status_code=400, detail="Too many incorrect attempts — request a new code.")

    if otp != pending["otp"]:
        raise HTTPException(status_code=400, detail="Incorrect code.")

    return pending


@router.post("/forgot-password/verify", response_model=SuccessResponse)
def verify_password_reset_code(req: VerifyResetCodeRequest):
    """
    Step 2: lets the frontend confirm the code before showing the new-
    password fields. Deliberately does NOT consume/delete the pending
    reset — the code is only actually invalidated once the password is
    changed (see reset_password below), so a user who verifies
    successfully but then closes the tab can still use the same code
    again within its expiry window instead of it being silently burned
    here.
    """
    email = req.email.lower().strip()
    _check_reset_code(email, req.otp)
    return SuccessResponse(success=True, message="Code verified. You can now set a new password.")


@router.post("/forgot-password/reset", response_model=SuccessResponse)
def reset_password(req: ResetPasswordRequest):
    """
    Step 3: re-validates the code (never trusts that /verify was called
    first — this is the only endpoint that actually changes anything)
    and, on success, hashes the new password with the same bcrypt
    mechanism every other account uses and overwrites password_hash.
    The code is deleted the moment it's confirmed valid, before the
    password write — a single successful reset always consumes it, so
    it can never be replayed.
    """
    email = req.email.lower().strip()
    pending = _check_reset_code(email, req.otp)

    del _pending_resets[email]

    new_hash = auth_service.hash_password(req.new_password)
    result = users_collection.update_one({"_id": pending["user_id"]}, {"$set": {"password_hash": new_hash}})
    if result.matched_count == 0:
        # Extremely unlikely (the account would have to have been
        # deleted mid-flow) — generic message, no account-existence
        # detail leaked.
        raise HTTPException(status_code=400, detail="Could not reset password — request a new code.")

    return SuccessResponse(success=True, message="Password changed successfully.")


@router.post("/login", response_model=UserResponse)
def login(req: LoginRequest, request: Request, response: Response):
    key = client_ip(request)
    try:
        with _login_limiter.guard(key):
            email = req.email.lower().strip()
            user_doc = users_collection.find_one({"email": email})

            # Same response — status, body, and (via the dummy-hash bcrypt
            # verify above) roughly the same timing — whether the email
            # doesn't exist, belongs to a Google-only account, or is a
            # real password account with the wrong password. An attacker
            # must not be able to tell these apart from the outside;
            # only the account owner, via the account itself, ever
            # learns which one it was.
            password_hash = (user_doc or {}).get("password_hash") or _DUMMY_PASSWORD_HASH
            password_ok = auth_service.verify_password(req.password, password_hash)

            if not user_doc or not user_doc.get("password_hash") or not password_ok:
                _login_limiter.record_failure(key)
                raise HTTPException(status_code=401, detail="Invalid email or password.")

            # Successful login — any earlier failed attempts from this
            # client no longer count against them.
            _login_limiter.reset(key)
            _set_session_cookie(response, user_doc["_id"])
            return _user_response(user_doc)
    except RateLimitExceeded as e:
        raise _too_many_requests("Too many login attempts. Please try again later.", e.retry_after_seconds)


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
