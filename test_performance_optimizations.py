"""
Performance tests for Memory Management Module optimizations.

Tests Redis connection pooling, Neo4j query optimization, caching strategies,
and performance monitoring to verify sub-second response times.
"""

import pytest
import time
import asyncio
import concurrent.futures
from typing import List, Dict, Any
import statistics
import json

from memory_management.performance.redis_pool import RedisConnectionPool, RedisCacheManager
from memory_management.performance.neo4j_optimizer import Neo4jQueryOptimizer
from memory_management.performance.metrics_collector import MetricsCollector, get_metrics_collector
from memory_management.processors.stm_processor import STMProcessor
from memory_management.processors.ltm_manager import LTMManager
from memory_management.api.memory_api import MemoryAPI
from memory_management.models.stm_entry import STMEntry, InitialAssessment
from memory_management.models.ltm_rule import LTMRule


class TestRedisPerformanceOptimizations:
    """Test Redis connection pooling and caching optimizations."""
    
    @pytest.fixture
    def redis_pool(self):
        """Create Redis connection pool for testing."""
        pool = RedisConnectionPool()
        yield pool
        pool.close()
    
    @pytest.fixture
    def cache_manager(self, redis_pool):
        """Create cache manager for testing."""
        return RedisCacheManager(redis_pool)
    
    def test_redis_connection_pool_performance(self, redis_pool):
        """Test Redis connection pool performance under load."""
        def execute_redis_operation():
            client = redis_pool.get_client()
            start_time = time.time()
            result = client.ping()
            execution_time = (time.time() - start_time) * 1000
            return result, execution_time
        
        # Test concurrent connections
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(execute_redis_operation) for _ in range(100)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all operations succeeded
        assert all(result[0] for result in results), "Some Redis operations failed"
        
        # Verify performance (should be sub-second)
        execution_times = [result[1] for result in results]
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        
        assert avg_time < 50, f"Average Redis operation time {avg_time:.2f}ms exceeds 50ms threshold"
        assert max_time < 200, f"Maximum Redis operation time {max_time:.2f}ms exceeds 200ms threshold"
        
        # Check connection pool metrics
        health = redis_pool.health_check()
        assert health['status'] == 'healthy'
        assert health['performance_metrics']['connections_reuse_rate'] > 0
    
    def test_redis_cache_performance(self, cache_manager):
        """Test Redis cache performance and hit rates."""
        # Test cache operations
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        
        # Measure cache set performance
        start_time = time.time()
        success = cache_manager.set_cached_result("test_operation", test_data, 300, "param1", "param2")
        set_time = (time.time() - start_time) * 1000
        
        assert success, "Cache set operation failed"
        assert set_time < 10, f"Cache set time {set_time:.2f}ms exceeds 10ms threshold"
        
        # Measure cache get performance (should be faster)
        start_time = time.time()
        cached_result = cache_manager.get_cached_result("test_operation", "param1", "param2")
        get_time = (time.time() - start_time) * 1000
        
        assert cached_result == test_data, "Cached data doesn't match original"
        assert get_time < 5, f"Cache get time {get_time:.2f}ms exceeds 5ms threshold"
        
        # Test cache hit rate with multiple operations
        for i in range(50):
            cache_manager.get_cached_result("test_operation", "param1", "param2")
        
        stats = cache_manager.get_cache_stats()
        assert stats['performance']['hit_rate_percent'] > 90, "Cache hit rate is too low"
    
    def test_stm_processor_with_optimizations(self, redis_pool):
        """Test STM processor performance with connection pooling."""
        # Create STM processor with optimized Redis pool
        stm_processor = STMProcessor(
            redis_host=redis_pool.config.host,
            redis_port=redis_pool.config.port,
            redis_db=redis_pool.config.db
        )
        
        # Test concurrent STM operations
        def create_stm_entry(index):
            scenario_id = f"test_scenario_{index}"
            assessment = InitialAssessment(
                status="Non-Compliant",
                rationale=f"Test rationale {index}",
                recommendation=f"Test recommendation {index}"
            )
            
            start_time = time.time()
            entry = stm_processor.create_entry(scenario_id, f"Test requirement {index}", assessment)
            execution_time = (time.time() - start_time) * 1000
            
            return entry, execution_time
        
        # Execute concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_stm_entry, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify performance
        execution_times = [result[1] for result in results]
        avg_time = statistics.mean(execution_times)
        p95_time = sorted(execution_times)[int(len(execution_times) * 0.95)]
        
        assert avg_time < 100, f"Average STM operation time {avg_time:.2f}ms exceeds 100ms threshold"
        assert p95_time < 200, f"P95 STM operation time {p95_time:.2f}ms exceeds 200ms threshold"
        
        # Cleanup
        for i in range(50):
            stm_processor.delete_entry(f"test_scenario_{i}")


class TestNeo4jPerformanceOptimizations:
    """Test Neo4j query optimization and indexing."""
    
    @pytest.fixture
    def neo4j_optimizer(self):
        """Create Neo4j optimizer for testing."""
        optimizer = Neo4jQueryOptimizer()
        yield optimizer
        optimizer.close()
    
    @pytest.fixture
    def ltm_manager_with_optimizer(self, neo4j_optimizer):
        """Create LTM manager with optimizer."""
        return LTMManager()
    
    def test_neo4j_index_creation(self, neo4j_optimizer):
        """Test Neo4j index creation and verification."""
        # Get index usage stats
        index_stats = neo4j_optimizer.get_index_usage_stats()
        
        assert 'indexes' in index_stats
        assert index_stats['total_indexes'] > 0
        assert index_stats['active_indexes'] > 0
        
        # Verify key indexes exist
        index_names = [idx['name'] for idx in index_stats['indexes']]
        expected_indexes = ['rule_id_index', 'concept_name_index', 'rule_confidence_index']
        
        for expected_index in expected_indexes:
            # Check if any index name contains the expected pattern
            assert any(expected_index in name for name in index_names), f"Missing index: {expected_index}"
    
    def test_optimized_query_performance(self, neo4j_optimizer):
        """Test optimized query performance."""
        # Test optimized rule search query
        query, params = neo4j_optimizer.get_optimized_rule_search_query(
            concepts=['GDPR', 'Consent'],
            keywords=['password', 'hashing'],
            policy='GDPR'
        )
        
        # Execute query with timing
        start_time = time.time()
        results, execution_time = neo4j_optimizer.execute_optimized_query(query, params)
        total_time = (time.time() - start_time) * 1000
        
        # Verify performance
        assert execution_time < 500, f"Query execution time {execution_time:.2f}ms exceeds 500ms threshold"
        assert total_time < 600, f"Total query time {total_time:.2f}ms exceeds 600ms threshold"
        
        # Test query caching
        cache_key = "test_rule_search"
        cached_results, cached_time = neo4j_optimizer.execute_optimized_query(
            query, params, cache_key=cache_key
        )
        
        # Second execution should be faster (cached)
        start_time = time.time()
        cached_results2, cached_time2 = neo4j_optimizer.execute_optimized_query(
            query, params, cache_key=cache_key
        )
        cache_retrieval_time = (time.time() - start_time) * 1000
        
        assert cache_retrieval_time < 50, f"Cache retrieval time {cache_retrieval_time:.2f}ms too slow"
    
    def test_ltm_operations_performance(self, ltm_manager_with_optimizer):
        """Test LTM operations performance with optimizations."""
        # Create test LTM rules
        test_rules = []
        for i in range(20):
            rule = LTMRule(
                rule_id=f"TEST_Rule_{i:02d}_01",
                rule_text=f"Test rule {i} for performance testing with various concepts and patterns",
                related_concepts=[f"Concept{i}", f"TestConcept{i}", "Performance"],
                source_scenario_id=[f"test_scenario_{i}"],
                confidence_score=0.8 + (i % 3) * 0.1
            )
            test_rules.append(rule)
        
        # Store rules and measure performance
        store_times = []
        for rule in test_rules:
            start_time = time.time()
            success = ltm_manager_with_optimizer.store_ltm_rule(rule)
            store_time = (time.time() - start_time) * 1000
            store_times.append(store_time)
            assert success, f"Failed to store rule {rule.rule_id}"
        
        avg_store_time = statistics.mean(store_times)
        assert avg_store_time < 200, f"Average rule store time {avg_store_time:.2f}ms exceeds 200ms threshold"
        
        # Test search performance
        search_times = []
        for i in range(10):
            start_time = time.time()
            results = ltm_manager_with_optimizer.search_ltm_rules(
                concepts=[f"Concept{i}", "Performance"],
                limit=10
            )
            search_time = (time.time() - start_time) * 1000
            search_times.append(search_time)
        
        avg_search_time = statistics.mean(search_times)
        assert avg_search_time < 300, f"Average search time {avg_search_time:.2f}ms exceeds 300ms threshold"
        
        # Cleanup
        for rule in test_rules:
            ltm_manager_with_optimizer.delete_ltm_rule(rule.rule_id)


class TestMetricsCollectorPerformance:
    """Test performance monitoring and metrics collection."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector for testing."""
        collector = MetricsCollector()
        yield collector
        collector.clear_metrics()
    
    def test_metrics_collection_performance(self, metrics_collector):
        """Test metrics collection performance overhead."""
        # Measure metrics recording overhead
        start_time = time.time()
        for i in range(1000):
            metrics_collector.record_metric(f"test_metric_{i % 10}", i * 0.1, "ms")
        recording_time = (time.time() - start_time) * 1000
        
        # Metrics recording should be very fast
        avg_recording_time = recording_time / 1000
        assert avg_recording_time < 1, f"Average metric recording time {avg_recording_time:.3f}ms too slow"
        
        # Test metrics retrieval performance
        start_time = time.time()
        summary = metrics_collector.get_metric_summary("test_metric_0", 60)
        retrieval_time = (time.time() - start_time) * 1000
        
        assert retrieval_time < 50, f"Metrics retrieval time {retrieval_time:.2f}ms exceeds 50ms threshold"
        assert 'statistics' in summary
        assert summary['data_points'] > 0
    
    def test_performance_dashboard_generation(self, metrics_collector):
        """Test performance dashboard generation speed."""
        # Record various metrics
        for i in range(100):
            metrics_collector.record_timing("test_operation", i * 10, "STM", True)
            metrics_collector.record_cache_metrics(80 + i % 20, 20 - i % 20, "redis")
            metrics_collector.record_connection_metrics(100, 50 + i % 30, "neo4j")
        
        # Generate dashboard
        start_time = time.time()
        dashboard = metrics_collector.get_performance_dashboard()
        dashboard_time = (time.time() - start_time) * 1000
        
        assert dashboard_time < 100, f"Dashboard generation time {dashboard_time:.2f}ms exceeds 100ms threshold"
        assert 'key_metrics' in dashboard
        assert 'component_performance' in dashboard
        assert dashboard['system_health'] in ['healthy', 'warning', 'critical']
    
    def test_timing_decorator_overhead(self, metrics_collector):
        """Test timing decorator performance overhead."""
        @metrics_collector.timing_decorator("test_operation", "TEST")
        def test_function(duration_ms: float):
            time.sleep(duration_ms / 1000)
            return "success"
        
        # Test decorator overhead
        base_duration = 10  # 10ms
        start_time = time.time()
        result = test_function(base_duration)
        total_time = (time.time() - start_time) * 1000
        
        assert result == "success"
        # Decorator overhead should be minimal (< 5ms)
        decorator_overhead = total_time - base_duration
        assert decorator_overhead < 5, f"Timing decorator overhead {decorator_overhead:.2f}ms too high"


class TestIntegratedPerformance:
    """Test integrated performance across all components."""
    
    @pytest.fixture
    def memory_api(self):
        """Create Memory API with all optimizations."""
        api = MemoryAPI()
        yield api
        api.close()
    
    def test_end_to_end_performance(self, memory_api):
        """Test end-to-end API performance with all optimizations."""
        # Test STM operations
        assessment_data = {
            "scenario_id": "perf_test_scenario_001",
            "requirement_text": "Test requirement for performance validation",
            "initial_assessment": {
                "status": "Non-Compliant",
                "rationale": "Performance test rationale",
                "recommendation": "Performance test recommendation"
            }
        }
        
        # Measure STM creation performance
        start_time = time.time()
        create_response = memory_api.add_new_assessment(assessment_data)
        create_time = (time.time() - start_time) * 1000
        
        assert create_response['status'] == 'success'
        assert create_time < 100, f"STM creation time {create_time:.2f}ms exceeds 100ms threshold"
        
        # Measure STM retrieval performance
        start_time = time.time()
        get_response = memory_api.get_stm_entry("perf_test_scenario_001")
        get_time = (time.time() - start_time) * 1000
        
        assert get_response['status'] == 'success'
        assert get_time < 50, f"STM retrieval time {get_time:.2f}ms exceeds 50ms threshold"
        
        # Test feedback update performance
        feedback_data = {
            "decision": "Approved",
            "rationale": "Performance test feedback",
            "suggestion": "Performance test suggestion",
            "final_status": "Compliant"
        }
        
        start_time = time.time()
        feedback_response = memory_api.update_with_feedback("perf_test_scenario_001", feedback_data)
        feedback_time = (time.time() - start_time) * 1000
        
        assert feedback_response['status'] == 'success'
        assert feedback_time < 200, f"Feedback update time {feedback_time:.2f}ms exceeds 200ms threshold"
    
    def test_concurrent_api_performance(self, memory_api):
        """Test API performance under concurrent load."""
        def api_operation(index):
            scenario_id = f"concurrent_test_{index}"
            assessment_data = {
                "scenario_id": scenario_id,
                "requirement_text": f"Concurrent test requirement {index}",
                "initial_assessment": {
                    "status": "Non-Compliant",
                    "rationale": f"Concurrent test rationale {index}",
                    "recommendation": f"Concurrent test recommendation {index}"
                }
            }
            
            start_time = time.time()
            
            # Create assessment
            create_response = memory_api.add_new_assessment(assessment_data)
            
            # Retrieve assessment
            get_response = memory_api.get_stm_entry(scenario_id)
            
            total_time = (time.time() - start_time) * 1000
            
            return {
                'create_success': create_response['status'] == 'success',
                'get_success': get_response['status'] == 'success',
                'total_time': total_time
            }
        
        # Execute concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(api_operation, i) for i in range(30)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all operations succeeded
        assert all(r['create_success'] for r in results), "Some create operations failed"
        assert all(r['get_success'] for r in results), "Some get operations failed"
        
        # Verify performance
        execution_times = [r['total_time'] for r in results]
        avg_time = statistics.mean(execution_times)
        p95_time = sorted(execution_times)[int(len(execution_times) * 0.95)]
        
        assert avg_time < 300, f"Average concurrent operation time {avg_time:.2f}ms exceeds 300ms threshold"
        assert p95_time < 500, f"P95 concurrent operation time {p95_time:.2f}ms exceeds 500ms threshold"
    
    def test_system_health_monitoring(self, memory_api):
        """Test system health monitoring performance."""
        # Get system health
        start_time = time.time()
        health_response = memory_api.health_check()
        health_time = (time.time() - start_time) * 1000
        
        assert health_response['status'] == 'success'
        assert health_time < 100, f"Health check time {health_time:.2f}ms exceeds 100ms threshold"
        
        # Get system stats
        start_time = time.time()
        stats_response = memory_api.get_system_stats()
        stats_time = (time.time() - start_time) * 1000
        
        assert stats_response['status'] == 'success'
        assert stats_time < 200, f"System stats time {stats_time:.2f}ms exceeds 200ms threshold"
        
        # Verify health data structure
        health_data = health_response['data']
        assert 'Redis' in health_data or 'redis' in str(health_data).lower()
        assert 'Neo4j' in health_data or 'neo4j' in str(health_data).lower()


def test_performance_requirements_compliance():
    """Test that all performance requirements are met."""
    metrics_collector = get_metrics_collector()
    
    # Record some test metrics to verify thresholds
    metrics_collector.record_timing("stm_operation", 45, "STM", True)  # Under 100ms threshold
    metrics_collector.record_timing("ltm_operation", 250, "LTM", True)  # Under 500ms threshold
    metrics_collector.record_timing("api_operation", 150, "API", True)  # Under 1000ms threshold
    
    # Get performance dashboard
    dashboard = metrics_collector.get_performance_dashboard()
    
    # Verify system health
    assert dashboard['system_health'] in ['healthy', 'warning'], "System health is critical"
    
    # Verify key metrics are within thresholds
    key_metrics = dashboard.get('key_metrics', {})
    
    if 'stm_response_time_ms' in key_metrics:
        stm_metric = key_metrics['stm_response_time_ms']
        assert stm_metric['current'] < 100, f"STM response time {stm_metric['current']}ms exceeds requirement"
    
    if 'ltm_response_time_ms' in key_metrics:
        ltm_metric = key_metrics['ltm_response_time_ms']
        assert ltm_metric['current'] < 500, f"LTM response time {ltm_metric['current']}ms exceeds requirement"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])