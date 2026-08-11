from fastapi import APIRouter, File, HTTPException, UploadFile

from app.dependencies import analyzer, whatsapp_import_service
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

_MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB


@router.post("/start", response_model=StartAnalysisResponse)
def start_analysis():
    try:
        res = analyzer.start_analysis()
        return StartAnalysisResponse(session_id=res["session_id"], message=res["question"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=AnalysisMessageResponse)
def send_analysis_message(req: AnalysisMessageRequest):
    session_id = req.session_id
    if not analyzer.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

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
def finalize_analysis(req: FinalizeAnalysisRequest):
    session_id = req.session_id
    if not analyzer.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

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
async def upload_whatsapp_chat(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Please upload a WhatsApp chat export (.txt).")

    raw_bytes = await file.read()
    if len(raw_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large — max 15MB.")

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_bytes.decode("utf-8", errors="replace")

    try:
        res = whatsapp_import_service.create_upload(text)
        return WhatsAppUploadResponse(**res)
    except WhatsAppParseError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/whatsapp/finalize")
def finalize_whatsapp_chat(req: WhatsAppFinalizeRequest):
    # No explicit name given — default to the WhatsApp sender's own
    # display name rather than relying on the LLM spotting a
    # self-mention, which rarely happens in casual chat.
    profile_name = (req.profile_name or "").strip() or req.target_sender

    try:
        res = whatsapp_import_service.finalize_upload(
            req.upload_id, req.target_sender, profile_name, analyzer
        )
        whatsapp_import_service.discard(req.upload_id)
        return res
    except WhatsAppParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
