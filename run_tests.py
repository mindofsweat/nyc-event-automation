#!/usr/bin/env python3
"""
Test runner script for NYC Event Automation.
"""

import sys
import subprocess
from pathlib import Path


def run_tests(test_type=None):
    """Run tests with optional filtering."""
    cmd = ["pytest"]
    
    if test_type:
        if test_type == "unit":
            cmd.extend(["-m", "unit"])
        elif test_type == "integration":
            cmd.extend(["-m", "integration"])
        elif test_type == "scrapers":
            cmd.append("tests/test_scrapers.py")
        elif test_type == "email":
            cmd.extend(["tests/test_reply_parser.py", "tests/test_email_digest.py", "tests/test_outreach.py"])
        elif test_type == "data":
            cmd.append("tests/test_data_models.py")
        elif test_type == "coverage":
            cmd.extend(["--cov=scrapers", "--cov=email_service", "--cov=data_store", 
                       "--cov-report=term-missing", "--cov-report=html"])
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode


def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests for NYC Event Automation")
    parser.add_argument(
        "type",
        nargs="?",
        choices=["all", "unit", "integration", "scrapers", "email", "data", "coverage"],
        default="all",
        help="Type of tests to run"
    )
    
    args = parser.parse_args()
    
    if args.type == "all":
        return_code = run_tests()
    else:
        return_code = run_tests(args.type)
    
    if return_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(return_code)


if __name__ == "__main__":
    main()