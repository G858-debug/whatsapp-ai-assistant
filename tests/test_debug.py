# tests/test_debug.py
"""
Debug test to find out why tests are failing in GitHub Actions
This will help identify import issues
"""

import sys
import os

def test_python_version():
    """Check Python version"""
    print(f"Python version: {sys.version}")
    assert sys.version_info >= (3, 8), "Python 3.8+ required"

def test_can_import_basic_modules():
    """Test basic imports work"""
    try:
        import pytest
        print("✅ pytest imported successfully")
    except ImportError as e:
        print(f"❌ pytest import failed: {e}")
        
    try:
        import json
        print("✅ json imported successfully")
    except ImportError as e:
        print(f"❌ json import failed: {e}")

def test_project_structure():
    """Check if project files exist"""
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    print(f"Directory contents: {os.listdir(current_dir)}")
    
    # Check if services directory exists
    if os.path.exists('services'):
        print("✅ services/ directory exists")
        print(f"   Contents: {os.listdir('services')[:5]}...")  # First 5 files
    else:
        print("❌ services/ directory not found")
    
    # Check if utils directory exists
    if os.path.exists('utils'):
        print("✅ utils/ directory exists")
        print(f"   Contents: {os.listdir('utils')[:5]}...")
    else:
        print("❌ utils/ directory not found")

def test_can_import_refiloe_modules():
    """Try to import Refiloe modules"""
    import_results = []
    
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    modules_to_test = [
        'services.refiloe',
        'services.ai_intent_handler',
        'services.registration.trainer_registration',
        'utils.logger',
        'config'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} imported successfully")
            import_results.append((module, True))
        except ImportError as e:
            print(f"❌ {module} import failed: {e}")
            import_results.append((module, False))
        except Exception as e:
            print(f"❌ {module} failed with: {type(e).__name__}: {e}")
            import_results.append((module, False))
    
    # Check if any imports failed
    failed = [m for m, success in import_results if not success]
    if failed:
        print(f"\n⚠️ Failed imports: {failed}")
        print("\nThis is likely because:")
        print("1. Missing __init__.py files in directories")
        print("2. Missing dependencies in requirements.txt")
        print("3. Circular imports in the code")

def test_check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        'flask',
        'supabase',
        'anthropic',
        'pytz',
        'requests'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")

if __name__ == "__main__":
    print("=" * 60)
    print("DEBUG TEST - Finding why tests fail")
    print("=" * 60)
    
    test_python_version()
    print()
    test_can_import_basic_modules()
    print()
    test_project_structure()
    print()
    test_can_import_refiloe_modules()
    print()
    test_check_requirements()
    
    print("\nDebug test complete!")
