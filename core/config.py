"""
Configuration management for SARYA system.
Handles loading, validation, and access to configuration.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("config")

# Default configuration
DEFAULT_CONFIG = {
    "system": {
        "log_level": "INFO",
        "debug_mode": False,
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "workers": 4,
        "jwt_secret": None,  # Will be loaded from environment
        "jwt_algorithm": "HS256",
        "jwt_expiration": 3600,  # 1 hour
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": None,  # Will be loaded from environment
    },
    "clone_system": {
        "max_workers": 10,
        "queue_timeout": 30,
        "heartbeat_interval": 5,
    },
    "plugins": {
        "enabled": True,
        "auto_discover": True,
        "plugin_dir": "plugins",
    },
    "metrics": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8001,
    },
    "reflex_system": {
        "emotional_reflex": {
            "enabled": True,
            "log_path": "logs/emotional_reflex.json",
        },
        "spiritual_reflex": {
            "enabled": True,
            "log_path": "logs/spiritual_reflex.json",
        },
    },
}

class ConfigManager:
    """
    Manages configuration for the SARYA system.
    
    Features:
    - Load from multiple sources (defaults, files, environment)
    - Environment variable overrides
    - Nested configuration access
    - Configuration validation
    """
    
    def __init__(self):
        self.config = {}
        self.loaded = False
        self.logger = logger
    
    def load(self, config_path: Optional[str] = None) -> bool:
        """
        Load configuration from default values, config file, and environment variables.
        
        Args:
            config_path: Path to JSON configuration file (optional)
            
        Returns:
            bool: True if configuration loaded successfully
        """
        # Start with default configuration
        self.config = DEFAULT_CONFIG.copy()
        
        # Load from config file if provided
        if config_path:
            path = Path(config_path)
            if path.exists() and path.is_file():
                try:
                    with open(path, 'r') as f:
                        file_config = json.load(f)
                    
                    # Merge file configuration with defaults
                    self._merge_config(self.config, file_config)
                    self.logger.info(f"Loaded configuration from {config_path}")
                except Exception as e:
                    self.logger.error(f"Error loading config file {config_path}: {str(e)}")
                    return False
            else:
                self.logger.warning(f"Config file not found: {config_path}")
        
        # Override with environment variables
        self._load_from_env()
        
        # Validate the configuration
        if not self._validate_config():
            self.logger.error("Configuration validation failed")
            return False
        
        self.loaded = True
        self.logger.info("Configuration loaded successfully")
        return True
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation path.
        
        Args:
            key_path: Dot-separated path to config value (e.g., "api.port")
            default: Default value if not found
            
        Returns:
            The configuration value or default if not found
        """
        if not self.loaded:
            self.logger.warning("Accessing configuration before load() is called")
        
        # Navigate nested dictionaries using the dot notation
        parts = key_path.split('.')
        current = self.config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot notation path.
        
        Args:
            key_path: Dot-separated path to config value (e.g., "api.port")
            value: Value to set
        """
        if not self.loaded:
            self.logger.warning("Modifying configuration before load() is called")
        
        # Navigate nested dictionaries using the dot notation
        parts = key_path.split('.')
        current = self.config
        
        # Navigate to the nested dictionary
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
    
    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively merge source dictionary into target dictionary.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary with values to merge
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
    
    def _load_from_env(self) -> None:
        """
        Load configuration values from environment variables.
        Environment variables should be prefixed with SARYA_ and 
        use underscores for nested paths (e.g., SARYA_API_PORT).
        """
        prefix = "SARYA_"
        
        for name, value in os.environ.items():
            if name.startswith(prefix):
                # Convert environment variable name to config path
                # SARYA_API_PORT -> api.port
                key_path = name[len(prefix):].lower().replace('_', '.')
                
                # Try to infer the type of the value
                typed_value = self._infer_type(value)
                
                # Set the value in the config
                self.set(key_path, typed_value)
                self.logger.debug(f"Env override: {key_path} = {typed_value}")
    
    def _infer_type(self, value: str) -> Any:
        """
        Infer the type of a config value from string.
        
        Args:
            value: String value to convert
            
        Returns:
            The value converted to its inferred type
        """
        # Check if it's a boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Check if it's an integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Check if it's a float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Check if it's a JSON object or array
        if (value.startswith('{') and value.endswith('}')) or \
           (value.startswith('[') and value.endswith(']')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Return as string by default
        return value
    
    def _validate_config(self) -> bool:
        """
        Validate that all required configuration values are present and valid.
        
        Returns:
            bool: True if configuration is valid
        """
        # Validate API configuration
        if self.get('api.jwt_secret') is None:
            self.set('api.jwt_secret', os.environ.get('SARYA_JWT_SECRET', 'insecure_default_secret'))
            if self.get('api.jwt_secret') == 'insecure_default_secret':
                self.logger.warning("Using insecure default JWT secret! Set SARYA_JWT_SECRET in production.")
        
        # Validate Redis configuration
        if self.get('redis.password') is None:
            self.set('redis.password', os.environ.get('SARYA_REDIS_PASSWORD', ''))
        
        return True

# Create a singleton instance
config_manager = ConfigManager()
