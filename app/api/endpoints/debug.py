from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from app.schemas import debug as schemas
from app.modules.orchestrator.workflow import get_orchestrator, Orchestrator

router = APIRouter()


@router.post("/", response_model=schemas.DebugSessionResponse)
async def create_debug_session(
    request: schemas.DebugRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Any:
    """
    Create a new debugging session for a codebase.
    
    This will:
    1. Ingest the codebase to create a snapshot
    2. Spin up a Docker container with the code
    3. Execute the specified commands
    4. Analyze the results to identify issues
    5. Generate proposed fixes
    """
    try:
        debug_options = schemas.DebugOptions(
            commands=request.commands,
            timeout=request.timeout or 60000,
            container_config=request.container_config or schemas.ContainerConfig(),
            analysis_options=request.analysis_options or {}
        )
        
        session = await orchestrator.debug(request.codebase_path, debug_options)
        return schemas.DebugSessionResponse.from_model(session)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create debug session: {str(e)}"
        )


@router.get("/{session_id}", response_model=schemas.DebugSessionResponse)
async def get_debug_session(
    session_id: str,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Any:
    """Get the status and results of a debugging session."""
    try:
        session = await orchestrator.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Debug session {session_id} not found"
            )
        return schemas.DebugSessionResponse.from_model(session)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve debug session: {str(e)}"
        )


@router.post("/{session_id}/continue", response_model=schemas.DebugSessionResponse)
async def continue_debug_session(
    session_id: str,
    request: schemas.ContinueSessionRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Any:
    """Continue an existing debugging session."""
    try:
        session = await orchestrator.continue_session(session_id, request.commands)
        return schemas.DebugSessionResponse.from_model(session)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to continue debug session: {str(e)}"
        )


@router.post("/{session_id}/apply-fix", response_model=schemas.ApplyFixResponse)
async def apply_fix(
    session_id: str,
    request: schemas.ApplyFixRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> Any:
    """Apply a proposed fix to the codebase."""
    try:
        success, message, modified_files = await orchestrator.apply_fix(
            session_id, request.fix_index
        )
        return schemas.ApplyFixResponse(
            success=success,
            message=message,
            modified_files=modified_files
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply fix: {str(e)}"
        )
