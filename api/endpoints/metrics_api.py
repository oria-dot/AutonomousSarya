"""
Metrics API endpoints for SARYA.
Provides endpoints for system metrics.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security, status
from pydantic import BaseModel, Field

from api.auth import User, get_current_active_user
from metrics.prometheus_metrics import metrics_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metrics_api")

# Create router
router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
    responses={404: {"description": "Not found"}},
)

# Models
class MetricInfo(BaseModel):
    """Information about a metric."""
    name: str
    description: str
    type: str
    labels: List[str] = Field(default_factory=list)

class MetricValue(BaseModel):
    """Value of a metric."""
    name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: float

class SystemStats(BaseModel):
    """System statistics."""
    uptime: float
    clone_count: int
    active_clones: int
    queue_size: int
    plugin_count: int
    event_count: int
    memory_usage: Dict[str, float] = Field(default_factory=dict)

# Endpoints
@router.get("/", response_model=List[MetricInfo])
async def get_metrics(
    current_user: User = Security(get_current_active_user, scopes=["read", "metrics"]),
):
    """Get all available metrics."""
    return metrics_manager.get_metric_info()

@router.get("/values", response_model=List[MetricValue])
async def get_metric_values(
    name: Optional[str] = Query(None, description="Filter by metric name"),
    current_user: User = Security(get_current_active_user, scopes=["read", "metrics"]),
):
    """Get current values of metrics."""
    return metrics_manager.get_metric_values(name)

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Security(get_current_active_user, scopes=["read", "metrics"]),
):
    """Get system statistics."""
    return metrics_manager.get_system_stats()

@router.get("/prometheus")
async def get_prometheus_metrics(
    current_user: User = Security(get_current_active_user, scopes=["read", "metrics"]),
):
    """Get metrics in Prometheus format."""
    metrics_text = metrics_manager.get_prometheus_metrics()
    return metrics_text
