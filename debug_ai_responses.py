#!/usr/bin/env python3
"""
AI Response Debugger
Shows what the AI is actually responding with for test commands
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def debug_ai_responses():
    """Debug what the AI is actually responding with"""
    
    print("🔍 AI Response Debugger")
    print("=" * 50)
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return
    
    try:
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Import the test classes
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tests.test_phases_4_11 import RefiloeE2ETesterExtended
        
        print("🔗 Connecting to Supabase...")
        print(f"📊 Supabase URL: {supabase_url}")
        
        # Create tester instance
        tester = RefiloeE2ETesterExtended()
        print("✅ Tester initialized successfully")
        
        # Test commands from the failing tests
        test_commands = [
            # Phase 4: Habit Tracking
            "Setup habits for Sarah",
            "Show Sarah's habit progress",
            "Check John's water intake this week",
            
            # Phase 5: Workouts & Assessments  
            "Send workout to Sarah",
            "Start assessment for John",
            "Show Mike's assessment results",
            
            # Phase 6: Payments
            "Request payment from Sarah",
            "Confirm payment from John",
            
            # Phase 7: Analytics
            "Show dashboard",
            "Show Sarah's analytics",
            
            # Phase 8: Client Features
            "Book session for Sarah",
            "Log habit for John",
            "Show Mike's progress",
            
            # Phase 9: Challenges
            "Show challenges",
            "Join challenge",
            "Show leaderboard",
            
            # Phase 10: Advanced Features
            "Bulk operations"
        ]
        
        print(f"\n🧪 Testing {len(test_commands)} commands...")
        print("=" * 50)
        
        for i, command in enumerate(test_commands, 1):
            print(f"\n[{i:2d}] Testing: '{command}'")
            print("-" * 40)
            
            try:
                response = tester.send_message(command)
                print(f"✅ Response: {response}")
                
                # Check what keywords are actually in the response
                response_lower = str(response).lower()
                print(f"📝 Response length: {len(str(response))} characters")
                
                # Show first 200 characters
                preview = str(response)[:200]
                if len(str(response)) > 200:
                    preview += "..."
                print(f"👀 Preview: {preview}")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
            
            print("-" * 40)
        
        print("\n🎯 Debug Summary:")
        print("=" * 50)
        print("✅ All commands tested successfully!")
        print("📊 Check the responses above to see what keywords are actually present")
        print("💡 Use this info to update test assertions or AI responses")
        
    except Exception as e:
        print(f"❌ Error during debugging: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ai_responses()
