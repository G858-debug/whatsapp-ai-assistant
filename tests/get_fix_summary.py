#!/usr/bin/env python3
"""
Get a one-line summary of fixes for commit message
"""

import json


def get_fix_summary():
    """Generate one-line fix summary"""
    
    try:
        with open('fix_summary.json', 'r') as f:
            summary = json.load(f)
        
        fixes = summary.get('applied_fixes', [])
        if not fixes:
            print("No fixes applied")
            return
        
        # Count fix types
        fix_types = {}
        for fix in fixes:
            fix_type = fix['type']
            fix_types[fix_type] = fix_types.get(fix_type, 0) + 1
        
        # Generate summary
        parts = []
        if 'currency_parsing' in fix_types:
            parts.append("Fix currency parsing")
        if 'phone_format' in fix_types:
            parts.append("Fix phone normalization")
        if 'trainer_recognition' in fix_types:
            parts.append("Fix trainer recognition")
        if 'client_registration' in fix_types:
            parts.append("Fix client welcome message")
        if 'duplicate_check' in fix_types:
            parts.append("Add duplicate registration check")
        if 'input_validation' in fix_types:
            parts.append("Add input length validation")
        if 'ai_intent' in fix_types:
            parts.append("Improve AI command recognition")
        if 'missing_method' in fix_types:
            parts.append("Add missing validation methods")
        if 'mock_database_fix' in fix_types:
            parts.append("Fix mock database issues")
        if 'mock_list_fix' in fix_types:
            parts.append("Fix mock list handling")
        if 'mock_dict_fix' in fix_types:
            parts.append("Fix mock dict handling")
        
        if parts:
            print(", ".join(parts[:3]))  # Limit to first 3 for commit message
        else:
            print(f"Fixed {len(fixes)} test issues")
    
    except Exception as e:
        print("Applied automated fixes")


if __name__ == "__main__":
    get_fix_summary()
