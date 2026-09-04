"""
Reflect / Journaling API.

Plain MongoDB CRUD for journal entries (mirrors profiles.py's direct
collection access), plus AI reflection generation via ReflectService.
Every route re-derives access from `current_user` — ownership is always
`{"_id": entry_id, "owner_id": current_user["id"]}` on the query itself,
never assumed from the entry id alone, so one user can never read, edit,
re-analyze, or delete another user's journal entry.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import profiles_collection, reflections_collection
from app.dependencies import get_current_user, reflect_service
from app.schemas import CreateReflectEntryRequest, ReflectEntryResponse, UpdateReflectEntryRequest
from app.services.reflect_service import ReflectAnalysisError

router = APIRouter(prefix="/api/reflect", tags=["reflect"])

DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 50


def _to_response(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "profile_id": doc.get("profile_id"),
        "content": doc.get("content", ""),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "analysis": doc.get("analysis"),
    }


def _run_analysis(entry_id: str, content: str) -> dict:
    """
    Runs AI analysis and persists it, but never lets an analysis failure
    raise past this point — by the time this is called the entry itself
    is already durably saved, so a bad Ollama call can only leave
    `analysis.status` as "failed", never lose the journal text.
    """
    try:
        analysis = reflect_service.analyze(content)
        analysis["status"] = "ready"
    except ReflectAnalysisError as e:
        analysis = {"status": "failed", "error": str(e)}

    try:
        reflections_collection.update_one({"_id": entry_id}, {"$set": {"analysis": analysis}})
    except Exception:
        # Mongo hiccup writing the analysis back — the caller already has
        # this analysis dict in hand and returns it in the response either
        # way, so the user still sees it even if persistence lagged.
        pass
    return analysis


@router.post("", response_model=ReflectEntryResponse, status_code=201)
def create_entry(req: CreateReflectEntryRequest, current_user: dict = Depends(get_current_user)):
    if not profiles_collection.find_one({"_id": req.profile_id, "owner_id": current_user["id"]}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Profile not found")

    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Journal entry cannot be empty.")

    entry_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    doc = {
        "_id": entry_id,
        "owner_id": current_user["id"],
        "profile_id": req.profile_id,
        "content": content,
        "created_at": now,
        "updated_at": now,
        "analysis": {"status": "pending"},
    }

    try:
        reflections_collection.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save journal entry: {e}")

    # The entry is durably saved above — whatever happens next can only
    # change `analysis`, never lose the entry itself.
    doc["analysis"] = _run_analysis(entry_id, content)
    return _to_response(doc)


@router.get("", response_model=List[ReflectEntryResponse])
def list_entries(
    profile_id: Optional[str] = Query(default=None),
    limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    skip: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    query = {"owner_id": current_user["id"]}
    if profile_id:
        query["profile_id"] = profile_id

    try:
        cursor = reflections_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [_to_response(doc) for doc in cursor]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}", response_model=ReflectEntryResponse)
def get_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    try:
        doc = reflections_collection.find_one({"_id": entry_id, "owner_id": current_user["id"]})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not doc:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return _to_response(doc)


@router.patch("/{entry_id}", response_model=ReflectEntryResponse)
def update_entry(entry_id: str, req: UpdateReflectEntryRequest, current_user: dict = Depends(get_current_user)):
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Journal entry cannot be empty.")

    try:
        result = reflections_collection.update_one(
            {"_id": entry_id, "owner_id": current_user["id"]},
            {
                "$set": {
                    "content": content,
                    "updated_at": datetime.now().isoformat(),
                    # The old analysis was of the old text — clear it
                    # immediately so it's never shown as if it analyzed
                    # the new content while a fresh analysis is pending.
                    "analysis": {"status": "pending"},
                }
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    doc = reflections_collection.find_one({"_id": entry_id, "owner_id": current_user["id"]})
    doc["analysis"] = _run_analysis(entry_id, content)
    return _to_response(doc)


@router.post("/{entry_id}/analyze", response_model=ReflectEntryResponse)
def reanalyze_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    """Re-runs AI analysis on the entry's current text — the "try analysis
    again" action when a previous attempt failed (Ollama unreachable, etc)."""
    doc = reflections_collection.find_one({"_id": entry_id, "owner_id": current_user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    doc["analysis"] = _run_analysis(entry_id, doc["content"])
    return _to_response(doc)


@router.delete("/{entry_id}")
def delete_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    try:
        result = reflections_collection.delete_one({"_id": entry_id, "owner_id": current_user["id"]})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return {"success": True, "message": "Journal entry deleted."}
