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


def send_otp_email(to_email: str, name: str, otp: str) -> None:
    if not config.smtp_configured():
        raise RuntimeError(
            "Email sign-up isn't configured on this server yet — SMTP_USERNAME/"
            "SMTP_PASSWORD are missing from backend/.env. See backend/.env.example "
            "for how to generate a Gmail App Password."
        )

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

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        smtp.send_message(message)
