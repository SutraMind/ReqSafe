"""
STM (Short-Term Memory) Processor for managing immediate compliance assessments.
"""
import redis
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from ..performance.redis_pool import get_redis_pool, get_cache_manager
from ..performance.metrics_collector import get_metrics_collector, timing_decorator


class STMProcessor:
    """
    Processor for managing Short-Term Memory entries in Redis.
    
    Handles CRUD operations for STM entries, providing fast access to
    immediate compliance assessment results.
    """
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, 
                 redis_db: int = 0, redis_password: Optional[str] = None, use_pool: bool = True):
        """
        Initialize STM processor with Redis connection.
        
        Args:
            redis_host: Redis server hostname
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password (optional)
            use_pool: Whether to use connection pooling (recommended)
        """
        self.logger = logging.getLogger(__name__)
        self.metrics_collector = get_metrics_collector()
        
        if use_pool:
            # Use optimized connection pool
            self.redis_pool = get_redis_pool()
            self.redis_client = self.redis_pool.get_client()
            self.cache_manager = get_cache_manager()
            self.logger.info("Using Redis connection pool for STM operations")
        else:
            # Fallback to direct connection
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True
            )
            self.redis_pool = None
            self.cache_manager = None
        
        # Test connection
        try:
            self.redis_client.ping()
            self.logger.info("Connected to Redis successfully")
        except redis.ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    @timing_decorator("stm_create_entry", "STM")
    def create_entry(self, scenario_id: str, requirement_text: str, 
                    initial_assessment: InitialAssessment) -> STMEntry:
        """
        Create a new STM entry with performance monitoring.
        
        Args:
            scenario_id: Unique identifier for the compliance scenario
            requirement_text: Original requirement text
            initial_assessment: Initial assessment from RA_Agent
            
        Returns:
            Created STMEntry
            
        Raises:
            ValueError: If entry with scenario_id already exists
        """
        if self.get_entry(scenario_id):
            raise ValueError(f"STM entry with scenario_id '{scenario_id}' already exists")
        
        entry = STMEntry(
            scenario_id=scenario_id,
            requirement_text=requirement_text,
            initial_assessment=initial_assessment
        )
        
        if not entry.validate():
            raise ValueError("Invalid STM entry data")
        
        # Store in Redis with TTL of 24 hours using optimized connection
        key = f"stm:{scenario_id}"
        if self.redis_pool:
            result, execution_time = self.redis_pool.execute_with_timing(
                "stm_create",
                self.redis_client.setex,
                key, timedelta(hours=24), entry.to_json()
            )
        else:
            self.redis_client.setex(key, timedelta(hours=24), entry.to_json())
        
        # Record metrics
        self.metrics_collector.record_metric("stm_entries_created", 1, "count")
        
        self.logger.info(f"Created STM entry: {scenario_id}")
        return entry
    
    def get_entry(self, scenario_id: str) -> Optional[STMEntry]:
        """
        Retrieve STM entry by scenario ID.
        
        Args:
            scenario_id: Scenario identifier
            
        Returns:
            STMEntry if found, None otherwise
        """
        key = f"stm:{scenario_id}"
        data = self.redis_client.get(key)
        
        if not data:
            return None
        
        try:
            return STMEntry.from_json(data)
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Failed to deserialize STM entry {scenario_id}: {e}")
            return None
    
    def update_entry(self, scenario_id: str, **kwargs) -> Optional[STMEntry]:
        """
        Update an existing STM entry.
        
        Args:
            scenario_id: Scenario identifier
            **kwargs: Fields to update
            
        Returns:
            Updated STMEntry if found, None otherwise
        """
        entry = self.get_entry(scenario_id)
        if not entry:
            return None
        
        # Update fields
        for field, value in kwargs.items():
            if hasattr(entry, field):
                setattr(entry, field, value)
        
        entry.updated_at = datetime.utcnow()
        
        if not entry.validate():
            raise ValueError("Invalid STM entry data after update")
        
        # Store updated entry
        key = f"stm:{scenario_id}"
        self.redis_client.setex(key, timedelta(hours=24), entry.to_json())
        
        self.logger.info(f"Updated STM entry: {scenario_id}")
        return entry
    
    def add_human_feedback(self, scenario_id: str, decision: str, 
                          rationale: str, suggestion: str) -> Optional[STMEntry]:
        """
        Add human feedback to an STM entry.
        
        Args:
            scenario_id: Scenario identifier
            decision: Human expert decision
            rationale: Reasoning behind the decision
            suggestion: Expert suggestion
            
        Returns:
            Updated STMEntry if found, None otherwise
        """
        entry = self.get_entry(scenario_id)
        if not entry:
            return None
        
        entry.update_with_feedback(decision, rationale, suggestion)
        
        # Store updated entry
        key = f"stm:{scenario_id}"
        self.redis_client.setex(key, timedelta(hours=24), entry.to_json())
        
        self.logger.info(f"Added human feedback to STM entry: {scenario_id}")
        return entry
    
    def set_final_status(self, scenario_id: str, status: str) -> Optional[STMEntry]:
        """
        Set final compliance status for an STM entry.
        
        Args:
            scenario_id: Scenario identifier
            status: Final compliance status
            
        Returns:
            Updated STMEntry if found, None otherwise
        """
        entry = self.get_entry(scenario_id)
        if not entry:
            return None
        
        entry.set_final_status(status)
        
        # Store updated entry
        key = f"stm:{scenario_id}"
        self.redis_client.setex(key, timedelta(hours=24), entry.to_json())
        
        self.logger.info(f"Set final status for STM entry {scenario_id}: {status}")
        return entry
    
    def delete_entry(self, scenario_id: str) -> bool:
        """
        Delete an STM entry.
        
        Args:
            scenario_id: Scenario identifier
            
        Returns:
            True if deleted, False if not found
        """
        key = f"stm:{scenario_id}"
        result = self.redis_client.delete(key)
        
        if result:
            self.logger.info(f"Deleted STM entry: {scenario_id}")
            return True
        return False
    
    def list_entries(self, pattern: str = "*") -> List[STMEntry]:
        """
        List all STM entries matching a pattern.
        
        Args:
            pattern: Redis key pattern (default: all entries)
            
        Returns:
            List of STMEntry objects
        """
        keys = self.redis_client.keys(f"stm:{pattern}")
        entries = []
        
        for key in keys:
            data = self.redis_client.get(key)
            if data:
                try:
                    entry = STMEntry.from_json(data)
                    entries.append(entry)
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.error(f"Failed to deserialize entry {key}: {e}")
        
        return entries
    
    def get_entries_by_status(self, status: str) -> List[STMEntry]:
        """
        Get all entries with a specific initial assessment status.
        
        Args:
            status: Assessment status to filter by
            
        Returns:
            List of matching STMEntry objects
        """
        all_entries = self.list_entries()
        return [entry for entry in all_entries 
                if entry.initial_assessment.status == status]
    
    def get_entries_with_feedback(self) -> List[STMEntry]:
        """
        Get all entries that have human feedback.
        
        Returns:
            List of STMEntry objects with human feedback
        """
        all_entries = self.list_entries()
        return [entry for entry in all_entries if entry.human_feedback is not None]
    
    def get_entries_without_feedback(self) -> List[STMEntry]:
        """
        Get all entries that don't have human feedback.
        
        Returns:
            List of STMEntry objects without human feedback
        """
        all_entries = self.list_entries()
        return [entry for entry in all_entries if entry.human_feedback is None]
    
    def extend_ttl(self, scenario_id: str, hours: int = 24) -> bool:
        """
        Extend the TTL (time-to-live) for an STM entry.
        
        Args:
            scenario_id: Scenario identifier
            hours: Hours to extend TTL
            
        Returns:
            True if TTL was extended, False if entry not found
        """
        key = f"stm:{scenario_id}"
        if self.redis_client.exists(key):
            self.redis_client.expire(key, timedelta(hours=hours))
            self.logger.info(f"Extended TTL for STM entry {scenario_id} by {hours} hours")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about STM entries.
        
        Returns:
            Dictionary with statistics
        """
        all_entries = self.list_entries()
        
        stats = {
            'total_entries': len(all_entries),
            'entries_with_feedback': len(self.get_entries_with_feedback()),
            'entries_without_feedback': len(self.get_entries_without_feedback()),
            'status_breakdown': {}
        }
        
        # Count by status
        for entry in all_entries:
            status = entry.initial_assessment.status
            stats['status_breakdown'][status] = stats['status_breakdown'].get(status, 0) + 1
        
        return stats
    
    def get_related_ltm_rules(self, scenario_id: str) -> List[str]:
        """
        Get LTM rule IDs that were derived from this STM entry.
        
        This method provides traceability from STM to LTM by finding
        rules that reference this scenario_id as a source.
        
        Args:
            scenario_id: Scenario identifier
            
        Returns:
            List of LTM rule IDs that reference this scenario
        """
        # Store related rule IDs in Redis for fast lookup
        key = f"stm_ltm_links:{scenario_id}"
        rule_ids = self.redis_client.smembers(key)
        return list(rule_ids) if rule_ids else []
    
    def add_ltm_rule_link(self, scenario_id: str, rule_id: str) -> bool:
        """
        Add a link from STM entry to an LTM rule.
        
        This creates bidirectional traceability between STM and LTM.
        
        Args:
            scenario_id: STM scenario identifier
            rule_id: LTM rule identifier
            
        Returns:
            True if link was added successfully
        """
        if not self.get_entry(scenario_id):
            self.logger.error(f"STM entry {scenario_id} not found")
            return False
        
        key = f"stm_ltm_links:{scenario_id}"
        result = self.redis_client.sadd(key, rule_id)
        
        # Set TTL to match STM entry TTL
        self.redis_client.expire(key, timedelta(hours=24))
        
        if result:
            self.logger.info(f"Added LTM rule link: {scenario_id} -> {rule_id}")
            return True
        return False
    
    def remove_ltm_rule_link(self, scenario_id: str, rule_id: str) -> bool:
        """
        Remove a link from STM entry to an LTM rule.
        
        Args:
            scenario_id: STM scenario identifier
            rule_id: LTM rule identifier
            
        Returns:
            True if link was removed successfully
        """
        key = f"stm_ltm_links:{scenario_id}"
        result = self.redis_client.srem(key, rule_id)
        
        if result:
            self.logger.info(f"Removed LTM rule link: {scenario_id} -> {rule_id}")
            return True
        return False
    
    def get_traceability_info(self, scenario_id: str) -> Dict[str, Any]:
        """
        Get complete traceability information for an STM entry.
        
        This provides a comprehensive view of how this STM entry
        relates to LTM rules and other system components.
        
        Args:
            scenario_id: Scenario identifier
            
        Returns:
            Dictionary containing traceability information
        """
        entry = self.get_entry(scenario_id)
        if not entry:
            return {}
        
        related_rules = self.get_related_ltm_rules(scenario_id)
        
        return {
            'stm_entry': entry.to_dict(),
            'related_ltm_rules': related_rules,
            'has_human_feedback': entry.human_feedback is not None,
            'final_status': entry.final_status,
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
            'updated_at': entry.updated_at.isoformat() if entry.updated_at else None
        }
    
    def cleanup_expired(self) -> int:
        """
        Clean up any expired entries (Redis handles this automatically, but this is for manual cleanup).
        
        Returns:
            Number of entries cleaned up
        """
        # Redis handles TTL automatically, but we can implement manual cleanup if needed
        keys = self.redis_client.keys("stm:*")
        cleaned = 0
        
        for key in keys:
            if not self.redis_client.exists(key):
                cleaned += 1
        
        self.logger.info(f"Cleaned up {cleaned} expired STM entries")
        return cleaned