from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import shutil
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from app.schemas import (
    StartAnalysisResponse,
    AnalysisMessageRequest,
    AnalysisMessageResponse,
    FinalizeAnalysisRequest,
    StartChatRequest,
    StartChatResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    SuccessResponse
)
from app.services.analyzer import PersonalityAnalyzer
from app.services.chat import TwinChat

app = FastAPI(title="ReflectAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = PersonalityAnalyzer()
print(">>> Global analyzer created:", id(analyzer))

# TODO:
# Replace lazy initialization once chat no longer depends
# on personality.json during construction.
_chat_service = None

def get_chat_service() -> TwinChat:
    global _chat_service
    if _chat_service is None:
        _chat_service = TwinChat()
    return _chat_service

@app.post("/api/analyze/start", response_model=StartAnalysisResponse)
def start_analysis():
    print("Global analyzer instance:", id(analyzer))
    try:
        res = analyzer.start_analysis()
        return StartAnalysisResponse(
            session_id=res["session_id"],
            message=res["question"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze/message", response_model=AnalysisMessageResponse)
def send_analysis_message(req: AnalysisMessageRequest):
    print("Global analyzer instance:", id(analyzer))
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
        
        return AnalysisMessageResponse(
            question=res.get("question", ""),
            progress=progress
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze/finalize")
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

@app.post("/api/chat/start", response_model=StartChatResponse)
def start_chat(req: StartChatRequest):
    try:
        chat_service = get_chat_service()
        session_id = str(uuid.uuid4())
        chat_service.create_session(session_id, req.profile_id)
        return StartChatResponse(
            session_id=session_id,
            message="Hey! Ready to chat?"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/message", response_model=ChatMessageResponse)
def send_chat_message(req: ChatMessageRequest):
    session_id = req.session_id
    try:
        chat_service = get_chat_service()
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not chat_service.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        res = chat_service.chat(session_id, req.message)
        return ChatMessageResponse(reply=res["reply"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================
# Profiles API
# ==========================================================

@app.get("/api/profiles")
def list_profiles():
    profiles_dir = Path("profiles")
    if not profiles_dir.exists():
        return []
    
    summaries = []
    try:
        for item in profiles_dir.iterdir():
            if item.is_dir():
                meta_file = item / "metadata.json"
                if meta_file.exists():
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    
                    # Count conversations
                    conv_dir = item / "conversations"
                    conv_count = 0
                    if conv_dir.exists():
                        conv_count = sum(1 for c in conv_dir.iterdir() if c.is_file() and c.suffix == ".json")
                    
                    summaries.append({
                        "id": meta.get("id"),
                        "name": meta.get("name"),
                        "created_at": meta.get("created_at"),
                        "last_used": meta.get("last_used"),
                        "conversation_count": conv_count
                    })
        # Sort profiles by last_used descending
        summaries.sort(key=lambda x: x.get("last_used", ""), reverse=True)
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profiles/{id}")
def get_profile(id: str):
    profile_dir = Path("profiles") / id
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        meta_file = profile_dir / "metadata.json"
        prof_file = profile_dir / "profile.json"
        
        meta = {}
        prof = {}
        
        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        if prof_file.exists():
            with open(prof_file, "r", encoding="utf-8") as f:
                prof = json.load(f)
                
        return {
            "metadata": meta,
            "profile": prof
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/profiles/{id}", response_model=SuccessResponse)
def delete_profile(id: str):
    profile_dir = Path("profiles") / id
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        shutil.rmtree(profile_dir)
        return SuccessResponse(success=True, message=f"Profile {id} deleted successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/profiles/{id}/conversations")
def list_profile_conversations(id: str):
    profile_dir = Path("profiles") / id
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        conv_dir = profile_dir / "conversations"
        results = []
        if conv_dir.exists():
            for item in conv_dir.iterdir():
                if item.is_file() and item.suffix == ".json":
                    # Get message count
                    with open(item, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        msg_count = len(data.get("messages", []))
                    
                    # Get last modified time as ISO string
                    mtime = item.stat().st_mtime
                    updated_at = datetime.fromtimestamp(mtime).isoformat()
                    
                    results.append({
                        "id": item.stem,
                        "title": "Main Conversation" if item.stem == "default" else item.stem.capitalize(),
                        "message_count": msg_count,
                        "updated_at": updated_at
                    })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
