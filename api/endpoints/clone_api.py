"""
Clone API endpoints for SARYA.
Provides endpoints for clone management.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security, status
from pydantic import BaseModel, Field

from api.auth import User, get_current_active_user
from clone_system.clone_base import CloneStatus
from clone_system.clone_manager import clone_manager
from clone_system.clone_queue import clone_queue
from clone_system.clone_registry import clone_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("clone_api")

# Create router
router = APIRouter(
    prefix="/clones",
    tags=["Clones"],
    responses={404: {"description": "Not found"}},
)

# Models
class CloneTypeInfo(BaseModel):
    """Information about a clone type."""
    name: str
    description: str = ""
    parameters: Dict = Field(default_factory=dict)

class CloneInfo(BaseModel):
    """Information about a clone."""
    clone_id: str
    name: str
    type: str
    status: str
    creation_time: float
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    last_active_time: Optional[float] = None
    runtime: Optional[float] = None
    progress: float
    failure_reason: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)

class CloneQueueInfo(BaseModel):
    """Information about the clone queue."""
    queue_size: int
    processing_size: int
    queued_clones: List[str]
    processing_clones: List[str]

class CloneCreate(BaseModel):
    """Request body for creating a clone."""
    type_name: str
    name: Optional[str] = None
    priority: int = 0
    config: Dict = Field(default_factory=dict)
    auto_start: bool = False

class CloneAction(BaseModel):
    """Request body for clone actions."""
    action: str = Field(..., description="Action to perform: start, stop, pause, resume")

# Endpoints
@router.get("/types", response_model=List[CloneTypeInfo])
async def get_clone_types(
    current_user: User = Security(get_current_active_user, scopes=["read"]),
):
    """Get all available clone types."""
    clone_types = clone_registry.get_clone_types()
    
    result = []
    for name, clone_class in clone_types.items():
        # Extract class docstring as description
        description = clone_class.__doc__ or ""
        description = description.strip()
        
        # Create response object
        result.append(
            CloneTypeInfo(
                name=name,
                description=description,
                parameters={},  # Could extract from class definition
            )
        )
    
    return result

@router.post("/", response_model=CloneInfo, status_code=status.HTTP_201_CREATED)
async def create_clone(
    clone_create: CloneCreate,
    current_user: User = Security(get_current_active_user, scopes=["write", "clone"]),
):
    """Create a new clone."""
    # Validate clone type
    if not clone_registry.get_clone_type(clone_create.type_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clone type '{clone_create.type_name}' not found",
        )
    
    # Create clone
    clone = clone_manager.create_clone(
        type_name=clone_create.type_name,
        name=clone_create.name,
    )
    
    if not clone:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clone of type '{clone_create.type_name}'",
        )
    
    # Initialize clone
    if not clone_manager.initialize_clone(clone.clone_id, clone_create.config):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize clone '{clone.clone_id}'",
        )
    
    # Auto-start if requested
    if clone_create.auto_start:
        # Enqueue the clone
        clone_queue.enqueue(clone.clone_id, clone_create.priority)
    
    # Return clone info
    return clone_manager.get_clone_info(clone.clone_id)

@router.get("/", response_model=List[CloneInfo])
async def get_clones(
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Security(get_current_active_user, scopes=["read"]),
):
    """Get all clones, optionally filtered by status."""
    # Convert status string to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = CloneStatus[status.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{status}'",
            )
    
    # Get clone info
    return clone_manager.get_all_clone_info(status_enum)

@router.get("/queue", response_model=CloneQueueInfo)
async def get_queue_info(
    current_user: User = Security(get_current_active_user, scopes=["read"]),
):
    """Get information about the clone queue."""
    return {
        "queue_size": clone_queue.get_queue_size(),
        "processing_size": clone_queue.get_processing_size(),
        "queued_clones": clone_queue.get_queued_clones(),
        "processing_clones": clone_queue.get_processing_clones(),
    }

@router.get("/{clone_id}", response_model=CloneInfo)
async def get_clone(
    clone_id: str = Path(..., description="ID of the clone"),
    current_user: User = Security(get_current_active_user, scopes=["read"]),
):
    """Get information about a specific clone."""
    clone_info = clone_manager.get_clone_info(clone_id)
    
    if not clone_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clone '{clone_id}' not found",
        )
    
    return clone_info

@router.post("/{clone_id}/enqueue")
async def enqueue_clone(
    clone_id: str = Path(..., description="ID of the clone"),
    priority: int = Query(0, description="Priority of the clone"),
    current_user: User = Security(get_current_active_user, scopes=["write", "clone"]),
):
    """Enqueue a clone for execution."""
    # Check if clone exists
    clone = clone_manager.get_clone(clone_id)
    if not clone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clone '{clone_id}' not found",
        )
    
    # Check clone status
    if not clone.initialized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clone '{clone_id}' is not initialized",
        )
    
    # Enqueue the clone
    if not clone_queue.enqueue(clone_id, priority):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue clone '{clone_id}'",
        )
    
    return {"status": "success", "message": f"Clone '{clone_id}' enqueued"}

@router.post("/{clone_id}/action")
async def perform_clone_action(
    clone_action: CloneAction,
    clone_id: str = Path(..., description="ID of the clone"),
    current_user: User = Security(get_current_active_user, scopes=["write", "clone"]),
):
    """Perform an action on a clone."""
    # Check if clone exists
    clone = clone_manager.get_clone(clone_id)
    if not clone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clone '{clone_id}' not found",
        )
    
    # Perform the action
    if clone_action.action == "start":
        if not clone_manager.start_clone(clone_id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start clone '{clone_id}'",
            )
    elif clone_action.action == "stop":
        if not clone_manager.stop_clone(clone_id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stop clone '{clone_id}'",
            )
    elif clone_action.action == "pause":
        if not clone_manager.pause_clone(clone_id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to pause clone '{clone_id}'",
            )
    elif clone_action.action == "resume":
        if not clone_manager.resume_clone(clone_id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to resume clone '{clone_id}'",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{clone_action.action}'",
        )
    
    return {
        "status": "success", 
        "message": f"Action '{clone_action.action}' performed on clone '{clone_id}'",
        "timestamp": datetime.now().isoformat()
    }

@router.delete("/{clone_id}")
async def remove_clone(
    clone_id: str = Path(..., description="ID of the clone"),
    force: bool = Query(False, description="Force removal of active clone"),
    current_user: User = Security(get_current_active_user, scopes=["write", "clone"]),
):
    """Remove a clone."""
    # Check if clone exists
    if not clone_manager.get_clone(clone_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clone '{clone_id}' not found",
        )
    
    # Remove from queue first if present
    clone_queue.remove(clone_id)
    
    # Remove the clone
    if not clone_manager.remove_clone(clone_id, force):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot remove active clone '{clone_id}' without force flag",
        )
    
    return {
        "status": "success", 
        "message": f"Clone '{clone_id}' removed",
        "timestamp": datetime.now().isoformat()
    }
