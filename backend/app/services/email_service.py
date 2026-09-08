"""
Sends the signup OTP email over SMTP (Gmail by default — see
backend/.env.example for the App Password setup).

Kept as one small function with no state — app/routers/auth.py owns
generating/storing/expiring the OTP itself, this module only knows how to
deliver one.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app import config


def _connect() -> smtplib.SMTP:
    """Opens an authenticated SMTP connection. Raises RuntimeError if SMTP
    isn't configured. Shared by send_otp_email() and touch_smtp_connection()
    so both pay the exact same connect/TLS/auth cost."""
    if not config.smtp_configured():
        raise RuntimeError(
            "Email sign-up isn't configured on this server yet — SMTP_USERNAME/"
            "SMTP_PASSWORD are missing from backend/.env. See backend/.env.example "
            "for how to generate a Gmail App Password."
        )

    smtp = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10)
    smtp.starttls()
    smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
    return smtp


def send_otp_email(to_email: str, name: str, otp: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Your ReflectAI verification code"
    message["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USERNAME}>"
    message["To"] = to_email
    message.set_content(
        f"Hi {name},\n\n"
        f"Your ReflectAI verification code is: {otp}\n\n"
        f"This code expires in {config.OTP_EXPIRE_MINUTES} minutes. "
        "If you didn't request this, you can ignore this email.\n"
    )

    with _connect() as smtp:
        smtp.send_message(message)


def send_password_reset_email(to_email: str, name: str, otp: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Your ReflectAI password reset code"
    message["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USERNAME}>"
    message["To"] = to_email
    greeting = f"Hi {name}," if name else "Hi,"
    message.set_content(
        f"{greeting}\n\n"
        f"Your ReflectAI password reset code is: {otp}\n\n"
        f"This code expires in {config.OTP_EXPIRE_MINUTES} minutes. "
        "If you didn't request this, you can safely ignore this email — "
        "your password won't be changed.\n"
    )

    with _connect() as smtp:
        smtp.send_message(message)


def touch_smtp_connection() -> None:
    """
    Opens and immediately closes an authenticated SMTP connection without
    sending anything — pays the same connect/TLS/auth latency
    send_otp_email() pays (typically the dominant cost, well over a
    second against a real mail provider), without delivering a message.

    Used by POST /api/auth/signup/request-otp when it deliberately skips
    a real send (an already-registered email, or a resend still on
    cooldown) so the response time stays consistent whether or not a
    code was actually sent — otherwise an attacker could tell "sent"
    from "not sent" apart just by how long the request took, even with
    an identical response body. Never raises — any failure here (SMTP
    not configured, network hiccup) is irrelevant to the caller, which
    must return its generic response regardless.
    """
    try:
        with _connect():
            pass
    except Exception:
        pass
