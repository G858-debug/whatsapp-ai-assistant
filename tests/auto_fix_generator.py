#!/usr/bin/env python3
"""Auto-Fix Generator - Fixed version"""

import json
import re
from typing import Dict, List, Optional

class AutoFixGenerator:
    def __init__(self):
        self.test_results = self.load_test_results()
        self.fixes = []
    
    def load_test_results(self) -> Dict:
        try:
            with open('test-results.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading results: {e}")
            return {}
    
    def analyze_failure(self, test: Dict) -> Optional[Dict]:
        test_name = test.get('nodeid', '')
        error_msg = str(test.get('call', {}).get('longrepr', ''))
        
        # Skip pure mock issues
        if 'MagicMock' in error_msg or 'Mock object' in error_msg:
            print(f"  → Skipping mock issue in {test_name[:50]}")
            return None
        
        # Real issues to fix
        if 'currency' in error_msg.lower() or 'pricing' in error_msg.lower():
            return {
                'type': 'currency_parsing',
                'file': 'services/registration/trainer_registration.py',
                'test': test_name,
                'diagnosis': 'Currency parsing needed'
            }
        
        if 'phone' in error_msg.lower() or '+27' in error_msg:
            return {
                'type': 'phone_format', 
                'file': 'utils/validators.py',
                'test': test_name,
                'diagnosis': 'Phone format issue'
            }
        
        return None
    
    def process_all_failures(self):
        if not self.test_results:
            print("No test results found")
            return
        
        failed_tests = [
            t for t in self.test_results.get('tests', [])
            if t.get('outcome') == 'failed'
        ]
        
        print(f"Analyzing {len(failed_tests)} failures...")
        
        for test in failed_tests:
            fix = self.analyze_failure(test)
            if fix:
                # Avoid duplicates
                key = f"{fix['type']}_{fix['file']}"
                if not any(f['type'] == fix['type'] and f['file'] == fix['file'] for f in self.fixes):
                    self.fixes.append(fix)
                    print(f"  ✅ Generated {fix['type']} fix")
        
        self.save_fixes()
    
    def save_fixes(self):
        with open('generated_fixes.json', 'w') as f:
            json.dump(self.fixes, f, indent=2)
        print(f"Saved {len(self.fixes)} fixes")
        
        with open('fix_summary.json', 'w') as f:
            json.dump({
                'total_tests': len(self.test_results.get('tests', [])),
                'failed_tests': len([t for t in self.test_results.get('tests', []) if t.get('outcome') == 'failed']),
                'fixes_generated': len(self.fixes)
            }, f, indent=2)

if __name__ == "__main__":
    generator = AutoFixGenerator()
    generator.process_all_failures()
