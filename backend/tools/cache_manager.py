"""
Redis Cache Manager
Caches SQL queries, schema, and expensive computations
"""
import redis
import json
import hashlib
from typing import Any, Optional
from datetime import timedelta

class CacheManager:
    """
    Handles caching with Redis
    
    Cache keys:
    - schema:* → Database schema (1 hour TTL)
    - query:* → SQL query results (10 min TTL)
    - plan:* → Execution plans (5 min TTL)

    """
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.default_ttl = 600  # 10 minutes

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
        
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set value in cache with TTL"""
        try:
            ttl = ttl or self.default_ttl
            self.client.setex(
            key,
            ttl,
            json.dumps(value, default=str)
            )
        
        except Exception as e:
            print(f"Cache set error: {e}")

    def delete(self, key: str):
        """Delete key from cache"""
        try:
            self.client.delete(key)
        except Exception as e:
            print(f"Cache delete error: {e}")

    def generate_query_key(self, sql: str) -> str:
        """Generate cache key for SQL query"""
        # Hash SQL to create unique key
        sql_hash = hashlib.md5(sql.encode()).hexdigest()
        return f"query: {sql_hash}"
    
    def cache_query_result(self, sql: str, results: list, ttl: int = 600):
        """Cache SQL query results"""
        key = self.generate_query_key(sql)
        self.set(key, results, ttl)
    
    def get_cached_query(self, sql: str) -> Optional[list]:
        """Get cached query results"""
        key = self.generate_query_key(sql)
        return self.get(key)
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        info = self.client.info('stats')
        return {
            'hits': info.get('keyspace_hits', 0),
            'misses': info.get('keyspace_misses', 0),
            'keys': self.client.dbsize()
        }
