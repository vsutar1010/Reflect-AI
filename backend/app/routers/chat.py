import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.database import profiles_collection
from app.dependencies import get_current_user, text_chat_service
from app.schemas import ChatMessageRequest, ChatMessageResponse, StartChatRequest, StartChatResponse
from app.services.twin_engine import ProfileNotFoundError, SessionNotFoundError

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/start", response_model=StartChatResponse)
def start_chat(req: StartChatRequest, current_user: dict = Depends(get_current_user)):
    if not profiles_collection.find_one({"_id": req.profile_id, "owner_id": current_user["id"]}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        session_id = str(uuid.uuid4())
        text_chat_service.create_session(session_id, req.profile_id, current_user["id"])
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


@router.post("/message")
def send_chat_message(req: ChatMessageRequest, request: Request, current_user: dict = Depends(get_current_user)):
    session_id = req.session_id
    session = text_chat_service.get_session(session_id)

    if session is None or session.get("owner_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    # The frontend chat UI asks for `text/event-stream` to get a token-
    # by-token reply as it's generated. Anything else (e.g. eval/collect.py,
    # which just wants the final text) gets the plain JSON shape unchanged.
    accepts_stream = "text/event-stream" in request.headers.get("accept", "")

    if not accepts_stream:
        try:
            res = text_chat_service.chat(session_id, req.message)
            return ChatMessageResponse(reply=res["reply"])
        except SessionNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def event_stream():
        # NOTE: never `yield` inside a `finally` here — if the client
        # disconnects mid-stream, Starlette throws GeneratorExit into this
        # generator to close it, and a `finally` that yields turns that
        # into a silently-dropped response instead of raising anything
        # visible (same caution as voice.py's custom-llm stream).
        try:
            for token in text_chat_service.stream_chat(session_id, req.message):
                yield f"data: {json.dumps({'delta': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except SessionNotFoundError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
