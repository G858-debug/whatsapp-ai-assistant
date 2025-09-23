#!/usr/bin/env python3
# fix_test_issues.py

import os
import re

def fix_phone_plus_prefix():
    """Remove the + prefix from phone number formatting"""
    
    # Fix utils/validators.py
    filepath = 'utils/validators.py'
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Find and replace the line that adds +
        content = re.sub(
            r'return True, f"\+27\{phone_digits\[1:\]\}", None',
            'return True, f"27{phone_digits[1:]}", None',
            content
        )
        
        # Also check for any other + prefix additions
        content = re.sub(
            r'f"\+27\{',
            'f"27{',
            content
        )
        
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Fixed + prefix in {filepath}")
    
    # Check and fix any other files that might add +
    other_files = [
        'utils/input_sanitizer.py',
        'services/whatsapp.py',
        'services/helpers/validation_helpers.py'
    ]
    
    for filepath in other_files:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                original_content = content = f.read()
            
            # Remove any + prefix additions
            content = re.sub(r'return\s+["\']?\+["\']?\s*\+\s*', 'return ', content)
            content = re.sub(r'f["\']?\+\{', 'f"{', content)
            content = re.sub(r'"\+"\s*\+', '', content)
            
            if content != original_content:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"✅ Fixed + prefix in {filepath}")

def fix_test_imports():
    """Fix incorrect import paths in tests"""
    test_files = [
        'tests/test_phase1_registration.py',
        'tests/test_refiloe_complete.py'
    ]
    
    for filepath in test_files:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                original_content = content = f.read()
            
            # Fix import paths
            content = content.replace(
                "'services.refiloe.AIIntentHandler'",
                "'services.ai_intent_handler.AIIntentHandler'"
            )
            
            if content != original_content:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"✅ Fixed imports in {filepath}")

def show_current_issues():
    """Show where + is being added"""
    print("\n🔍 Checking for + prefix issues...")
    
    # Look for the specific line in validators.py
    if os.path.exists('utils/validators.py'):
        with open('utils/validators.py', 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if '+27' in line and 'return' in line:
                    print(f"  Found + prefix at utils/validators.py:{i}")
                    print(f"  Line: {line.strip()}")

if __name__ == "__main__":
    print("🔧 Starting fixes...\n")
    
    # Show current issues
    show_current_issues()
    
    # Apply fixes
    print("\n📝 Applying fixes...")
    fix_phone_plus_prefix()
    fix_test_imports()
    
    print("\n✨ Done! Now run your tests to see if they pass:")
    print("  pytest tests/test_phase2_client_management.py::TestAddClientReal::test_phone_number_normalization -xvs")
