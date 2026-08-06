from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.database import conversations_collection, profiles_collection
from app.dependencies import engine
from app.schemas import SuccessResponse

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
        }
        return {"metadata": meta, "profile": doc.get("profile", {})}
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
