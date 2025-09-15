# tests/run_tests.py
"""
Script to run specific categories of tests
Makes it easy to test specific features
"""

import sys
import subprocess
import argparse


def run_tests(category=None, verbose=False):
    """Run tests for a specific category"""
    
    cmd = ["python", "-m", "pytest"]
    
    if category:
        # Map user-friendly names to test markers
        category_map = {
            'registration': '-m registration',
            'trainer': '-m trainer',
            'client': '-m client',
            'booking': '-m booking',
            'payment': '-m payment',
            'ai': '-m ai',
            'critical': '-m critical',
            'phase1': 'test_refiloe_complete.py::TestPhase1_UserRegistration',
            'phase2': 'test_refiloe_complete.py::TestPhase2_ClientManagement',
            'phase3': 'test_refiloe_complete.py::TestPhase3_SchedulingBookings',
            'phase4': 'test_refiloe_complete.py::TestPhase4_HabitTracking',
            'phase5': 'test_refiloe_complete.py::TestPhase5_WorkoutsAssessments',
            'phase6': 'test_refiloe_complete.py::TestPhase6_PaymentsRevenue',
            'phase8': 'test_refiloe_complete.py::TestPhase8_ClientFeatures',
            'phase10': 'test_refiloe_complete.py::TestPhase10_AdvancedFeatures',
            'bugs': 'test_refiloe_complete.py::TestCriticalBugs',
        }
        
        if category in category_map:
            if '-m' in category_map[category]:
                cmd.extend(category_map[category].split())
            else:
                cmd.append(f"tests/{category_map[category]}")
        else:
            print(f"Unknown category: {category}")
            print(f"Available categories: {', '.join(category_map.keys())}")
            return 1
    else:
        # Run all tests
        cmd.append("tests/")
    
    if verbose:
        cmd.append("-v")
        cmd.append("--tb=short")
    else:
        cmd.append("-q")
    
    # Add test report generation
    cmd.extend([
        "--html=test-report.html",
        "--self-contained-html",
        "--json-report",
        "--json-report-file=test-results.json"
    ])
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description='Run Refiloe tests')
    parser.add_argument(
        'category',
        nargs='?',
        help='Test category to run (e.g., registration, trainer, client, booking, ai, bugs, phase1-10)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List available test categories'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available test categories:")
        print("  registration - User registration tests")
        print("  trainer     - Trainer functionality tests")
        print("  client      - Client functionality tests")
        print("  booking     - Booking system tests")
        print("  payment     - Payment processing tests")
        print("  ai          - AI/Natural language tests")
        print("  critical    - Critical tests that must pass")
        print("  bugs        - Tests for known bugs")
        print("  phase1-10   - Run specific phase tests")
        return 0
    
    return run_tests(args.category, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
