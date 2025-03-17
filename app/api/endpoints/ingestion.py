from fastapi import APIRouter, HTTPException, Depends
from app.modules.code_ingestion.snapshot import CodeIngestionManager
from app.schemas.debug import DebuggingPayload, DebuggingSession
from app.modules.code_ingestion.storage import SnapshotStorage
from typing import Dict, Any, Optional

router = APIRouter()

async def get_ingestion_manager() -> CodeIngestionManager:
    """Dependency to get CodeIngestionManager instance."""
    return CodeIngestionManager()

@router.post("/ingest")
async def ingest_debugging_payload(
    payload: DebuggingPayload,
    manager: CodeIngestionManager = Depends(get_ingestion_manager)
) -> Dict[str, Any]:
    """
    Ingest a debugging payload from Cline.
    
    The payload contains:
    - error: Description of the error/problem
    - logs: Terminal or console logs
    - context: Background information
    - codebase: Updated code files (path -> content)
    - session_id: Optional ID for continuing a session
    
    Args:
        payload: DebuggingPayload containing error details and code
        
    Returns:
        Dictionary containing the snapshot ID and metadata
    """
    try:
        snapshot, metadata = await manager.process_debugging_payload(payload)
        return {
            "snapshot_id": snapshot.id,
            "metadata": metadata,
            "message": "Successfully processed debugging payload"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process debugging payload: {str(e)}"
        )

@router.get("/session/{session_id}")
async def get_debugging_session(
    session_id: str,
    manager: CodeIngestionManager = Depends(get_ingestion_manager)
) -> Dict[str, Any]:
    """
    Retrieve a debugging session by ID.
    
    Args:
        session_id: ID of the debugging session
        
    Returns:
        Dictionary containing the session data and associated snapshot
    """
    try:
        session = await manager.session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Debugging session {session_id} not found"
            )
        return {
            "session": session.dict(),
            "message": "Successfully retrieved debugging session"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve debugging session: {str(e)}"
        )

@router.get("/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    manager: CodeIngestionManager = Depends(get_ingestion_manager)
) -> Dict[str, Any]:
    """
    Get version history for a debugging session.
    
    Args:
        session_id: ID of the debugging session
        
    Returns:
        Dictionary containing the version history
    """
    try:
        history = await manager.get_session_history(session_id)
        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"No history found for session {session_id}"
            )
        return {
            "history": history,
            "message": "Successfully retrieved session history"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve session history: {str(e)}"
        )

@router.post("/session/{session_id}/revert/{version}")
async def revert_session_version(
    session_id: str,
    version: int,
    manager: CodeIngestionManager = Depends(get_ingestion_manager)
) -> Dict[str, Any]:
    """
    Revert a debugging session to a specific version.
    
    Args:
        session_id: ID of the debugging session
        version: Version number to revert to
        
    Returns:
        Dictionary containing the reverted session data
    """
    try:
        session = await manager.revert_session(session_id, version)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to revert session {session_id} to version {version}"
            )
        return {
            "session": session.dict(),
            "message": f"Successfully reverted to version {version}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revert session: {str(e)}"
        )
