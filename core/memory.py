"""
Memory system for SARYA.
Provides persistent storage and retrieval of data.
"""
import json
import logging
import os
import pickle
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import redis
from redis.exceptions import RedisError

from core.base_module import BaseModule
from core.config import config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("memory")

class MemoryBackend(ABC):
    """Abstract base class for memory backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value with an optional TTL."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a value by key."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        pass
    
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern."""
        pass
    
    @abstractmethod
    def flush(self) -> bool:
        """Flush all data."""
        pass

class RedisMemoryBackend(MemoryBackend):
    """Redis-based memory backend."""
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379, 
        db: int = 0, 
        password: Optional[str] = None
    ):
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=False  # We handle encoding/decoding ourselves
        )
        self.logger = logging.getLogger("memory.redis")
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key."""
        try:
            value = self.redis.get(key)
            if value is None:
                return None
            return pickle.loads(value)
        except (RedisError, pickle.PickleError) as e:
            self.logger.error(f"Error retrieving key {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value with an optional TTL."""
        try:
            pickled_value = pickle.dumps(value)
            if ttl is not None:
                return bool(self.redis.setex(key, ttl, pickled_value))
            else:
                return bool(self.redis.set(key, pickled_value))
        except (RedisError, pickle.PickleError) as e:
            self.logger.error(f"Error storing key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a value by key."""
        try:
            return bool(self.redis.delete(key))
        except RedisError as e:
            self.logger.error(f"Error deleting key {key}: {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        try:
            return bool(self.redis.exists(key))
        except RedisError as e:
            self.logger.error(f"Error checking if key {key} exists: {str(e)}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern."""
        try:
            keys = self.redis.keys(pattern)
            return [k.decode('utf-8') for k in keys]
        except RedisError as e:
            self.logger.error(f"Error getting keys with pattern {pattern}: {str(e)}")
            return []
    
    def flush(self) -> bool:
        """Flush all data."""
        try:
            self.redis.flushdb()
            return True
        except RedisError as e:
            self.logger.error(f"Error flushing database: {str(e)}")
            return False

class FileMemoryBackend(MemoryBackend):
    """File-based memory backend."""
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, Any] = {}
        self.logger = logging.getLogger("memory.file")
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key."""
        # Check cache first
        if key in self.cache:
            return self.cache[key]
        
        # Check file
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                value = pickle.load(f)
            
            # Cache the value
            self.cache[key] = value
            return value
        except (IOError, pickle.PickleError) as e:
            self.logger.error(f"Error reading file for key {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value with an optional TTL."""
        # Store in cache
        self.cache[key] = value
        
        # Store in file
        file_path = self._get_file_path(key)
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save value to file
            with open(file_path, 'wb') as f:
                pickle.dump(value, f)
            
            # Handle TTL
            if ttl is not None:
                self._set_ttl(key, ttl)
            
            return True
        except (IOError, pickle.PickleError) as e:
            self.logger.error(f"Error writing file for key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a value by key."""
        # Remove from cache
        if key in self.cache:
            del self.cache[key]
        
        # Remove file
        file_path = self._get_file_path(key)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except IOError as e:
                self.logger.error(f"Error deleting file for key {key}: {str(e)}")
                return False
        
        return True
    
    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        # Check cache first
        if key in self.cache:
            return True
        
        # Check file
        file_path = self._get_file_path(key)
        return file_path.exists()
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern."""
        # Convert pattern to regex-like style
        import fnmatch
        
        keys = []
        
        # Walk through all files in base_dir
        for root, _, files in os.walk(self.base_dir):
            rel_root = os.path.relpath(root, self.base_dir)
            for file in files:
                if file.endswith('.pkl'):
                    if rel_root == '.':
                        key = file[:-4]  # Remove .pkl
                    else:
                        key = f"{rel_root}/{file[:-4]}"
                    
                    if fnmatch.fnmatch(key, pattern):
                        keys.append(key)
        
        return keys
    
    def flush(self) -> bool:
        """Flush all data."""
        try:
            # Clear cache
            self.cache.clear()
            
            # Remove all files
            for file_path in self.base_dir.glob('**/*.pkl'):
                file_path.unlink()
            
            return True
        except IOError as e:
            self.logger.error(f"Error flushing file backend: {str(e)}")
            return False
    
    def _get_file_path(self, key: str) -> Path:
        """Convert a key to a file path."""
        # Replace dangerous characters
        safe_key = key.replace('..', '')
        
        # Create path
        path = self.base_dir / f"{safe_key}.pkl"
        return path
    
    def _set_ttl(self, key: str, ttl: int) -> None:
        """Set a TTL for a key using a background thread."""
        import threading
        
        def delete_after_ttl():
            time.sleep(ttl)
            self.delete(key)
        
        thread = threading.Thread(target=delete_after_ttl)
        thread.daemon = True
        thread.start()

class MemorySystem(BaseModule):
    """
    Memory system for SARYA.
    
    Features:
    - Multiple storage backends (Redis, file)
    - Namespaced key management
    - Key expiration (TTL)
    - Serialization/deserialization
    - Transaction support
    """
    
    def __init__(self):
        super().__init__("MemorySystem")
        self.backends: Dict[str, MemoryBackend] = {}
        self.default_backend = "redis"
        self.default_namespace = "sarya"
        self.transactions: Dict[str, List[Tuple[str, str, Any, Optional[int]]]] = {}
    
    def _initialize(self) -> bool:
        """Initialize the memory system."""
        # Configure Redis backend
        redis_host = config_manager.get("redis.host", "localhost")
        redis_port = config_manager.get("redis.port", 6379)
        redis_db = config_manager.get("redis.db", 0)
        redis_password = config_manager.get("redis.password", None)
        
        try:
            redis_backend = RedisMemoryBackend(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password
            )
            self.backends["redis"] = redis_backend
            self.logger.info(f"Initialized Redis backend at {redis_host}:{redis_port}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis backend: {str(e)}")
            self.logger.info("Falling back to file backend as default")
            self.default_backend = "file"
        
        # Configure file backend
        file_backend = FileMemoryBackend(base_dir="data")
        self.backends["file"] = file_backend
        self.logger.info("Initialized file backend at data/")
        
        return len(self.backends) > 0
    
    def _start(self) -> bool:
        """Start the memory system."""
        return True
    
    def _stop(self) -> bool:
        """Stop the memory system."""
        self.backends.clear()
        return True
    
    def get(
        self, 
        key: str, 
        namespace: Optional[str] = None, 
        backend: Optional[str] = None
    ) -> Optional[Any]:
        """
        Retrieve a value from memory.
        
        Args:
            key: The key to retrieve
            namespace: Optional namespace (defaults to default_namespace)
            backend: Optional backend name (defaults to default_backend)
            
        Returns:
            The value or None if not found
        """
        ns = namespace or self.default_namespace
        be = backend or self.default_backend
        
        if be not in self.backends:
            self.logger.error(f"Backend {be} not found")
            return None
        
        full_key = f"{ns}:{key}"
        return self.backends[be].get(full_key)
    
    def set(
        self, 
        key: str, 
        value: Any, 
        namespace: Optional[str] = None, 
        backend: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store a value in memory.
        
        Args:
            key: The key to store
            value: The value to store
            namespace: Optional namespace (defaults to default_namespace)
            backend: Optional backend name (defaults to default_backend)
            ttl: Optional time-to-live in seconds
            
        Returns:
            bool: True if the value was stored successfully
        """
        ns = namespace or self.default_namespace
        be = backend or self.default_backend
        
        if be not in self.backends:
            self.logger.error(f"Backend {be} not found")
            return False
        
        full_key = f"{ns}:{key}"
        return self.backends[be].set(full_key, value, ttl)
    
    def delete(
        self, 
        key: str, 
        namespace: Optional[str] = None, 
        backend: Optional[str] = None
    ) -> bool:
        """
        Delete a value from memory.
        
        Args:
            key: The key to delete
            namespace: Optional namespace (defaults to default_namespace)
            backend: Optional backend name (defaults to default_backend)
            
        Returns:
            bool: True if the value was deleted successfully
        """
        ns = namespace or self.default_namespace
        be = backend or self.default_backend
        
        if be not in self.backends:
            self.logger.error(f"Backend {be} not found")
            return False
        
        full_key = f"{ns}:{key}"
        return self.backends[be].delete(full_key)
    
    def exists(
        self, 
        key: str, 
        namespace: Optional[str] = None, 
        backend: Optional[str] = None
    ) -> bool:
        """
        Check if a key exists in memory.
        
        Args:
            key: The key to check
            namespace: Optional namespace (defaults to default_namespace)
            backend: Optional backend name (defaults to default_backend)
            
        Returns:
            bool: True if the key exists
        """
        ns = namespace or self.default_namespace
        be = backend or self.default_backend
        
        if be not in self.backends:
            self.logger.error(f"Backend {be} not found")
            return False
        
        full_key = f"{ns}:{key}"
        return self.backends[be].exists(full_key)
    
    def keys(
        self, 
        pattern: str = "*", 
        namespace: Optional[str] = None, 
        backend: Optional[str] = None
    ) -> List[str]:
        """
        Get keys matching a pattern.
        
        Args:
            pattern: Pattern to match
            namespace: Optional namespace (defaults to default_namespace)
            backend: Optional backend name (defaults to default_backend)
            
        Returns:
            List of matching keys
        """
        ns = namespace or self.default_namespace
        be = backend or self.default_backend
        
        if be not in self.backends:
            self.logger.error(f"Backend {be} not found")
            return []
        
        full_pattern = f"{ns}:{pattern}"
        full_keys = self.backends[be].keys(full_pattern)
        
        # Strip namespace from keys
        prefix = f"{ns}:"
        return [k[len(prefix):] for k in full_keys if k.startswith(prefix)]
    
    def flush(
        self, 
        namespace: Optional[str] = None, 
        backend: Optional[str] = None
    ) -> bool:
        """
        Flush a namespace or entire backend.
        
        Args:
            namespace: Optional namespace to flush (if None, flush all)
            backend: Optional backend name (defaults to default_backend)
            
        Returns:
            bool: True if the flush was successful
        """
        be = backend or self.default_backend
        
        if be not in self.backends:
            self.logger.error(f"Backend {be} not found")
            return False
        
        if namespace:
            # Delete all keys in the namespace
            keys = self.backends[be].keys(f"{namespace}:*")
            for key in keys:
                self.backends[be].delete(key)
            return True
        else:
            # Flush the entire backend
            return self.backends[be].flush()
    
    @contextmanager
    def transaction(self, namespace: Optional[str] = None, backend: Optional[str] = None):
        """
        Create a transaction context.
        
        Args:
            namespace: Optional namespace (defaults to default_namespace)
            backend: Optional backend name (defaults to default_backend)
            
        Yields:
            TransactionContext: Transaction context
        """
        ns = namespace or self.default_namespace
        be = backend or self.default_backend
        
        if be not in self.backends:
            self.logger.error(f"Backend {be} not found")
            raise ValueError(f"Backend {be} not found")
        
        # Create transaction ID
        transaction_id = f"{ns}:{be}:{str(uuid.uuid4())}"
        self.transactions[transaction_id] = []
        
        try:
            # Create transaction context
            ctx = TransactionContext(self, transaction_id, ns, be)
            yield ctx
            
            # Commit the transaction
            self._commit_transaction(transaction_id)
        except Exception as e:
            # Rollback on error
            self._rollback_transaction(transaction_id)
            raise e
        finally:
            # Clean up
            if transaction_id in self.transactions:
                del self.transactions[transaction_id]
    
    def _commit_transaction(self, transaction_id: str) -> bool:
        """
        Commit a transaction.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            bool: True if the transaction was committed successfully
        """
        if transaction_id not in self.transactions:
            self.logger.error(f"Transaction {transaction_id} not found")
            return False
        
        # Execute the transaction
        operations = self.transactions[transaction_id]
        success = True
        
        for op_type, key, value, ttl in operations:
            if op_type == "set":
                if not self.backends[value[0]].set(key, value[1], ttl):
                    success = False
                    break
            elif op_type == "delete":
                if not self.backends[value[0]].delete(key):
                    success = False
                    break
        
        return success
    
    def _rollback_transaction(self, transaction_id: str) -> None:
        """
        Rollback a transaction.
        
        Args:
            transaction_id: ID of the transaction
        """
        if transaction_id in self.transactions:
            self.logger.info(f"Rolling back transaction {transaction_id}")
            self.transactions[transaction_id] = []

class TransactionContext:
    """Context for a memory transaction."""
    
    def __init__(self, memory_system: MemorySystem, transaction_id: str, namespace: str, backend: str):
        self.memory_system = memory_system
        self.transaction_id = transaction_id
        self.namespace = namespace
        self.backend = backend
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Add a set operation to the transaction."""
        full_key = f"{self.namespace}:{key}"
        self.memory_system.transactions[self.transaction_id].append(
            ("set", full_key, (self.backend, value), ttl)
        )
    
    def delete(self, key: str) -> None:
        """Add a delete operation to the transaction."""
        full_key = f"{self.namespace}:{key}"
        self.memory_system.transactions[self.transaction_id].append(
            ("delete", full_key, (self.backend, None), None)
        )

# Create a singleton instance
memory_system = MemorySystem()
