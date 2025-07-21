"""
Performance monitoring and metrics collection for Memory Management Module.

Implements comprehensive performance monitoring, metrics collection, and alerting
to ensure sub-second response times and optimal system performance.
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import statistics
from functools import wraps

from ..config.settings import get_settings


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Performance alert rule configuration."""
    name: str
    metric_name: str
    threshold: float
    comparison: str  # 'gt', 'lt', 'eq'
    duration_seconds: int
    enabled: bool = True
    callback: Optional[Callable] = None


class MetricsCollector:
    """
    Comprehensive metrics collector for performance monitoring.
    
    Collects, aggregates, and analyzes performance metrics from all
    Memory Management Module components.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        
        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.aggregated_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Alert rules and state
        self.alert_rules: List[AlertRule] = []
        self.alert_state: Dict[str, Dict[str, Any]] = {}
        
        # Performance thresholds
        self.thresholds = {
            'stm_response_time_ms': 100,  # Sub-second requirement
            'ltm_response_time_ms': 500,  # Sub-second requirement
            'api_response_time_ms': 1000,  # 1 second max
            'cache_hit_rate_percent': 70,  # Minimum cache efficiency
            'connection_pool_utilization_percent': 80,  # Max pool usage
            'error_rate_percent': 1  # Maximum error rate
        }
        
        # Metrics collection thread
        self._collection_thread = None
        self._stop_collection = threading.Event()
        
        # Initialize default alert rules
        self._setup_default_alerts()
        
        self.logger.info("Metrics collector initialized")
    
    def _setup_default_alerts(self) -> None:
        """Setup default performance alert rules."""
        default_alerts = [
            AlertRule(
                name="High STM Response Time",
                metric_name="stm_response_time_ms",
                threshold=self.thresholds['stm_response_time_ms'],
                comparison="gt",
                duration_seconds=60
            ),
            AlertRule(
                name="High LTM Response Time",
                metric_name="ltm_response_time_ms",
                threshold=self.thresholds['ltm_response_time_ms'],
                comparison="gt",
                duration_seconds=60
            ),
            AlertRule(
                name="Low Cache Hit Rate",
                metric_name="cache_hit_rate_percent",
                threshold=self.thresholds['cache_hit_rate_percent'],
                comparison="lt",
                duration_seconds=300
            ),
            AlertRule(
                name="High Error Rate",
                metric_name="error_rate_percent",
                threshold=self.thresholds['error_rate_percent'],
                comparison="gt",
                duration_seconds=120
            )
        ]
        
        self.alert_rules.extend(default_alerts)
    
    def record_metric(self, name: str, value: float, unit: str = "count", 
                     tags: Dict[str, str] = None, metadata: Dict[str, Any] = None) -> None:
        """
        Record a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            tags: Optional tags for categorization
            metadata: Optional additional metadata
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self.metrics[name].append(metric)
        self.logger.debug(f"Recorded metric: {name}={value}{unit}")
        
        # Check alert rules
        self._check_alerts(metric)
    
    def record_timing(self, operation_name: str, execution_time_ms: float, 
                     component: str = None, success: bool = True) -> None:
        """
        Record operation timing metric.
        
        Args:
            operation_name: Name of the operation
            execution_time_ms: Execution time in milliseconds
            component: Component name (STM, LTM, API)
            success: Whether operation was successful
        """
        tags = {
            'operation': operation_name,
            'success': str(success)
        }
        if component:
            tags['component'] = component
        
        self.record_metric(
            name=f"{component.lower()}_response_time_ms" if component else "response_time_ms",
            value=execution_time_ms,
            unit="ms",
            tags=tags
        )
        
        # Record success/error rate
        self.record_metric(
            name=f"{component.lower()}_operation_result" if component else "operation_result",
            value=1 if success else 0,
            unit="bool",
            tags=tags
        )
    
    def timing_decorator(self, operation_name: str, component: str = None):
        """
        Decorator for automatic timing measurement.
        
        Args:
            operation_name: Name of the operation
            component: Component name
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    execution_time = (time.time() - start_time) * 1000
                    self.record_timing(operation_name, execution_time, component, success)
            return wrapper
        return decorator
    
    def record_cache_metrics(self, hits: int, misses: int, component: str = "cache") -> None:
        """
        Record cache performance metrics.
        
        Args:
            hits: Number of cache hits
            misses: Number of cache misses
            component: Component name
        """
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
        
        self.record_metric(
            name=f"{component}_hit_rate_percent",
            value=hit_rate,
            unit="percent",
            tags={'component': component}
        )
        
        self.record_metric(
            name=f"{component}_requests_total",
            value=total_requests,
            unit="count",
            tags={'component': component}
        )
    
    def record_connection_metrics(self, pool_size: int, active_connections: int, 
                                 component: str = "database") -> None:
        """
        Record database connection pool metrics.
        
        Args:
            pool_size: Maximum pool size
            active_connections: Currently active connections
            component: Component name
        """
        utilization = (active_connections / pool_size * 100) if pool_size > 0 else 0
        
        self.record_metric(
            name=f"{component}_pool_utilization_percent",
            value=utilization,
            unit="percent",
            tags={'component': component}
        )
        
        self.record_metric(
            name=f"{component}_active_connections",
            value=active_connections,
            unit="count",
            tags={'component': component}
        )
    
    def get_metric_summary(self, metric_name: str, time_window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get summary statistics for a metric over a time window.
        
        Args:
            metric_name: Name of the metric
            time_window_minutes: Time window in minutes
            
        Returns:
            Dictionary with metric summary
        """
        if metric_name not in self.metrics:
            return {'error': f'Metric {metric_name} not found'}
        
        # Filter metrics by time window
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_metrics = [m for m in self.metrics[metric_name] if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {'error': f'No recent data for metric {metric_name}'}
        
        values = [m.value for m in recent_metrics]
        
        return {
            'metric_name': metric_name,
            'time_window_minutes': time_window_minutes,
            'data_points': len(values),
            'statistics': {
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                'p95': self._calculate_percentile(values, 95),
                'p99': self._calculate_percentile(values, 99)
            },
            'latest_value': recent_metrics[-1].value,
            'latest_timestamp': recent_metrics[-1].timestamp.isoformat(),
            'unit': recent_metrics[-1].unit
        }
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive performance dashboard data.
        
        Returns:
            Dictionary with dashboard metrics
        """
        dashboard = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_health': 'healthy',
            'alerts': [],
            'key_metrics': {},
            'component_performance': {}
        }
        
        # Key performance indicators
        key_metrics = [
            'stm_response_time_ms',
            'ltm_response_time_ms',
            'api_response_time_ms',
            'cache_hit_rate_percent',
            'error_rate_percent'
        ]
        
        for metric_name in key_metrics:
            summary = self.get_metric_summary(metric_name, 15)  # Last 15 minutes
            if 'error' not in summary:
                dashboard['key_metrics'][metric_name] = {
                    'current': summary['latest_value'],
                    'average': summary['statistics']['mean'],
                    'p95': summary['statistics']['p95'],
                    'threshold': self.thresholds.get(metric_name),
                    'status': self._get_metric_status(metric_name, summary['latest_value'])
                }
        
        # Component-specific performance
        components = ['stm', 'ltm', 'api', 'redis', 'neo4j']
        for component in components:
            component_metrics = {}
            for metric_name in self.metrics:
                if component in metric_name:
                    summary = self.get_metric_summary(metric_name, 15)
                    if 'error' not in summary:
                        component_metrics[metric_name] = summary['latest_value']
            
            if component_metrics:
                dashboard['component_performance'][component] = component_metrics
        
        # Active alerts
        dashboard['alerts'] = self._get_active_alerts()
        
        # Overall system health
        if dashboard['alerts']:
            dashboard['system_health'] = 'warning' if any(a['severity'] == 'warning' for a in dashboard['alerts']) else 'critical'
        
        return dashboard
    
    def _get_metric_status(self, metric_name: str, current_value: float) -> str:
        """Get status for a metric based on thresholds."""
        threshold = self.thresholds.get(metric_name)
        if not threshold:
            return 'unknown'
        
        if 'response_time' in metric_name or 'error_rate' in metric_name:
            # Lower is better
            if current_value <= threshold * 0.7:
                return 'good'
            elif current_value <= threshold:
                return 'warning'
            else:
                return 'critical'
        else:
            # Higher is better (like cache hit rate)
            if current_value >= threshold:
                return 'good'
            elif current_value >= threshold * 0.8:
                return 'warning'
            else:
                return 'critical'
    
    def _check_alerts(self, metric: PerformanceMetric) -> None:
        """Check if metric triggers any alert rules."""
        for rule in self.alert_rules:
            if not rule.enabled or rule.metric_name != metric.name:
                continue
            
            # Check threshold condition
            triggered = False
            if rule.comparison == 'gt' and metric.value > rule.threshold:
                triggered = True
            elif rule.comparison == 'lt' and metric.value < rule.threshold:
                triggered = True
            elif rule.comparison == 'eq' and metric.value == rule.threshold:
                triggered = True
            
            if triggered:
                self._handle_alert_trigger(rule, metric)
    
    def _handle_alert_trigger(self, rule: AlertRule, metric: PerformanceMetric) -> None:
        """Handle alert rule trigger."""
        alert_key = f"{rule.name}_{rule.metric_name}"
        current_time = datetime.utcnow()
        
        if alert_key not in self.alert_state:
            self.alert_state[alert_key] = {
                'first_triggered': current_time,
                'last_triggered': current_time,
                'trigger_count': 1,
                'active': False
            }
        else:
            self.alert_state[alert_key]['last_triggered'] = current_time
            self.alert_state[alert_key]['trigger_count'] += 1
        
        # Check if alert should be active based on duration
        alert_duration = (current_time - self.alert_state[alert_key]['first_triggered']).total_seconds()
        
        if alert_duration >= rule.duration_seconds and not self.alert_state[alert_key]['active']:
            self.alert_state[alert_key]['active'] = True
            self._fire_alert(rule, metric, alert_duration)
    
    def _fire_alert(self, rule: AlertRule, metric: PerformanceMetric, duration: float) -> None:
        """Fire an active alert."""
        alert_message = (f"Alert: {rule.name} - {rule.metric_name} is {metric.value} "
                        f"(threshold: {rule.threshold}) for {duration:.0f} seconds")
        
        self.logger.warning(alert_message)
        
        # Call custom callback if provided
        if rule.callback:
            try:
                rule.callback(rule, metric, duration)
            except Exception as e:
                self.logger.error(f"Alert callback error: {e}")
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of currently active alerts."""
        active_alerts = []
        current_time = datetime.utcnow()
        
        for alert_key, state in self.alert_state.items():
            if state['active']:
                # Find corresponding rule
                rule_name = alert_key.split('_')[0]
                rule = next((r for r in self.alert_rules if r.name == rule_name), None)
                
                if rule:
                    duration = (current_time - state['first_triggered']).total_seconds()
                    active_alerts.append({
                        'name': rule.name,
                        'metric': rule.metric_name,
                        'threshold': rule.threshold,
                        'duration_seconds': duration,
                        'trigger_count': state['trigger_count'],
                        'severity': 'critical' if duration > 600 else 'warning'  # 10 minutes
                    })
        
        return active_alerts
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add a custom alert rule."""
        self.alert_rules.append(rule)
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str) -> bool:
        """Remove an alert rule by name."""
        original_count = len(self.alert_rules)
        self.alert_rules = [r for r in self.alert_rules if r.name != rule_name]
        removed = len(self.alert_rules) < original_count
        
        if removed:
            self.logger.info(f"Removed alert rule: {rule_name}")
        
        return removed
    
    def start_background_collection(self, interval_seconds: int = 60) -> None:
        """
        Start background metrics collection thread.
        
        Args:
            interval_seconds: Collection interval in seconds
        """
        if self._collection_thread and self._collection_thread.is_alive():
            self.logger.warning("Background collection already running")
            return
        
        def collection_loop():
            while not self._stop_collection.wait(interval_seconds):
                try:
                    self._collect_system_metrics()
                except Exception as e:
                    self.logger.error(f"Background collection error: {e}")
        
        self._collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self._collection_thread.start()
        self.logger.info(f"Started background metrics collection (interval: {interval_seconds}s)")
    
    def stop_background_collection(self) -> None:
        """Stop background metrics collection."""
        self._stop_collection.set()
        if self._collection_thread:
            self._collection_thread.join(timeout=5)
        self.logger.info("Stopped background metrics collection")
    
    def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        try:
            # This would integrate with actual system monitoring
            # For now, we'll record basic health metrics
            self.record_metric("system_timestamp", time.time(), "timestamp")
            self.record_metric("metrics_collected", len(self.metrics), "count")
            
        except Exception as e:
            self.logger.error(f"System metrics collection error: {e}")
    
    def export_metrics(self, format_type: str = "json", time_window_minutes: int = 60) -> str:
        """
        Export metrics in specified format.
        
        Args:
            format_type: Export format ('json', 'csv')
            time_window_minutes: Time window for export
            
        Returns:
            Exported metrics string
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        if format_type == "json":
            export_data = {}
            for metric_name, metric_deque in self.metrics.items():
                recent_metrics = [m for m in metric_deque if m.timestamp >= cutoff_time]
                export_data[metric_name] = [
                    {
                        'value': m.value,
                        'unit': m.unit,
                        'timestamp': m.timestamp.isoformat(),
                        'tags': m.tags,
                        'metadata': m.metadata
                    }
                    for m in recent_metrics
                ]
            
            return json.dumps(export_data, indent=2)
        
        elif format_type == "csv":
            # Simple CSV export
            lines = ["metric_name,value,unit,timestamp,tags"]
            for metric_name, metric_deque in self.metrics.items():
                recent_metrics = [m for m in metric_deque if m.timestamp >= cutoff_time]
                for m in recent_metrics:
                    tags_str = json.dumps(m.tags) if m.tags else ""
                    lines.append(f"{metric_name},{m.value},{m.unit},{m.timestamp.isoformat()},{tags_str}")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def clear_metrics(self, metric_name: str = None) -> int:
        """
        Clear metrics data.
        
        Args:
            metric_name: Specific metric to clear (clears all if None)
            
        Returns:
            Number of metrics cleared
        """
        if metric_name:
            if metric_name in self.metrics:
                count = len(self.metrics[metric_name])
                self.metrics[metric_name].clear()
                self.logger.info(f"Cleared {count} data points for metric: {metric_name}")
                return count
            return 0
        else:
            total_count = sum(len(deque) for deque in self.metrics.values())
            self.metrics.clear()
            self.alert_state.clear()
            self.logger.info(f"Cleared all metrics ({total_count} data points)")
            return total_count


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_performance_metric(name: str, value: float, unit: str = "count", 
                            tags: Dict[str, str] = None) -> None:
    """Convenience function to record a performance metric."""
    collector = get_metrics_collector()
    collector.record_metric(name, value, unit, tags)


def timing_decorator(operation_name: str, component: str = None):
    """Convenience decorator for timing operations."""
    collector = get_metrics_collector()
    return collector.timing_decorator(operation_name, component)