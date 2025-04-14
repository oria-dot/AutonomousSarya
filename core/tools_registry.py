#!/usr/bin/env python3
"""
Tools Registry for SARYA.
Manages the registration and access to external and internal tools.
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional

from core.base_module import BaseModule

logger = logging.getLogger(__name__)

class ToolsRegistry(BaseModule):
    """
    Registry for tools and external services that SARYA can use.
    """
    
    def __init__(self):
        """Initialize the ToolsRegistry."""
        super().__init__(name="ToolsRegistry")
        self.tools = {}
        self.registry_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tools_registry.json")
    
    def _start(self) -> bool:
        """Start the tools registry module."""
        return True
        
    def _stop(self) -> bool:
        """Stop the tools registry module."""
        return True
        
    def _initialize(self) -> bool:
        """
        Initialize the registry by loading tool definitions from file.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            if os.path.exists(self.registry_path):
                with open(self.registry_path, 'r') as f:
                    self.tools = json.load(f)
                logger.info(f"Loaded {len(self.tools)} tools from registry")
            else:
                logger.warning(f"Tools registry file not found at {self.registry_path}")
                self.tools = {}
            return True
        except Exception as e:
            logger.error(f"Error initializing tools registry: {e}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool definition or None if not found
        """
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tools in the registry.
        
        Returns:
            Dictionary of all tools
        """
        return self.tools
    
    def get_tools_by_type(self, tool_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Get tools by type.
        
        Args:
            tool_type: Type of tool to filter by
            
        Returns:
            Dictionary of tools of the specified type
        """
        return {name: tool for name, tool in self.tools.items() 
                if tool.get('type') == tool_type}
    
    def get_enabled_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all enabled tools.
        
        Returns:
            Dictionary of enabled tools
        """
        return {name: tool for name, tool in self.tools.items() 
                if tool.get('status') == 'enabled'}
    
    def add_tool(self, tool_name: str, tool_definition: Dict[str, Any]) -> bool:
        """
        Add a new tool to the registry.
        
        Args:
            tool_name: Name of the tool
            tool_definition: Tool definition
            
        Returns:
            bool: True if the tool was added successfully
        """
        try:
            self.tools[tool_name] = tool_definition
            self._save_registry()
            logger.info(f"Added tool {tool_name} to registry")
            return True
        except Exception as e:
            logger.error(f"Error adding tool {tool_name} to registry: {e}")
            return False
    
    def update_tool(self, tool_name: str, tool_definition: Dict[str, Any]) -> bool:
        """
        Update an existing tool in the registry.
        
        Args:
            tool_name: Name of the tool
            tool_definition: Updated tool definition
            
        Returns:
            bool: True if the tool was updated successfully
        """
        if tool_name not in self.tools:
            logger.error(f"Tool {tool_name} not found in registry")
            return False
        
        try:
            self.tools[tool_name] = tool_definition
            self._save_registry()
            logger.info(f"Updated tool {tool_name} in registry")
            return True
        except Exception as e:
            logger.error(f"Error updating tool {tool_name} in registry: {e}")
            return False
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            bool: True if the tool was removed successfully
        """
        if tool_name not in self.tools:
            logger.error(f"Tool {tool_name} not found in registry")
            return False
        
        try:
            del self.tools[tool_name]
            self._save_registry()
            logger.info(f"Removed tool {tool_name} from registry")
            return True
        except Exception as e:
            logger.error(f"Error removing tool {tool_name} from registry: {e}")
            return False
    
    def _save_registry(self) -> bool:
        """
        Save the registry to file.
        
        Returns:
            bool: True if the registry was saved successfully
        """
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            with open(self.registry_path, 'w') as f:
                json.dump(self.tools, f, indent=4)
            logger.info(f"Saved tools registry to {self.registry_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving tools registry: {e}")
            return False
    
    def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[Any]:
        """
        Invoke a tool with specified parameters.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters to pass to the tool
            
        Returns:
            Result of the tool invocation, or None if the tool is not found or invocation fails
        """
        tool = self.get_tool(tool_name)
        if not tool:
            logger.error(f"Tool {tool_name} not found in registry")
            return None
        
        if tool.get('status') != 'enabled':
            logger.error(f"Tool {tool_name} is not enabled")
            return None
        
        try:
            access_method = tool.get('access_method')
            
            if access_method == 'http_webhook':
                return self._invoke_webhook_tool(tool, parameters)
            elif access_method == 'internal_prompt':
                return self._invoke_internal_prompt_tool(tool, parameters)
            elif access_method == 'api_prompt':
                return self._invoke_api_prompt_tool(tool, parameters)
            else:
                logger.error(f"Unsupported access method {access_method} for tool {tool_name}")
                return None
        except Exception as e:
            logger.error(f"Error invoking tool {tool_name}: {e}")
            return None
    
    def _invoke_webhook_tool(self, tool: Dict[str, Any], parameters: Dict[str, Any]) -> Optional[Any]:
        """
        Invoke a webhook-based tool.
        
        Args:
            tool: Tool definition
            parameters: Parameters to pass to the tool
            
        Returns:
            Response from the webhook
        """
        webhook_url = tool.get('webhook_url')
        if not webhook_url:
            logger.error(f"No webhook URL specified for tool {tool.get('name')}")
            return None
        
        try:
            response = requests.post(webhook_url, json=parameters, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error invoking webhook tool: {e}")
            return None
    
    def _invoke_internal_prompt_tool(self, tool: Dict[str, Any], parameters: Dict[str, Any]) -> Optional[Any]:
        """
        Invoke an internal prompt-based tool.
        
        Args:
            tool: Tool definition
            parameters: Parameters to pass to the tool
            
        Returns:
            Result of the internal prompt
        """
        # Placeholder for internal prompt implementation
        logger.info(f"Invoking internal prompt tool with parameters: {parameters}")
        return {"status": "not_implemented", "message": "Internal prompt tools not yet implemented"}
    
    def _invoke_api_prompt_tool(self, tool: Dict[str, Any], parameters: Dict[str, Any]) -> Optional[Any]:
        """
        Invoke an API-based prompt tool.
        
        Args:
            tool: Tool definition
            parameters: Parameters to pass to the tool
            
        Returns:
            Response from the API
        """
        # Placeholder for API prompt implementation
        logger.info(f"Invoking API prompt tool with parameters: {parameters}")
        return {"status": "not_implemented", "message": "API prompt tools not yet implemented"}