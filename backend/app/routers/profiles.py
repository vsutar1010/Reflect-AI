from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.config import VAPI_VOICE_PRESETS
from app.database import conversations_collection, profiles_collection
from app.dependencies import engine
from app.schemas import SetProfileVoiceRequest, SuccessResponse

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("")
def list_profiles():
    try:
        summaries = []
        for doc in profiles_collection.find(
            {}, {"_id": 1, "name": 1, "created_at": 1, "last_used": 1}
        ):
            conv_count = conversations_collection.count_documents({"profile_id": doc["_id"]})
            summaries.append(
                {
                    "id": doc.get("_id"),
                    "name": doc.get("name"),
                    "created_at": doc.get("created_at"),
                    "last_used": doc.get("last_used"),
                    "conversation_count": conv_count,
                }
            )
        summaries.sort(key=lambda x: x.get("last_used", ""), reverse=True)
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}")
def get_profile(id: str):
    try:
        doc = profiles_collection.find_one({"_id": id})
        if not doc:
            raise HTTPException(status_code=404, detail="Profile not found")

        meta = {
            "id": doc.get("_id"),
            "name": doc.get("name"),
            "created_at": doc.get("created_at"),
            "last_used": doc.get("last_used"),
            "version": doc.get("version"),
            "voice": doc.get("voice"),
        }
        return {"metadata": meta, "profile": doc.get("profile", {})}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{id}/voice", response_model=SuccessResponse)
def set_profile_voice(id: str, req: SetProfileVoiceRequest):
    preset = VAPI_VOICE_PRESETS.get(req.gender)
    if not preset:
        options = ", ".join(VAPI_VOICE_PRESETS.keys())
        raise HTTPException(status_code=400, detail=f"Unknown voice option '{req.gender}'. Choose one of: {options}")

    try:
        result = profiles_collection.update_one(
            {"_id": id},
            {"$set": {"voice": {"gender": req.gender, **preset}}},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Voice Chat caches per-profile voice choice inside live in-memory
        # call sessions (set once at session start) — nothing to invalidate
        # here since there's no persistent per-profile cache in the engine,
        # only the next /api/voice/start reads this field fresh.
        return SuccessResponse(success=True, message="Voice updated.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id}", response_model=SuccessResponse)
def delete_profile(id: str):
    try:
        result = profiles_collection.delete_one({"_id": id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Profile not found")

        conversations_collection.delete_many({"profile_id": id})
        engine.invalidate_cache(id)
        return SuccessResponse(success=True, message=f"Profile {id} deleted successfully.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}/conversations")
def list_profile_conversations(id: str):
    try:
        if not profiles_collection.find_one({"_id": id}, {"_id": 1}):
            raise HTTPException(status_code=404, detail="Profile not found")

        results = []
        for doc in conversations_collection.find({"profile_id": id}):
            thread = doc.get("thread", "default")
            results.append(
                {
                    "id": thread,
                    "title": "Main Conversation" if thread == "default" else thread.capitalize(),
                    "message_count": len(doc.get("messages", [])),
                    "updated_at": doc.get("updated_at") or datetime.now().isoformat(),
                }
            )
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
