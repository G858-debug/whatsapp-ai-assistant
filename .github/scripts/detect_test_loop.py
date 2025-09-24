#!/usr/bin/env python3
"""Loop detection script - prevents infinite auto-fix loops"""

import json
import hashlib
import sys
from pathlib import Path

def get_failure_signature():
    """Generate a signature from failed tests"""
    try:
        with open('test-results.json', 'r') as f:
            data = json.load(f)
        
        failed_tests = sorted([
            t['nodeid'] for t in data.get('tests', [])
            if t.get('outcome') == 'failed'
        ])
        
        if not failed_tests:
            return None, []
        
        signature = hashlib.md5(''.join(failed_tests).encode()).hexdigest()[:10]
        return signature, failed_tests
    except Exception as e:
        print(f"Error: {e}")
        return None, []

def main():
    current_sig, failed_tests = get_failure_signature()
    
    if not current_sig:
        print("No failures found")
        sys.exit(0)
    
    print(f"Signature: {current_sig}, Failed: {len(failed_tests)}")
    
    history_dir = Path('.test-history')
    history_dir.mkdir(exist_ok=True)
    
    sig_file = history_dir / 'last-signature.txt'
    loop_count_file = history_dir / 'loop-count.txt'
    
    loop_count = 0
    if sig_file.exists():
        last_sig = sig_file.read_text().strip()
        if last_sig == current_sig:
            if loop_count_file.exists():
                loop_count = int(loop_count_file.read_text().strip())
            loop_count += 1
            loop_count_file.write_text(str(loop_count))
            
            if loop_count >= 3:
                print(f"🔄 LOOP DETECTED! Same failures recurring (signature: {current_sig}...)")
                print("The same tests are failing with identical errors.")
                print("Manual intervention required to fix the root cause.")
                print("Repeatedly failing tests:")
                for test in failed_tests[:10]:
                    print(f" - {test}")
                sys.exit(1)
            else:
                print(f"Attempt {loop_count} of 2")
                sys.exit(0)
        else:
            loop_count_file.write_text('0')
    else:
        loop_count_file.write_text('0')
    
    sig_file.write_text(current_sig)
    sys.exit(0)

if __name__ == "__main__":
    if not sys.stdin.isatty():
        sys.exit(0)  # Compatibility mode
    else:
        main()
