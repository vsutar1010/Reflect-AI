import json
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.dependencies import engine
from app.schemas import SuccessResponse

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

PROFILES_DIR = Path("profiles")


@router.get("")
def list_profiles():
    if not PROFILES_DIR.exists():
        return []

    summaries = []
    try:
        for item in PROFILES_DIR.iterdir():
            if item.is_dir():
                meta_file = item / "metadata.json"
                if meta_file.exists():
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)

                    conv_dir = item / "conversations"
                    conv_count = 0
                    if conv_dir.exists():
                        conv_count = sum(1 for c in conv_dir.iterdir() if c.is_file() and c.suffix == ".json")

                    summaries.append(
                        {
                            "id": meta.get("id"),
                            "name": meta.get("name"),
                            "created_at": meta.get("created_at"),
                            "last_used": meta.get("last_used"),
                            "conversation_count": conv_count,
                        }
                    )
        summaries.sort(key=lambda x: x.get("last_used", ""), reverse=True)
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}")
def get_profile(id: str):
    profile_dir = PROFILES_DIR / id
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

        return {"metadata": meta, "profile": prof}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id}", response_model=SuccessResponse)
def delete_profile(id: str):
    profile_dir = PROFILES_DIR / id
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        shutil.rmtree(profile_dir)
        engine.invalidate_cache(id)
        return SuccessResponse(success=True, message=f"Profile {id} deleted successfully.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}/conversations")
def list_profile_conversations(id: str):
    profile_dir = PROFILES_DIR / id
    if not profile_dir.exists():
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        conv_dir = profile_dir / "conversations"
        results = []
        if conv_dir.exists():
            for item in conv_dir.iterdir():
                if item.is_file() and item.suffix == ".json":
                    with open(item, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        msg_count = len(data.get("messages", []))

                    mtime = item.stat().st_mtime
                    updated_at = datetime.fromtimestamp(mtime).isoformat()

                    results.append(
                        {
                            "id": item.stem,
                            "title": "Main Conversation" if item.stem == "default" else item.stem.capitalize(),
                            "message_count": msg_count,
                            "updated_at": updated_at,
                        }
                    )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
