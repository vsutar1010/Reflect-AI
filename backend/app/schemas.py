"""
Pydantic schemas for ReflectAI API.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ==========================================================
# Auth API
# ==========================================================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


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
    profile_name: Optional[str] = None


# ==========================================================
# WhatsApp Chat Import
# ==========================================================

class WhatsAppParticipant(BaseModel):
    name: str
    message_count: int


class WhatsAppUploadResponse(BaseModel):
    upload_id: str
    participants: List[WhatsAppParticipant]
    total_messages: int
    system_messages_skipped: int
    media_messages_skipped: int
    deleted_messages_skipped: int


class WhatsAppFinalizeRequest(BaseModel):
    upload_id: str
    target_sender: str
    profile_name: Optional[str] = None


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


class ChatHistoryMessage(BaseModel):
    role: str
    content: str
    channel: Optional[str] = None


class StartChatResponse(BaseModel):
    session_id: str
    message: str
    history: List[ChatHistoryMessage] = []


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    reply: str


# ==========================================================
# Voice Chat API (Vapi)
# ==========================================================

class VoiceConfigResponse(BaseModel):
    enabled: bool
    public_key: str
    llm_provider: str
    reason: str = ""


class StartVoiceSessionRequest(BaseModel):
    profile_id: str


class StartVoiceSessionResponse(BaseModel):
    session_id: str
    public_key: str
    assistant: Dict[str, Any]


class EndVoiceSessionRequest(BaseModel):
    session_id: str


class VoiceSessionStatusResponse(BaseModel):
    session_id: str
    status: str
    duration_seconds: float


# ==========================================================
# Profile Voice Selection
# ==========================================================

class SetProfileVoiceRequest(BaseModel):
    gender: str  # "male" | "female" — keys into config.VAPI_VOICE_PRESETS


# ==========================================================
# Generic API Response
# ==========================================================

class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str