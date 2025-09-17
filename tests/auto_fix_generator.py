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
        error_msg = str(test.get('call', {}).get('longrepr', ''))
        
        # Debug: Print what we're analyzing
        print(f"Analyzing: {test_name[:80]}...")
        
        # Critical: Currency parsing fix - the most common issue
        if ("'R450' == 450" in error_msg or 
            "pricing_per_session" in error_msg and "'R" in error_msg):
            return {
                'type': 'currency_parsing',
                'file': 'services/registration/trainer_registration.py',
                'test': test_name,
                'diagnosis': 'Currency value saved as string "R450" instead of number 450',
                'line': 0,  # Will search for the line
                'search_pattern': "'pricing_per_session': data.get('pricing'",
                'original_code': "'pricing_per_session': data.get('pricing', 400),",
                'fixed_code': "'pricing_per_session': self._parse_currency(data.get('pricing', 400)),"
            }
        
        # Phone number format issue
        if "Expected 27821234567 but got +27821234567" in error_msg:
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
        if "has no attribute 'validate_time_format'" in error_msg:
            return {
                'type': 'missing_method',
                'file': 'utils/validators.py',
                'test': test_name,
                'diagnosis': 'Method validate_time_format does not exist',
                'line': 0,
                'add_method': True,
                'method_code': '''
    def validate_time_format(self, time_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate time format (wrapper for validate_time)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        is_valid, formatted_time, error = self.validate_time(time_str)
        return is_valid, error'''
            }
        
        # Duplicate registration check
        if "duplicate_registration" in test_name.lower() and "already" not in error_msg.lower():
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
        if "assert 500 <= 255" in error_msg:
            return {
                'type': 'input_validation',
                'file': 'services/registration/trainer_registration.py',
                'test': test_name,
                'diagnosis': 'Not truncating long input',
                'line': 0,
                'add_validation': True,
                'validation_code': "name = name[:255] if len(name) > 255 else name  # Truncate if too long"
            }
        
        # AI intent recognition issues
        if ("Failed to list clients" in error_msg or 
            "Failed to show schedule" in error_msg or
            "general_question" in error_msg and "view_clients" in test_name.lower()):
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
        
        print(f"Found {len(failed_tests)} failed tests")
        
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
        
        with open('generated_fixes.json', 'w') as f:
            json.dump(self.fixes, f, indent=2)
        
        print(f"\n📝 Generated {len(self.fixes)} fixes")
        
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

if __name__ == "__main__":
    print("🔍 Analyzing test failures...")
    generator = AutoFixGenerator()
    generator.process_all_failures()
    print("✅ Fix generation complete!")
