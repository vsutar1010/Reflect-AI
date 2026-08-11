"""
WhatsApp exported chat (.txt) parser.

Turns WhatsApp's semi-structured export format into a flat list of
message records, then into the same [{role, content}] shape the rest
of the personality-analysis pipeline (CommunicationAnalyzer, the
Ollama prompt builders in analyzer.py) already consumes from the
interview flow. This file's only job is getting raw WhatsApp text into
that shape — it does no personality analysis itself.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

_INVISIBLE_MARKS = ("‎", "‏", "﻿")

# iOS export: "[10/08/26, 4:17:05 PM] Krushnali: message"
_IOS_RE = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?)\]\s(.*)$"
)
# Android export: "10/08/26, 4:17 pm - Krushnali: message"
_ANDROID_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2}(?:\s?[APap][Mm])?)\s-\s(.*)$"
)

_MEDIA_KEYWORD = "omitted"
_DELETED_PLACEHOLDERS = {"this message was deleted", "you deleted this message"}

MIN_TARGET_MESSAGES = 5
MAX_PARTICIPANTS = 2


class WhatsAppParseError(ValueError):
    """Raised for user-facing problems with an uploaded chat export."""


def _strip_invisibles(line: str) -> str:
    for mark in _INVISIBLE_MARKS:
        line = line.replace(mark, "")
    return line


def _classify_message_type(message: str) -> str:
    normalized = _strip_invisibles(message).strip().lower()

    if normalized in _DELETED_PLACEHOLDERS:
        return "deleted"

    if _MEDIA_KEYWORD in normalized and len(normalized) < 40:
        return "media"

    return "message"


def _classify_remainder(remainder: str) -> Tuple[Optional[str], str, str]:
    """
    Splits "Sender: message text" from a WhatsApp system message, which
    never has that "Name: " shape — it's plain narrative text generated
    by WhatsApp itself (e.g. "X created group Y", "Messages and calls
    are end-to-end encrypted...").
    """
    remainder = remainder.strip()

    if ": " in remainder:
        idx = remainder.index(": ")
        candidate_sender = remainder[:idx].strip()
        candidate_message = remainder[idx + 2:]

        if candidate_sender and len(candidate_sender) <= 50 and "\n" not in candidate_sender:
            return candidate_sender, candidate_message, _classify_message_type(candidate_message)

    return None, remainder, "system"


class WhatsAppParser:
    """Parses WhatsApp .txt exports into role-tagged message lists."""

    def parse(self, raw_text: str) -> List[Dict]:
        records: List[Dict] = []

        for raw_line in raw_text.splitlines():
            line = _strip_invisibles(raw_line).rstrip("\r")

            match = _IOS_RE.match(line) or _ANDROID_RE.match(line)

            if match:
                date, time, remainder = match.groups()
                sender, message, msg_type = _classify_remainder(remainder)
                records.append(
                    {
                        "date": date,
                        "time": time,
                        "sender": sender,
                        "message": message,
                        "type": msg_type,
                    }
                )
            elif records and line.strip():
                # Continuation of a multiline message — WhatsApp exports
                # embedded newlines as literal newlines with no new
                # date/time prefix on the wrapped lines.
                records[-1]["message"] += "\n" + line
            # else: blank line, or stray text before the first real
            # message (e.g. a leading BOM artifact) — skip.

        if not records:
            raise WhatsAppParseError(
                "Couldn't find any WhatsApp messages in this file. Make sure you "
                "uploaded a WhatsApp chat export (.txt)."
            )

        return records

    def detect_participants(self, records: List[Dict]) -> List[Dict]:
        counts: Dict[str, int] = {}
        order: List[str] = []

        for record in records:
            if record["type"] != "message" or not record["sender"]:
                continue
            sender = record["sender"]
            if sender not in counts:
                counts[sender] = 0
                order.append(sender)
            counts[sender] += 1

        participants = [{"name": name, "message_count": counts[name]} for name in order]
        participants.sort(key=lambda p: p["message_count"], reverse=True)
        return participants

    def validate_one_on_one(self, participants: List[Dict]) -> None:
        if not participants:
            raise WhatsAppParseError(
                "Couldn't find any messages from a real participant in this chat."
            )
        if len(participants) > MAX_PARTICIPANTS:
            names = ", ".join(p["name"] for p in participants)
            raise WhatsAppParseError(
                f"This looks like a group chat with {len(participants)} participants "
                f"({names}) — group chats aren't supported yet. Please upload a 1:1 chat export."
            )

    def build_target_messages(self, records: List[Dict], target_sender: str) -> List[Dict]:
        """
        Only the target sender's own lines become the conversation fed
        into personality analysis — the other participant's messages
        are never read by CommunicationAnalyzer or the LLM prompt
        builder (both filter to role == "user" only), so there's no
        reason to store a non-consenting third party's private texts.
        """
        messages = [
            {"role": "user", "content": record["message"]}
            for record in records
            if record["type"] == "message"
            and record["sender"] == target_sender
            and record["message"].strip()
        ]

        if len(messages) < MIN_TARGET_MESSAGES:
            raise WhatsAppParseError(
                f"Only found {len(messages)} messages from {target_sender} — need at "
                f"least {MIN_TARGET_MESSAGES} to build a personality profile."
            )

        return messages
