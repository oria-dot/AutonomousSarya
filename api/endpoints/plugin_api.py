"""
Plugin API endpoints for SARYA.
Provides endpoints for plugin management.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security, status
from pydantic import BaseModel, Field

from api.auth import User, get_current_active_user
from core.plugin_manager import plugin_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("plugin_api")

# Create router
router = APIRouter(
    prefix="/plugins",
    tags=["Plugins"],
    responses={404: {"description": "Not found"}},
)

# Models
class PluginInfo(BaseModel):
    """Information about a plugin."""
    plugin_id: str
    name: str
    description: str
    version: str
    enabled: bool
    running: bool
    
class PluginAction(BaseModel):
    """Request body for plugin actions."""
    action: str = Field(..., description="Action to perform: load, unload, enable, disable")

class PluginConfig(BaseModel):
    """Plugin configuration."""
    config: Dict = Field(default_factory=dict)

# Endpoints
@router.get("/", response_model=List[PluginInfo])
async def get_plugins(
    current_user: User = Security(get_current_active_user, scopes=["read"]),
):
    """Get all available plugins."""
    # Get all plugin types
    plugin_types = plugin_manager.get_available_plugins()
    disabled_plugins = plugin_manager.get_disabled_plugins()
    loaded_plugins = plugin_manager.get_loaded_plugins()
    
    result = []
    for plugin_id in plugin_types:
        # Check plugin status
        is_enabled = plugin_id not in disabled_plugins
        is_loaded = plugin_id in loaded_plugins
        is_running = is_loaded and loaded_plugins[plugin_id].is_running()
        
        # Get plugin info
        if is_loaded:
            plugin = loaded_plugins[plugin_id]
            name = plugin.name
            description = plugin.description
            version = plugin.version
        else:
            # Use default values for unloaded plugins
            name = plugin_id
            description = "Plugin not loaded"
            version = "unknown"
        
        # Create response object
        result.append(
            PluginInfo(
                plugin_id=plugin_id,
                name=name,
                description=description,
                version=version,
                enabled=is_enabled,
                running=is_running
            )
        )
    
    return result

@router.get("/{plugin_id}", response_model=PluginInfo)
async def get_plugin(
    plugin_id: str = Path(..., description="ID of the plugin"),
    current_user: User = Security(get_current_active_user, scopes=["read"]),
):
    """Get information about a specific plugin."""
    # Check if plugin exists
    if plugin_id not in plugin_manager.get_available_plugins():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    # Check plugin status
    is_enabled = plugin_id not in plugin_manager.get_disabled_plugins()
    loaded_plugins = plugin_manager.get_loaded_plugins()
    is_loaded = plugin_id in loaded_plugins
    is_running = is_loaded and loaded_plugins[plugin_id].is_running()
    
    # Get plugin info
    if is_loaded:
        plugin = loaded_plugins[plugin_id]
        name = plugin.name
        description = plugin.description
        version = plugin.version
    else:
        # Use default values for unloaded plugins
        name = plugin_id
        description = "Plugin not loaded"
        version = "unknown"
    
    # Create response object
    return PluginInfo(
        plugin_id=plugin_id,
        name=name,
        description=description,
        version=version,
        enabled=is_enabled,
        running=is_running
    )

@router.post("/{plugin_id}/action")
async def perform_plugin_action(
    plugin_action: PluginAction,
    plugin_id: str = Path(..., description="ID of the plugin"),
    current_user: User = Security(get_current_active_user, scopes=["write", "plugin"]),
):
    """Perform an action on a plugin."""
    # Check if plugin exists
    if plugin_id not in plugin_manager.get_available_plugins():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found",
        )
    
    # Perform the action
    result = False
    if plugin_action.action == "load":
        result = plugin_manager.load_plugin(plugin_id)
    elif plugin_action.action == "unload":
        result = plugin_manager.unload_plugin(plugin_id)
    elif plugin_action.action == "enable":
        result = plugin_manager.enable_plugin(plugin_id)
    elif plugin_action.action == "disable":
        result = plugin_manager.disable_plugin(plugin_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{plugin_action.action}'",
        )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {plugin_action.action} plugin '{plugin_id}'",
        )
    
    return {
        "status": "success", 
        "message": f"Action '{plugin_action.action}' performed on plugin '{plugin_id}'",
        "timestamp": datetime.now().isoformat()
    }

@router.post("/{plugin_id}/config")
async def update_plugin_config(
    plugin_config: PluginConfig,
    plugin_id: str = Path(..., description="ID of the plugin"),
    current_user: User = Security(get_current_active_user, scopes=["write", "plugin"]),
):
    """Update plugin configuration."""
    # Check if plugin exists and is loaded
    loaded_plugins = plugin_manager.get_loaded_plugins()
    if plugin_id not in loaded_plugins:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_id}' not found or not loaded",
        )
    
    # Get plugin
    plugin = loaded_plugins[plugin_id]
    
    # Update config
    try:
        plugin.update_config(plugin_config.config)
        return {
            "status": "success", 
            "message": f"Configuration updated for plugin '{plugin_id}'",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception(f"Error updating plugin config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update plugin configuration: {str(e)}",
        )

@router.post("/discover")
async def discover_plugins(
    current_user: User = Security(get_current_active_user, scopes=["write", "plugin"]),
):
    """Discover new plugins."""
    try:
        discovered = plugin_manager.discover_plugins()
        return {
            "status": "success", 
            "message": f"Discovered {len(discovered)} plugins",
            "discovered": discovered,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception(f"Error discovering plugins: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover plugins: {str(e)}",
        )
