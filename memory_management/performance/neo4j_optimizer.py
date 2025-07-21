"""
Neo4j query optimization and indexing for LTM operations.

Implements query optimization, proper indexing, and performance monitoring
for Neo4j-based Long-Term Memory operations.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, TransientError
from datetime import datetime, timedelta
from functools import wraps
import json

from ..config.settings import get_settings


class Neo4jQueryOptimizer:
    """
    Neo4j query optimizer with performance monitoring and index management.
    
    Provides optimized queries, automatic indexing, and performance tracking
    for Neo4j-based LTM operations.
    """
    
    def __init__(self, driver: Driver = None):
        """
        Initialize Neo4j optimizer.
        
        Args:
            driver: Neo4j driver instance (creates new if None)
        """
        self.config = get_settings().neo4j
        self.logger = logging.getLogger(__name__)
        
        if driver:
            self.driver = driver
        else:
            self.driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
                max_connection_lifetime=self.config.max_connection_lifetime,
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_acquisition_timeout=self.config.connection_acquisition_timeout,
                connection_timeout=self.config.connection_timeout,
                max_retry_time=self.config.max_retry_time,
                initial_retry_delay=self.config.initial_retry_delay,
                retry_delay_multiplier=self.config.retry_delay_multiplier,
                retry_delay_jitter_factor=self.config.retry_delay_jitter_factor
            )
        
        # Performance metrics
        self.query_metrics = {
            'total_queries': 0,
            'query_times': [],
            'slow_queries': [],
            'index_usage': {},
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Query cache
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize optimizations
        self._setup_indexes()
        self._setup_constraints()
        
        self.logger.info("Neo4j query optimizer initialized")
    
    def _setup_indexes(self) -> None:
        """Create performance indexes for common queries."""
        indexes = [
            # Primary indexes for unique constraints
            "CREATE INDEX rule_id_index IF NOT EXISTS FOR (r:Rule) ON (r.rule_id)",
            "CREATE INDEX concept_name_index IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX scenario_id_index IF NOT EXISTS FOR (s:Scenario) ON (s.scenario_id)",
            "CREATE INDEX policy_name_index IF NOT EXISTS FOR (p:Policy) ON (p.name)",
            
            # Performance indexes for common queries
            "CREATE INDEX rule_text_fulltext IF NOT EXISTS FOR (r:Rule) ON (r.rule_text)",
            "CREATE INDEX rule_confidence_index IF NOT EXISTS FOR (r:Rule) ON (r.confidence_score)",
            "CREATE INDEX rule_created_index IF NOT EXISTS FOR (r:Rule) ON (r.created_at)",
            "CREATE INDEX rule_version_index IF NOT EXISTS FOR (r:Rule) ON (r.version)",
            
            # Composite indexes for complex queries
            "CREATE INDEX rule_policy_confidence IF NOT EXISTS FOR (r:Rule) ON (r.rule_id, r.confidence_score)",
            "CREATE INDEX rule_created_confidence IF NOT EXISTS FOR (r:Rule) ON (r.created_at, r.confidence_score)",
            
            # Full-text search indexes
            "CALL db.index.fulltext.createNodeIndex('ruleTextSearch', ['Rule'], ['rule_text']) IF NOT EXISTS",
            "CALL db.index.fulltext.createNodeIndex('conceptSearch', ['Concept'], ['name']) IF NOT EXISTS"
        ]
        
        with self.driver.session() as session:
            for index_query in indexes:
                try:
                    session.run(index_query)
                    self.logger.debug(f"Created/verified index: {index_query[:50]}...")
                except Exception as e:
                    # Some index creation commands may fail if they already exist
                    self.logger.debug(f"Index creation note: {e}")
    
    def _setup_constraints(self) -> None:
        """Create constraints for data integrity and performance."""
        constraints = [
            "CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.rule_id IS UNIQUE",
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT scenario_id_unique IF NOT EXISTS FOR (s:Scenario) REQUIRE s.scenario_id IS UNIQUE",
            "CREATE CONSTRAINT policy_name_unique IF NOT EXISTS FOR (p:Policy) REQUIRE p.name IS UNIQUE"
        ]
        
        with self.driver.session() as session:
            for constraint_query in constraints:
                try:
                    session.run(constraint_query)
                    self.logger.debug(f"Created/verified constraint: {constraint_query[:50]}...")
                except Exception as e:
                    self.logger.debug(f"Constraint creation note: {e}")
    
    def execute_optimized_query(self, query: str, parameters: Dict[str, Any] = None, 
                               cache_key: str = None, cache_ttl: int = None) -> Tuple[Any, float]:
        """
        Execute Neo4j query with optimization and performance tracking.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            cache_key: Cache key for result caching
            cache_ttl: Cache TTL in seconds
            
        Returns:
            Tuple of (result, execution_time_ms)
        """
        parameters = parameters or {}
        start_time = time.time()
        
        # Check cache first
        if cache_key and cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if datetime.utcnow() < cache_entry['expires']:
                self.query_metrics['cache_hits'] += 1
                execution_time = (time.time() - start_time) * 1000
                self.logger.debug(f"Cache hit for query: {cache_key}")
                return cache_entry['result'], execution_time
            else:
                # Remove expired cache entry
                del self.query_cache[cache_key]
        
        self.query_metrics['cache_misses'] += 1
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                records = list(result)  # Consume all records
                
                execution_time = (time.time() - start_time) * 1000
                
                # Track performance metrics
                self._track_query_performance(query, execution_time, parameters)
                
                # Cache result if requested
                if cache_key and records:
                    cache_ttl = cache_ttl or self.cache_ttl
                    self.query_cache[cache_key] = {
                        'result': records,
                        'expires': datetime.utcnow() + timedelta(seconds=cache_ttl),
                        'created': datetime.utcnow()
                    }
                
                return records, execution_time
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.error(f"Query execution failed after {execution_time:.2f}ms: {e}")
            self._track_query_performance(query, execution_time, parameters, error=str(e))
            raise
    
    def _track_query_performance(self, query: str, execution_time: float, 
                                parameters: Dict[str, Any], error: str = None) -> None:
        """Track query performance metrics."""
        self.query_metrics['total_queries'] += 1
        
        query_info = {
            'query': query[:100] + '...' if len(query) > 100 else query,
            'execution_time_ms': execution_time,
            'parameters_count': len(parameters),
            'timestamp': datetime.utcnow().isoformat(),
            'error': error
        }
        
        self.query_metrics['query_times'].append(query_info)
        
        # Track slow queries (>100ms)
        if execution_time > 100:
            self.query_metrics['slow_queries'].append(query_info)
            self.logger.warning(f"Slow query detected: {execution_time:.2f}ms - {query[:50]}...")
        
        # Keep only last 1000 query records for memory efficiency
        if len(self.query_metrics['query_times']) > 1000:
            self.query_metrics['query_times'] = self.query_metrics['query_times'][-1000:]
        
        if len(self.query_metrics['slow_queries']) > 100:
            self.query_metrics['slow_queries'] = self.query_metrics['slow_queries'][-100:]
    
    def get_optimized_rule_search_query(self, concepts: List[str] = None, 
                                       keywords: List[str] = None, 
                                       policy: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        Generate optimized query for rule search with proper indexing.
        
        Args:
            concepts: List of concepts to match
            keywords: List of keywords for full-text search
            policy: Policy name filter
            
        Returns:
            Tuple of (optimized_query, parameters)
        """
        # Build optimized query using indexes
        query_parts = []
        parameters = {}
        
        if keywords:
            # Use full-text search index for keywords
            query_parts.append("""
                CALL db.index.fulltext.queryNodes('ruleTextSearch', $keyword_query) YIELD node as r, score
            """)
            # Combine keywords with OR for full-text search
            keyword_query = ' OR '.join(f'"{keyword}"' for keyword in keywords)
            parameters['keyword_query'] = keyword_query
        else:
            query_parts.append("MATCH (r:Rule)")
        
        # Add concept matching with index
        if concepts:
            query_parts.append("""
                MATCH (r)-[:RELATES_TO]->(c:Concept)
                WHERE c.name IN $concepts
            """)
            parameters['concepts'] = concepts
        
        # Add policy filtering with index
        if policy:
            query_parts.append("""
                MATCH (p:Policy {name: $policy})-[:GOVERNS]->(r)
            """)
            parameters['policy'] = policy
        
        # Add related data collection
        query_parts.append("""
            OPTIONAL MATCH (r)-[:RELATES_TO]->(all_c:Concept)
            OPTIONAL MATCH (r)-[:DERIVED_FROM]->(s:Scenario)
        """)
        
        # Return clause with ordering
        if keywords:
            query_parts.append("""
                RETURN r, collect(DISTINCT all_c.name) as concepts, 
                       collect(DISTINCT s.scenario_id) as scenarios, score
                ORDER BY score DESC, r.confidence_score DESC, r.created_at DESC
            """)
        else:
            query_parts.append("""
                RETURN r, collect(DISTINCT all_c.name) as concepts, 
                       collect(DISTINCT s.scenario_id) as scenarios
                ORDER BY r.confidence_score DESC, r.created_at DESC
            """)
        
        optimized_query = '\n'.join(query_parts)
        return optimized_query, parameters
    
    def get_optimized_concept_relationships_query(self, concept: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generate optimized query for concept relationships.
        
        Args:
            concept: Concept name
            
        Returns:
            Tuple of (optimized_query, parameters)
        """
        # Use index for concept lookup
        query = """
            MATCH (c:Concept {name: $concept})<-[:RELATES_TO]-(r:Rule)
            OPTIONAL MATCH (r)-[:DERIVED_FROM]->(s:Scenario)
            RETURN r, collect(DISTINCT s.scenario_id) as scenarios
            ORDER BY r.confidence_score DESC, r.created_at DESC
        """
        
        parameters = {'concept': concept}
        return query, parameters
    
    def get_optimized_traceability_query(self, rule_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generate optimized query for rule traceability.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Tuple of (optimized_query, parameters)
        """
        # Use unique constraint index for rule lookup
        query = """
            MATCH (r:Rule {rule_id: $rule_id})
            OPTIONAL MATCH (r)-[:RELATES_TO]->(c:Concept)
            OPTIONAL MATCH (r)-[:DERIVED_FROM]->(s:Scenario)
            OPTIONAL MATCH (p:Policy)-[:GOVERNS]->(r)
            RETURN r, 
                   collect(DISTINCT c.name) as concepts,
                   collect(DISTINCT s.scenario_id) as scenarios,
                   collect(DISTINCT p.name) as policies
        """
        
        parameters = {'rule_id': rule_id}
        return query, parameters
    
    def get_optimized_version_history_query(self, base_rule_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generate optimized query for rule version history.
        
        Args:
            base_rule_id: Base rule identifier
            
        Returns:
            Tuple of (optimized_query, parameters)
        """
        # Use index for rule_id prefix matching
        query = """
            MATCH (r:Rule)
            WHERE r.rule_id STARTS WITH $base_rule_id
            OPTIONAL MATCH (r)-[:DERIVED_FROM]->(s:Scenario)
            OPTIONAL MATCH (r)-[:RELATES_TO]->(c:Concept)
            RETURN r, 
                   collect(DISTINCT s.scenario_id) as scenarios,
                   collect(DISTINCT c.name) as concepts
            ORDER BY r.version ASC
        """
        
        parameters = {'base_rule_id': base_rule_id}
        return query, parameters
    
    def analyze_query_performance(self) -> Dict[str, Any]:
        """
        Analyze query performance and provide optimization recommendations.
        
        Returns:
            Dictionary with performance analysis and recommendations
        """
        if not self.query_metrics['query_times']:
            return {'message': 'No query data available for analysis'}
        
        # Calculate performance statistics
        query_times = [q['execution_time_ms'] for q in self.query_metrics['query_times']]
        avg_time = sum(query_times) / len(query_times)
        min_time = min(query_times)
        max_time = max(query_times)
        
        # Calculate percentiles
        sorted_times = sorted(query_times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        # Analyze slow queries
        slow_query_patterns = {}
        for slow_query in self.query_metrics['slow_queries']:
            # Extract query pattern (first 50 chars)
            pattern = slow_query['query'][:50]
            if pattern not in slow_query_patterns:
                slow_query_patterns[pattern] = {'count': 0, 'avg_time': 0, 'times': []}
            slow_query_patterns[pattern]['count'] += 1
            slow_query_patterns[pattern]['times'].append(slow_query['execution_time_ms'])
        
        # Calculate average times for slow query patterns
        for pattern in slow_query_patterns:
            times = slow_query_patterns[pattern]['times']
            slow_query_patterns[pattern]['avg_time'] = sum(times) / len(times)
        
        # Generate recommendations
        recommendations = []
        
        if avg_time > 50:
            recommendations.append({
                'type': 'performance',
                'message': f'Average query time ({avg_time:.2f}ms) is above optimal threshold (50ms)',
                'suggestion': 'Consider adding more specific indexes or optimizing query patterns'
            })
        
        if len(self.query_metrics['slow_queries']) > len(self.query_metrics['query_times']) * 0.1:
            recommendations.append({
                'type': 'slow_queries',
                'message': f'{len(self.query_metrics["slow_queries"])} slow queries detected',
                'suggestion': 'Review and optimize frequently slow query patterns'
            })
        
        cache_hit_rate = (self.query_metrics['cache_hits'] / 
                         (self.query_metrics['cache_hits'] + self.query_metrics['cache_misses']) * 100
                         if (self.query_metrics['cache_hits'] + self.query_metrics['cache_misses']) > 0 else 0)
        
        if cache_hit_rate < 30:
            recommendations.append({
                'type': 'caching',
                'message': f'Query cache hit rate ({cache_hit_rate:.1f}%) is low',
                'suggestion': 'Consider increasing cache TTL or caching more query results'
            })
        
        return {
            'performance_statistics': {
                'total_queries': self.query_metrics['total_queries'],
                'avg_execution_time_ms': avg_time,
                'min_execution_time_ms': min_time,
                'max_execution_time_ms': max_time,
                'p50_execution_time_ms': p50,
                'p95_execution_time_ms': p95,
                'p99_execution_time_ms': p99
            },
            'slow_queries': {
                'total_slow_queries': len(self.query_metrics['slow_queries']),
                'slow_query_patterns': slow_query_patterns
            },
            'cache_performance': {
                'hit_rate_percent': cache_hit_rate,
                'total_hits': self.query_metrics['cache_hits'],
                'total_misses': self.query_metrics['cache_misses'],
                'cached_entries': len(self.query_cache)
            },
            'recommendations': recommendations,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        Perform database optimization operations.
        
        Returns:
            Dictionary with optimization results
        """
        optimization_results = []
        
        try:
            with self.driver.session() as session:
                # Update statistics for query planner
                session.run("CALL db.stats.collect()")
                optimization_results.append("Updated database statistics")
                
                # Clean up expired cache entries
                expired_keys = [key for key, value in self.query_cache.items() 
                              if datetime.utcnow() >= value['expires']]
                for key in expired_keys:
                    del self.query_cache[key]
                optimization_results.append(f"Cleaned up {len(expired_keys)} expired cache entries")
                
                # Get index usage statistics
                index_stats = session.run("CALL db.indexes() YIELD name, state, populationPercent")
                active_indexes = sum(1 for record in index_stats if record['state'] == 'ONLINE')
                optimization_results.append(f"Verified {active_indexes} active indexes")
                
        except Exception as e:
            self.logger.error(f"Database optimization error: {e}")
            optimization_results.append(f"Optimization error: {str(e)}")
        
        return {
            'optimization_results': optimization_results,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_index_usage_stats(self) -> Dict[str, Any]:
        """
        Get index usage statistics.
        
        Returns:
            Dictionary with index usage information
        """
        try:
            with self.driver.session() as session:
                # Get index information
                index_result = session.run("CALL db.indexes() YIELD name, state, populationPercent, type")
                indexes = []
                for record in index_result:
                    indexes.append({
                        'name': record['name'],
                        'state': record['state'],
                        'population_percent': record['populationPercent'],
                        'type': record['type']
                    })
                
                return {
                    'indexes': indexes,
                    'total_indexes': len(indexes),
                    'active_indexes': sum(1 for idx in indexes if idx['state'] == 'ONLINE'),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error getting index stats: {e}")
            return {'error': str(e)}
    
    def clear_query_cache(self) -> int:
        """
        Clear query result cache.
        
        Returns:
            Number of cache entries cleared
        """
        cache_size = len(self.query_cache)
        self.query_cache.clear()
        self.logger.info(f"Cleared {cache_size} query cache entries")
        return cache_size
    
    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j optimizer connection closed")


# Global optimizer instance
_neo4j_optimizer = None


def get_neo4j_optimizer(driver: Driver = None) -> Neo4jQueryOptimizer:
    """Get global Neo4j optimizer instance."""
    global _neo4j_optimizer
    if _neo4j_optimizer is None:
        _neo4j_optimizer = Neo4jQueryOptimizer(driver)
    return _neo4j_optimizer


def close_optimizer():
    """Close Neo4j optimizer connection."""
    global _neo4j_optimizer
    if _neo4j_optimizer:
        _neo4j_optimizer.close()
        _neo4j_optimizer = None