"""
Shared service singletons, created once and imported by every router.

DigitalTwinEngine is the one piece that MUST be shared between the text
and voice services — it's what makes them read/write the same profile
cache and the same conversation memory instead of drifting apart.
"""

from app.services.analyzer import PersonalityAnalyzer
from app.services.chat import TextChatService
from app.services.twin_engine import DigitalTwinEngine
from app.services.voice_chat_service import VoiceChatService
from app.services.whatsapp_import_service import WhatsAppImportService

analyzer = PersonalityAnalyzer()
whatsapp_import_service = WhatsAppImportService()

engine = DigitalTwinEngine()
text_chat_service = TextChatService(engine)
voice_chat_service = VoiceChatService(engine)
