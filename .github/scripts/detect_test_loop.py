#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

def get_failure_signature(test_output):
    """Extract unique signature from test failures"""
    # Extract just the failure messages
    failures = []
    for line in test_output.split('\n'):
        if 'FAILED' in line or 'assert' in line:
            failures.append(line.strip())
    
    # Create hash of failures
    return hashlib.md5('\n'.join(sorted(failures)).encode()).hexdigest()

if __name__ == "__main__":
    test_output = sys.stdin.read()
    signature = get_failure_signature(test_output)
    
    history_file = Path('.test_failure_history.json')
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    
    if signature in history[-3:]:  # Check last 3 runs
        print("🔄 LOOP DETECTED! Same failures recurring.")
        print("Manual intervention required.")
        sys.exit(1)
    
    history.append(signature)
    history = history[-10:]  # Keep last 10
    history_file.write_text(json.dumps(history))
    
    print("✅ No loop detected")
    sys.exit(0)
