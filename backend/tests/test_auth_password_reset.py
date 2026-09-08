"""
Integration tests for the forgot-password flow (POST /api/auth/forgot-
password/request|verify|reset), against the real FastAPI app and the
real MongoDB Atlas `users` collection — but using a throwaway test user
created/deleted by this file, and with the real email send stubbed out
(captured instead) so tests never actually send mail or depend on
reading an inbox.

Does not touch the RAG collections/tests at all.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import users_collection
from app.main import app
from app.services import auth_service, email_service
import app.routers.auth as auth_router

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_auth_state(monkeypatch):
    """Every test gets a clean slate: no leftover pending resets, and a
    rate limiter that won't have been exhausted by a previous test (all
    requests from TestClient appear to come from the same synthetic
    client, so a shared limiter would otherwise leak across tests)."""
    auth_router._pending_resets.clear()
    auth_router._reset_request_limiter._state.clear()
    auth_router._reset_request_limiter._locks.clear()
    yield
    auth_router._pending_resets.clear()


@pytest.fixture
def sent_emails(monkeypatch):
    """Stubs the real SMTP send so tests never actually deliver mail —
    captures (to_email, name, otp) tuples instead."""
    captured = []

    def fake_send(to_email, name, otp):
        captured.append((to_email, name, otp))

    monkeypatch.setattr(email_service, "send_password_reset_email", fake_send)
    monkeypatch.setattr(email_service, "touch_smtp_connection", lambda: None)
    return captured


@pytest.fixture
def test_user():
    """A throwaway password-auth user in the REAL users collection,
    deleted after the test regardless of outcome."""
    user_id = str(uuid.uuid4())
    email = f"pwreset-test-{uuid.uuid4().hex[:8]}@example.com"
    original_password = "OriginalPass123!"
    users_collection.insert_one(
        {
            "_id": user_id,
            "email": email,
            "name": "Reset Test User",
            "password_hash": auth_service.hash_password(original_password),
            "created_at": "2026-01-01T00:00:00",
        }
    )
    try:
        yield {"id": user_id, "email": email, "password": original_password}
    finally:
        users_collection.delete_one({"_id": user_id})


@pytest.fixture
def google_only_user():
    """A Google-sign-in-only account (no password_hash) — forgot-password
    must not send a code for this, since there's no password to reset."""
    user_id = str(uuid.uuid4())
    email = f"pwreset-google-{uuid.uuid4().hex[:8]}@example.com"
    users_collection.insert_one(
        {
            "_id": user_id,
            "email": email,
            "name": "Google Only User",
            "password_hash": None,
            "google_sub": f"sub-{uuid.uuid4().hex[:8]}",
            "created_at": "2026-01-01T00:00:00",
        }
    )
    try:
        yield {"id": user_id, "email": email}
    finally:
        users_collection.delete_one({"_id": user_id})


# ============================================================
# /forgot-password/request
# ============================================================

def test_request_reset_sends_code_for_real_account(test_user, sent_emails):
    res = client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert len(sent_emails) == 1
    assert sent_emails[0][0] == test_user["email"]
    assert len(sent_emails[0][2]) == 6 and sent_emails[0][2].isdigit()


def test_request_reset_same_response_for_unknown_email(sent_emails):
    res = client.post("/api/auth/forgot-password/request", json={"email": "nobody-here@example.com"})
    assert res.status_code == 200
    assert res.json()["message"] == "If this email is registered, a password reset code has been sent."
    assert len(sent_emails) == 0  # nothing actually sent, but response is identical to the real-account case


def test_request_reset_response_identical_for_known_and_unknown_email(test_user, sent_emails):
    res_known = client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    res_unknown = client.post("/api/auth/forgot-password/request", json={"email": "still-nobody@example.com"})
    assert res_known.status_code == res_unknown.status_code == 200
    assert res_known.json() == res_unknown.json()


def test_request_reset_does_not_send_for_google_only_account(google_only_user, sent_emails):
    res = client.post("/api/auth/forgot-password/request", json={"email": google_only_user["email"]})
    assert res.status_code == 200
    assert len(sent_emails) == 0


def test_request_reset_rejects_malformed_email(sent_emails):
    res = client.post("/api/auth/forgot-password/request", json={"email": "not-an-email"})
    assert res.status_code == 422  # pydantic EmailStr validation
    assert len(sent_emails) == 0


def test_request_reset_resend_cooldown_does_not_send_second_email(test_user, sent_emails):
    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    assert len(sent_emails) == 1  # second call was inside the resend cooldown


# ============================================================
# /forgot-password/verify
# ============================================================

def test_verify_correct_code_succeeds(test_user, sent_emails):
    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    otp = sent_emails[0][2]

    res = client.post("/api/auth/forgot-password/verify", json={"email": test_user["email"], "otp": otp})
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_verify_incorrect_code_fails(test_user, sent_emails):
    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})

    res = client.post("/api/auth/forgot-password/verify", json={"email": test_user["email"], "otp": "000000"})
    assert res.status_code == 400
    assert "incorrect" in res.json()["detail"].lower()


def test_verify_with_no_pending_reset_fails(sent_emails):
    res = client.post("/api/auth/forgot-password/verify", json={"email": "never-requested@example.com", "otp": "123456"})
    assert res.status_code == 400
    assert "no pending reset" in res.json()["detail"].lower()


def test_verify_does_not_consume_code_can_verify_twice(test_user, sent_emails):
    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    otp = sent_emails[0][2]

    res1 = client.post("/api/auth/forgot-password/verify", json={"email": test_user["email"], "otp": otp})
    res2 = client.post("/api/auth/forgot-password/verify", json={"email": test_user["email"], "otp": otp})
    assert res1.status_code == 200
    assert res2.status_code == 200  # verify is a non-consuming pre-check


def test_verify_exhausts_after_max_attempts(test_user, sent_emails):
    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})

    from app import config

    last_res = None
    for _ in range(config.OTP_MAX_ATTEMPTS + 1):
        last_res = client.post("/api/auth/forgot-password/verify", json={"email": test_user["email"], "otp": "000000"})

    assert last_res.status_code == 400
    assert "too many" in last_res.json()["detail"].lower()

    # Even the CORRECT code is now rejected — the pending reset was deleted.
    otp = sent_emails[0][2]
    res = client.post("/api/auth/forgot-password/verify", json={"email": test_user["email"], "otp": otp})
    assert res.status_code == 400


# ============================================================
# /forgot-password/reset — the full happy path + security properties
# ============================================================

def test_full_reset_flow_changes_password(test_user, sent_emails):
    new_password = "BrandNewPass456!"

    res_request = client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    assert res_request.status_code == 200
    otp = sent_emails[0][2]

    res_verify = client.post("/api/auth/forgot-password/verify", json={"email": test_user["email"], "otp": otp})
    assert res_verify.status_code == 200

    res_reset = client.post(
        "/api/auth/forgot-password/reset",
        json={"email": test_user["email"], "otp": otp, "new_password": new_password},
    )
    assert res_reset.status_code == 200
    assert res_reset.json()["message"] == "Password changed successfully."

    # Old password no longer works, new password does.
    old_login = client.post("/api/auth/login", json={"email": test_user["email"], "password": test_user["password"]})
    assert old_login.status_code == 401

    new_login = client.post("/api/auth/login", json={"email": test_user["email"], "password": new_password})
    assert new_login.status_code == 200

    # The stored hash is bcrypt, never the plaintext password.
    doc = users_collection.find_one({"_id": test_user["id"]})
    assert doc["password_hash"] != new_password
    assert doc["password_hash"].startswith("$2")  # bcrypt hash prefix


def test_reset_code_cannot_be_reused(test_user, sent_emails):
    new_password = "FirstReset789!"
    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    otp = sent_emails[0][2]

    first = client.post(
        "/api/auth/forgot-password/reset",
        json={"email": test_user["email"], "otp": otp, "new_password": new_password},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/auth/forgot-password/reset",
        json={"email": test_user["email"], "otp": otp, "new_password": "SomethingElse999!"},
    )
    assert second.status_code == 400


def test_reset_rejects_expired_code(test_user, sent_emails):
    from datetime import datetime, timedelta

    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    otp = sent_emails[0][2]

    # Force-expire the pending reset instead of sleeping in a test.
    auth_router._pending_resets[test_user["email"]]["expires_at"] = datetime.now() - timedelta(seconds=1)

    res = client.post(
        "/api/auth/forgot-password/reset",
        json={"email": test_user["email"], "otp": otp, "new_password": "WontWork1234!"},
    )
    assert res.status_code == 400
    assert "no pending reset" in res.json()["detail"].lower()


def test_reset_rejects_password_under_minimum_length(test_user, sent_emails):
    client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    otp = sent_emails[0][2]

    res = client.post(
        "/api/auth/forgot-password/reset",
        json={"email": test_user["email"], "otp": otp, "new_password": "short"},
    )
    assert res.status_code == 422  # pydantic min_length=8


def test_reset_response_never_contains_the_code(test_user, sent_emails):
    res_request = client.post("/api/auth/forgot-password/request", json={"email": test_user["email"]})
    otp = sent_emails[0][2]
    assert otp not in res_request.text

    res_verify = client.post("/api/auth/forgot-password/verify", json={"email": test_user["email"], "otp": otp})
    assert otp not in res_verify.text

    res_reset = client.post(
        "/api/auth/forgot-password/reset",
        json={"email": test_user["email"], "otp": otp, "new_password": "FinalPass000!"},
    )
    assert otp not in res_reset.text
