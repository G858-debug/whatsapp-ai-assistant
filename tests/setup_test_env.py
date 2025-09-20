#!/usr/bin/env python3
"""
Setup test environment before running tests
"""

import os
import sys
from pathlib import Path


def setup_test_environment():
    """Setup test environment"""
    
    print("🔧 Setting up test environment...")
    
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Set test environment variables if not set
    if not os.environ.get('TESTING'):
        os.environ['TESTING'] = 'true'
    
    # Ensure required directories exist
    os.makedirs('tests/fixtures', exist_ok=True)
    os.makedirs('tests/reports', exist_ok=True)
    
    print("✅ Test environment ready")


if __name__ == "__main__":
    setup_test_environment()
