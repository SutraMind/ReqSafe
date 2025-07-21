"""
Application startup configuration with performance optimizations.

Initializes all performance components and ensures optimal system startup.
"""

import logging
import asyncio
import time
from typing import Dict, Any
import sys
import os

from .settings import get_settings, setup_logging, validate_environment
from ..performance.redis_pool import get_redis_pool, get_cache_manager
from ..performance.neo4j_optimizer import get_neo4j_optimizer
from ..performance.metrics_collector import get_metrics_collector


class StartupManager:
    """
    Manages application startup with performance optimizations.
    
    Ensures all components are properly initialized and performance
    monitoring is active before the application starts serving requests.
    """
    
    def __init__(self):
        """Initialize startup manager."""
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        self.startup_metrics = {}
        
    def initialize_logging(self) -> None:
        """Initialize logging configuration."""
        try:
            setup_logging(self.settings.logging)
            self.logger.info("Logging system initialized")
        except Exception as e:
            print(f"Failed to initialize logging: {e}")
            sys.exit(1)
    
    def validate_configuration(self) -> None:
        """Validate application configuration."""
        try:
            # Validate environment variables
            if not validate_environment():
                raise ValueError("Required environment variables are missing")
            
            # Validate settings
            if not self.settings.validate():
                raise ValueError("Configuration validation failed")
            
            self.logger.info("Configuration validation passed")
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            sys.exit(1)
    
    def initialize_performance_components(self) -> Dict[str, Any]:
        """
        Initialize all performance optimization components.
        
        Returns:
            Dictionary with initialization results
        """
        initialization_results = {}
        
        try:
            # Initialize Redis connection pool
            start_time = time.time()
            redis_pool = get_redis_pool()
            redis_health = redis_pool.health_check()
            redis_init_time = (time.time() - start_time) * 1000
            
            initialization_results['redis'] = {
                'status': 'success' if redis_health['status'] == 'healthy' else 'failed',
                'init_time_ms': redis_init_time,
                'health': redis_health
            }
            
            if redis_health['status'] != 'healthy':
                raise Exception(f"Redis initialization failed: {redis_health}")
            
            self.logger.info(f"Redis connection pool initialized ({redis_init_time:.2f}ms)")
            
        except Exception as e:
            self.logger.error(f"Redis initialization failed: {e}")
            initialization_results['redis'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        try:
            # Initialize Redis cache manager
            start_time = time.time()
            cache_manager = get_cache_manager()
            cache_stats = cache_manager.get_cache_stats()
            cache_init_time = (time.time() - start_time) * 1000
            
            initialization_results['cache'] = {
                'status': 'success',
                'init_time_ms': cache_init_time,
                'stats': cache_stats
            }
            
            self.logger.info(f"Cache manager initialized ({cache_init_time:.2f}ms)")
            
        except Exception as e:
            self.logger.error(f"Cache manager initialization failed: {e}")
            initialization_results['cache'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        try:
            # Initialize Neo4j optimizer
            start_time = time.time()
            neo4j_optimizer = get_neo4j_optimizer()
            index_stats = neo4j_optimizer.get_index_usage_stats()
            neo4j_init_time = (time.time() - start_time) * 1000
            
            initialization_results['neo4j'] = {
                'status': 'success',
                'init_time_ms': neo4j_init_time,
                'index_stats': index_stats
            }
            
            self.logger.info(f"Neo4j optimizer initialized ({neo4j_init_time:.2f}ms)")
            
        except Exception as e:
            self.logger.error(f"Neo4j optimizer initialization failed: {e}")
            initialization_results['neo4j'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        try:
            # Initialize metrics collector
            start_time = time.time()
            metrics_collector = get_metrics_collector()
            
            # Start background metrics collection
            metrics_collector.start_background_collection(
                interval_seconds=self.settings.api.timeout or 60
            )
            
            metrics_init_time = (time.time() - start_time) * 1000
            
            initialization_results['metrics'] = {
                'status': 'success',
                'init_time_ms': metrics_init_time,
                'background_collection': True
            }
            
            self.logger.info(f"Metrics collector initialized ({metrics_init_time:.2f}ms)")
            
        except Exception as e:
            self.logger.error(f"Metrics collector initialization failed: {e}")
            initialization_results['metrics'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        return initialization_results
    
    def perform_health_checks(self) -> Dict[str, Any]:
        """
        Perform comprehensive health checks on all components.
        
        Returns:
            Dictionary with health check results
        """
        health_results = {}
        
        try:
            # Redis health check
            redis_pool = get_redis_pool()
            redis_health = redis_pool.health_check()
            health_results['redis'] = redis_health
            
        except Exception as e:
            health_results['redis'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        try:
            # Neo4j health check
            neo4j_optimizer = get_neo4j_optimizer()
            
            # Simple connectivity test
            start_time = time.time()
            with neo4j_optimizer.driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_result = result.single()['test']
            
            neo4j_response_time = (time.time() - start_time) * 1000
            
            health_results['neo4j'] = {
                'status': 'healthy' if test_result == 1 else 'unhealthy',
                'response_time_ms': neo4j_response_time
            }
            
        except Exception as e:
            health_results['neo4j'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        try:
            # Metrics collector health check
            metrics_collector = get_metrics_collector()
            dashboard = metrics_collector.get_performance_dashboard()
            
            health_results['metrics'] = {
                'status': 'healthy',
                'system_health': dashboard['system_health'],
                'active_alerts': len(dashboard.get('alerts', []))
            }
            
        except Exception as e:
            health_results['metrics'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        return health_results
    
    def optimize_system_performance(self) -> Dict[str, Any]:
        """
        Perform initial system performance optimizations.
        
        Returns:
            Dictionary with optimization results
        """
        optimization_results = {}
        
        try:
            # Optimize Neo4j database
            neo4j_optimizer = get_neo4j_optimizer()
            neo4j_optimization = neo4j_optimizer.optimize_database()
            optimization_results['neo4j'] = neo4j_optimization
            
        except Exception as e:
            optimization_results['neo4j'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        try:
            # Optimize cache settings
            cache_manager = get_cache_manager()
            cache_optimization = cache_manager.optimize_cache_settings()
            optimization_results['cache'] = cache_optimization
            
        except Exception as e:
            optimization_results['cache'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        return optimization_results
    
    def startup(self) -> Dict[str, Any]:
        """
        Perform complete application startup sequence.
        
        Returns:
            Dictionary with startup results
        """
        startup_start_time = time.time()
        
        self.logger.info("Starting Memory Management Module with performance optimizations...")
        
        # Step 1: Initialize logging
        self.initialize_logging()
        
        # Step 2: Validate configuration
        self.validate_configuration()
        
        # Step 3: Initialize performance components
        self.logger.info("Initializing performance components...")
        init_results = self.initialize_performance_components()
        
        # Step 4: Perform health checks
        self.logger.info("Performing health checks...")
        health_results = self.perform_health_checks()
        
        # Step 5: Optimize system performance
        self.logger.info("Optimizing system performance...")
        optimization_results = self.optimize_system_performance()
        
        # Calculate total startup time
        total_startup_time = (time.time() - startup_start_time) * 1000
        
        # Determine overall startup status
        failed_components = [
            name for name, result in init_results.items() 
            if result.get('status') != 'success'
        ]
        
        unhealthy_components = [
            name for name, result in health_results.items() 
            if result.get('status') != 'healthy'
        ]
        
        startup_status = 'success'
        if failed_components or unhealthy_components:
            startup_status = 'partial_failure' if len(failed_components) < len(init_results) else 'failure'
        
        startup_summary = {
            'status': startup_status,
            'total_startup_time_ms': total_startup_time,
            'initialization_results': init_results,
            'health_check_results': health_results,
            'optimization_results': optimization_results,
            'failed_components': failed_components,
            'unhealthy_components': unhealthy_components,
            'timestamp': time.time()
        }
        
        # Log startup summary
        if startup_status == 'success':
            self.logger.info(f"Memory Management Module started successfully ({total_startup_time:.2f}ms)")
        elif startup_status == 'partial_failure':
            self.logger.warning(f"Memory Management Module started with issues ({total_startup_time:.2f}ms)")
            self.logger.warning(f"Failed components: {failed_components}")
            self.logger.warning(f"Unhealthy components: {unhealthy_components}")
        else:
            self.logger.error(f"Memory Management Module startup failed ({total_startup_time:.2f}ms)")
            self.logger.error(f"Failed components: {failed_components}")
            self.logger.error(f"Unhealthy components: {unhealthy_components}")
        
        # Record startup metrics
        try:
            metrics_collector = get_metrics_collector()
            metrics_collector.record_metric("startup_time_ms", total_startup_time, "ms")
            metrics_collector.record_metric("startup_success", 1 if startup_status == 'success' else 0, "bool")
            
            for component, result in init_results.items():
                if 'init_time_ms' in result:
                    metrics_collector.record_metric(
                        f"{component}_init_time_ms", 
                        result['init_time_ms'], 
                        "ms"
                    )
        except Exception as e:
            self.logger.warning(f"Failed to record startup metrics: {e}")
        
        return startup_summary
    
    def shutdown(self) -> None:
        """Perform graceful application shutdown."""
        self.logger.info("Shutting down Memory Management Module...")
        
        try:
            # Stop metrics collection
            metrics_collector = get_metrics_collector()
            metrics_collector.stop_background_collection()
            self.logger.info("Stopped metrics collection")
        except Exception as e:
            self.logger.error(f"Error stopping metrics collection: {e}")
        
        try:
            # Close Neo4j connections
            from ..performance.neo4j_optimizer import close_optimizer
            close_optimizer()
            self.logger.info("Closed Neo4j connections")
        except Exception as e:
            self.logger.error(f"Error closing Neo4j connections: {e}")
        
        try:
            # Close Redis connections
            from ..performance.redis_pool import close_connections
            close_connections()
            self.logger.info("Closed Redis connections")
        except Exception as e:
            self.logger.error(f"Error closing Redis connections: {e}")
        
        self.logger.info("Memory Management Module shutdown complete")


# Global startup manager instance
_startup_manager = None


def get_startup_manager() -> StartupManager:
    """Get global startup manager instance."""
    global _startup_manager
    if _startup_manager is None:
        _startup_manager = StartupManager()
    return _startup_manager


def startup_application() -> Dict[str, Any]:
    """Convenience function to start the application."""
    manager = get_startup_manager()
    return manager.startup()


def shutdown_application() -> None:
    """Convenience function to shutdown the application."""
    manager = get_startup_manager()
    manager.shutdown()