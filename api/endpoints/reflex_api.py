"""
Reflex API endpoints for SARYA.
Provides endpoints for reflex system management.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security, status
from pydantic import BaseModel, Field

from api.auth import User, get_current_active_user
from reflex_system.emotional_reflex import emotional_reflex_manager
from reflex_system.reflex_processor import reflex_processor
from reflex_system.spiritual_reflex import spiritual_reflex_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("reflex_api")

# Create router
router = APIRouter(
    prefix="/reflex",
    tags=["Reflex"],
    responses={404: {"description": "Not found"}},
)

# Models
class ReflexEvent(BaseModel):
    """A reflex event."""
    source: str
    event_type: str
    data: Dict = Field(default_factory=dict)
    timestamp: Optional[float] = None

class EmotionalReflexMapping(BaseModel):
    """Emotional reflex mapping."""
    event_type: str
    emotion: str
    intensity: float
    description: str

class SpiritualReflexMapping(BaseModel):
    """Spiritual reflex mapping."""
    event_type: str
    symbol: str
    meaning: str
    description: str

class ReflexLog(BaseModel):
    """A reflex log entry."""
    id: str
    event_type: str
    timestamp: float
    source: str
    emotional_reflexes: List[Dict] = Field(default_factory=list)
    spiritual_reflexes: List[Dict] = Field(default_factory=list)
    data: Dict = Field(default_factory=dict)

class ReflexStats(BaseModel):
    """Reflex system statistics."""
    total_events: int
    emotional_mappings: int
    spiritual_mappings: int
    recent_events: List[str] = Field(default_factory=list)
    top_emotions: List[Dict[str, float]] = Field(default_factory=list)
    top_symbols: List[Dict[str, float]] = Field(default_factory=list)

# Endpoints
@router.post("/process", response_model=ReflexLog)
async def process_reflex_event(
    event: ReflexEvent,
    current_user: User = Security(get_current_active_user, scopes=["write", "reflex"]),
):
    """Process a reflex event."""
    # Set timestamp if not provided
    if not event.timestamp:
        event.timestamp = datetime.now().timestamp()
    
    # Process the event
    result = reflex_processor.process_event(
        event_type=event.event_type,
        source=event.source,
        data=event.data,
        timestamp=event.timestamp
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process reflex event",
        )
    
    return result

@router.get("/logs", response_model=List[ReflexLog])
async def get_reflex_logs(
    limit: int = Query(10, description="Maximum number of logs to return"),
    offset: int = Query(0, description="Offset for pagination"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    source: Optional[str] = Query(None, description="Filter by source"),
    emotion: Optional[str] = Query(None, description="Filter by emotion"),
    symbol: Optional[str] = Query(None, description="Filter by spiritual symbol"),
    current_user: User = Security(get_current_active_user, scopes=["read", "reflex"]),
):
    """Get reflex logs."""
    filters = {}
    if event_type:
        filters["event_type"] = event_type
    if source:
        filters["source"] = source
    if emotion:
        filters["emotion"] = emotion
    if symbol:
        filters["symbol"] = symbol
    
    return reflex_processor.get_logs(limit, offset, filters)

@router.get("/emotional/mappings", response_model=List[EmotionalReflexMapping])
async def get_emotional_mappings(
    current_user: User = Security(get_current_active_user, scopes=["read", "reflex"]),
):
    """Get emotional reflex mappings."""
    return emotional_reflex_manager.get_mappings()

@router.get("/spiritual/mappings", response_model=List[SpiritualReflexMapping])
async def get_spiritual_mappings(
    current_user: User = Security(get_current_active_user, scopes=["read", "reflex"]),
):
    """Get spiritual reflex mappings."""
    return spiritual_reflex_manager.get_mappings()

@router.post("/emotional/mappings")
async def update_emotional_mapping(
    mapping: EmotionalReflexMapping,
    current_user: User = Security(get_current_active_user, scopes=["write", "reflex"]),
):
    """Create or update an emotional reflex mapping."""
    success = emotional_reflex_manager.set_mapping(
        event_type=mapping.event_type,
        emotion=mapping.emotion,
        intensity=mapping.intensity,
        description=mapping.description
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update emotional reflex mapping",
        )
    
    return {
        "status": "success", 
        "message": f"Emotional reflex mapping updated for '{mapping.event_type}'",
        "timestamp": datetime.now().isoformat()
    }

@router.post("/spiritual/mappings")
async def update_spiritual_mapping(
    mapping: SpiritualReflexMapping,
    current_user: User = Security(get_current_active_user, scopes=["write", "reflex"]),
):
    """Create or update a spiritual reflex mapping."""
    success = spiritual_reflex_manager.set_mapping(
        event_type=mapping.event_type,
        symbol=mapping.symbol,
        meaning=mapping.meaning,
        description=mapping.description
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update spiritual reflex mapping",
        )
    
    return {
        "status": "success", 
        "message": f"Spiritual reflex mapping updated for '{mapping.event_type}'",
        "timestamp": datetime.now().isoformat()
    }

@router.delete("/emotional/mappings/{event_type}")
async def delete_emotional_mapping(
    event_type: str = Path(..., description="Event type to delete mapping for"),
    current_user: User = Security(get_current_active_user, scopes=["write", "reflex"]),
):
    """Delete an emotional reflex mapping."""
    success = emotional_reflex_manager.delete_mapping(event_type)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Emotional mapping for '{event_type}' not found",
        )
    
    return {
        "status": "success", 
        "message": f"Emotional reflex mapping deleted for '{event_type}'",
        "timestamp": datetime.now().isoformat()
    }

@router.delete("/spiritual/mappings/{event_type}")
async def delete_spiritual_mapping(
    event_type: str = Path(..., description="Event type to delete mapping for"),
    current_user: User = Security(get_current_active_user, scopes=["write", "reflex"]),
):
    """Delete a spiritual reflex mapping."""
    success = spiritual_reflex_manager.delete_mapping(event_type)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spiritual mapping for '{event_type}' not found",
        )
    
    return {
        "status": "success", 
        "message": f"Spiritual reflex mapping deleted for '{event_type}'",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/stats", response_model=ReflexStats)
async def get_reflex_stats(
    current_user: User = Security(get_current_active_user, scopes=["read", "reflex"]),
):
    """Get reflex system statistics."""
    return reflex_processor.get_stats()

@router.post("/sync/validate/{clone_id}")
async def validate_reflex_sync(
    clone_id: str,
    reflex_data: Dict,
    current_user: User = Security(get_current_active_user, scopes=["write"])
):
    """Validate reflex sync for a clone."""
    is_valid = reflex_sync_validator.validate_sync(clone_id, reflex_data)
    return {"valid": is_valid, "timestamp": time.time()}

@router.post("/memory/fuse/{clone_id}")
async def fuse_memory(
    clone_id: str,
    pattern_data: Dict,
    current_user: User = Security(get_current_active_user, scopes=["write"])
):
    """Fuse clone memory with reflex pattern."""
    fused_state = memory_link_fusion.fuse_memory(clone_id, pattern_data)
    return {"status": "success", "fused_state": fused_state}
from flask import Blueprint, jsonify, request
from reflex_system.reflex_processor import reflex_processor
from reflex_system.reflex_learning_engine import reflex_learning_engine
from reflex_system.reflex_integrity_sweep import reflex_integrity_sweep

@router.post("/integrity/sweep")
async def perform_integrity_sweep(
    current_user: User = Security(get_current_active_user, scopes=["admin"])
):
    """Perform reflex integrity sweep and archive state."""
    sweep_result = reflex_integrity_sweep.perform_sweep()
    return {
        "status": "success",
        "sweep_result": sweep_result,
        "system_status": "Fully Reflex-Operational"
    }
from reflex_system.reflex_pattern_analyzer import reflex_pattern_analyzer

reflex_bp = Blueprint('reflex', __name__)

@reflex_bp.route('/reflexes', methods=['GET'])
def get_reflexes():
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    filters = request.args.get('filters', {}, type=dict)
    
    logs = reflex_processor.get_logs(limit=limit, offset=offset, filters=filters)
    return jsonify(logs)

@reflex_bp.route('/reflexes/stats', methods=['GET'])
def get_reflex_stats():
    stats = reflex_processor.get_stats()
    return jsonify(stats)

@reflex_bp.route('/reflexes/patterns', methods=['GET'])
def get_patterns():
    patterns = reflex_pattern_analyzer.get_patterns()
    return jsonify(patterns)

@reflex_bp.route('/reflexes/learning', methods=['GET'])
def get_learning_status():
    status = reflex_learning_engine.get_status()
    return jsonify(status)
