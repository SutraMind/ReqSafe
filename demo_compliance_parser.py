"""Demo script for testing ComplianceReportParser with real data."""

import json
import logging
from memory_management.parsers.compliance_report_parser import ComplianceReportParser
from memory_management.llm.client import LLMClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Demo the ComplianceReportParser with the actual compliance report."""
    
    print("=== Compliance Report Parser Demo ===\n")
    
    # Initialize the parser
    print("1. Initializing ComplianceReportParser...")
    try:
        llm_client = LLMClient()
        parser = ComplianceReportParser(llm_client=llm_client, model='qwq:32b')
        print("✓ Parser initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize parser: {e}")
        return
    
    # Check LLM health (optional - will work with mock if Ollama not available)
    print("\n2. Checking LLM client health...")
    try:
        health_status = llm_client.check_health()
        if health_status:
            print("✓ LLM client is healthy")
        else:
            print("⚠ LLM client health check failed - will use mock responses for demo")
    except Exception as e:
        print(f"⚠ LLM health check error: {e} - continuing with demo")
    
    # Parse the actual compliance report file
    print("\n3. Parsing compliance report file...")
    report_file = "Compliance_report_ra_agent.txt"
    
    try:
        parsed_report = parser.parse_report_file(report_file)
        
        if parsed_report.parsing_success:
            print(f"✓ Successfully parsed compliance report")
            print(f"  Found {len(parsed_report.requirements)} requirements")
        else:
            print(f"✗ Failed to parse compliance report: {parsed_report.error_message}")
            # For demo purposes, let's try with sample text if file parsing fails
            print("\n  Trying with sample text for demo...")
            sample_text = """
**Requirement R1:** During account signup, the user must agree to our Terms of Service.
*   **Status:** Non-Compliant
*   **Rationale:** Bundled consent violates GDPR Art. 7.
*   **Recommendation:** Implement separate opt-in checkboxes.
"""
            parsed_report = parser.parse_report_text(sample_text)
            
    except Exception as e:
        print(f"✗ Error during parsing: {e}")
        return
    
    # Display parsing results
    if parsed_report.parsing_success and parsed_report.requirements:
        print("\n4. Parsing Results:")
        print("-" * 50)
        
        for i, req in enumerate(parsed_report.requirements, 1):
            print(f"\nRequirement {i}:")
            print(f"  Number: {req.requirement_number}")
            print(f"  Status: {req.status}")
            print(f"  Text: {req.requirement_text[:100]}{'...' if len(req.requirement_text) > 100 else ''}")
            print(f"  Rationale: {req.rationale[:100]}{'...' if len(req.rationale) > 100 else ''}")
            if req.recommendation:
                print(f"  Recommendation: {req.recommendation[:100]}{'...' if len(req.recommendation) > 100 else ''}")
    
    # Validate the parsed data
    print("\n5. Validating parsed data...")
    validation_results = parser.validate_parsed_data(parsed_report)
    
    if validation_results['is_valid']:
        print("✓ Validation passed")
    else:
        print("✗ Validation failed:")
        for error in validation_results['errors']:
            print(f"  - {error}")
    
    # Display statistics
    print("\n6. Parsing Statistics:")
    stats = parser.get_parsing_statistics(parsed_report)
    print(f"  Total requirements: {stats.get('total_requirements', 0)}")
    if 'status_distribution' in stats:
        print("  Status distribution:")
        for status, count in stats['status_distribution'].items():
            print(f"    {status}: {count}")
    
    # Test filtering by status
    if parsed_report.parsing_success and parsed_report.requirements:
        print("\n7. Testing status filtering...")
        
        non_compliant = parser.get_requirements_by_status(parsed_report, "Non-Compliant")
        print(f"  Non-Compliant requirements: {len(non_compliant)}")
        
        compliant = parser.get_requirements_by_status(parsed_report, "Compliant")
        compliant_only = [req for req in compliant if "Non-" not in req.status]
        print(f"  Compliant requirements: {len(compliant_only)}")
        
        partial = parser.get_requirements_by_status(parsed_report, "Partial")
        print(f"  Partially Compliant requirements: {len(partial)}")
    
    # Export results to JSON for inspection
    print("\n8. Exporting results...")
    try:
        results_dict = parsed_report.to_dict()
        with open("parsed_compliance_results.json", "w", encoding="utf-8") as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        print("✓ Results exported to 'parsed_compliance_results.json'")
    except Exception as e:
        print(f"✗ Failed to export results: {e}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()