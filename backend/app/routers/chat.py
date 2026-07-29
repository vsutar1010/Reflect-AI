import uuid

from fastapi import APIRouter, HTTPException

from app.dependencies import text_chat_service
from app.schemas import ChatMessageRequest, ChatMessageResponse, StartChatRequest, StartChatResponse
from app.services.twin_engine import ProfileNotFoundError, SessionNotFoundError

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/start", response_model=StartChatResponse)
def start_chat(req: StartChatRequest):
    try:
        session_id = str(uuid.uuid4())
        text_chat_service.create_session(session_id, req.profile_id)
        session = text_chat_service.get_session(session_id)
        history = session["history"] if session else []

        return StartChatResponse(
            session_id=session_id,
            message=text_chat_service.opening_line(req.profile_id),
            history=history,
        )
    except ProfileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(req: ChatMessageRequest):
    session_id = req.session_id

    if not text_chat_service.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        res = text_chat_service.chat(session_id, req.message)
        return ChatMessageResponse(reply=res["reply"])
    except SessionNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
