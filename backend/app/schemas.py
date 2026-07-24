"""
Pydantic schemas for ReflectAI API.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==========================================================
# Analysis API
# ==========================================================

class StartAnalysisResponse(BaseModel):
    session_id: str
    message: str


class AnalysisMessageRequest(BaseModel):
    session_id: str
    message: str


class AnalysisMessageResponse(BaseModel):
    question: str
    progress: int = Field(..., ge=0, le=100)


class FinalizeAnalysisRequest(BaseModel):
    session_id: str
    profile_name: str


# ==========================================================
# Personality Profile
# ==========================================================

class PersonalityProfile(BaseModel):

    identity: Dict[str, Any]

    vocabulary: Dict[str, Any]

    writing_style: Dict[str, Any]

    conversation_style: Dict[str, Any]

    personality: Dict[str, Any]

    thinking_pattern: Dict[str, Any]

    interests: List[str]

    behavior: Dict[str, Any]

    summary: str


# ==========================================================
# Chat API
# ==========================================================

class StartChatRequest(BaseModel):
    profile_id: str


class StartChatResponse(BaseModel):
    session_id: str
    message: str


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    reply: str


# ==========================================================
# Generic API Response
# ==========================================================

class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str