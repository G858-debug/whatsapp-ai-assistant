#!/usr/bin/env python3
"""
Improved Auto-Fix Generator - Better pattern recognition and fix generation
"""

import json
import re
from typing import Dict, List, Optional
from pathlib import Path


class ImprovedAutoFixGenerator:
    """Enhanced fix generator with better pattern matching"""
    
    def __init__(self):
        self.test_results = self.load_test_results()
        self.fixes = []
        self.fix_patterns = self.initialize_fix_patterns()
    
    def initialize_fix_patterns(self) -> List[Dict]:
        """Initialize comprehensive fix patterns"""
        return [
            {
                'pattern': r"currency|pricing|R\d+|price.*string.*expected.*number",
                'type': 'currency_parsing',
                'file_pattern': 'trainer_registration',
                'solution': 'add_currency_parser'
            },
            {
                'pattern': r"phone.*format|\+27.*expected.*27|normalize.*phone",
                'type': 'phone_format',
                'file_pattern': 'validators',
                'solution': 'fix_phone_format'
            },
            {
                'pattern': r"already.*registered|duplicate.*registration|existing.*trainer",
                'type': 'duplicate_check',
                'file_pattern': 'trainer_registration',
                'solution': 'add_duplicate_check'
            },
            {
                'pattern': r"trainer.*recognition|recognize.*trainer|existing.*trainer.*name",
                'type': 'trainer_recognition',
                'file_pattern': 'ai_intent',
                'solution': 'add_trainer_check'
            },
            {
                'pattern': r"client.*welcome|client.*added|welcome.*message",
                'type': 'client_registration',
                'file_pattern': 'client_registration',
                'solution': 'fix_welcome_message'
            },
            {
                'pattern': r"command.*not.*recognized|ai.*intent|view.*clients|show.*schedule",
                'type': 'ai_intent',
                'file_pattern': 'ai_intent',
                'solution': 'improve_intent_recognition'
            },
            {
                'pattern': r"validate_time_format.*not.*found|missing.*method|AttributeError.*validate",
                'type': 'missing_method',
                'file_pattern': 'validators',
                'solution': 'add_missing_method'
            },
            {
                'pattern': r"Mock.*object|mock.*not.*callable|Mock.*has.*no.*attribute",
                'type': 'mock_issue',
                'file_pattern': 'test_',
                'solution': 'fix_mock_setup'
            }
        ]
    
    def load_test_results(self) -> Dict:
        """Load test results from JSON file"""
        try:
            with open('test-results.json', 'r') as f:
                data = json.load(f)
                print(f"📥 Loaded test results: {len(data.get('tests', []))} tests")
                return data
        except FileNotFoundError:
            print("❌ test-results.json not found")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing test-results.json: {e}")
            return {}
    
    def extract_error_context(self, test: Dict) -> Dict:
        """Extract comprehensive error context from test failure"""
        context = {
            'test_name': test.get('nodeid', ''),
            'error_message': '',
            'error_type': '',
            'file_path': '',
            'line_number': 0,
            'assertion': ''
        }
        
        # Parse the call information
        call_info = test.get('call', {})
        if call_info:
            # Get the full error message
            longrepr = call_info.get('longrepr', '')
            if longrepr:
                context['error_message'] = longrepr[:500]  # First 500 chars
                
                # Extract error type
                if 'AssertionError' in longrepr:
                    context['error_type'] = 'assertion'
                elif 'AttributeError' in longrepr:
                    context['error_type'] = 'missing_attribute'
                elif 'KeyError' in longrepr:
                    context['error_type'] = 'missing_key'
                elif 'TypeError' in longrepr:
                    context['error_type'] = 'type_error'
                
                # Extract file and line number
                file_match = re.search(r'(\w+\.py):(\d+):', longrepr)
                if file_match:
                    context['file_path'] = file_match.group(1)
                    context['line_number'] = int(file_match.group(2))
                
                # Extract assertion details
                assert_match = re.search(r'assert (.+)', longrepr)
                if assert_match:
                    context['assertion'] = assert_match.group(1)
        
        return context
    
    def determine_fix_type(self, context: Dict) -> Optional[Dict]:
        """Determine the type of fix needed based on error context"""
        error_text = f"{context['error_message']} {context['test_name']} {context['assertion']}"
        error_text_lower = error_text.lower()
        
        # Check each pattern
        for pattern_config in self.fix_patterns:
            if re.search(pattern_config['pattern'], error_text_lower):
                print(f"  ✅ Matched pattern: {pattern_config['type']}")
                return pattern_config
        
        # Fallback patterns for common issues
        if 'mock' in error_text_lower:
            print(f"  ⚠️ Mock-related issue detected")
            return None  # Skip mock issues as they're test setup problems
        
        print(f"  ❓ No pattern matched")
        return None
    
    def generate_fix(self, test: Dict, context: Dict, fix_config: Dict) -> Optional[Dict]:
        """Generate a specific fix based on the error and fix type"""
        fix_type = fix_config['type']
        test_file = test.get('nodeid', '').split('::')[0]
        
        # Determine target file
        if 'trainer_registration' in fix_config['file_pattern']:
            target_file = 'services/registration/trainer_registration.py'
        elif 'client_registration' in fix_config['file_pattern']:
            target_file = 'services/registration/client_registration.py'
        elif 'validators' in fix_config['file_pattern']:
            target_file = 'utils/validators.py'
        elif 'ai_intent' in fix_config['file_pattern']:
            target_file = 'services/ai_intent_handler.py'
        else:
            # Try to guess from test name
            if 'phase1' in test_file:
                target_file = 'services/registration/trainer_registration.py'
            elif 'phase2' in test_file:
                target_file = 'services/registration/client_registration.py'
            else:
                target_file = 'services/ai_intent_handler.py'
        
        # Create fix based on type
        fix = {
            'type': fix_type,
            'file': target_file,
            'test': test.get('nodeid', ''),
            'diagnosis': self.get_diagnosis(fix_type, context),
            'line': context['line_number']
        }
        
        # Add specific fix details based on type
        if fix_type == 'currency_parsing':
            fix.update({
                'search_pattern': "'pricing_per_session': data.get('pricing'",
                'fixed_code': "'pricing_per_session': self._parse_currency(data.get('pricing', 300))",
                'add_method': True,
                'method_name': '_parse_currency'
            })
        
        elif fix_type == 'phone_format':
            fix.update({
                'search_pattern': "return True, f'+{phone_digits}', None",
                'fixed_code': "return True, phone_digits, None"
            })
        
        elif fix_type == 'duplicate_check':
            fix.update({
                'add_check': True,
                'check_code': '''
        # Check if trainer already registered
        existing = self.db.table('trainers').select('id').eq('whatsapp', phone).execute()
        if existing.data:
            return {"success": True, "message": "Welcome back! You're already registered. How can I help you today?"}'''
            })
        
        elif fix_type == 'trainer_recognition':
            fix.update({
                'add_check': True,
                'check_code': '''
        # Check if user is an existing trainer
        trainer = self.db.table('trainers').select('name').eq('whatsapp', phone).execute()
        if trainer.data:
            trainer_name = trainer.data[0]['name']
            return {"success": True, "message": f"Welcome back, {trainer_name}! How can I help you today?"}'''
            })
        
        elif fix_type == 'client_registration':
            fix.update({
                'add_response': True,
                'response_code': '''
        return {
            "success": True,
            "message": f"Great! {client_name} has been added as your client."
        }'''
            })
        
        elif fix_type == 'ai_intent':
            fix.update({
                'add_patterns': True,
                'pattern_code': '''
        # Common command patterns
        command_patterns = {
            'view_clients': [r'show.*clients?', r'list.*clients?', r'my clients?'],
            'view_schedule': [r'show.*schedule', r'my schedule', r"what.*today"],
            'add_client': [r'add.*client', r'new client', r'register.*client'],
            'book_session': [r'book.*session', r'schedule.*training', r'book.*time']
        }'''
            })
        
        elif fix_type == 'missing_method':
            # Determine which method is missing
            if 'validate_time_format' in context['error_message']:
                fix.update({
                    'add_method': True,
                    'method_code': '''
    def validate_time_format(self, time_str):
        """Validate time format"""
        import re
        patterns = [
            r'^\d{1,2}:\d{2}$',  # 9:00, 09:00
            r'^\d{1,2}:\d{2}\s*[aApP][mM]$',  # 9:00am, 09:00 PM
            r'^\d{1,2}[aApP][mM]$'  # 9am, 10PM
        ]
        
        for pattern in patterns:
            if re.match(pattern, time_str.strip()):
                return True
        return False'''
                })
        
        return fix
    
    def get_diagnosis(self, fix_type: str, context: Dict) -> str:
        """Generate a human-readable diagnosis"""
        diagnoses = {
            'currency_parsing': 'Currency value saved as string instead of number',
            'phone_format': 'Phone number format inconsistency (+ prefix)',
            'duplicate_check': 'Not checking for existing registration',
            'trainer_recognition': 'Not recognizing existing trainers by name',
            'client_registration': 'Client not receiving proper welcome message',
            'ai_intent': 'AI not recognizing natural language commands',
            'missing_method': f'Missing method: {context.get("assertion", "validation method")}',
            'mock_issue': 'Test mock configuration issue'
        }
        return diagnoses.get(fix_type, 'Issue detected in code')
    
    def process_all_failures(self):
        """Process all test failures and generate fixes"""
        if not self.test_results:
            print("❌ No test results to process")
            return
        
        # Get failed tests
        failed_tests = [
            test for test in self.test_results.get('tests', [])
            if test.get('outcome') == 'failed'
        ]
        
        print(f"\n📊 Found {len(failed_tests)} failed tests")
        print("=" * 60)
        
        # Track unique fixes to avoid duplicates
        unique_fixes = {}
        skipped_count = 0
        
        for i, test in enumerate(failed_tests, 1):
            test_name = test.get('nodeid', 'Unknown')
            print(f"\n[{i}/{len(failed_tests)}] Analyzing: {test_name[:80]}...")
            
            # Extract error context
            context = self.extract_error_context(test)
            
            # Determine fix type
            fix_config = self.determine_fix_type(context)
            
            if fix_config:
                # Generate fix
                fix = self.generate_fix(test, context, fix_config)
                
                if fix:
                    # Use fix type and file as unique key
                    key = f"{fix['type']}_{fix['file']}"
                    
                    if key not in unique_fixes:
                        unique_fixes[key] = fix
                        self.fixes.append(fix)
                        print(f"  ✅ Generated fix: {fix['type']}")
                    else:
                        print(f"  ⏭️  Duplicate fix skipped")
                else:
                    print(f"  ❌ Could not generate fix")
            else:
                if 'mock' in context['error_message'].lower():
                    print(f"  ⏭️  Skipped: Mock/test setup issue")
                else:
                    print(f"  ❓ No fix pattern matched")
                skipped_count += 1
        
        print("\n" + "=" * 60)
        print(f"📝 Summary:")
        print(f"  Total failures: {len(failed_tests)}")
        print(f"  Fixes generated: {len(self.fixes)}")
        print(f"  Skipped: {skipped_count}")
        
        # Save fixes
        self.save_fixes()
    
    def save_fixes(self) -> None:
        """Save generated fixes to file"""
        if self.fixes:
            with open('generated_fixes.json', 'w') as f:
                json.dump(self.fixes, f, indent=2)
            
            print(f"\n✅ Saved {len(self.fixes)} fixes to generated_fixes.json")
            
            # Create summary for PR
            summary = {
                'total_tests': len(self.test_results.get('tests', [])),
                'failed_tests': len([t for t in self.test_results.get('tests', []) 
                                   if t.get('outcome') == 'failed']),
                'fixes_generated': len(self.fixes),
                'fix_types': {}
            }
            
            for fix in self.fixes:
                fix_type = fix['type']
                summary['fix_types'][fix_type] = summary['fix_types'].get(fix_type, 0) + 1
            
            with open('fix_summary.json', 'w') as f:
                json.dump(summary, f, indent=2)
            
            print("✅ Created fix_summary.json")
            
            # Display fix type breakdown
            print("\n📊 Fix Types Generated:")
            for fix_type, count in summary['fix_types'].items():
                print(f"  - {fix_type}: {count}")
        else:
            print("\n⚠️ No fixes were generated")
            
            # Create empty files so the workflow doesn't fail
            with open('generated_fixes.json', 'w') as f:
                json.dump([], f)
            
            with open('fix_summary.json', 'w') as f:
                json.dump({'fixes_generated': 0}, f)


if __name__ == "__main__":
    print("🔍 Refiloe Auto-Fix Generator v2.0")
    print("=" * 60)
    
    generator = ImprovedAutoFixGenerator()
    generator.process_all_failures()
    
    print("\n✅ Fix generation complete!")
