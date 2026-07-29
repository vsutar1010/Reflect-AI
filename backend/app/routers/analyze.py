from fastapi import APIRouter, HTTPException

from app.dependencies import analyzer
from app.schemas import (
    AnalysisMessageRequest,
    AnalysisMessageResponse,
    FinalizeAnalysisRequest,
    StartAnalysisResponse,
)

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


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
