#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner for Compliance Memory Management Module.

This script runs the comprehensive test suite and provides a summary of results.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_test_suite(test_file: str, description: str) -> dict:
    """Run a test suite and return results."""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run pytest with JSON report
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_file, 
            "-v", "--tb=short", "--maxfail=10"
        ], capture_output=True, text=True, timeout=300)
        
        execution_time = time.time() - start_time
        
        # Parse results from output
        output_lines = result.stdout.split('\n')
        
        # Find the summary line
        summary_line = ""
        for line in reversed(output_lines):
            if "passed" in line or "failed" in line:
                summary_line = line
                break
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'errors': result.stderr,
            'summary': summary_line,
            'execution_time': execution_time,
            'return_code': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': "",
            'errors': "Test suite timed out after 5 minutes",
            'summary': "TIMEOUT",
            'execution_time': 300,
            'return_code': -1
        }
    except Exception as e:
        return {
            'success': False,
            'output': "",
            'errors': str(e),
            'summary': f"ERROR: {str(e)}",
            'execution_time': time.time() - start_time,
            'return_code': -1
        }


def main():
    """Run comprehensive tests and provide summary."""
    print("Compliance Memory Management Module - Comprehensive Test Suite")
    print("=" * 70)
    
    test_suites = [
        ("test_comprehensive_mocked.py", "Comprehensive Mocked Test Suite"),
        ("test_fixtures_and_mocks.py", "Test Fixtures and Mock Data Generators"),
    ]
    
    results = {}
    total_start_time = time.time()
    
    for test_file, description in test_suites:
        if Path(test_file).exists():
            results[test_file] = run_test_suite(test_file, description)
        else:
            print(f"\nSkipping {test_file} - file not found")
            results[test_file] = {
                'success': False,
                'summary': 'FILE NOT FOUND',
                'execution_time': 0
            }
    
    # Print comprehensive summary
    total_execution_time = time.time() - total_start_time
    
    print(f"\n{'='*70}")
    print("COMPREHENSIVE TEST SUITE SUMMARY")
    print(f"{'='*70}")
    
    total_passed = 0
    total_failed = 0
    total_suites = 0
    successful_suites = 0
    
    for test_file, result in results.items():
        print(f"\n{test_file}:")
        print(f"  Status: {'✓ PASSED' if result['success'] else '✗ FAILED'}")
        print(f"  Summary: {result['summary']}")
        print(f"  Time: {result['execution_time']:.2f}s")
        
        if result['success']:
            successful_suites += 1
        
        total_suites += 1
        
        # Extract test counts from summary if available
        summary = result['summary']
        if 'passed' in summary:
            try:
                # Try to extract numbers from summary like "15 passed, 2 failed"
                parts = summary.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        total_passed += int(parts[i-1])
                    elif part == 'failed' and i > 0:
                        total_failed += int(parts[i-1])
            except:
                pass
    
    print(f"\n{'='*70}")
    print("OVERALL RESULTS:")
    print(f"  Test Suites: {successful_suites}/{total_suites} successful")
    print(f"  Individual Tests: {total_passed} passed, {total_failed} failed")
    print(f"  Total Execution Time: {total_execution_time:.2f}s")
    
    if successful_suites == total_suites and total_failed == 0:
        print(f"  Overall Status: ✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"  Overall Status: ✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())