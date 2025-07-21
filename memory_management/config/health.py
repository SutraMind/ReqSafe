"""
Health check system for Memory Management Module.

Provides comprehensive health monitoring for all system components
with performance metrics and alerting capabilities.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .settings import get_settings
from ..performance.redis_pool import get_redis_pool
from ..performance.neo4j_optimizer import get_neo4j_optimizer
from ..performance.metrics_collector import get_metrics_collector


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Individual health check result."""
    component: str
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'component': self.component,
            'status': self.status.value,
            'response_time_ms': self.response_time_ms,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class HealthChecker:
    """
    Comprehensive health checker for all system components.
    
    Monitors Redis, Neo4j, application components, and overall system health
    with configurable thresholds and alerting.
    """
    
    def __init__(self):
        """Initialize health checker."""
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        
        # Health check thresholds (in milliseconds)
        self.thresholds = {
            'redis_response_time_ms': 50,
            'neo4j_response_time_ms': 100,
            'cache_hit_rate_percent': 70,
            'connection_pool_utilization_percent': 80,
            'memory_usage_percent': 85,
            'error_rate_percent': 5
        }
        
        # Health check history
        self.health_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
    def check_redis_health(self) -> HealthCheckResult:
        """
        Check Redis health and performance.
        
        Returns:
            HealthCheckResult for Redis
        """
        start_time = time.time()
        
        try:
            redis_pool = get_redis_pool()
            health_data = redis_pool.health_check()
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time and health data
            if health_data['status'] == 'healthy':
                if response_time <= self.thresholds['redis_response_time_ms']:
                    status = HealthStatus.HEALTHY
                    message = "Redis is healthy and responsive"
                elif response_time <= self.thresholds['redis_response_time_ms'] * 2:
                    status = HealthStatus.DEGRADED
                    message = f"Redis response time elevated ({response_time:.2f}ms)"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"Redis response time too high ({response_time:.2f}ms)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Redis health check failed: {health_data.get('error', 'Unknown error')}"
            
            # Additional performance checks
            performance_metrics = health_data.get('performance_metrics', {})
            pool_info = health_data.get('pool_info', {})
            
            # Check connection pool utilization
            if pool_info:
                max_connections = pool_info.get('max_connections', 1)
                in_use = pool_info.get('in_use_connections', 0)
                utilization = (in_use / max_connections) * 100
                
                if utilization > self.thresholds['connection_pool_utilization_percent']:
                    if status == HealthStatus.HEALTHY:
                        status = HealthStatus.DEGRADED
                    message += f" | High pool utilization ({utilization:.1f}%)"
            
            # Check cache performance
            cache_hit_rate = performance_metrics.get('cache_hit_rate', 0)
            if cache_hit_rate < self.thresholds['cache_hit_rate_percent']:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                message += f" | Low cache hit rate ({cache_hit_rate:.1f}%)"
            
            return HealthCheckResult(
                component="redis",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    'health_data': health_data,
                    'thresholds': {
                        'response_time_ms': self.thresholds['redis_response_time_ms'],
                        'pool_utilization_percent': self.thresholds['connection_pool_utilization_percent'],
                        'cache_hit_rate_percent': self.thresholds['cache_hit_rate_percent']
                    }
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Redis health check failed: {e}")
            
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Redis health check error: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            )
    
    def check_neo4j_health(self) -> HealthCheckResult:
        """
        Check Neo4j health and performance.
        
        Returns:
            HealthCheckResult for Neo4j
        """
        start_time = time.time()
        
        try:
            neo4j_optimizer = get_neo4j_optimizer()
            
            # Test basic connectivity
            with neo4j_optimizer.driver.session() as session:
                result = session.run("RETURN 1 as test, timestamp() as ts")
                record = result.single()
                test_value = record['test']
                db_timestamp = record['ts']
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time and connectivity
            if test_value == 1:
                if response_time <= self.thresholds['neo4j_response_time_ms']:
                    status = HealthStatus.HEALTHY
                    message = "Neo4j is healthy and responsive"
                elif response_time <= self.thresholds['neo4j_response_time_ms'] * 2:
                    status = HealthStatus.DEGRADED
                    message = f"Neo4j response time elevated ({response_time:.2f}ms)"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"Neo4j response time too high ({response_time:.2f}ms)"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Neo4j connectivity test failed"
            
            # Get additional performance metrics
            try:
                index_stats = neo4j_optimizer.get_index_usage_stats()
                performance_analysis = neo4j_optimizer.analyze_query_performance()
                
                # Check for performance issues
                if 'performance_statistics' in performance_analysis:
                    perf_stats = performance_analysis['performance_statistics']
                    avg_query_time = perf_stats.get('avg_execution_time_ms', 0)
                    
                    if avg_query_time > self.thresholds['neo4j_response_time_ms']:
                        if status == HealthStatus.HEALTHY:
                            status = HealthStatus.DEGRADED
                        message += f" | High avg query time ({avg_query_time:.2f}ms)"
                
                # Check for slow queries
                slow_queries = performance_analysis.get('slow_queries', {})
                if slow_queries.get('total_slow_queries', 0) > 10:
                    if status == HealthStatus.HEALTHY:
                        status = HealthStatus.DEGRADED
                    message += f" | {slow_queries['total_slow_queries']} slow queries detected"
                
            except Exception as e:
                self.logger.warning(f"Failed to get Neo4j performance metrics: {e}")
                index_stats = {}
                performance_analysis = {}
            
            return HealthCheckResult(
                component="neo4j",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    'database_timestamp': db_timestamp,
                    'index_stats': index_stats,
                    'performance_analysis': performance_analysis,
                    'thresholds': {
                        'response_time_ms': self.thresholds['neo4j_response_time_ms']
                    }
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Neo4j health check failed: {e}")
            
            return HealthCheckResult(
                component="neo4j",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Neo4j health check error: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            )
    
    def check_application_health(self) -> HealthCheckResult:
        """
        Check application-level health and performance.
        
        Returns:
            HealthCheckResult for application
        """
        start_time = time.time()
        
        try:
            metrics_collector = get_metrics_collector()
            dashboard = metrics_collector.get_performance_dashboard()
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on system health and alerts
            system_health = dashboard.get('system_health', 'unknown')
            active_alerts = dashboard.get('alerts', [])
            
            if system_health == 'healthy' and not active_alerts:
                status = HealthStatus.HEALTHY
                message = "Application is healthy"
            elif system_health == 'warning' or len(active_alerts) <= 2:
                status = HealthStatus.DEGRADED
                message = f"Application has {len(active_alerts)} active alerts"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Application has {len(active_alerts)} critical alerts"
            
            # Check key performance metrics
            key_metrics = dashboard.get('key_metrics', {})
            performance_issues = []
            
            for metric_name, metric_data in key_metrics.items():
                current_value = metric_data.get('current', 0)
                threshold = metric_data.get('threshold')
                metric_status = metric_data.get('status', 'unknown')
                
                if metric_status == 'critical':
                    performance_issues.append(f"{metric_name}: {current_value}")
            
            if performance_issues:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                message += f" | Performance issues: {', '.join(performance_issues)}"
            
            return HealthCheckResult(
                component="application",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    'dashboard': dashboard,
                    'performance_issues': performance_issues,
                    'thresholds': self.thresholds
                },
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Application health check failed: {e}")
            
            return HealthCheckResult(
                component="application",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Application health check error: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            )
    
    def check_system_resources(self) -> HealthCheckResult:
        """
        Check system resource utilization.
        
        Returns:
            HealthCheckResult for system resources
        """
        start_time = time.time()
        
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on resource utilization
            status = HealthStatus.HEALTHY
            issues = []
            
            if memory.percent > self.thresholds['memory_usage_percent']:
                status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                issues.append(f"High memory usage ({memory.percent:.1f}%)")
            
            if cpu_percent > 80:
                status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                issues.append(f"High CPU usage ({cpu_percent:.1f}%)")
            
            if disk.percent > 85:
                status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                issues.append(f"High disk usage ({disk.percent:.1f}%)")
            
            message = "System resources are healthy" if not issues else f"Resource issues: {', '.join(issues)}"
            
            return HealthCheckResult(
                component="system",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_free_gb': disk.free / (1024**3),
                    'thresholds': {
                        'memory_usage_percent': self.thresholds['memory_usage_percent']
                    }
                },
                timestamp=datetime.utcnow()
            )
            
        except ImportError:
            # psutil not available, return basic check
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="system",
                status=HealthStatus.UNKNOWN,
                response_time_ms=response_time,
                message="System resource monitoring not available (psutil not installed)",
                details={'note': 'Install psutil for system resource monitoring'},
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"System resource check failed: {e}")
            
            return HealthCheckResult(
                component="system",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"System resource check error: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            )
    
    def perform_comprehensive_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all components.
        
        Returns:
            Dictionary with complete health status
        """
        health_check_start = time.time()
        
        # Perform individual health checks
        health_checks = {
            'redis': self.check_redis_health(),
            'neo4j': self.check_neo4j_health(),
            'application': self.check_application_health(),
            'system': self.check_system_resources()
        }
        
        # Determine overall system health
        statuses = [check.status for check in health_checks.values()]
        
        if all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN
        
        # Calculate total health check time
        total_check_time = (time.time() - health_check_start) * 1000
        
        # Count issues by severity
        healthy_components = sum(1 for check in health_checks.values() if check.status == HealthStatus.HEALTHY)
        degraded_components = sum(1 for check in health_checks.values() if check.status == HealthStatus.DEGRADED)
        unhealthy_components = sum(1 for check in health_checks.values() if check.status == HealthStatus.UNHEALTHY)
        
        # Create comprehensive health report
        health_report = {
            'overall_status': overall_status.value,
            'total_check_time_ms': total_check_time,
            'timestamp': datetime.utcnow().isoformat(),
            'components': {name: check.to_dict() for name, check in health_checks.items()},
            'summary': {
                'total_components': len(health_checks),
                'healthy_components': healthy_components,
                'degraded_components': degraded_components,
                'unhealthy_components': unhealthy_components,
                'health_score': (healthy_components + degraded_components * 0.5) / len(health_checks) * 100
            },
            'recommendations': self._generate_health_recommendations(health_checks)
        }
        
        # Store in health history
        self.health_history.append(health_report)
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size:]
        
        # Log health status
        if overall_status == HealthStatus.HEALTHY:
            self.logger.info(f"System health check passed ({total_check_time:.2f}ms)")
        elif overall_status == HealthStatus.DEGRADED:
            self.logger.warning(f"System health degraded ({total_check_time:.2f}ms) - {degraded_components} degraded, {unhealthy_components} unhealthy")
        else:
            self.logger.error(f"System health critical ({total_check_time:.2f}ms) - {unhealthy_components} unhealthy components")
        
        return health_report
    
    def _generate_health_recommendations(self, health_checks: Dict[str, HealthCheckResult]) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        for name, check in health_checks.items():
            if check.status == HealthStatus.UNHEALTHY:
                recommendations.append(f"Critical: Fix {name} component - {check.message}")
            elif check.status == HealthStatus.DEGRADED:
                recommendations.append(f"Warning: Optimize {name} component - {check.message}")
        
        # Add general recommendations based on patterns
        if len([c for c in health_checks.values() if c.response_time_ms > 100]) > 1:
            recommendations.append("Consider optimizing database connections and queries")
        
        return recommendations
    
    def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get health check history for specified time period.
        
        Args:
            hours: Number of hours of history to return
            
        Returns:
            List of health check results
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            report for report in self.health_history
            if datetime.fromisoformat(report['timestamp']) >= cutoff_time
        ]
    
    def get_health_trends(self) -> Dict[str, Any]:
        """
        Analyze health trends over time.
        
        Returns:
            Dictionary with health trend analysis
        """
        if len(self.health_history) < 2:
            return {'message': 'Insufficient data for trend analysis'}
        
        # Analyze trends over last 10 health checks
        recent_checks = self.health_history[-10:]
        
        # Calculate average health scores
        health_scores = [check['summary']['health_score'] for check in recent_checks]
        avg_health_score = sum(health_scores) / len(health_scores)
        
        # Calculate trend direction
        if len(health_scores) >= 3:
            recent_avg = sum(health_scores[-3:]) / 3
            older_avg = sum(health_scores[:3]) / 3
            trend = 'improving' if recent_avg > older_avg else 'declining' if recent_avg < older_avg else 'stable'
        else:
            trend = 'stable'
        
        # Component-specific trends
        component_trends = {}
        for component in ['redis', 'neo4j', 'application', 'system']:
            component_scores = []
            for check in recent_checks:
                comp_status = check['components'].get(component, {}).get('status', 'unknown')
                score = {'healthy': 100, 'degraded': 50, 'unhealthy': 0, 'unknown': 25}.get(comp_status, 0)
                component_scores.append(score)
            
            if component_scores:
                component_trends[component] = {
                    'average_score': sum(component_scores) / len(component_scores),
                    'current_score': component_scores[-1],
                    'trend': 'improving' if component_scores[-1] > component_scores[0] else 'declining' if component_scores[-1] < component_scores[0] else 'stable'
                }
        
        return {
            'overall_health_score': avg_health_score,
            'trend': trend,
            'component_trends': component_trends,
            'analysis_period': f"Last {len(recent_checks)} health checks",
            'timestamp': datetime.utcnow().isoformat()
        }


# Global health checker instance
_health_checker = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def perform_health_check() -> Dict[str, Any]:
    """Convenience function to perform comprehensive health check."""
    checker = get_health_checker()
    return checker.perform_comprehensive_health_check()