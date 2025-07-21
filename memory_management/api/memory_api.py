"""
Unified Memory API for accessing STM and LTM data.

Provides REST-like interface for compliance system integration.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json

from ..processors.stm_processor import STMProcessor
from ..processors.ltm_manager import LTMManager
from ..models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from ..models.ltm_rule import LTMRule


class MemoryAPIError(Exception):
    """Base exception for Memory API errors."""
    pass


class ValidationError(MemoryAPIError):
    """Raised when input validation fails."""
    pass


class NotFoundError(MemoryAPIError):
    """Raised when requested resource is not found."""
    pass


class MemoryAPI:
    """
    Unified API for accessing Short-Term Memory (STM) and Long-Term Memory (LTM) data.
    
    Provides structured access to memory data with proper error handling
    and JSON response formatting as required by Requirement 6.5.
    """
    
    def __init__(self, stm_processor: STMProcessor = None, ltm_manager: LTMManager = None):
        """
        Initialize Memory API with STM and LTM processors.
        
        Args:
            stm_processor: STMProcessor instance (creates default if None)
            ltm_manager: LTMManager instance (creates default if None)
        """
        self.stm_processor = stm_processor or STMProcessor()
        self.ltm_manager = ltm_manager or LTMManager()
        self.logger = logging.getLogger(__name__)
        
        # Link processors for bidirectional traceability
        if hasattr(self.ltm_manager, 'link_rule_to_stm_processor'):
            self.ltm_manager.link_rule_to_stm_processor(self.stm_processor)
    
    def _format_success_response(self, data: Any, message: str = "Success") -> Dict[str, Any]:
        """Format successful API response."""
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
    
    def _format_error_response(self, error: str, error_type: str = "error", 
                              details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format error API response."""
        response = {
            "status": "error",
            "error_type": error_type,
            "message": error,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        if details:
            response["details"] = details
        return response
    
    def _validate_scenario_id(self, scenario_id: str) -> None:
        """Validate scenario_id format."""
        if not scenario_id or not isinstance(scenario_id, str):
            raise ValidationError("scenario_id must be a non-empty string")
        
        # Check format: {domain}_{requirement_number}_{key_concept}
        parts = scenario_id.split('_')
        if len(parts) < 3:
            raise ValidationError("scenario_id must follow format: {domain}_{requirement_number}_{key_concept}")
    
    def _validate_assessment_data(self, data: Dict[str, Any]) -> None:
        """Validate assessment data structure."""
        required_fields = ['scenario_id', 'requirement_text', 'initial_assessment']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate initial_assessment structure
        assessment = data['initial_assessment']
        if not isinstance(assessment, dict):
            raise ValidationError("initial_assessment must be a dictionary")
        
        required_assessment_fields = ['status', 'rationale', 'recommendation']
        for field in required_assessment_fields:
            if field not in assessment:
                raise ValidationError(f"Missing required field in initial_assessment: {field}")
    
    def _validate_feedback_data(self, data: Dict[str, Any]) -> None:
        """Validate human feedback data structure."""
        required_fields = ['decision', 'rationale', 'suggestion']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field in feedback: {field}")
    
    # STM API Methods (Requirement 6.1)
    
    def get_stm_entry(self, scenario_id: str) -> Dict[str, Any]:
        """
        Retrieve STM entry by scenario_id.
        
        Implements Requirement 6.1: STM retrieval API by scenario_id
        
        Args:
            scenario_id: Unique scenario identifier
            
        Returns:
            Dict: JSON response with STM entry data or error
        """
        try:
            self._validate_scenario_id(scenario_id)
            
            entry = self.stm_processor.get_entry(scenario_id)
            if not entry:
                raise NotFoundError(f"STM entry not found: {scenario_id}")
            
            # Include traceability information
            traceability = self.stm_processor.get_traceability_info(scenario_id)
            
            return self._format_success_response({
                "stm_entry": entry.to_dict(),
                "traceability": traceability
            }, f"Retrieved STM entry: {scenario_id}")
            
        except (ValidationError, NotFoundError) as e:
            self.logger.warning(f"STM retrieval failed: {e}")
            return self._format_error_response(str(e), type(e).__name__.lower())
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving STM entry {scenario_id}: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    def list_stm_entries(self, status: str = None, has_feedback: bool = None, 
                        limit: int = 50) -> Dict[str, Any]:
        """
        List STM entries with optional filtering.
        
        Args:
            status: Filter by initial assessment status
            has_feedback: Filter by presence of human feedback
            limit: Maximum number of entries to return
            
        Returns:
            Dict: JSON response with list of STM entries
        """
        try:
            if status:
                entries = self.stm_processor.get_entries_by_status(status)
            elif has_feedback is True:
                entries = self.stm_processor.get_entries_with_feedback()
            elif has_feedback is False:
                entries = self.stm_processor.get_entries_without_feedback()
            else:
                entries = self.stm_processor.list_entries()
            
            # Apply limit
            entries = entries[:limit]
            
            # Convert to dict format
            entries_data = [entry.to_dict() for entry in entries]
            
            return self._format_success_response({
                "entries": entries_data,
                "count": len(entries_data),
                "filters": {
                    "status": status,
                    "has_feedback": has_feedback,
                    "limit": limit
                }
            }, f"Retrieved {len(entries_data)} STM entries")
            
        except Exception as e:
            self.logger.error(f"Error listing STM entries: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    def get_stm_stats(self) -> Dict[str, Any]:
        """
        Get STM statistics.
        
        Returns:
            Dict: JSON response with STM statistics
        """
        try:
            stats = self.stm_processor.get_stats()
            return self._format_success_response(stats, "Retrieved STM statistics")
            
        except Exception as e:
            self.logger.error(f"Error getting STM stats: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    # LTM API Methods (Requirement 6.2)
    
    def search_ltm_rules(self, query: str = None, concepts: List[str] = None, 
                        keywords: List[str] = None, policy: str = None, 
                        limit: int = 10) -> Dict[str, Any]:
        """
        Search LTM rules by concepts, keywords, and policy.
        
        Implements Requirement 6.2: LTM search API by concepts and keywords
        
        Args:
            query: Natural language query for semantic search
            concepts: List of concepts to match
            keywords: List of keywords to search in rule text
            policy: Policy name to filter by
            limit: Maximum number of results
            
        Returns:
            Dict: JSON response with matching LTM rules
        """
        try:
            if query:
                # Use semantic search for natural language queries
                scored_rules = self.ltm_manager.semantic_search_rules(query, limit)
                rules_data = []
                for rule, score in scored_rules:
                    rule_dict = rule.to_dict()
                    rule_dict['relevance_score'] = score
                    rules_data.append(rule_dict)
                
                search_type = "semantic"
                search_params = {"query": query, "limit": limit}
            else:
                # Use structured search
                rules = self.ltm_manager.search_ltm_rules(
                    concepts=concepts, 
                    keywords=keywords, 
                    policy=policy, 
                    limit=limit
                )
                rules_data = [rule.to_dict() for rule in rules]
                
                search_type = "structured"
                search_params = {
                    "concepts": concepts,
                    "keywords": keywords,
                    "policy": policy,
                    "limit": limit
                }
            
            return self._format_success_response({
                "rules": rules_data,
                "count": len(rules_data),
                "search_type": search_type,
                "search_params": search_params
            }, f"Found {len(rules_data)} matching LTM rules")
            
        except Exception as e:
            self.logger.error(f"Error searching LTM rules: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    def get_ltm_rule(self, rule_id: str) -> Dict[str, Any]:
        """
        Retrieve specific LTM rule by rule_id.
        
        Args:
            rule_id: Unique rule identifier
            
        Returns:
            Dict: JSON response with LTM rule data
        """
        try:
            if not rule_id or not isinstance(rule_id, str):
                raise ValidationError("rule_id must be a non-empty string")
            
            rule = self.ltm_manager.get_ltm_rule(rule_id)
            if not rule:
                raise NotFoundError(f"LTM rule not found: {rule_id}")
            
            # Include traceability information
            traceability = self.ltm_manager.get_rule_traceability(rule_id)
            
            return self._format_success_response({
                "ltm_rule": rule.to_dict(),
                "traceability": traceability
            }, f"Retrieved LTM rule: {rule_id}")
            
        except (ValidationError, NotFoundError) as e:
            self.logger.warning(f"LTM rule retrieval failed: {e}")
            return self._format_error_response(str(e), type(e).__name__.lower())
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving LTM rule {rule_id}: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    def get_rules_by_concept(self, concept: str) -> Dict[str, Any]:
        """
        Get all rules related to a specific concept.
        
        Args:
            concept: Concept name
            
        Returns:
            Dict: JSON response with related rules
        """
        try:
            if not concept or not isinstance(concept, str):
                raise ValidationError("concept must be a non-empty string")
            
            rules = self.ltm_manager.get_concept_relationships(concept)
            
            return self._format_success_response({
                "concept": concept,
                "rules": rules,
                "count": len(rules)
            }, f"Found {len(rules)} rules for concept: {concept}")
            
        except ValidationError as e:
            self.logger.warning(f"Concept search failed: {e}")
            return self._format_error_response(str(e), "validation_error")
        except Exception as e:
            self.logger.error(f"Error getting rules by concept {concept}: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    # Assessment Management API Methods (Requirements 6.3, 6.4)
    
    def add_new_assessment(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new compliance assessment to STM.
        
        Implements Requirement 6.3: APIs for adding new assessments
        
        Args:
            assessment_data: Dictionary containing assessment information
            
        Returns:
            Dict: JSON response with created STM entry
        """
        try:
            self._validate_assessment_data(assessment_data)
            
            scenario_id = assessment_data['scenario_id']
            requirement_text = assessment_data['requirement_text']
            
            # Create InitialAssessment object
            assessment_info = assessment_data['initial_assessment']
            initial_assessment = InitialAssessment(
                status=assessment_info['status'],
                rationale=assessment_info['rationale'],
                recommendation=assessment_info['recommendation']
            )
            
            # Create STM entry
            entry = self.stm_processor.create_entry(
                scenario_id=scenario_id,
                requirement_text=requirement_text,
                initial_assessment=initial_assessment
            )
            
            return self._format_success_response({
                "stm_entry": entry.to_dict(),
                "scenario_id": scenario_id
            }, f"Created new assessment: {scenario_id}")
            
        except ValidationError as e:
            self.logger.warning(f"Assessment creation failed: {e}")
            return self._format_error_response(str(e), "validation_error")
        except ValueError as e:
            self.logger.warning(f"Assessment creation failed: {e}")
            return self._format_error_response(str(e), "conflict_error")
        except Exception as e:
            self.logger.error(f"Unexpected error creating assessment: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    def update_with_feedback(self, scenario_id: str, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing STM entry with human feedback and generate LTM rules.
        
        Implements Requirement 6.4: APIs for updating with feedback
        
        Args:
            scenario_id: Scenario identifier
            feedback_data: Dictionary containing human feedback
            
        Returns:
            Dict: JSON response with updated STM entry and any generated LTM rules
        """
        try:
            self._validate_scenario_id(scenario_id)
            self._validate_feedback_data(feedback_data)
            
            # Update STM entry with feedback
            updated_entry = self.stm_processor.add_human_feedback(
                scenario_id=scenario_id,
                decision=feedback_data['decision'],
                rationale=feedback_data['rationale'],
                suggestion=feedback_data['suggestion']
            )
            
            if not updated_entry:
                raise NotFoundError(f"STM entry not found: {scenario_id}")
            
            # Set final status if provided
            if 'final_status' in feedback_data:
                updated_entry = self.stm_processor.set_final_status(
                    scenario_id, feedback_data['final_status']
                )
            
            # Generate LTM rules from the feedback (if rule extractor is available)
            generated_rules = []
            try:
                # This would integrate with the RuleExtractor when available
                # For now, we'll return the updated entry
                pass
            except Exception as e:
                self.logger.warning(f"LTM rule generation failed for {scenario_id}: {e}")
            
            response_data = {
                "updated_stm_entry": updated_entry.to_dict(),
                "generated_ltm_rules": generated_rules,
                "scenario_id": scenario_id
            }
            
            return self._format_success_response(
                response_data, 
                f"Updated assessment with feedback: {scenario_id}"
            )
            
        except (ValidationError, NotFoundError) as e:
            self.logger.warning(f"Feedback update failed: {e}")
            return self._format_error_response(str(e), type(e).__name__.lower())
        except Exception as e:
            self.logger.error(f"Unexpected error updating with feedback: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    def update_stm_entry(self, scenario_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update specific fields of an STM entry.
        
        Args:
            scenario_id: Scenario identifier
            updates: Dictionary of fields to update
            
        Returns:
            Dict: JSON response with updated STM entry
        """
        try:
            self._validate_scenario_id(scenario_id)
            
            updated_entry = self.stm_processor.update_entry(scenario_id, **updates)
            if not updated_entry:
                raise NotFoundError(f"STM entry not found: {scenario_id}")
            
            return self._format_success_response({
                "updated_stm_entry": updated_entry.to_dict(),
                "scenario_id": scenario_id,
                "updated_fields": list(updates.keys())
            }, f"Updated STM entry: {scenario_id}")
            
        except (ValidationError, NotFoundError) as e:
            self.logger.warning(f"STM update failed: {e}")
            return self._format_error_response(str(e), type(e).__name__.lower())
        except Exception as e:
            self.logger.error(f"Unexpected error updating STM entry: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    # Traceability API Methods (Requirement 4.1-4.5)
    
    def get_traceability_chain(self, scenario_id: str) -> Dict[str, Any]:
        """
        Get complete traceability chain from STM entry to derived LTM rules.
        
        Args:
            scenario_id: STM scenario identifier
            
        Returns:
            Dict: JSON response with complete traceability information
        """
        try:
            self._validate_scenario_id(scenario_id)
            
            # Get STM traceability info
            stm_traceability = self.stm_processor.get_traceability_info(scenario_id)
            if not stm_traceability:
                raise NotFoundError(f"STM entry not found: {scenario_id}")
            
            # Get derived LTM rules
            derived_rules = self.ltm_manager.get_rules_by_source_scenario(scenario_id)
            
            # Get audit trails for each derived rule
            rule_audit_trails = {}
            for rule in derived_rules:
                rule_audit_trails[rule.rule_id] = self.ltm_manager.get_complete_audit_trail(rule.rule_id)
            
            return self._format_success_response({
                "scenario_id": scenario_id,
                "stm_traceability": stm_traceability,
                "derived_ltm_rules": [rule.to_dict() for rule in derived_rules],
                "rule_audit_trails": rule_audit_trails,
                "traceability_summary": {
                    "has_stm_entry": bool(stm_traceability.get('stm_entry')),
                    "has_human_feedback": stm_traceability.get('has_human_feedback', False),
                    "derived_rules_count": len(derived_rules),
                    "final_status": stm_traceability.get('final_status')
                }
            }, f"Retrieved traceability chain for: {scenario_id}")
            
        except (ValidationError, NotFoundError) as e:
            self.logger.warning(f"Traceability retrieval failed: {e}")
            return self._format_error_response(str(e), type(e).__name__.lower())
        except Exception as e:
            self.logger.error(f"Unexpected error getting traceability chain: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    def get_rule_audit_trail(self, rule_id: str) -> Dict[str, Any]:
        """
        Get complete audit trail for an LTM rule.
        
        Args:
            rule_id: LTM rule identifier
            
        Returns:
            Dict: JSON response with complete audit trail
        """
        try:
            if not rule_id or not isinstance(rule_id, str):
                raise ValidationError("rule_id must be a non-empty string")
            
            audit_trail = self.ltm_manager.get_complete_audit_trail(rule_id)
            if not audit_trail:
                raise NotFoundError(f"LTM rule not found: {rule_id}")
            
            return self._format_success_response(
                audit_trail, 
                f"Retrieved audit trail for rule: {rule_id}"
            )
            
        except (ValidationError, NotFoundError) as e:
            self.logger.warning(f"Audit trail retrieval failed: {e}")
            return self._format_error_response(str(e), type(e).__name__.lower())
        except Exception as e:
            self.logger.error(f"Unexpected error getting audit trail: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    # Health and Status API Methods
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health status of memory systems.
        
        Returns:
            Dict: JSON response with health status
        """
        try:
            health_status = {
                "stm_processor": "healthy",
                "ltm_manager": "healthy",
                "redis_connection": "unknown",
                "neo4j_connection": "unknown"
            }
            
            # Test Redis connection
            try:
                self.stm_processor.redis_client.ping()
                health_status["redis_connection"] = "healthy"
            except Exception as e:
                health_status["redis_connection"] = f"unhealthy: {str(e)}"
            
            # Test Neo4j connection
            try:
                with self.ltm_manager.driver.session() as session:
                    session.run("RETURN 1")
                health_status["neo4j_connection"] = "healthy"
            except Exception as e:
                health_status["neo4j_connection"] = f"unhealthy: {str(e)}"
            
            overall_status = "healthy" if all(
                status == "healthy" for status in health_status.values()
            ) else "degraded"
            
            return self._format_success_response({
                "overall_status": overall_status,
                "components": health_status
            }, "Health check completed")
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return self._format_error_response("Health check failed", "internal_error")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics.
        
        Returns:
            Dict: JSON response with system statistics
        """
        try:
            stm_stats = self.stm_processor.get_stats()
            
            # Get LTM stats
            all_rules = self.ltm_manager.get_all_rules()
            ltm_stats = {
                "total_rules": len(all_rules),
                "average_confidence": sum(rule.confidence_score for rule in all_rules) / len(all_rules) if all_rules else 0,
                "rules_by_policy": {},
                "total_concepts": len(set(concept for rule in all_rules for concept in rule.related_concepts))
            }
            
            # Count rules by policy
            for rule in all_rules:
                policy = rule.rule_id.split('_')[0]
                ltm_stats["rules_by_policy"][policy] = ltm_stats["rules_by_policy"].get(policy, 0) + 1
            
            return self._format_success_response({
                "stm_stats": stm_stats,
                "ltm_stats": ltm_stats,
                "system_info": {
                    "api_version": "1.0.0",
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                }
            }, "Retrieved system statistics")
            
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return self._format_error_response("Internal server error", "internal_error")
    
    def close(self) -> None:
        """Close database connections."""
        try:
            if hasattr(self.ltm_manager, 'close'):
                self.ltm_manager.close()
            self.logger.info("Memory API connections closed")
        except Exception as e:
            self.logger.error(f"Error closing connections: {e}")