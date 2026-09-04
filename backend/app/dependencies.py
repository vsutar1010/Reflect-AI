"""
Shared service singletons, created once and imported by every router.

DigitalTwinEngine is the one piece that MUST be shared between the text
and voice services — it's what makes them read/write the same profile
cache and the same conversation memory instead of drifting apart.
"""

from fastapi import HTTPException, Request

from app.config import SESSION_COOKIE_NAME
from app.database import users_collection
from app.services import auth_service
from app.services.analyzer import PersonalityAnalyzer
from app.services.chat import TextChatService
from app.services.reflect_service import ReflectService
from app.services.twin_engine import DigitalTwinEngine
from app.services.voice_chat_service import VoiceChatService
from app.services.whatsapp_import_service import WhatsAppImportService

analyzer = PersonalityAnalyzer()
whatsapp_import_service = WhatsAppImportService()

engine = DigitalTwinEngine()
text_chat_service = TextChatService(engine)
voice_chat_service = VoiceChatService(engine)
reflect_service = ReflectService()


def get_current_user(request: Request) -> dict:
    """
    Reads the session cookie, decodes the JWT, and loads the owning user —
    the one dependency every twin-scoped route in the app relies on to know
    who's asking. Raises 401 on anything missing/expired/invalid, so a
    protected route never has to separately branch on "am I logged in".
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user_id = auth_service.decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")

    user_doc = users_collection.find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")

    return {"id": user_doc["_id"], "email": user_doc["email"], "name": user_doc.get("name", "")}
