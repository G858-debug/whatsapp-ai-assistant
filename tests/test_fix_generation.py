#!/usr/bin/env python3
"""Test if fix generation is working"""

import json
import os
import sys

def test_fix_generation():
    """Test that fixes are generated from test results"""
    
    # Check if test results exist
    if not os.path.exists('test-results.json'):
        print("❌ No test-results.json found")
        return False
    
    # Load test results
    with open('test-results.json', 'r') as f:
        results = json.load(f)
    
    failed_count = len([t for t in results.get('tests', []) 
                       if t.get('outcome') == 'failed'])
    
    print(f"Found {failed_count} failed tests")
    
    if failed_count == 0:
        print("✅ No failures to fix")
        return True
    
    # Try to generate fixes
    os.system('python tests/auto_fix_generator.py')
    
    # Check if fixes were generated
    if os.path.exists('generated_fixes.json'):
        with open('generated_fixes.json', 'r') as f:
            fixes = json.load(f)
        
        print(f"✅ Generated {len(fixes)} fixes")
        
        # Show what fixes were generated
        for fix in fixes:
            print(f"  - {fix.get('type')}: {fix.get('file')}")
        
        return len(fixes) > 0
    else:
        print("❌ No fixes generated")
        return False

if __name__ == "__main__":
    success = test_fix_generation()
    sys.exit(0 if success else 1)
