# tests/auto_fix_generator.py
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
        """Analyze a single test failure and generate fix"""
        
        test_name = test.get('nodeid', '')
        error_msg = test.get('call', {}).get('longrepr', '')
        
        # Pattern 1: Currency parsing issue (R450 stored as string)
        if "assert 'R450' == 450" in error_msg:
            return self.fix_currency_parsing(test_name, error_msg)
        
        # Pattern 2: Phone number format (+27 vs 27)
        if "'+27" in error_msg and "== '27" in error_msg:
            return self.fix_phone_format(test_name, error_msg)
        
        # Pattern 3: Missing validate_time_format method
        if "validate_time_format" in error_msg:
            return self.fix_validator_method(test_name, error_msg)
        
        # Pattern 4: AI not understanding commands
        if "assert ('added' in ''" in error_msg or "assert ('schedule' in ''" in error_msg:
            return self.fix_ai_understanding(test_name, error_msg)
        
        # Pattern 5: Name length validation
        if "assert 500 <= 255" in error_msg:
            return self.fix_name_length(test_name, error_msg)
        
        # Pattern 6: Duplicate registration not detected
        if "already" in error_msg and "welcome back" in error_msg:
            return self.fix_duplicate_check(test_name, error_msg)
        
        return None
    
    def fix_currency_parsing(self, test_name: str, error: str) -> Dict:
        """Fix for currency being stored as string instead of number"""
        
        return {
            'test': test_name,
            'type': 'currency_parsing',
            'file': 'services/registration/trainer_registration.py',
            'diagnosis': 'Currency value stored as string (R450) instead of number (450)',
            'original_code': """pricing_per_session = f"R{pricing}"  # Or similar string storage""",
            'fixed_code': """# Extract numeric value from currency string
import re

# If pricing comes in as "R450" or similar
if isinstance(pricing, str):
    # Remove currency symbols and extract number
    pricing_text = re.sub(r'[^\\d.]', '', str(pricing))
    pricing_per_session = float(pricing_text) if pricing_text else 0
else:
    pricing_per_session = float(pricing)
    
# Store as numeric value in database
trainer_data['pricing_per_session'] = pricing_per_session"""
        }
    
    def fix_phone_format(self, test_name: str, error: str) -> Dict:
        """Fix for phone number format consistency"""
        
        return {
            'test': test_name,
            'type': 'phone_format',
            'file': 'utils/validators.py',
            'diagnosis': 'Phone returns +27... but tests expect 27...',
            'original_code': """return True, f"+{phone_digits}", None""",
            'fixed_code': """# Return without + prefix for consistency
return True, phone_digits, None  # Return without + prefix"""
        }
    
    def fix_validator_method(self, test_name: str, error: str) -> Dict:
        """Fix for missing validate_time_format method"""
        
        return {
            'test': test_name,
            'type': 'missing_method',
            'file': 'utils/validators.py',
            'diagnosis': 'Method validate_time_format does not exist',
            'original_code': """# Method doesn't exist""",
            'fixed_code': """def validate_time_format(self, time_str: str) -> Tuple[bool, Optional[str]]:
    \"\"\"
    Validate time format (wrapper for validate_time)
    
    Returns:
        Tuple of (is_valid, error_message)
    \"\"\"
    is_valid, formatted_time, error = self.validate_time(time_str)
    return is_valid, error"""
        }
    
    def fix_ai_understanding(self, test_name: str, error: str) -> Dict:
        """Fix for AI not understanding commands"""
        
        return {
            'test': test_name,
            'type': 'ai_intent',
            'file': 'services/ai_intent_handler.py',
            'diagnosis': 'AI not recognizing basic commands like "Show my clients"',
            'original_code': """# Current intent detection not working""",
            'fixed_code': """# Add explicit command patterns
command_patterns = {
    'add_client': [
        r'add.*client',
        r'register.*client',
        r'new.*client',
        r'sign.*up.*client'
    ],
    'view_clients': [
        r'show.*clients?',
        r'list.*clients?',
        r'view.*clients?',
        r'my.*clients?'
    ],
    'view_schedule': [
        r'show.*schedule',
        r'my.*schedule',
        r'what.*today',
        r'booking'
    ],
    'set_pricing': [
        r'set.*price',
        r'change.*rate',
        r'update.*pricing',
        r'\\brate\\b.*\\d+'
    ]
}

# Check patterns first before AI
for intent, patterns in command_patterns.items():
    for pattern in patterns:
        if re.search(pattern, message.lower()):
            return {'intent': intent, 'confidence': 0.95}"""
        }
    
    def fix_name_length(self, test_name: str, error: str) -> Dict:
        """Fix for name length validation"""
        
        return {
            'test': test_name,
            'type': 'validation',
            'file': 'services/registration/trainer_registration.py',
            'diagnosis': 'Name field accepts 500 chars but should limit to 255',
            'original_code': """# No length check""",
            'fixed_code': """# Limit name length
if len(name) > 255:
    name = name[:255]  # Truncate to max length"""
        }
    
    def fix_duplicate_check(self, test_name: str, error: str) -> Dict:
        """Fix for duplicate registration check"""
        
        return {
            'test': test_name,
            'type': 'duplicate_check',
            'file': 'services/refiloe.py',
            'diagnosis': 'Not checking for existing trainer before registration',
            'original_code': """# Start registration without checking""",
            'fixed_code': """# Check if trainer exists first
existing = self.db.table('trainers').select('*').eq('whatsapp', phone).single().execute()

if existing.data:
    return {
        'success': True,
        'response': f"Welcome back {existing.data['first_name']}! You're already registered. How can I help you today?"
    }
    
# Otherwise continue with registration..."""
        }
    
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
        
        for test in failed_tests:
            fix = self.analyze_failure(test)
            if fix:
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
        
        # Create readable report
        with open('fix_report.md', 'w') as f:
            f.write("# 🔧 Auto-Generated Fixes for Refiloe\n\n")
            f.write(f"**Failed Tests:** {summary['failed_tests']}\n")
            f.write(f"**Fixes Generated:** {summary['fixes_generated']}\n\n")
            
            f.write("## Fix Details\n\n")
            for i, fix in enumerate(self.fixes, 1):
                f.write(f"### Fix {i}: {fix['type'].replace('_', ' ').title()}\n")
                f.write(f"**Test:** {fix['test']}\n")
                f.write(f"**File:** `{fix['file']}`\n")
                f.write(f"**Issue:** {fix['diagnosis']}\n\n")
                f.write("**Solution:**\n")
                f.write(f"```python\n{fix['fixed_code']}\n```\n\n")
                f.write("---\n\n")

if __name__ == "__main__":
    print("🔍 Analyzing test failures...")
    generator = AutoFixGenerator()
    generator.process_all_failures()
    print("✅ Fix generation complete!")
