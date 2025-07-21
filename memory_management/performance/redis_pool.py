"""
Redis connection pooling and caching strategies for STM operations.

Implements connection pooling, query result caching, and performance optimizations
for Redis-based Short-Term Memory operations.
"""

import redis
import redis.connection
from redis.connection import ConnectionPool
import json
import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from functools import wraps
import hashlib

from ..config.settings import get_settings


class RedisConnectionPool:
    """
    Enhanced Redis connection pool with performance optimizations.
    
    Provides connection pooling, automatic failover, and connection health monitoring
    for optimal Redis performance.
    """
    
    def __init__(self, config=None):
        """
        Initialize Redis connection pool with performance settings.
        
        Args:
            config: Redis configuration object (uses global settings if None)
        """
        self.config = config or get_settings().redis
        self.logger = logging.getLogger(__name__)
        
        # Create connection pool with optimized settings
        self.pool = ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password,
            max_connections=self.config.connection_pool_max_connections,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_keepalive=self.config.socket_keepalive,
            socket_keepalive_options=self.config.socket_keepalive_options,
            retry_on_timeout=self.config.retry_on_timeout,
            health_check_interval=self.config.health_check_interval,
            # Performance optimizations
            decode_responses=True,
            encoding='utf-8',
            encoding_errors='strict'
        )
        
        # Create Redis client with pool
        self.client = redis.Redis(connection_pool=self.pool)
        
        # Performance metrics
        self.metrics = {
            'connections_created': 0,
            'connections_reused': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'query_times': [],
            'last_health_check': None
        }
        
        # Test connection
        self._test_connection()
        
        self.logger.info(f"Redis connection pool initialized with {self.config.connection_pool_max_connections} max connections")
    
    def _test_connection(self) -> None:
        """Test Redis connection and log performance info."""
        try:
            start_time = time.time()
            result = self.client.ping()
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if result:
                self.logger.info(f"Redis connection test successful (response time: {response_time:.2f}ms)")
                self.metrics['last_health_check'] = datetime.utcnow()
            else:
                raise redis.ConnectionError("Ping failed")
                
        except Exception as e:
            self.logger.error(f"Redis connection test failed: {e}")
            raise
    
    def get_client(self) -> redis.Redis:
        """
        Get Redis client from pool.
        
        Returns:
            Redis client instance
        """
        return self.client
    
    def execute_with_timing(self, operation_name: str, func, *args, **kwargs):
        """
        Execute Redis operation with performance timing.
        
        Args:
            operation_name: Name of the operation for metrics
            func: Function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result and execution time
        """
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Track performance metrics
            self.metrics['query_times'].append({
                'operation': operation_name,
                'time_ms': execution_time,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Keep only last 1000 query times for memory efficiency
            if len(self.metrics['query_times']) > 1000:
                self.metrics['query_times'] = self.metrics['query_times'][-1000:]
            
            self.logger.debug(f"Redis {operation_name} completed in {execution_time:.2f}ms")
            return result, execution_time
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.error(f"Redis {operation_name} failed after {execution_time:.2f}ms: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of Redis connection pool.
        
        Returns:
            Dictionary with health status and performance metrics
        """
        try:
            start_time = time.time()
            
            # Test basic connectivity
            ping_result = self.client.ping()
            ping_time = (time.time() - start_time) * 1000
            
            # Get connection pool info
            pool_info = {
                'max_connections': self.pool.max_connections,
                'created_connections': self.pool.created_connections,
                'available_connections': len(self.pool._available_connections),
                'in_use_connections': len(self.pool._in_use_connections)
            }
            
            # Calculate performance metrics
            recent_queries = [q for q in self.metrics['query_times'] 
                            if datetime.fromisoformat(q['timestamp']) > datetime.utcnow() - timedelta(minutes=5)]
            
            avg_response_time = sum(q['time_ms'] for q in recent_queries) / len(recent_queries) if recent_queries else 0
            
            health_status = {
                'status': 'healthy' if ping_result else 'unhealthy',
                'ping_time_ms': ping_time,
                'pool_info': pool_info,
                'performance_metrics': {
                    'avg_response_time_5min_ms': avg_response_time,
                    'total_queries': len(self.metrics['query_times']),
                    'cache_hit_rate': self._calculate_cache_hit_rate(),
                    'connections_reuse_rate': self._calculate_connection_reuse_rate()
                },
                'last_health_check': datetime.utcnow().isoformat()
            }
            
            self.metrics['last_health_check'] = datetime.utcnow()
            return health_status
            
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_health_check': datetime.utcnow().isoformat()
            }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_requests = self.metrics['cache_hits'] + self.metrics['cache_misses']
        if total_requests == 0:
            return 0.0
        return (self.metrics['cache_hits'] / total_requests) * 100
    
    def _calculate_connection_reuse_rate(self) -> float:
        """Calculate connection reuse rate percentage."""
        total_connections = self.metrics['connections_created'] + self.metrics['connections_reused']
        if total_connections == 0:
            return 0.0
        return (self.metrics['connections_reused'] / total_connections) * 100
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get detailed performance metrics.
        
        Returns:
            Dictionary with performance statistics
        """
        recent_queries = [q for q in self.metrics['query_times'] 
                        if datetime.fromisoformat(q['timestamp']) > datetime.utcnow() - timedelta(hours=1)]
        
        if recent_queries:
            query_times = [q['time_ms'] for q in recent_queries]
            avg_time = sum(query_times) / len(query_times)
            min_time = min(query_times)
            max_time = max(query_times)
            
            # Calculate percentiles
            sorted_times = sorted(query_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            avg_time = min_time = max_time = p50 = p95 = p99 = 0
        
        return {
            'query_performance': {
                'total_queries_1h': len(recent_queries),
                'avg_response_time_ms': avg_time,
                'min_response_time_ms': min_time,
                'max_response_time_ms': max_time,
                'p50_response_time_ms': p50,
                'p95_response_time_ms': p95,
                'p99_response_time_ms': p99
            },
            'cache_performance': {
                'hit_rate_percent': self._calculate_cache_hit_rate(),
                'total_hits': self.metrics['cache_hits'],
                'total_misses': self.metrics['cache_misses']
            },
            'connection_performance': {
                'reuse_rate_percent': self._calculate_connection_reuse_rate(),
                'pool_utilization_percent': (len(self.pool._in_use_connections) / self.pool.max_connections) * 100,
                'created_connections': self.metrics['connections_created'],
                'reused_connections': self.metrics['connections_reused']
            }
        }
    
    def close(self) -> None:
        """Close connection pool and cleanup resources."""
        try:
            self.pool.disconnect()
            self.logger.info("Redis connection pool closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis connection pool: {e}")


class RedisCacheManager:
    """
    Advanced caching manager for Redis with query result caching and TTL management.
    
    Implements intelligent caching strategies for frequently accessed data
    to improve response times.
    """
    
    def __init__(self, redis_pool: RedisConnectionPool):
        """
        Initialize cache manager with Redis pool.
        
        Args:
            redis_pool: RedisConnectionPool instance
        """
        self.redis_pool = redis_pool
        self.client = redis_pool.get_client()
        self.logger = logging.getLogger(__name__)
        
        # Cache configuration
        self.default_ttl = 300  # 5 minutes
        self.cache_prefix = "cache:"
        
        # Performance tracking
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
    
    def _generate_cache_key(self, operation: str, *args, **kwargs) -> str:
        """
        Generate cache key from operation and parameters.
        
        Args:
            operation: Operation name
            *args, **kwargs: Operation parameters
            
        Returns:
            Cache key string
        """
        # Create deterministic key from operation and parameters
        key_data = {
            'operation': operation,
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{self.cache_prefix}{operation}:{key_hash}"
    
    def get_cached_result(self, operation: str, *args, **kwargs) -> Optional[Any]:
        """
        Get cached result for operation.
        
        Args:
            operation: Operation name
            *args, **kwargs: Operation parameters
            
        Returns:
            Cached result or None if not found
        """
        cache_key = self._generate_cache_key(operation, *args, **kwargs)
        
        try:
            result, _ = self.redis_pool.execute_with_timing(
                f"cache_get_{operation}",
                self.client.get,
                cache_key
            )
            
            if result:
                self.cache_stats['hits'] += 1
                self.redis_pool.metrics['cache_hits'] += 1
                self.logger.debug(f"Cache hit for {operation}")
                return json.loads(result)
            else:
                self.cache_stats['misses'] += 1
                self.redis_pool.metrics['cache_misses'] += 1
                self.logger.debug(f"Cache miss for {operation}")
                return None
                
        except Exception as e:
            self.logger.error(f"Cache get error for {operation}: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def set_cached_result(self, operation: str, result: Any, ttl: int = None, *args, **kwargs) -> bool:
        """
        Set cached result for operation.
        
        Args:
            operation: Operation name
            result: Result to cache
            ttl: Time to live in seconds (uses default if None)
            *args, **kwargs: Operation parameters
            
        Returns:
            True if cached successfully
        """
        cache_key = self._generate_cache_key(operation, *args, **kwargs)
        ttl = ttl or self.default_ttl
        
        try:
            serialized_result = json.dumps(result, default=str)
            
            success, _ = self.redis_pool.execute_with_timing(
                f"cache_set_{operation}",
                self.client.setex,
                cache_key,
                ttl,
                serialized_result
            )
            
            if success:
                self.cache_stats['sets'] += 1
                self.logger.debug(f"Cached result for {operation} (TTL: {ttl}s)")
                return True
            else:
                self.logger.warning(f"Failed to cache result for {operation}")
                return False
                
        except Exception as e:
            self.logger.error(f"Cache set error for {operation}: {e}")
            return False
    
    def invalidate_cache(self, pattern: str = None) -> int:
        """
        Invalidate cached results matching pattern.
        
        Args:
            pattern: Cache key pattern (invalidates all if None)
            
        Returns:
            Number of keys deleted
        """
        try:
            if pattern:
                search_pattern = f"{self.cache_prefix}{pattern}*"
            else:
                search_pattern = f"{self.cache_prefix}*"
            
            keys = self.client.keys(search_pattern)
            if keys:
                deleted, _ = self.redis_pool.execute_with_timing(
                    "cache_invalidate",
                    self.client.delete,
                    *keys
                )
                self.cache_stats['deletes'] += deleted
                self.logger.info(f"Invalidated {deleted} cache entries")
                return deleted
            else:
                return 0
                
        except Exception as e:
            self.logger.error(f"Cache invalidation error: {e}")
            return 0
    
    def cached_operation(self, operation_name: str, ttl: int = None):
        """
        Decorator for caching operation results.
        
        Args:
            operation_name: Name of the operation for cache key
            ttl: Cache TTL in seconds
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Try to get cached result
                cached_result = self.get_cached_result(operation_name, *args, **kwargs)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set_cached_result(operation_name, result, ttl, *args, **kwargs)
                
                return result
            return wrapper
        return decorator
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'performance': {
                'hit_rate_percent': hit_rate,
                'total_requests': total_requests,
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses']
            },
            'operations': {
                'sets': self.cache_stats['sets'],
                'deletes': self.cache_stats['deletes'],
                'evictions': self.cache_stats['evictions']
            },
            'configuration': {
                'default_ttl_seconds': self.default_ttl,
                'cache_prefix': self.cache_prefix
            }
        }
    
    def optimize_cache_settings(self) -> Dict[str, Any]:
        """
        Analyze cache performance and suggest optimizations.
        
        Returns:
            Dictionary with optimization recommendations
        """
        stats = self.get_cache_stats()
        hit_rate = stats['performance']['hit_rate_percent']
        
        recommendations = []
        
        if hit_rate < 50:
            recommendations.append({
                'type': 'ttl_increase',
                'message': 'Consider increasing cache TTL to improve hit rate',
                'suggested_ttl': self.default_ttl * 2
            })
        
        if hit_rate > 90:
            recommendations.append({
                'type': 'ttl_decrease',
                'message': 'Cache hit rate is very high, consider reducing TTL to save memory',
                'suggested_ttl': max(60, self.default_ttl // 2)
            })
        
        if stats['operations']['sets'] > stats['operations']['hits']:
            recommendations.append({
                'type': 'cache_strategy',
                'message': 'More cache sets than hits, review caching strategy'
            })
        
        return {
            'current_performance': stats,
            'recommendations': recommendations,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }


# Global instances
_redis_pool = None
_cache_manager = None


def get_redis_pool() -> RedisConnectionPool:
    """Get global Redis connection pool instance."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = RedisConnectionPool()
    return _redis_pool


def get_cache_manager() -> RedisCacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = RedisCacheManager(get_redis_pool())
    return _cache_manager


def close_connections():
    """Close all Redis connections."""
    global _redis_pool, _cache_manager
    if _redis_pool:
        _redis_pool.close()
        _redis_pool = None
    _cache_manager = None