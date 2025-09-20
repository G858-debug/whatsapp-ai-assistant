#!/usr/bin/env python3
"""Test PR generation by creating simple fixes"""

import json
import os

# Create a test-results.json with known failures
test_data = {
    "tests": [
        {
            "nodeid": "test_phone",
            "outcome": "failed",
            "call": {
                "longrepr": "AssertionError: Expected 27821234567 but got +27821234567"
            }
        },
        {
            "nodeid": "test_time",
            "outcome": "failed",
            "call": {
                "longrepr": "AssertionError: Failed to validate time: 9am"
            }
        }
    ]
}

# Save it
with open('test-results.json', 'w') as f:
    json.dump(test_data, f)

print("Created test-results.json")

# Now run the generator
os.system('python tests/auto_fix_generator.py')

# Check if fixes were created
if os.path.exists('generated_fixes.json'):
    with open('generated_fixes.json') as f:
        fixes = json.load(f)
    print(f"✅ Generated {len(fixes)} fixes")
    for fix in fixes:
        print(f"  - {fix['type']}")
else:
    print("❌ No fixes generated")
