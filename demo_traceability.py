"""
Demonstration of traceability and source linking features.

Shows how STM and LTM entries are linked bidirectionally with complete audit trails.
"""

import json
from datetime import datetime
from unittest.mock import Mock

from memory_management.processors.traceability_service import TraceabilityService
from memory_management.processors.stm_processor import STMProcessor
from memory_management.processors.ltm_manager import LTMManager
from memory_management.models.stm_entry import STMEntry, InitialAssessment, HumanFeedback
from memory_management.models.ltm_rule import LTMRule


def create_mock_processors():
    """Create mock processors for demonstration."""
    # Mock STM processor
    stm_processor = Mock(spec=STMProcessor)
    
    # Mock LTM manager
    ltm_manager = Mock(spec=LTMManager)
    
    return stm_processor, ltm_manager


def setup_sample_data():
    """Create sample STM entries and LTM rules for demonstration."""
    
    # Sample STM entries
    stm_entries = {
        "ecommerce_r1_consent": STMEntry(
            scenario_id="ecommerce_r1_consent",
            requirement_text="During account signup, the user must agree to terms and conditions",
            initial_assessment=InitialAssessment(
                status="Non-Compliant",
                rationale="Bundled consent violates GDPR Article 7 requirements for specific consent",
                recommendation="Implement separate, unticked opt-in checkboxes for each purpose"
            ),
            human_feedback=HumanFeedback(
                decision="Agree with assessment",
                rationale="Agent's analysis is correct. Bundled consent is indeed non-compliant",
                suggestion="Use granular consent with clear purpose descriptions"
            ),
            final_status="Non-Compliant"
        ),
        
        "ecommerce_r2_data_processing": STMEntry(
            scenario_id="ecommerce_r2_data_processing",
            requirement_text="User data must be processed only for stated purposes",
            initial_assessment=InitialAssessment(
                status="Partial",
                rationale="Some data processing exceeds stated purposes",
                recommendation="Implement purpose limitation controls"
            ),
            human_feedback=HumanFeedback(
                decision="Needs clarification",
                rationale="Assessment is partially correct but missing key details",
                suggestion="Add specific controls for purpose limitation"
            ),
            final_status="Non-Compliant"
        ),
        
        "inventory_r1_data_retention": STMEntry(
            scenario_id="inventory_r1_data_retention",
            requirement_text="Personal data must be deleted after retention period",
            initial_assessment=InitialAssessment(
                status="Non-Compliant",
                rationale="No automated deletion process exists",
                recommendation="Implement automated data deletion workflows"
            ),
            human_feedback=HumanFeedback(
                decision="Agree",
                rationale="Automated deletion is essential for compliance",
                suggestion="Use scheduled jobs for data lifecycle management"
            ),
            final_status="Non-Compliant"
        )
    }
    
    # Sample LTM rules
    ltm_rules = {
        "gdpr_consent_001": LTMRule(
            rule_id="gdpr_consent_001",
            rule_text="Consent must be granular and specific for each data processing purpose",
            related_concepts=["consent", "gdpr", "granular", "specific"],
            source_scenario_id=["ecommerce_r1_consent", "ecommerce_r2_data_processing"],
            confidence_score=0.95,
            version=1
        ),
        
        "gdpr_retention_001": LTMRule(
            rule_id="gdpr_retention_001",
            rule_text="Personal data must be automatically deleted when retention period expires",
            related_concepts=["retention", "deletion", "automated", "lifecycle"],
            source_scenario_id=["inventory_r1_data_retention"],
            confidence_score=0.88,
            version=1
        ),
        
        "gdpr_purpose_limitation_001": LTMRule(
            rule_id="gdpr_purpose_limitation_001",
            rule_text="Data processing must be limited to explicitly stated and consented purposes",
            related_concepts=["purpose_limitation", "consent", "processing"],
            source_scenario_id=["ecommerce_r2_data_processing"],
            confidence_score=0.92,
            version=2  # Updated version
        )
    }
    
    return stm_entries, ltm_rules


def setup_mock_behaviors(stm_processor, ltm_manager, stm_entries, ltm_rules):
    """Configure mock behaviors for demonstration."""
    
    # STM processor behaviors
    def mock_get_entry(scenario_id):
        return stm_entries.get(scenario_id)
    
    def mock_get_related_ltm_rules(scenario_id):
        # Return rules that reference this scenario
        related = []
        for rule_id, rule in ltm_rules.items():
            if scenario_id in rule.source_scenario_id:
                related.append(rule_id)
        return related
    
    def mock_get_traceability_info(scenario_id):
        entry = stm_entries.get(scenario_id)
        if not entry:
            return {}
        
        return {
            'stm_entry': entry.to_dict(),
            'related_ltm_rules': mock_get_related_ltm_rules(scenario_id),
            'has_human_feedback': entry.human_feedback is not None,
            'final_status': entry.final_status,
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
            'updated_at': entry.updated_at.isoformat() if entry.updated_at else None
        }
    
    # LTM manager behaviors
    def mock_get_ltm_rule(rule_id):
        return ltm_rules.get(rule_id)
    
    def mock_get_rules_by_source_scenario(scenario_id):
        related = []
        for rule in ltm_rules.values():
            if scenario_id in rule.source_scenario_id:
                related.append(rule)
        return related
    
    def mock_get_complete_audit_trail(rule_id):
        rule = ltm_rules.get(rule_id)
        if not rule:
            return {}
        
        return {
            'rule': rule.to_dict(),
            'source_scenarios': rule.source_scenario_id,
            'version_history': [
                {
                    'rule_id': rule.rule_id,
                    'version': rule.version,
                    'created_at': rule.created_at,
                    'updated_at': rule.updated_at
                }
            ],
            'audit_metadata': {
                'total_versions': rule.version,
                'source_count': len(rule.source_scenario_id),
                'concept_count': len(rule.related_concepts),
                'confidence_score': rule.confidence_score,
                'last_updated': rule.updated_at
            }
        }
    
    # Configure mocks
    stm_processor.get_entry.side_effect = mock_get_entry
    stm_processor.get_related_ltm_rules.side_effect = mock_get_related_ltm_rules
    stm_processor.get_traceability_info.side_effect = mock_get_traceability_info
    stm_processor.list_entries.return_value = list(stm_entries.values())
    stm_processor.add_ltm_rule_link.return_value = True
    
    ltm_manager.get_ltm_rule.side_effect = mock_get_ltm_rule
    ltm_manager.get_rules_by_source_scenario.side_effect = mock_get_rules_by_source_scenario
    ltm_manager.get_complete_audit_trail.side_effect = mock_get_complete_audit_trail
    ltm_manager.get_all_rules.return_value = list(ltm_rules.values())
    ltm_manager.store_ltm_rule.return_value = True
    ltm_manager.update_rule_with_new_scenario.return_value = True


def demonstrate_stm_to_ltm_navigation(traceability_service):
    """Demonstrate navigation from STM entry to related LTM rules."""
    print("=" * 80)
    print("DEMONSTRATION: STM to LTM Navigation")
    print("=" * 80)
    
    scenario_id = "ecommerce_r1_consent"
    print(f"Navigating from STM entry: {scenario_id}")
    
    navigation_info = traceability_service.get_stm_to_ltm_navigation(scenario_id)
    
    if navigation_info:
        print(f"\nSTM Entry Details:")
        stm_entry = navigation_info['stm_entry']
        print(f"  Scenario ID: {stm_entry['scenario_id']}")
        print(f"  Requirement: {stm_entry['requirement_text'][:80]}...")
        print(f"  Initial Status: {stm_entry['initial_assessment']['status']}")
        print(f"  Final Status: {stm_entry['final_status']}")
        print(f"  Has Human Feedback: {stm_entry['human_feedback'] is not None}")
        
        print(f"\nRelated LTM Rules ({navigation_info['rule_count']} found):")
        for i, rule in enumerate(navigation_info['related_ltm_rules'], 1):
            print(f"  {i}. Rule ID: {rule['rule_id']}")
            print(f"     Rule Text: {rule['rule_text']}")
            print(f"     Confidence: {rule['confidence_score']}")
            print(f"     Concepts: {', '.join(rule['related_concepts'])}")
            print()
    else:
        print("No navigation information found.")


def demonstrate_ltm_to_stm_navigation(traceability_service):
    """Demonstrate navigation from LTM rule to source STM entries."""
    print("=" * 80)
    print("DEMONSTRATION: LTM to STM Navigation")
    print("=" * 80)
    
    rule_id = "gdpr_consent_001"
    print(f"Navigating from LTM rule: {rule_id}")
    
    navigation_info = traceability_service.get_ltm_to_stm_navigation(rule_id)
    
    if navigation_info:
        print(f"\nLTM Rule Details:")
        ltm_rule = navigation_info['ltm_rule']
        print(f"  Rule ID: {ltm_rule['rule_id']}")
        print(f"  Rule Text: {ltm_rule['rule_text']}")
        print(f"  Version: {ltm_rule['version']}")
        print(f"  Confidence: {ltm_rule['confidence_score']}")
        print(f"  Related Concepts: {', '.join(ltm_rule['related_concepts'])}")
        
        print(f"\nSource STM Entries ({navigation_info['source_count']} found):")
        for i, stm_entry in enumerate(navigation_info['source_stm_entries'], 1):
            print(f"  {i}. Scenario ID: {stm_entry['scenario_id']}")
            print(f"     Requirement: {stm_entry['requirement_text'][:60]}...")
            print(f"     Initial Status: {stm_entry['initial_assessment']['status']}")
            print(f"     Final Status: {stm_entry['final_status']}")
            if stm_entry['human_feedback']:
                print(f"     Human Decision: {stm_entry['human_feedback']['decision']}")
            print()
        
        if navigation_info['missing_sources'] > 0:
            print(f"  Warning: {navigation_info['missing_sources']} source scenarios are missing from STM")
    else:
        print("No navigation information found.")


def demonstrate_complete_audit_trail(traceability_service):
    """Demonstrate complete audit trail generation."""
    print("=" * 80)
    print("DEMONSTRATION: Complete Audit Trail")
    print("=" * 80)
    
    rule_id = "gdpr_purpose_limitation_001"
    print(f"Generating complete audit trail for: {rule_id}")
    
    audit_trail = traceability_service.get_complete_traceability_chain(rule_id)
    
    if audit_trail:
        print(f"\nRule Information:")
        rule_info = audit_trail['rule_audit_trail']['rule']
        print(f"  Rule ID: {rule_info['rule_id']}")
        print(f"  Rule Text: {rule_info['rule_text']}")
        print(f"  Version: {rule_info['version']}")
        print(f"  Confidence Score: {rule_info['confidence_score']}")
        
        print(f"\nAudit Metadata:")
        metadata = audit_trail['rule_audit_trail']['audit_metadata']
        print(f"  Total Versions: {metadata['total_versions']}")
        print(f"  Source Count: {metadata['source_count']}")
        print(f"  Concept Count: {metadata['concept_count']}")
        print(f"  Last Updated: {metadata['last_updated']}")
        
        print(f"\nTraceability Metadata:")
        trace_meta = audit_trail['traceability_metadata']
        print(f"  Chain Length: {trace_meta['chain_length']}")
        print(f"  Has Human Feedback: {trace_meta['has_human_feedback']}")
        print(f"  Evidence Completeness: {trace_meta['evidence_completeness']:.2%}")
        
        print(f"\nDetailed Source Scenarios:")
        for i, source in enumerate(audit_trail['detailed_source_scenarios'], 1):
            stm_entry = source['stm_entry']
            print(f"  {i}. Scenario: {stm_entry['scenario_id']}")
            print(f"     Requirement: {stm_entry['requirement_text'][:50]}...")
            print(f"     Has Feedback: {source['has_human_feedback']}")
            print(f"     Final Status: {source['final_status']}")
            if source['has_human_feedback']:
                feedback = stm_entry['human_feedback']
                print(f"     Expert Decision: {feedback['decision']}")
                print(f"     Expert Rationale: {feedback['rationale'][:60]}...")
            print()
    else:
        print("No audit trail information found.")


def demonstrate_traceability_integrity(traceability_service):
    """Demonstrate traceability integrity validation."""
    print("=" * 80)
    print("DEMONSTRATION: Traceability Integrity Validation")
    print("=" * 80)
    
    validation_result = traceability_service.validate_traceability_integrity()
    
    print(f"Validation Status: {validation_result['integrity_status']}")
    print(f"Validation Time: {validation_result['validation_timestamp']}")
    
    print(f"\nStatistics:")
    stats = validation_result['statistics']
    print(f"  Total STM Entries: {stats['total_stm_entries']}")
    print(f"  Total LTM Rules: {stats['total_ltm_rules']}")
    print(f"  Orphaned STM Entries: {stats['orphaned_stm_entries']}")
    print(f"  Orphaned LTM Rules: {stats['orphaned_ltm_rules']}")
    print(f"  Broken Links: {stats['broken_links']}")
    
    if validation_result.get('issues'):
        print(f"\nIssues Found ({len(validation_result['issues'])}):")
        for i, issue in enumerate(validation_result['issues'], 1):
            print(f"  {i}. {issue}")
    else:
        print(f"\nNo integrity issues found!")


def main():
    """Main demonstration function."""
    print("TRACEABILITY AND SOURCE LINKING DEMONSTRATION")
    print("=" * 80)
    print("This demonstration shows the bidirectional traceability features")
    print("between Short-Term Memory (STM) and Long-Term Memory (LTM) components.")
    print()
    
    # Setup
    stm_processor, ltm_manager = create_mock_processors()
    stm_entries, ltm_rules = setup_sample_data()
    setup_mock_behaviors(stm_processor, ltm_manager, stm_entries, ltm_rules)
    
    # Create traceability service
    traceability_service = TraceabilityService(stm_processor, ltm_manager)
    
    # Run demonstrations
    demonstrate_stm_to_ltm_navigation(traceability_service)
    print()
    
    demonstrate_ltm_to_stm_navigation(traceability_service)
    print()
    
    demonstrate_complete_audit_trail(traceability_service)
    print()
    
    demonstrate_traceability_integrity(traceability_service)
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("Key Features Demonstrated:")
    print("1. STM to LTM navigation - Find rules derived from scenarios")
    print("2. LTM to STM navigation - Trace rules back to source evidence")
    print("3. Complete audit trails - Full chain of evidence")
    print("4. Integrity validation - Detect and report broken links")
    print("5. Multiple source scenarios - Rules can derive from multiple STM entries")
    print("6. Version history tracking - Maintain rule evolution history")


if __name__ == "__main__":
    main()