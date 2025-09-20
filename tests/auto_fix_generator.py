#!/usr/bin/env python3
"""
Auto-Fix Generator for Refiloe
Analyzes test failures and generates automated fixes
"""

import json
import re
import os
from typing import Dict, List, Optional
from pathlib import Path

# ADD DEBUGGING SECTION
print("=== AUTO FIX GENERATOR DEBUG ===")
print(f"Current directory: {os.getcwd()}")
print(f"test-results.json exists: {os.path.exists('test-results.json')}")

if os.path.exists('test-results.json'):
    with open('test-results.json', 'r') as f:
        data = json.load(f)
    print(f"JSON keys: {list(data.keys())}")
    if 'tests' in data:
        print(f"Total tests in JSON: {len(data['tests'])}")
        failed = [t for t in data['tests'] if t.get('outcome') == 'failed']
        print(f"Failed tests in JSON: {len(failed)}")
        if failed and len(failed) > 0:
            print(f"First failure: {failed[0].get('nodeid', 'UNKNOWN')[:60]}")
            # Show what the error looks like
            first_error = failed[0].get('call', {}).get('longrepr', '')
            print(f"Error type: {type(first_error)}")
            if isinstance(first_error, str):
                print(f"Error preview: {first_error[:200]}")
    else:
        print("ERROR: No 'tests' key in JSON!")
print("=== END DEBUG ===\n")

class AutoFixGenerator:
    """Generates fixes for common test failures"""
    
    def __init__(self):
        self.test_results = self.load_test_results()
        self.fixes = []
        
    def load_test_results(self) -> Dict:
        """Load test results from pytest json report"""
        try:
            with open('test-results.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("No test results found")
            return {}
    
    def analyze_failure(self, test: Dict) -> Optional[Dict]:
        """Analyze test failure and generate fix"""
        
        test_name = test.get('nodeid', '')
        
        # Handle different formats of longrepr
        call_data = test.get('call', {})
        longrepr = call_data.get('longrepr', '')
        
        if isinstance(longrepr, list):
            error_msg = ' '.join(str(item) for item in longrepr)
        elif isinstance(longrepr, dict):
            error_msg = json.dumps(longrepr)
        else:
            error_msg = str(longrepr)
        
        # Debug: Print what we're analyzing
        print(f"Analyzing: {test_name[:80]}...")
        print(f"  Error snippet: {error_msg[:150]}")
        
        # Critical: Currency parsing fix - make pattern matching more flexible
        if ("R450" in error_msg and "450" in error_msg and "pricing" in error_msg) or \
           ("pricing_per_session" in error_msg):
            print("  → Matched currency parsing issue")
            return {
                'type': 'currency_parsing',
                'file': 'services/registration/trainer_registration.py',
                'test': test_name,
                'diagnosis': 'Currency value saved as string "R450" instead of number 450',
                'line': 0,
                'search_pattern': "'pricing_per_session': data.get('pricing', 300),",
                'original_code': "'pricing_per_session': data.get('pricing', 300),",
                'fixed_code': "'pricing_per_session': self._parse_currency(data.get('pricing', 300)),"
            }
        
        # Phone number format issue - more flexible matching
        if ("+27" in error_msg and "27821234567" in error_msg) or \
           ("Expected 27" in error_msg and "got +27" in error_msg):
            print("  → Matched phone format issue")
            return {
                'type': 'phone_format',
                'file': 'utils/validators.py',
                'test': test_name,
                'diagnosis': 'Phone returns with + prefix but tests expect without',
                'line': 0,
                'search_pattern': "return True, f'+{phone_digits}', None",
                'original_code': "return True, f'+{phone_digits}', None",
                'fixed_code': "return True, phone_digits, None"
            }
        
        # Missing validate_time_format method
        if "validate_time_format" in error_msg or \
           ("Failed to validate time" in error_msg and "9am" in error_msg):
            print("  → Matched time format issue")
            return {
                'type': 'missing_method',
                'file': 'utils/validators.py',
                'test': test_name,
                'diagnosis': 'Method validate_time_format does not exist or time validation fails',
                'line': 0,
                'add_method': True,
                'method_code': '''
    def validate_time_format(self, time_str: str):
        """Validate time format (wrapper for validate_time)"""
        from typing import Tuple, Optional
        is_valid, formatted_time, error = self.validate_time(time_str)
        return is_valid, error'''
            }
        
        # Duplicate registration check - more flexible
        if "duplicate_registration" in test_name.lower() or \
           ("already" in test_name.lower() and "registration" in test_name.lower()):
            print("  → Matched duplicate registration issue")
            return {
                'type': 'duplicate_check',
                'file': 'services/registration/trainer_registration.py',
                'test': test_name,
                'diagnosis': 'Not checking for existing registration',
                'line': 0,
                'add_check': True,
                'check_code': '''
        # Check if trainer already registered
        existing = self.db.table('trainers').select('id').eq('whatsapp', phone).execute()
        if existing.data:
            return "Welcome back! You're already registered. How can I help you today?"'''
            }
        
        # Input length validation
        if ("assert 500 <= 255" in error_msg) or \
           ("500" in error_msg and "255" in error_msg and "len" in error_msg.lower()):
            print("  → Matched input length issue")
            return {
                'type': 'input_validation',
                'file': 'services/registration/trainer_registration.py',
                'test': test_name,
                'diagnosis': 'Not truncating long input',
                'line': 0,
                'add_validation': True,
                'validation_code': "response = response[:255] if len(response) > 255 else response  # Truncate if too long"
            }
        
        # AI intent recognition issues - broader matching
        if ("Failed to list clients" in error_msg) or \
           ("Failed to show schedule" in error_msg) or \
           ("view_clients" in test_name.lower() and "client" not in error_msg.lower()) or \
           ("view_schedule" in test_name.lower() and "schedule" not in error_msg.lower()):
            print("  → Matched AI intent issue")
            return {
                'type': 'ai_intent',
                'file': 'services/ai_intent_handler.py',
                'test': test_name,
                'diagnosis': 'AI not recognizing basic commands',
                'line': 0,
                'add_patterns': True,
                'pattern_code': '''
        # Common command patterns
        command_patterns = {
            'view_clients': [r'show.*clients?', r'list.*clients?', r'my clients?'],
            'view_schedule': [r'show.*schedule', r'my schedule', r"what.*today"],
            'add_client': [r'add.*client', r'new client', r'register.*client'],
        }'''
            }
        
        print("  → No fix pattern matched")
        return None
    
    def process_all_failures(self):
        """Process all test failures and generate fixes"""
        
        if not self.test_results:
            print("No test results to process")
            return
        
        # Get failed tests
        failed_tests = [
            test for test in self.test_results.get('tests', [])
            if test.get('outcome') == 'failed'
        ]
        
        print(f"\nFound {len(failed_tests)} failed tests")
        
        # Track unique fixes to avoid duplicates
        unique_fixes = {}
        
        for test in failed_tests:
            fix = self.analyze_failure(test)
            if fix:
                # Use fix type and file as unique key
                key = f"{fix['type']}_{fix['file']}"
                if key not in unique_fixes:
                    unique_fixes[key] = fix
                    self.fixes.append(fix)
                    print(f"✅ Generated fix for: {fix['type']}")
        
        # Save fixes
        self.save_fixes()
    
    def save_fixes(self) -> None:
        """Save generated fixes to file"""
        
        if self.fixes:
            with open('generated_fixes.json', 'w') as f:
                json.dump(self.fixes, f, indent=2)
            print(f"\n📝 Generated {len(self.fixes)} fixes")
            print("✅ Created generated_fixes.json")
        else:
            print("\n⚠️ No fixes were generated")
            print("   Check that error patterns match the actual test failures")
        
        # Create summary for PR
        summary = {
            'total_tests': len(self.test_results.get('tests', [])),
            'failed_tests': len([t for t in self.test_results.get('tests', []) if t.get('outcome') == 'failed']),
            'fixes_generated': len(self.fixes),
            'fix_types': {}
        }
        
        for fix in self.fixes:
            fix_type = fix['type']
            summary['fix_types'][fix_type] = summary['fix_types'].get(fix_type, 0) + 1
        
        with open('fix_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("✅ Created fix_summary.json")

if __name__ == "__main__":
    print("🔍 Analyzing test failures...")
    generator = AutoFixGenerator()
    generator.process_all_failures()
    print("✅ Fix generation complete!")
