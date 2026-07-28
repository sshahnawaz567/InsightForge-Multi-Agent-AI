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
        # Bounded timeouts so a bad host (unreachable, not just refused)
        # can never block the event loop for long.
        self.client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        self.default_ttl = 600  # 10 minutes
        # Probe once at startup instead of on every get/set - avoids
        # reconnecting (and re-logging the same failure) on every query.
        self.available = self._check_available()

    def _check_available(self) -> bool:
        try:
            self.client.ping()
            return True
        except Exception:
            print("⚠️  Redis not available - caching disabled for this session")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.available:
            return None

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
        if not self.available:
            return

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
        if not self.available:
            return

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
        if not self.available:
            return {'hits': 0, 'misses': 0, 'keys': 0}

        try:
            info = self.client.info('stats')
            return {
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'keys': self.client.dbsize()
            }
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {'hits': 0, 'misses': 0, 'keys': 0}
