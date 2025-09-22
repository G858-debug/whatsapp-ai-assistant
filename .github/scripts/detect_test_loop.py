#!/usr/bin/env python3
"""
Detect if tests are failing in a loop with the same errors
"""
import hashlib
import json
import sys
from pathlib import Path


def get_failure_signature(test_output):
    """Extract unique signature from test failures"""
    failures = []
    for line in test_output.split('\n'):
        if 'FAILED' in line:
            # Extract just the test name and assertion
            parts = line.split(' - ')
            if len(parts) > 1:
                failures.append(parts[0].strip())
        elif 'assert' in line and '==' in line:
            # Extract assertion failures
            failures.append(line.strip()[:100])  # First 100 chars
    
    # Create hash of sorted failures
    failure_text = '\n'.join(sorted(set(failures)))
    return hashlib.md5(failure_text.encode()).hexdigest()


def main():
    test_output = sys.stdin.read()
    
    if not test_output:
        print("⚠️ No test output to analyze")
        sys.exit(0)
    
    signature = get_failure_signature(test_output)
    
    history_file = Path('.test_failure_history.json')
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    
    # Check if this signature appeared in the last 3 runs
    recent_signatures = history[-3:] if len(history) >= 3 else history
    
    if signature in recent_signatures:
        print(f"🔄 LOOP DETECTED! Same failures recurring (signature: {signature[:8]}...)")
        print("The same tests are failing with identical errors.")
        print("Manual intervention required to fix the root cause.")
        
        # Show which tests are failing repeatedly
        print("\nRepeatedly failing tests:")
        for line in test_output.split('\n'):
            if 'FAILED' in line:
                print(f"  - {line.strip()}")
        
        sys.exit(1)
    
    # Add to history
    history.append(signature)
    history = history[-10:]  # Keep last 10
    history_file.write_text(json.dumps(history, indent=2))
    
    print(f"✅ No loop detected (signature: {signature[:8]}...)")
    print(f"This is occurrence #{len([s for s in history if s == signature])} of this failure pattern")
    sys.exit(0)


if __name__ == "__main__":
    main()
