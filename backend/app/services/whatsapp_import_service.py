"""
WhatsAppImportService — holds a parsed chat export between the
"upload" and "finalize" API calls.

Mirrors the in-memory session-dict pattern PersonalityAnalyzer already
uses for interview sessions (this app has no session-persistence layer
yet). Kept as its own service rather than folded into
PersonalityAnalyzer because it owns upload lifecycle state, a
different concern from interview/session state.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Optional

from app.services.whatsapp_parser import WhatsAppParser


class WhatsAppImportService:
    def __init__(self):
        self.parser = WhatsAppParser()
        self.pending: Dict[str, dict] = {}

    def create_upload(self, raw_text: str, owner_id: str) -> dict:
        records = self.parser.parse(raw_text)
        participants = self.parser.detect_participants(records)
        self.parser.validate_one_on_one(participants)

        upload_id = str(uuid.uuid4())
        self.pending[upload_id] = {
            "owner_id": owner_id,
            "records": records,
            "participants": participants,
            "created_at": datetime.now(),
        }

        counts = {"message": 0, "system": 0, "media": 0, "deleted": 0}
        for record in records:
            counts[record["type"]] = counts.get(record["type"], 0) + 1

        return {
            "upload_id": upload_id,
            "participants": participants,
            "total_messages": counts["message"],
            "system_messages_skipped": counts["system"],
            "media_messages_skipped": counts["media"],
            "deleted_messages_skipped": counts["deleted"],
        }

    def finalize_upload(
        self,
        upload_id: str,
        target_sender: str,
        profile_name: Optional[str],
        analyzer,
        owner_id: str,
    ) -> dict:
        pending = self.pending.get(upload_id)
        if not pending or pending["owner_id"] != owner_id:
            raise ValueError("Upload not found or expired — please upload the chat again.")

        known_senders = {p["name"] for p in pending["participants"]}
        if target_sender not in known_senders:
            raise ValueError(f"'{target_sender}' isn't a participant detected in this chat.")

        messages = self.parser.build_target_messages(pending["records"], target_sender)

        return analyzer.analyze_whatsapp_messages(messages, profile_name, owner_id)

    def discard(self, upload_id: str) -> None:
        self.pending.pop(upload_id, None)
