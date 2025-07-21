"""
Long-Term Memory (LTM) Manager for Neo4j operations.

Handles CRUD operations for LTM rules in Neo4j graph database with semantic search capabilities.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, TransientError
import json
import os
from datetime import datetime

from ..models.ltm_rule import LTMRule
from ..llm.client import LLMClient


class LTMManager:
    """
    Manages Long-Term Memory rules in Neo4j graph database.
    
    Provides CRUD operations, semantic search, and relationship management
    for compliance rules, concepts, and scenarios.
    """
    
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """
        Initialize LTM Manager with Neo4j connection.
        
        Args:
            uri: Neo4j database URI (defaults to env var NEO4J_URI)
            username: Neo4j username (defaults to env var NEO4J_USERNAME)
            password: Neo4j password (defaults to env var NEO4J_PASSWORD)
        """
        self.uri = uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.username = username or os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD', 'password')
        
        self.driver: Optional[Driver] = None
        self.llm_client = LLMClient()
        self.logger = logging.getLogger(__name__)
        
        self._connect()
        self._create_schema()
    
    def _connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.logger.info("Connected to Neo4j database")
        except ServiceUnavailable as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def _create_schema(self) -> None:
        """Create Neo4j schema with indexes and constraints."""
        schema_queries = [
            # Create constraints
            "CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.rule_id IS UNIQUE",
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT scenario_id_unique IF NOT EXISTS FOR (s:Scenario) REQUIRE s.scenario_id IS UNIQUE",
            "CREATE CONSTRAINT policy_name_unique IF NOT EXISTS FOR (p:Policy) REQUIRE p.name IS UNIQUE",
            
            # Create indexes for performance
            "CREATE INDEX rule_text_index IF NOT EXISTS FOR (r:Rule) ON (r.rule_text)",
            "CREATE INDEX concept_name_index IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX rule_created_index IF NOT EXISTS FOR (r:Rule) ON (r.created_at)",
            "CREATE INDEX rule_confidence_index IF NOT EXISTS FOR (r:Rule) ON (r.confidence_score)"
        ]
        
        with self.driver.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                except Exception as e:
                    self.logger.warning(f"Schema query failed (may already exist): {query} - {e}")
    
    def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j connection closed")
    
    def store_ltm_rule(self, rule: LTMRule) -> bool:
        """
        Store an LTM rule in Neo4j with all relationships.
        
        Args:
            rule: LTMRule object to store
            
        Returns:
            bool: True if successfully stored
        """
        if not rule.validate():
            self.logger.error(f"Invalid LTM rule: {rule.rule_id}")
            return False
        
        try:
            with self.driver.session() as session:
                # Create rule node
                rule_query = """
                MERGE (r:Rule {rule_id: $rule_id})
                SET r.rule_text = $rule_text,
                    r.confidence_score = $confidence_score,
                    r.version = $version,
                    r.created_at = $created_at,
                    r.updated_at = $updated_at
                RETURN r
                """
                
                session.run(rule_query, {
                    'rule_id': rule.rule_id,
                    'rule_text': rule.rule_text,
                    'confidence_score': rule.confidence_score,
                    'version': rule.version,
                    'created_at': rule.created_at,
                    'updated_at': rule.updated_at
                })
                
                # Create concept nodes and relationships
                for concept in rule.related_concepts:
                    concept_query = """
                    MERGE (c:Concept {name: $concept})
                    WITH c
                    MATCH (r:Rule {rule_id: $rule_id})
                    MERGE (r)-[:RELATES_TO]->(c)
                    """
                    session.run(concept_query, {
                        'concept': concept,
                        'rule_id': rule.rule_id
                    })
                
                # Create scenario nodes and relationships
                for scenario_id in rule.source_scenario_id:
                    scenario_query = """
                    MERGE (s:Scenario {scenario_id: $scenario_id})
                    WITH s
                    MATCH (r:Rule {rule_id: $rule_id})
                    MERGE (r)-[:DERIVED_FROM]->(s)
                    """
                    session.run(scenario_query, {
                        'scenario_id': scenario_id,
                        'rule_id': rule.rule_id
                    })
                
                # Extract policy from rule_id and create policy relationship
                policy_name = rule.rule_id.split('_')[0]
                policy_query = """
                MERGE (p:Policy {name: $policy_name})
                WITH p
                MATCH (r:Rule {rule_id: $rule_id})
                MERGE (p)-[:GOVERNS]->(r)
                """
                session.run(policy_query, {
                    'policy_name': policy_name,
                    'rule_id': rule.rule_id
                })
                
                self.logger.info(f"Stored LTM rule: {rule.rule_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store LTM rule {rule.rule_id}: {e}")
            return False
    
    def get_ltm_rule(self, rule_id: str) -> Optional[LTMRule]:
        """
        Retrieve an LTM rule by rule_id.
        
        Args:
            rule_id: Unique identifier for the rule
            
        Returns:
            LTMRule object or None if not found
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH (r:Rule {rule_id: $rule_id})
                OPTIONAL MATCH (r)-[:RELATES_TO]->(c:Concept)
                OPTIONAL MATCH (r)-[:DERIVED_FROM]->(s:Scenario)
                RETURN r, collect(DISTINCT c.name) as concepts, collect(DISTINCT s.scenario_id) as scenarios
                """
                
                result = session.run(query, {'rule_id': rule_id})
                record = result.single()
                
                if not record:
                    return None
                
                rule_data = record['r']
                return LTMRule(
                    rule_id=rule_data['rule_id'],
                    rule_text=rule_data['rule_text'],
                    related_concepts=record['concepts'] or [],
                    source_scenario_id=record['scenarios'] or [],
                    confidence_score=rule_data.get('confidence_score', 0.0),
                    version=rule_data.get('version', 1),
                    created_at=rule_data.get('created_at'),
                    updated_at=rule_data.get('updated_at')
                )
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve LTM rule {rule_id}: {e}")
            return None
    
    def search_ltm_rules(self, concepts: List[str] = None, keywords: List[str] = None, 
                        policy: str = None, limit: int = 10) -> List[LTMRule]:
        """
        Search LTM rules by concepts, keywords, and policy.
        
        Args:
            concepts: List of concepts to match
            keywords: List of keywords to search in rule text
            policy: Policy name to filter by
            limit: Maximum number of results
            
        Returns:
            List of matching LTMRule objects
        """
        try:
            with self.driver.session() as session:
                # Build dynamic query based on search criteria
                where_clauses = []
                params = {'limit': limit}
                
                if concepts:
                    where_clauses.append("ANY(concept IN $concepts WHERE concept IN [c.name])")
                    params['concepts'] = concepts
                
                if keywords:
                    keyword_conditions = []
                    for i, keyword in enumerate(keywords):
                        keyword_conditions.append(f"r.rule_text CONTAINS $keyword_{i}")
                        params[f'keyword_{i}'] = keyword
                    where_clauses.append(f"({' OR '.join(keyword_conditions)})")
                
                if policy:
                    where_clauses.append("p.name = $policy")
                    params['policy'] = policy
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "true"
                
                query = f"""
                MATCH (r:Rule)
                OPTIONAL MATCH (r)-[:RELATES_TO]->(c:Concept)
                OPTIONAL MATCH (r)-[:DERIVED_FROM]->(s:Scenario)
                OPTIONAL MATCH (p:Policy)-[:GOVERNS]->(r)
                WHERE {where_clause}
                WITH r, collect(DISTINCT c.name) as concepts, collect(DISTINCT s.scenario_id) as scenarios
                ORDER BY r.confidence_score DESC, r.created_at DESC
                LIMIT $limit
                RETURN r, concepts, scenarios
                """
                
                results = session.run(query, params)
                rules = []
                
                for record in results:
                    rule_data = record['r']
                    rule = LTMRule(
                        rule_id=rule_data['rule_id'],
                        rule_text=rule_data['rule_text'],
                        related_concepts=record['concepts'] or [],
                        source_scenario_id=record['scenarios'] or [],
                        confidence_score=rule_data.get('confidence_score', 0.0),
                        version=rule_data.get('version', 1),
                        created_at=rule_data.get('created_at'),
                        updated_at=rule_data.get('updated_at')
                    )
                    rules.append(rule)
                
                return rules
                
        except Exception as e:
            self.logger.error(f"Failed to search LTM rules: {e}")
            return []
    
    def semantic_search_rules(self, query_text: str, limit: int = 10) -> List[Tuple[LTMRule, float]]:
        """
        Perform semantic search using LLM to find relevant rules.
        
        Args:
            query_text: Natural language query
            limit: Maximum number of results
            
        Returns:
            List of tuples (LTMRule, relevance_score)
        """
        try:
            # Get all rules first
            all_rules = self.get_all_rules()
            if not all_rules:
                return []
            
            # Use LLM to score relevance
            prompt = f"""
            Given the query: "{query_text}"
            
            Score the relevance of each rule on a scale of 0.0 to 1.0.
            Return only a JSON array of scores in the same order as the rules.
            
            Rules:
            {json.dumps([{'rule_id': r.rule_id, 'rule_text': r.rule_text, 'concepts': r.related_concepts} for r in all_rules], indent=2)}
            """
            
            response = self.llm_client.generate_response(prompt)
            
            try:
                scores = json.loads(response)
                if len(scores) != len(all_rules):
                    self.logger.warning("LLM returned incorrect number of scores, falling back to concept matching")
                    return self._fallback_semantic_search(query_text, all_rules, limit)
                
                # Combine rules with scores and sort
                scored_rules = [(rule, score) for rule, score in zip(all_rules, scores) if score > 0.1]
                scored_rules.sort(key=lambda x: x[1], reverse=True)
                
                return scored_rules[:limit]
                
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse LLM response, falling back to concept matching")
                return self._fallback_semantic_search(query_text, all_rules, limit)
                
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return []
    
    def _fallback_semantic_search(self, query_text: str, rules: List[LTMRule], limit: int) -> List[Tuple[LTMRule, float]]:
        """Fallback semantic search using simple text matching."""
        query_words = set(query_text.lower().split())
        scored_rules = []
        
        for rule in rules:
            # Calculate simple relevance score based on word overlap
            rule_words = set(rule.rule_text.lower().split())
            concept_words = set(' '.join(rule.related_concepts).lower().split())
            all_rule_words = rule_words.union(concept_words)
            
            overlap = len(query_words.intersection(all_rule_words))
            score = overlap / max(len(query_words), 1) if overlap > 0 else 0.0
            
            if score > 0:
                scored_rules.append((rule, score))
        
        scored_rules.sort(key=lambda x: x[1], reverse=True)
        return scored_rules[:limit]
    
    def get_all_rules(self) -> List[LTMRule]:
        """Get all LTM rules from the database."""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (r:Rule)
                OPTIONAL MATCH (r)-[:RELATES_TO]->(c:Concept)
                OPTIONAL MATCH (r)-[:DERIVED_FROM]->(s:Scenario)
                RETURN r, collect(DISTINCT c.name) as concepts, collect(DISTINCT s.scenario_id) as scenarios
                ORDER BY r.created_at DESC
                """
                
                results = session.run(query)
                rules = []
                
                for record in results:
                    rule_data = record['r']
                    rule = LTMRule(
                        rule_id=rule_data['rule_id'],
                        rule_text=rule_data['rule_text'],
                        related_concepts=record['concepts'] or [],
                        source_scenario_id=record['scenarios'] or [],
                        confidence_score=rule_data.get('confidence_score', 0.0),
                        version=rule_data.get('version', 1),
                        created_at=rule_data.get('created_at'),
                        updated_at=rule_data.get('updated_at')
                    )
                    rules.append(rule)
                
                return rules
                
        except Exception as e:
            self.logger.error(f"Failed to get all rules: {e}")
            return []
    
    def update_ltm_rule(self, rule: LTMRule) -> bool:
        """
        Update an existing LTM rule.
        
        Args:
            rule: Updated LTMRule object
            
        Returns:
            bool: True if successfully updated
        """
        if not rule.validate():
            return False
        
        rule.update_timestamp()
        return self.store_ltm_rule(rule)
    
    def delete_ltm_rule(self, rule_id: str) -> bool:
        """
        Delete an LTM rule and all its relationships.
        
        Args:
            rule_id: ID of the rule to delete
            
        Returns:
            bool: True if successfully deleted
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH (r:Rule {rule_id: $rule_id})
                DETACH DELETE r
                """
                result = session.run(query, {'rule_id': rule_id})
                
                # Check if any nodes were deleted
                summary = result.consume()
                deleted = summary.counters.nodes_deleted > 0
                
                if deleted:
                    self.logger.info(f"Deleted LTM rule: {rule_id}")
                
                return deleted
                
        except Exception as e:
            self.logger.error(f"Failed to delete LTM rule {rule_id}: {e}")
            return False
    
    def get_rule_traceability(self, rule_id: str) -> Dict[str, Any]:
        """
        Get complete traceability information for a rule.
        
        Args:
            rule_id: ID of the rule
            
        Returns:
            Dict containing rule, source scenarios, and related concepts
        """
        try:
            with self.driver.session() as session:
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
                
                result = session.run(query, {'rule_id': rule_id})
                record = result.single()
                
                if not record:
                    return {}
                
                rule_data = record['r']
                return {
                    'rule': {
                        'rule_id': rule_data['rule_id'],
                        'rule_text': rule_data['rule_text'],
                        'confidence_score': rule_data.get('confidence_score', 0.0),
                        'version': rule_data.get('version', 1),
                        'created_at': rule_data.get('created_at'),
                        'updated_at': rule_data.get('updated_at')
                    },
                    'related_concepts': record['concepts'] or [],
                    'source_scenarios': record['scenarios'] or [],
                    'governing_policies': record['policies'] or []
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get traceability for rule {rule_id}: {e}")
            return {}
    
    def get_concept_relationships(self, concept: str) -> List[Dict[str, Any]]:
        """
        Get all rules related to a specific concept.
        
        Args:
            concept: Concept name
            
        Returns:
            List of rule information dictionaries
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH (c:Concept {name: $concept})<-[:RELATES_TO]-(r:Rule)
                OPTIONAL MATCH (r)-[:DERIVED_FROM]->(s:Scenario)
                RETURN r, collect(DISTINCT s.scenario_id) as scenarios
                ORDER BY r.confidence_score DESC
                """
                
                results = session.run(query, {'concept': concept})
                rules = []
                
                for record in results:
                    rule_data = record['r']
                    rules.append({
                        'rule_id': rule_data['rule_id'],
                        'rule_text': rule_data['rule_text'],
                        'confidence_score': rule_data.get('confidence_score', 0.0),
                        'source_scenarios': record['scenarios'] or []
                    })
                
                return rules
                
        except Exception as e:
            self.logger.error(f"Failed to get concept relationships for {concept}: {e}")
            return []
    
    def get_rule_version_history(self, rule_id: str) -> List[Dict[str, Any]]:
        """
        Get version history for a rule.
        
        This tracks all versions of a rule to maintain audit trail
        and understand how rules evolved over time.
        
        Args:
            rule_id: Base rule ID (without version suffix)
            
        Returns:
            List of rule versions ordered by version number
        """
        try:
            with self.driver.session() as session:
                # Extract base rule ID (remove version suffix if present)
                base_rule_id = '_'.join(rule_id.split('_')[:-1]) if rule_id.split('_')[-1].isdigit() else rule_id
                
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
                
                results = session.run(query, {'base_rule_id': base_rule_id})
                versions = []
                
                for record in results:
                    rule_data = record['r']
                    versions.append({
                        'rule_id': rule_data['rule_id'],
                        'rule_text': rule_data['rule_text'],
                        'version': rule_data.get('version', 1),
                        'confidence_score': rule_data.get('confidence_score', 0.0),
                        'created_at': rule_data.get('created_at'),
                        'updated_at': rule_data.get('updated_at'),
                        'source_scenarios': record['scenarios'] or [],
                        'related_concepts': record['concepts'] or []
                    })
                
                return versions
                
        except Exception as e:
            self.logger.error(f"Failed to get version history for rule {rule_id}: {e}")
            return []
    
    def create_rule_version(self, base_rule_id: str, updated_rule: LTMRule) -> bool:
        """
        Create a new version of an existing rule.
        
        This maintains version history while updating rule content.
        
        Args:
            base_rule_id: Base rule ID to version
            updated_rule: Updated rule content
            
        Returns:
            True if version was created successfully
        """
        try:
            # Get current highest version
            versions = self.get_rule_version_history(base_rule_id)
            if not versions:
                self.logger.error(f"Base rule {base_rule_id} not found")
                return False
            
            next_version = max(v['version'] for v in versions) + 1
            
            # Create new rule ID with version
            new_rule_id = f"{base_rule_id}_{next_version:02d}"
            updated_rule.rule_id = new_rule_id
            updated_rule.version = next_version
            updated_rule.update_timestamp()
            
            # Store the new version
            return self.store_ltm_rule(updated_rule)
            
        except Exception as e:
            self.logger.error(f"Failed to create rule version for {base_rule_id}: {e}")
            return False
    
    def get_rules_by_source_scenario(self, scenario_id: str) -> List[LTMRule]:
        """
        Get all LTM rules that were derived from a specific STM scenario.
        
        This provides reverse traceability from STM to LTM.
        
        Args:
            scenario_id: STM scenario identifier
            
        Returns:
            List of LTMRule objects derived from this scenario
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH (s:Scenario {scenario_id: $scenario_id})<-[:DERIVED_FROM]-(r:Rule)
                OPTIONAL MATCH (r)-[:RELATES_TO]->(c:Concept)
                OPTIONAL MATCH (r)-[:DERIVED_FROM]->(all_s:Scenario)
                RETURN r, 
                       collect(DISTINCT c.name) as concepts,
                       collect(DISTINCT all_s.scenario_id) as all_scenarios
                ORDER BY r.created_at DESC
                """
                
                results = session.run(query, {'scenario_id': scenario_id})
                rules = []
                
                for record in results:
                    rule_data = record['r']
                    rule = LTMRule(
                        rule_id=rule_data['rule_id'],
                        rule_text=rule_data['rule_text'],
                        related_concepts=record['concepts'] or [],
                        source_scenario_id=record['all_scenarios'] or [],
                        confidence_score=rule_data.get('confidence_score', 0.0),
                        version=rule_data.get('version', 1),
                        created_at=rule_data.get('created_at'),
                        updated_at=rule_data.get('updated_at')
                    )
                    rules.append(rule)
                
                return rules
                
        except Exception as e:
            self.logger.error(f"Failed to get rules by source scenario {scenario_id}: {e}")
            return []
    
    def get_complete_audit_trail(self, rule_id: str) -> Dict[str, Any]:
        """
        Get complete audit trail for a rule including all source evidence.
        
        This provides the complete chain of evidence from human feedback
        to generalized rule as required by Requirement 4.5.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Dictionary containing complete audit trail
        """
        try:
            rule = self.get_ltm_rule(rule_id)
            if not rule:
                return {}
            
            # Get version history
            version_history = self.get_rule_version_history(rule_id)
            
            # Get source scenario details (would need STM processor integration)
            source_scenarios = rule.source_scenario_id
            
            # Get related concepts and their relationships
            concept_relationships = {}
            for concept in rule.related_concepts:
                concept_relationships[concept] = self.get_concept_relationships(concept)
            
            return {
                'rule': rule.to_dict(),
                'version_history': version_history,
                'source_scenarios': source_scenarios,
                'concept_relationships': concept_relationships,
                'audit_metadata': {
                    'total_versions': len(version_history),
                    'source_count': len(source_scenarios),
                    'concept_count': len(rule.related_concepts),
                    'confidence_score': rule.confidence_score,
                    'last_updated': rule.updated_at
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get audit trail for rule {rule_id}: {e}")
            return {}
    
    def link_rule_to_stm_processor(self, stm_processor) -> None:
        """
        Link this LTM manager to an STM processor for bidirectional traceability.
        
        Args:
            stm_processor: STMProcessor instance
        """
        self.stm_processor = stm_processor
    
    def update_rule_with_new_scenario(self, rule_id: str, new_scenario_id: str) -> bool:
        """
        Update an existing rule to include a new source scenario.
        
        This supports multiple source scenarios for single rules as required
        by the traceability requirements.
        
        Args:
            rule_id: Rule to update
            new_scenario_id: New scenario to add as source
            
        Returns:
            True if successfully updated
        """
        try:
            rule = self.get_ltm_rule(rule_id)
            if not rule:
                return False
            
            # Add new scenario if not already present
            if new_scenario_id not in rule.source_scenario_id:
                rule.add_source_scenario(new_scenario_id)
                
                # Update in database
                success = self.update_ltm_rule(rule)
                
                # Update bidirectional link in STM processor if available
                if hasattr(self, 'stm_processor') and self.stm_processor:
                    self.stm_processor.add_ltm_rule_link(new_scenario_id, rule_id)
                
                return success
            
            return True  # Already linked
            
        except Exception as e:
            self.logger.error(f"Failed to update rule {rule_id} with scenario {new_scenario_id}: {e}")
            return False