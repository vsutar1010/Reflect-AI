from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app import config
from app.dependencies import analyzer, get_current_user, whatsapp_import_service
from app.schemas import (
    AnalysisMessageRequest,
    AnalysisMessageResponse,
    FinalizeAnalysisRequest,
    StartAnalysisResponse,
    WhatsAppFinalizeRequest,
    WhatsAppUploadResponse,
)
from app.services.whatsapp_parser import WhatsAppParseError

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

# Read in fixed-size chunks rather than `await file.read()` in one shot —
# this bounds how far over the configured limit a rejected upload can
# ever get held in memory (at most one chunk past it) instead of fully
# materializing an arbitrarily large file before the size check runs.
_READ_CHUNK_BYTES = 1024 * 1024  # 1MB


def _owned_session_or_404(session_id: str, owner_id: str):
    session = analyzer.get_session(session_id)
    if session is None or session.get("owner_id") != owner_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/start", response_model=StartAnalysisResponse)
def start_analysis(current_user: dict = Depends(get_current_user)):
    try:
        res = analyzer.start_analysis(current_user["id"])
        return StartAnalysisResponse(session_id=res["session_id"], message=res["question"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=AnalysisMessageResponse)
def send_analysis_message(req: AnalysisMessageRequest, current_user: dict = Depends(get_current_user)):
    session_id = req.session_id
    _owned_session_or_404(session_id, current_user["id"])

    try:
        res = analyzer.continue_analysis(session_id, req.message)

        session = analyzer.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        if res.get("completed", False):
            return AnalysisMessageResponse(question="", progress=100)

        q_index = session["question_index"]
        total_questions = len(analyzer.question_bank)
        progress = int((q_index / total_questions) * 100)

        return AnalysisMessageResponse(question=res.get("question", ""), progress=progress)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/finalize")
def finalize_analysis(req: FinalizeAnalysisRequest, current_user: dict = Depends(get_current_user)):
    session_id = req.session_id
    _owned_session_or_404(session_id, current_user["id"])

    try:
        res = analyzer.finalize_analysis(session_id, req.profile_name)
        analyzer.delete_session(session_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================
# WhatsApp Chat Import
# ==========================================================

@router.post("/whatsapp/upload", response_model=WhatsAppUploadResponse)
async def upload_whatsapp_chat(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not (file.filename or "").lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Please upload a WhatsApp chat export (.txt).")

    max_bytes = config.MAX_WHATSAPP_UPLOAD_SIZE_BYTES

    # Read in bounded chunks and abort the instant the running total
    # crosses the limit — never holds more than ~one chunk over the
    # limit in memory, unlike `await file.read()` followed by a size
    # check, which fully materializes the file (however large) first.
    # This also guarantees an oversized file never reaches the parser,
    # AI analysis, or MongoDB below.
    buffer = bytearray()
    total_read = 0
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_bytes:
            await file.close()
            raise HTTPException(
                status_code=413,
                detail=(
                    f"WhatsApp export is too large. Maximum allowed size is "
                    f"{config.MAX_WHATSAPP_UPLOAD_SIZE_MB} MB."
                ),
            )
        buffer.extend(chunk)

    try:
        text = bytes(buffer).decode("utf-8-sig")
    except UnicodeDecodeError:
        text = bytes(buffer).decode("utf-8", errors="replace")

    try:
        res = whatsapp_import_service.create_upload(text, current_user["id"])
        return WhatsAppUploadResponse(**res)
    except WhatsAppParseError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/whatsapp/finalize")
def finalize_whatsapp_chat(req: WhatsAppFinalizeRequest, current_user: dict = Depends(get_current_user)):
    # No explicit name given — default to the WhatsApp sender's own
    # display name rather than relying on the LLM spotting a
    # self-mention, which rarely happens in casual chat.
    profile_name = (req.profile_name or "").strip() or req.target_sender

    try:
        res = whatsapp_import_service.finalize_upload(
            req.upload_id, req.target_sender, profile_name, analyzer, current_user["id"]
        )
        whatsapp_import_service.discard(req.upload_id)
        return res
    except WhatsAppParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
