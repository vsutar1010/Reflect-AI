"""
Voice Chat API — Vapi integration.

Endpoints:
  GET  /api/voice/config                        -> is voice configured + public key
  POST /api/voice/start                          -> create a session + Vapi assistant config
  POST /api/voice/end                            -> mark a session ended
  POST /api/voice/webhook                        -> Vapi call-lifecycle events
  POST /api/voice/llm/{session_id}/chat/completions
       -> OpenAI-compatible endpoint Vapi calls per utterance when
          VAPI_LLM_PROVIDER=custom-llm. This is what makes voice replies
          come from the exact same DigitalTwinEngine + Ollama as Text
          Chat, instead of a separately-configured cloud model.
"""

from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import VAPI_PUBLIC_KEY, VAPI_LLM_PROVIDER, VAPI_SECRET_HEADER, voice_status
from app.database import profiles_collection
from app.dependencies import get_current_user, voice_chat_service
from app.schemas import (
    EndVoiceSessionRequest,
    StartVoiceSessionRequest,
    StartVoiceSessionResponse,
    VoiceConfigResponse,
    VoiceSessionStatusResponse,
)
from app.services.twin_engine import ProfileNotFoundError, SessionNotFoundError
from app.services.vapi_client import verify_server_secret

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/config", response_model=VoiceConfigResponse)
def get_voice_config():
    enabled, reason = voice_status()
    return VoiceConfigResponse(
        enabled=enabled,
        public_key=VAPI_PUBLIC_KEY,
        llm_provider=VAPI_LLM_PROVIDER,
        reason=reason,
    )


@router.post("/start", response_model=StartVoiceSessionResponse)
def start_voice_session(req: StartVoiceSessionRequest, current_user: dict = Depends(get_current_user)):
    enabled, reason = voice_status()
    if not enabled:
        raise HTTPException(status_code=503, detail=reason)

    if not profiles_collection.find_one({"_id": req.profile_id, "owner_id": current_user["id"]}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        result = voice_chat_service.start_session(req.profile_id, current_user["id"])
        return StartVoiceSessionResponse(
            session_id=result["session_id"],
            public_key=VAPI_PUBLIC_KEY,
            assistant=result["assistant"],
        )
    except ProfileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _owned_voice_session_or_404(session_id: str, owner_id: str) -> dict:
    session = voice_chat_service.get_session(session_id)
    if session is None or session.get("owner_id") != owner_id:
        raise HTTPException(status_code=404, detail="Voice session not found")
    return session


@router.post("/end", response_model=VoiceSessionStatusResponse)
def end_voice_session(req: EndVoiceSessionRequest, current_user: dict = Depends(get_current_user)):
    _owned_voice_session_or_404(req.session_id, current_user["id"])
    try:
        result = voice_chat_service.end_session(req.session_id)
        return VoiceSessionStatusResponse(**result)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=VoiceSessionStatusResponse)
def get_voice_session_status(session_id: str, current_user: dict = Depends(get_current_user)):
    session = _owned_voice_session_or_404(session_id, current_user["id"])

    duration = (session.get("ended_at") or time.time()) - session["started_at"]
    return VoiceSessionStatusResponse(
        session_id=session_id,
        status=session["status"],
        duration_seconds=round(duration, 1),
    )


@router.post("/webhook")
async def voice_webhook(request: Request):
    if not verify_server_secret(request.headers.get(VAPI_SECRET_HEADER)):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    result = voice_chat_service.handle_webhook_event(payload)
    return JSONResponse(result)


@router.post("/llm/{session_id}/chat/completions")
async def voice_llm_completions(session_id: str, request: Request):
    """
    OpenAI Chat Completions-compatible endpoint. Vapi's custom-llm
    provider POSTs here with the running conversation for this call;
    we respond with a standard SSE chat-completion-chunk stream so Vapi
    can start speaking the reply as it's generated.
    """
    if not verify_server_secret(request.headers.get(VAPI_SECRET_HEADER)):
        raise HTTPException(status_code=401, detail="Invalid custom-llm secret")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    incoming_messages = body.get("messages", [])
    wants_stream = body.get("stream", True)

    if voice_chat_service.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Voice session not found")

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model_name = "reflectai-twin"

    def sse_chunk(delta: dict, finish_reason=None) -> str:
        payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model_name,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        }
        return f"data: {json.dumps(payload)}\n\n"

    def event_stream():
        # NOTE: never `yield` inside a `finally` here. If Vapi closes the
        # connection early, Starlette throws GeneratorExit into this
        # generator to close it — a `finally` that yields turns that into
        # "generator ignored GeneratorExit", which silently drops the
        # response instead of raising anything visible.
        yield sse_chunk({"role": "assistant"})
        try:
            for token in voice_chat_service.stream_turn(session_id, incoming_messages):
                yield sse_chunk({"content": token})
            yield sse_chunk({}, finish_reason="stop")
        except SessionNotFoundError:
            yield sse_chunk({"content": "sorry, connection dropped."})
            yield sse_chunk({}, finish_reason="stop")
        except RuntimeError:
            # Ollama unreachable/errored mid-stream — end the turn
            # gracefully instead of leaving Vapi hanging indefinitely.
            yield sse_chunk({"content": "hold on, having trouble thinking."})
            yield sse_chunk({}, finish_reason="stop")
        yield "data: [DONE]\n\n"

    if not wants_stream:
        try:
            full_text = "".join(voice_chat_service.stream_turn(session_id, incoming_messages))
        except SessionNotFoundError:
            raise HTTPException(status_code=404, detail="Voice session not found")
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))

        return JSONResponse(
            {
                "id": completion_id,
                "object": "chat.completion",
                "created": created,
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": full_text},
                        "finish_reason": "stop",
                    }
                ],
            }
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
