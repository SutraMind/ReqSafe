"""Demo script for using the HumanFeedbackParser with mock data."""

import json
import logging
from memory_management.parsers.human_feedback_parser import (
    HumanFeedbackParser, 
    ParsedHumanFeedback,
    FeedbackItem
)
from memory_management.parsers.compliance_report_parser import (
    ComplianceReportParser,
    ParsedComplianceReport,
    ComplianceRequirement
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_mock_compliance_data():
    """Create mock compliance report data for demonstration."""
    requirements = [
        ComplianceRequirement(
            requirement_number="R1",
            requirement_text="During account signup, the user must agree to our Terms of Service, Privacy Policy, and consent to receive marketing emails about our products and partner offers by ticking a single checkbox.",
            status="Non-Compliant",
            rationale="Bundled consent violates GDPR Art. 7. Consent must be granular, specific, and freely given for distinct processing activities.",
            recommendation="Implement separate, unticked opt-in checkboxes for marketing emails and for partner offers."
        ),
        ComplianceRequirement(
            requirement_number="R2",
            requirement_text="To improve our services, user purchase history and browsing data will be stored indefinitely for trend analysis.",
            status="Non-Compliant",
            rationale="Indefinite storage violates the storage limitation principle of GDPR Art. 5(1)(e).",
            recommendation="Define a specific retention period, e.g., \"5 years after the last customer interaction,\" and document this in the privacy policy."
        ),
        ComplianceRequirement(
            requirement_number="R3",
            requirement_text="Users can access their personal data through the \"My Account\" dashboard.",
            status="Partially Compliant",
            rationale="Fulfills the right of access (Art. 15), but fails to mention the rights to rectification (Art. 16) and erasure (Art. 17).",
            recommendation="The \"My Account\" dashboard should be updated to include functionality for users to access, edit, and request erasure of their personal data."
        ),
        ComplianceRequirement(
            requirement_number="R4",
            requirement_text="All user passwords will be stored in the database using industry-standard SHA-256 hashing.",
            status="Compliant",
            rationale="Using SHA-256 hashing is a recognized technical measure for securing data at rest, aligning with the principles of security by design under GDPR Art. 32.",
            recommendation="None needed."
        ),
        ComplianceRequirement(
            requirement_number="R5",
            requirement_text="For order fulfillment, user shipping details (name, address, phone number) will be shared with our third-party logistics partners.",
            status="Partially Compliant",
            rationale="Sharing data with partners is necessary for the performance of a contract (Art. 6(1)(b)). However, the requirement should specify that a Data Processing Agreement (DPA) is in place.",
            recommendation="Ensure Data Processing Agreements (DPAs) are in place with all logistics partners and this data sharing is clearly disclosed in the privacy policy."
        )
    ]
    
    return ParsedComplianceReport(
        requirements=requirements,
        raw_text="Mock compliance report text",
        parsing_success=True
    )

def create_mock_feedback_data():
    """Create mock human feedback data for demonstration."""
    feedback_items = [
        FeedbackItem(
            requirement_reference="R2",
            decision="Modify",
            rationale="The recommendation of a fixed '5 years' is too simplistic and arbitrary. A better, more defensible policy is event-driven.",
            suggestion="The data retention policy should be event-based. For example: 'User data will be retained for 3 years following the user's last login or transaction. The account will be considered inactive after this period and scheduled for deletion.'",
            confidence="High"
        ),
        FeedbackItem(
            requirement_reference="R4",
            decision="Change status from 'Compliant' to 'Partially Compliant'",
            rationale="A raw (unsalted) hash is vulnerable to pre-computed 'rainbow table' attacks. GDPR's 'state-of-the-art' security requirement implies protection against such common attack vectors.",
            suggestion="The requirement must be updated to specify the use of a salted hash. For example: 'All user passwords will be stored using a salted SHA-256 hashing algorithm to ensure strong cryptographic protection.'",
            confidence="High"
        )
    ]
    
    return ParsedHumanFeedback(
        feedback_items=feedback_items,
        raw_text="Mock human feedback text",
        parsing_success=True
    )

def main():
    """Run the human feedback parser demo with mock data."""
    # Initialize parsers
    feedback_parser = HumanFeedbackParser()
    
    # Create mock data
    logger.info("Creating mock compliance report data")
    compliance_result = create_mock_compliance_data()
    logger.info(f"Created mock data with {len(compliance_result.requirements)} requirements")
    
    logger.info("Creating mock human feedback data")
    feedback_result = create_mock_feedback_data()
    logger.info(f"Created mock data with {len(feedback_result.feedback_items)} feedback items")
    
    # Validate the parsed feedback
    validation_results = feedback_parser.validate_parsed_data(feedback_result)
    if not validation_results['is_valid']:
        logger.warning("Validation found issues with the parsed feedback:")
        for error in validation_results['errors']:
            logger.warning(f"  - {error}")
    else:
        logger.info("Feedback data validation passed")
    
    # Print feedback statistics
    stats = feedback_parser.get_parsing_statistics(feedback_result)
    logger.info(f"Feedback statistics: {json.dumps(stats, indent=2)}")
    
    # Map feedback to requirements
    requirements_data = [req.to_dict() for req in compliance_result.requirements]
    mapping = feedback_parser.map_feedback_to_requirements(feedback_result, requirements_data)
    
    logger.info(f"Mapped {len(mapping)} feedback items to requirements")
    
    # Print the mapped data
    for req_num, data in mapping.items():
        logger.info(f"\nRequirement {req_num}:")
        logger.info(f"  Text: {data['requirement']['requirement_text']}")
        logger.info(f"  Initial Status: {data['requirement']['status']}")
        logger.info(f"  Feedback Decision: {data['feedback']['decision']}")
        logger.info(f"  Feedback Rationale: {data['feedback']['rationale']}")
        if data['feedback']['suggestion']:
            logger.info(f"  Suggestion: {data['feedback']['suggestion']}")
    
    # Demonstrate filtering by decision type
    modify_items = feedback_parser.get_feedback_by_decision(feedback_result, "Change")
    logger.info(f"\nFound {len(modify_items)} feedback items with 'Change' in decision")
    for item in modify_items:
        logger.info(f"  Requirement: {item.requirement_reference}")
        logger.info(f"  Decision: {item.decision}")

if __name__ == "__main__":
    main()