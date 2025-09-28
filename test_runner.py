#!/usr/bin/env python3
"""
Test Runner Script for WhatsApp AI Assistant
Runs tests and saves results to a file for AI analysis
"""

import subprocess
import sys
import os
from datetime import datetime

def run_tests():
    """Run the phases 4-11 tests and save results"""
    
    print("🧪 Running WhatsApp AI Assistant Tests (Phases 4-11)...")
    print("=" * 60)
    
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Run the tests
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_phases_4_11.py', '-v', '--tb=short'
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f'test_results_{timestamp}.txt'
        
        with open(results_file, 'w', encoding='utf-8') as f:
            f.write("WHATSAPP AI ASSISTANT - TEST RESULTS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Python Version: {sys.version}\n")
            f.write(f"Working Directory: {os.getcwd()}\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write("\n" + "=" * 50 + "\n")
            f.write("STDOUT:\n")
            f.write(result.stdout)
            f.write("\n" + "=" * 50 + "\n")
            f.write("STDERR:\n")
            f.write(result.stderr)
            f.write("\n" + "=" * 50 + "\n")
        
        print(f"✅ Test results saved to: {results_file}")
        print(f"📊 Return code: {result.returncode}")
        
        # Print summary to console
        if result.returncode == 0:
            print("🎉 All tests passed!")
        else:
            print("❌ Some tests failed. Check the results file for details.")
            
        # Show a preview of the results
        print("\n📋 Preview of results:")
        print("-" * 40)
        lines = result.stdout.split('\n')
        for line in lines[-10:]:  # Show last 10 lines
            if line.strip():
                print(line)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Tests timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def run_specific_phase(phase_number):
    """Run tests for a specific phase"""
    
    phase_classes = {
        4: "TestPhase4_HabitTracking",
        5: "TestPhase5_WorkoutsAssessments", 
        6: "TestPhase6_PaymentsRevenue",
        7: "TestPhase7_AnalyticsReports",
        8: "TestPhase8_ClientFeatures",
        9: "TestPhase9_Challenges",
        10: "TestPhase10_AdvancedFeatures",
        11: "TestPhase11_AutomatedFeatures"
    }
    
    if phase_number not in phase_classes:
        print(f"❌ Invalid phase number. Available phases: {list(phase_classes.keys())}")
        return False
    
    phase_class = phase_classes[phase_number]
    print(f"🧪 Running Phase {phase_number}: {phase_class}")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            f'tests/test_phases_4_11.py::{phase_class}', '-v', '--tb=short'
        ], capture_output=True, text=True, timeout=120)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f'test_results_phase_{phase_number}_{timestamp}.txt'
        
        with open(results_file, 'w', encoding='utf-8') as f:
            f.write(f"WHATSAPP AI ASSISTANT - PHASE {phase_number} TEST RESULTS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Phase: {phase_class}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write("\nSTDOUT:\n")
            f.write(result.stdout)
            f.write("\nSTDERR:\n")
            f.write(result.stderr)
        
        print(f"✅ Phase {phase_number} results saved to: {results_file}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running phase {phase_number}: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            phase = int(sys.argv[1])
            success = run_specific_phase(phase)
        except ValueError:
            print("❌ Please provide a valid phase number (4-11)")
            sys.exit(1)
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)
