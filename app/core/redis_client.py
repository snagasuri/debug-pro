"""Redis client configuration for caching with advanced functionality."""

import os
import json
import zlib
from typing import Optional, Any, Dict, List, Union
import redis
from redis.client import Redis
from redis.exceptions import RedisError

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
REDIS_TTL = int(os.environ.get("REDIS_CACHE_TTL", 3600))  # 1 hour default
COMPRESSION_THRESHOLD = 1024  # Compress values larger than 1KB
MAX_MEMORY_POLICY = "allkeys-lru"  # Evict least recently used keys when memory is full

class RedisClient:
    """Enhanced Redis client with advanced caching capabilities."""
    
    def __init__(self):
        """Initialize Redis client with configuration."""
        self.client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=5.0,
            retry_on_timeout=True
        )
        self._configure_client()
    
    def _configure_client(self) -> None:
        """Configure Redis client settings."""
        try:
            # Set memory management policy
            self.client.config_set('maxmemory-policy', MAX_MEMORY_POLICY)
        except RedisError:
            # Ignore if we can't set config (e.g., in restricted environments)
            pass
    
    def _compress(self, data: str) -> bytes:
        """Compress string data if it exceeds threshold."""
        encoded = data.encode('utf-8')
        if len(encoded) > COMPRESSION_THRESHOLD:
            return zlib.compress(encoded)
        return encoded
    
    def _decompress(self, data: bytes) -> str:
        """Decompress data if it was compressed."""
        try:
            return zlib.decompress(data).decode('utf-8')
        except zlib.error:
            return data.decode('utf-8')
    
    def get_cache_key(self, key_type: str, identifier: str) -> str:
        """Generate a standardized cache key."""
        return f"deebo:{key_type}:{identifier}"
    
    async def set_cache(
        self,
        key: str,
        value: Union[str, dict, list],
        ttl: Optional[int] = None,
        nx: bool = False  # Only set if key doesn't exist
    ) -> bool:
        """Set a value in Redis cache with optional TTL and compression."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            compressed = self._compress(value)
            return bool(
                self.client.set(
                    key,
                    compressed,
                    ex=ttl or REDIS_TTL,
                    nx=nx
                )
            )
        except RedisError as e:
            print(f"Redis set error: {str(e)}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get a value from Redis cache with automatic decompression."""
        try:
            data = self.client.get(key)
            if data is None:
                return None
            
            decompressed = self._decompress(data.encode('utf-8'))
            try:
                return json.loads(decompressed)
            except json.JSONDecodeError:
                return decompressed
        except RedisError as e:
            print(f"Redis get error: {str(e)}")
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """Delete a value from Redis cache."""
        try:
            return bool(self.client.delete(key))
        except RedisError as e:
            print(f"Redis delete error: {str(e)}")
            return False
    
    async def set_hash_cache(
        self,
        key: str,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Set a hash in Redis cache with optional TTL."""
        try:
            # Convert all values to strings
            string_mapping = {
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in mapping.items()
            }
            
            pipeline = self.client.pipeline()
            pipeline.hmset(key, string_mapping)
            if ttl:
                pipeline.expire(key, ttl)
            pipeline.execute()
            return True
        except RedisError as e:
            print(f"Redis hash set error: {str(e)}")
            return False
    
    async def get_hash_cache(self, key: str) -> Dict[str, Any]:
        """Get a hash from Redis cache with JSON deserialization."""
        try:
            result = self.client.hgetall(key)
            if not result:
                return None
            
            # Attempt to deserialize JSON values
            deserialized = {}
            for k, v in result.items():
                try:
                    deserialized[k] = json.loads(v)
                except json.JSONDecodeError:
                    deserialized[k] = v
            return deserialized
        except RedisError as e:
            print(f"Redis hash get error: {str(e)}")
            return None
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in Redis."""
        try:
            return self.client.incrby(key, amount)
        except RedisError as e:
            print(f"Redis increment error: {str(e)}")
            return None
    
    async def add_to_set(self, key: str, *values: str) -> bool:
        """Add values to a Redis set."""
        try:
            return bool(self.client.sadd(key, *values))
        except RedisError as e:
            print(f"Redis set add error: {str(e)}")
            return False
    
    async def get_set_members(self, key: str) -> List[str]:
        """Get all members of a Redis set."""
        try:
            return list(self.client.smembers(key))
        except RedisError as e:
            print(f"Redis set members error: {str(e)}")
            return []
    
    async def cleanup_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except RedisError as e:
            print(f"Redis cleanup error: {str(e)}")
            return 0
    
    async def flushdb(self) -> None:
        """Clear all keys in the current database."""
        try:
            self.client.flushdb()
        except RedisError as e:
            print(f"Redis flush error: {str(e)}")
    
    async def close(self) -> None:
        """Close the Redis connection."""
        try:
            self.client.close()
        except RedisError as e:
            print(f"Redis close error: {str(e)}")

# Global Redis client instance
redis_client = RedisClient()
