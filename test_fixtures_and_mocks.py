"""
Test Fixtures and Mock Data Generators for Compliance Memory Management Module.

This module provides comprehensive test fixtures, mock data generators, and utility
functions for testing all components of the memory management system.
"""

import json
import tempfile
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import random
import string

from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.models.ltm_rule import LTMRule


class MockDataGenerator:
    """Generate realistic mock data for testing."""
    
    @staticmethod
    def generate_scenario_id(domain: str = "test", requirement_num: int = 1, concept: str = "compliance") -> str:
        """Generate realistic scenario ID."""
        return f"{domain}_r{requirement_num}_{concept.lower().replace(' ', '_')}"
    
    @staticmethod
    def generate_rule_id(policy: str = "GDPR", concept: str = "Test", version: int = 1) -> str:
        """Generate realistic rule ID."""
        return f"{policy}_{concept.replace(' ', '_')}_{version:02d}"
    
    @staticmethod
    def generate_requirement_text(requirement_num: int = 1, domain: str = "system") -> str:
        """Generate realistic requirement text."""
        templates = [
            f"The {domain} must implement proper data encryption for requirement R{requirement_num}.",
            f"User consent mechanisms must be implemented according to requirement R{requirement_num}.",
            f"Data retention policies must be enforced as specified in requirement R{requirement_num}.",
            f"Access controls must be implemented to protect user data per requirement R{requirement_num}.",
            f"Audit logging must be maintained for compliance with requirement R{requirement_num}."
        ]
        return random.choice(templates)
    
    @staticmethod
    def generate_compliance_status() -> str:
        """Generate realistic compliance status."""
        return random.choice(["Compliant", "Non-Compliant", "Partially Compliant"])
    
    @staticmethod
    def generate_rationale(status: str) -> str:
        """Generate realistic rationale based on status."""
        if status == "Compliant":
            rationales = [
                "Implementation meets all GDPR requirements for data protection.",
                "Current security measures are adequate for compliance.",
                "Data processing procedures align with regulatory requirements."
            ]
        elif status == "Non-Compliant":
            rationales = [
                "Current implementation violates GDPR Article 7 consent requirements.",
                "Security measures are insufficient for regulatory compliance.",
                "Data retention policies do not meet legal requirements."
            ]
        else:  # Partially Compliant
            rationales = [
                "Implementation partially meets requirements but needs improvements.",
                "Some security measures are in place but additional controls needed.",
                "Compliance framework exists but requires enhancement."
            ]
        return random.choice(rationales)
    
    @staticmethod
    def generate_recommendation(status: str) -> str:
        """Generate realistic recommendation based on status."""
        if status == "Compliant":
            recommendations = [
                "Continue monitoring to ensure ongoing compliance.",
                "Consider implementing additional security measures for enhanced protection.",
                "Regular review of policies to maintain compliance."
            ]
        elif status == "Non-Compliant":
            recommendations = [
                "Implement separate consent checkboxes for different data processing purposes.",
                "Upgrade security measures to meet current regulatory standards.",
                "Establish proper data retention and deletion procedures."
            ]
        else:  # Partially Compliant
            recommendations = [
                "Address identified gaps in current implementation.",
                "Enhance existing security controls to meet full compliance.",
                "Implement additional monitoring and audit procedures."
            ]
        return random.choice(recommendations)
    
    @staticmethod
    def generate_human_decision() -> str:
        """Generate realistic human feedback decision."""
        return random.choice(["No change", "Change status", "Approved", "Needs revision"])
    
    @staticmethod
    def generate_concepts(base_concepts: List[str] = None) -> List[str]:
        """Generate realistic related concepts."""
        if base_concepts is None:
            base_concepts = ["GDPR", "Compliance", "Security", "Privacy", "Data Protection"]
        
        additional_concepts = [
            "Consent Management", "Data Retention", "Access Control", "Audit Logging",
            "Encryption", "User Rights", "Data Processing", "Legal Requirements",
            "Risk Assessment", "Policy Framework", "Technical Measures", "Organizational Measures"
        ]
        
        # Select 3-7 concepts
        num_concepts = random.randint(3, 7)
        selected = random.sample(base_concepts + additional_concepts, min(num_concepts, len(base_concepts + additional_concepts)))
        return selected
    
    @staticmethod
    def generate_confidence_score() -> float:
        """Generate realistic confidence score."""
        return round(random.uniform(0.7, 0.98), 2)


class ComplianceReportGenerator:
    """Generate realistic compliance reports for testing."""
    
    @staticmethod
    def generate_full_report(num_requirements: int = 5, domain: str = "ecommerce") -> str:
        """Generate a complete compliance report."""
        header = f"""## FINAL COMPLIANCE ASSESSMENT REPORT (RA_Agent) ##

**Project:** {domain.title()} Platform SRS
**Governing Policy:** GDPR
**Status:** {num_requirements} Requirements Assessed.

"""
        
        requirements = []
        for i in range(1, num_requirements + 1):
            status = MockDataGenerator.generate_compliance_status()
            rationale = MockDataGenerator.generate_rationale(status)
            recommendation = MockDataGenerator.generate_recommendation(status)
            req_text = MockDataGenerator.generate_requirement_text(i, domain)
            
            requirement = f"""---
**Requirement R{i}:** {req_text}
*   **Status:** {status}
*   **Rationale:** {rationale}
*   **Recommendation:** {recommendation}

"""
            requirements.append(requirement)
        
        return header + "".join(requirements)
    
    @staticmethod
    def generate_malformed_report() -> str:
        """Generate malformed report for error testing."""
        return """## INCOMPLETE REPORT ##
**Requirement R1:** Missing status and rationale
*   **Recommendation:** Some recommendation
---
**Requirement R2:** 
*   **Status:** 
*   **Rationale:** 
"""
    
    @staticmethod
    def generate_empty_report() -> str:
        """Generate empty report for edge case testing."""
        return ""


class HumanFeedbackGenerator:
    """Generate realistic human feedback for testing."""
    
    @staticmethod
    def generate_full_feedback(num_requirements: int = 5) -> str:
        """Generate complete human feedback."""
        header = """## HUMAN EXPERT FEEDBACK ##

**Reviewer:** Legal Expert - Data Protection Officer
**Date:** 2024-10-27
**Review Session:** GDPR Compliance Assessment Review

"""
        
        feedback_items = []
        for i in range(1, num_requirements + 1):
            decision = MockDataGenerator.generate_human_decision()
            rationale = f"Expert analysis of requirement R{i} based on legal precedent and regulatory guidance."
            suggestion = f"Implement enhanced measures for requirement R{i} to ensure full compliance."
            
            feedback = f"""**Feedback on R{i} (Requirement {i}):**
*   **Decision:** {decision}
*   **Rationale:** {rationale}
*   **Suggestion:** {suggestion}

"""
            feedback_items.append(feedback)
        
        return header + "".join(feedback_items)
    
    @staticmethod
    def generate_partial_feedback(num_requirements: int = 3) -> str:
        """Generate partial feedback for testing."""
        return HumanFeedbackGenerator.generate_full_feedback(num_requirements)
    
    @staticmethod
    def generate_malformed_feedback() -> str:
        """Generate malformed feedback for error testing."""
        return """## INCOMPLETE FEEDBACK ##
**Feedback on R1:**
*   **Decision:** 
*   **Rationale:** Missing rationale
"""


class STMEntryFactory:
    """Factory for creating STM entries with various configurations."""
    
    @staticmethod
    def create_basic_entry(scenario_id: str = None) -> STMEntry:
        """Create basic STM entry."""
        if scenario_id is None:
            scenario_id = MockDataGenerator.generate_scenario_id()
        
        status = MockDataGenerator.generate_compliance_status()
        initial_assessment = InitialAssessment(
            status=status,
            rationale=MockDataGenerator.generate_rationale(status),
            recommendation=MockDataGenerator.generate_recommendation(status)
        )
        
        return STMEntry(
            scenario_id=scenario_id,
            requirement_text=MockDataGenerator.generate_requirement_text(),
            initial_assessment=initial_assessment
        )
    
    @staticmethod
    def create_entry_with_feedback(scenario_id: str = None) -> STMEntry:
        """Create STM entry with human feedback."""
        entry = STMEntryFactory.create_basic_entry(scenario_id)
        
        human_feedback = HumanFeedback(
            decision=MockDataGenerator.generate_human_decision(),
            rationale="Expert review confirms the assessment accuracy.",
            suggestion="Consider implementing additional security measures."
        )
        
        entry.human_feedback = human_feedback
        entry.final_status = MockDataGenerator.generate_compliance_status()
        
        return entry
    
    @staticmethod
    def create_multiple_entries(count: int = 5, with_feedback: bool = True) -> List[STMEntry]:
        """Create multiple STM entries."""
        entries = []
        for i in range(count):
            scenario_id = MockDataGenerator.generate_scenario_id("test", i + 1, f"concept_{i}")
            if with_feedback:
                entry = STMEntryFactory.create_entry_with_feedback(scenario_id)
            else:
                entry = STMEntryFactory.create_basic_entry(scenario_id)
            entries.append(entry)
        return entries


class LTMRuleFactory:
    """Factory for creating LTM rules with various configurations."""
    
    @staticmethod
    def create_basic_rule(rule_id: str = None, source_scenario: str = None) -> LTMRule:
        """Create basic LTM rule."""
        if rule_id is None:
            rule_id = MockDataGenerator.generate_rule_id()
        
        if source_scenario is None:
            source_scenario = MockDataGenerator.generate_scenario_id()
        
        concepts = MockDataGenerator.generate_concepts()
        
        return LTMRule(
            rule_id=rule_id,
            rule_text=f"For GDPR compliance, systems must implement proper {concepts[0].lower()} measures to ensure data protection and user privacy rights are maintained.",
            related_concepts=concepts,
            source_scenario_id=[source_scenario],
            confidence_score=MockDataGenerator.generate_confidence_score()
        )
    
    @staticmethod
    def create_rule_with_multiple_sources(rule_id: str = None, num_sources: int = 3) -> LTMRule:
        """Create LTM rule with multiple source scenarios."""
        rule = LTMRuleFactory.create_basic_rule(rule_id)
        
        sources = []
        for i in range(num_sources):
            sources.append(MockDataGenerator.generate_scenario_id("test", i + 1, f"source_{i}"))
        
        rule.source_scenario_id = sources
        return rule
    
    @staticmethod
    def create_multiple_rules(count: int = 5) -> List[LTMRule]:
        """Create multiple LTM rules."""
        rules = []
        for i in range(count):
            rule_id = MockDataGenerator.generate_rule_id("GDPR", f"TestRule{i}", 1)
            rule = LTMRuleFactory.create_basic_rule(rule_id)
            rules.append(rule)
        return rules


class MockComponentFactory:
    """Factory for creating mock components for testing."""
    
    @staticmethod
    def create_mock_stm_processor() -> Mock:
        """Create mock STM processor."""
        mock_processor = Mock()
        
        # Mock successful operations
        mock_processor.create_entry.return_value = STMEntryFactory.create_basic_entry()
        mock_processor.get_entry.return_value = STMEntryFactory.create_entry_with_feedback()
        mock_processor.add_human_feedback.return_value = STMEntryFactory.create_entry_with_feedback()
        mock_processor.set_final_status.return_value = STMEntryFactory.create_entry_with_feedback()
        mock_processor.delete_entry.return_value = True
        mock_processor.add_ltm_rule_link.return_value = True
        mock_processor.health_check.return_value = {"status": "healthy"}
        mock_processor.get_stats.return_value = {
            "total_entries": 10,
            "entries_with_feedback": 8,
            "entries_without_feedback": 2
        }
        
        return mock_processor
    
    @staticmethod
    def create_mock_ltm_manager() -> Mock:
        """Create mock LTM manager."""
        mock_manager = Mock()
        
        # Mock successful operations
        mock_manager.store_ltm_rule.return_value = True
        mock_manager.get_ltm_rule.return_value = LTMRuleFactory.create_basic_rule()
        mock_manager.search_ltm_rules.return_value = LTMRuleFactory.create_multiple_rules(3)
        mock_manager.update_ltm_rule.return_value = True
        mock_manager.delete_ltm_rule.return_value = True
        mock_manager.health_check.return_value = {"status": "healthy"}
        mock_manager.get_all_rules.return_value = LTMRuleFactory.create_multiple_rules(5)
        mock_manager.close.return_value = None
        
        return mock_manager
    
    @staticmethod
    def create_mock_rule_extractor() -> Mock:
        """Create mock rule extractor."""
        mock_extractor = Mock()
        
        # Mock successful rule extraction
        from memory_management.processors.rule_extractor import RuleGenerationResult
        mock_result = RuleGenerationResult(
            success=True,
            rule=LTMRuleFactory.create_basic_rule(),
            confidence_score=0.85
        )
        mock_extractor.extract_rule_from_stm.return_value = mock_result
        
        return mock_extractor
    
    @staticmethod
    def create_mock_memory_api() -> Mock:
        """Create mock Memory API."""
        mock_api = Mock()
        
        # Mock successful API responses
        mock_api.add_new_assessment.return_value = {"status": "success", "scenario_id": "test_001"}
        mock_api.get_stm_entry.return_value = {
            "status": "success",
            "data": STMEntryFactory.create_entry_with_feedback().to_dict()
        }
        mock_api.search_ltm_rules.return_value = {
            "status": "success",
            "data": [rule.to_dict() for rule in LTMRuleFactory.create_multiple_rules(3)]
        }
        mock_api.update_with_feedback.return_value = {"status": "success"}
        mock_api.health_check.return_value = {"status": "success", "data": {"Redis": "healthy", "Neo4j": "healthy"}}
        mock_api.get_system_stats.return_value = {"status": "success", "data": {"total_stm": 10, "total_ltm": 5}}
        mock_api.close.return_value = None
        
        return mock_api


class TestFileManager:
    """Manage temporary test files and directories."""
    
    def __init__(self):
        self.temp_dirs = []
        self.temp_files = []
    
    def create_temp_file(self, content: str, filename: str = None, suffix: str = ".txt") -> str:
        """Create temporary file with content."""
        if filename:
            temp_dir = tempfile.mkdtemp()
            self.temp_dirs.append(temp_dir)
            file_path = Path(temp_dir) / filename
        else:
            fd, file_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            self.temp_files.append(str(file_path))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    
    def create_temp_files(self, compliance_content: str, feedback_content: str) -> tuple:
        """Create temporary compliance and feedback files."""
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        
        compliance_path = Path(temp_dir) / "compliance_report.txt"
        feedback_path = Path(temp_dir) / "human_feedback.txt"
        
        with open(compliance_path, 'w', encoding='utf-8') as f:
            f.write(compliance_content)
        
        with open(feedback_path, 'w', encoding='utf-8') as f:
            f.write(feedback_content)
        
        return str(compliance_path), str(feedback_path), temp_dir
    
    def cleanup(self):
        """Clean up all temporary files and directories."""
        import shutil
        
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
            except:
                pass
        
        for dir_path in self.temp_dirs:
            try:
                shutil.rmtree(dir_path)
            except:
                pass
        
        self.temp_files.clear()
        self.temp_dirs.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


class PerformanceTestHelper:
    """Helper for performance testing."""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs) -> tuple:
        """Measure function execution time."""
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        return result, execution_time
    
    @staticmethod
    def run_concurrent_operations(operation_func, num_operations: int = 10, max_workers: int = 5) -> List[Dict]:
        """Run operations concurrently and measure performance."""
        import concurrent.futures
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(operation_func, i) for i in range(num_operations)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e), "success": False})
        
        return results
    
    @staticmethod
    def calculate_performance_stats(execution_times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics."""
        import statistics
        
        if not execution_times:
            return {}
        
        return {
            "min_time": min(execution_times),
            "max_time": max(execution_times),
            "avg_time": statistics.mean(execution_times),
            "median_time": statistics.median(execution_times),
            "p95_time": sorted(execution_times)[int(len(execution_times) * 0.95)] if len(execution_times) > 1 else execution_times[0],
            "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        }


class DataQualityValidator:
    """Validate data quality in test results."""
    
    @staticmethod
    def validate_stm_entry(entry: STMEntry) -> Dict[str, Any]:
        """Validate STM entry data quality."""
        errors = []
        warnings = []
        
        # Required fields validation
        if not entry.scenario_id:
            errors.append("Missing scenario_id")
        elif not entry.scenario_id.count('_') >= 2:
            warnings.append("Scenario ID doesn't follow expected format")
        
        if not entry.requirement_text:
            errors.append("Missing requirement_text")
        elif len(entry.requirement_text) < 10:
            warnings.append("Requirement text seems too short")
        
        if not entry.initial_assessment:
            errors.append("Missing initial_assessment")
        else:
            if not entry.initial_assessment.status:
                errors.append("Missing initial assessment status")
            elif entry.initial_assessment.status not in ["Compliant", "Non-Compliant", "Partially Compliant"]:
                errors.append(f"Invalid status: {entry.initial_assessment.status}")
            
            if not entry.initial_assessment.rationale:
                errors.append("Missing initial assessment rationale")
            
            if not entry.initial_assessment.recommendation:
                errors.append("Missing initial assessment recommendation")
        
        # Human feedback validation (if present)
        if entry.human_feedback:
            if not entry.human_feedback.decision:
                warnings.append("Missing human feedback decision")
            if not entry.human_feedback.rationale:
                warnings.append("Missing human feedback rationale")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "quality_score": max(0, 100 - len(errors) * 25 - len(warnings) * 5)
        }
    
    @staticmethod
    def validate_ltm_rule(rule: LTMRule) -> Dict[str, Any]:
        """Validate LTM rule data quality."""
        errors = []
        warnings = []
        
        # Required fields validation
        if not rule.rule_id:
            errors.append("Missing rule_id")
        elif not rule.rule_id.count('_') >= 2:
            warnings.append("Rule ID doesn't follow expected format")
        
        if not rule.rule_text:
            errors.append("Missing rule_text")
        elif len(rule.rule_text) < 20:
            warnings.append("Rule text seems too short for meaningful rule")
        
        if not rule.related_concepts:
            errors.append("Missing related_concepts")
        elif len(rule.related_concepts) < 2:
            warnings.append("Should have at least 2 related concepts")
        
        if not rule.source_scenario_id:
            errors.append("Missing source_scenario_id")
        
        if rule.confidence_score is None:
            warnings.append("Missing confidence_score")
        elif rule.confidence_score < 0.5:
            warnings.append("Low confidence score")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "quality_score": max(0, 100 - len(errors) * 25 - len(warnings) * 5)
        }
    
    @staticmethod
    def validate_extraction_results(results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extraction results data quality."""
        errors = []
        warnings = []
        
        if not results.get('success'):
            errors.append("Extraction was not successful")
            return {"is_valid": False, "errors": errors, "warnings": warnings}
        
        # Validate STM results
        stm_results = results.get('stm_results', [])
        if not stm_results:
            errors.append("No STM results generated")
        else:
            for i, stm_data in enumerate(stm_results):
                if not isinstance(stm_data, dict):
                    errors.append(f"STM result {i} is not a dictionary")
                    continue
                
                required_fields = ['scenario_id', 'requirement_text', 'initial_assessment']
                for field in required_fields:
                    if field not in stm_data:
                        errors.append(f"STM result {i} missing {field}")
        
        # Validate LTM results
        ltm_results = results.get('ltm_results', [])
        if not ltm_results:
            warnings.append("No LTM results generated")
        
        # Validate statistics
        stats = results.get('extraction_summary', {}).get('statistics', {})
        if 'processing_success_rate' in stats:
            if stats['processing_success_rate'] < 50:
                warnings.append("Low processing success rate")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "quality_score": max(0, 100 - len(errors) * 20 - len(warnings) * 5)
        }


# Export main classes for easy import
__all__ = [
    'MockDataGenerator',
    'ComplianceReportGenerator', 
    'HumanFeedbackGenerator',
    'STMEntryFactory',
    'LTMRuleFactory',
    'MockComponentFactory',
    'TestFileManager',
    'PerformanceTestHelper',
    'DataQualityValidator'
]