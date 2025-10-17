#!/usr/bin/env python3
"""
Clear test trainer record for testing flows
"""

def clear_test_trainer():
    """Clear the test trainer record"""
    try:
        from app import app
        
        with app.app_context():
            db = app.config['supabase']
            
            # Delete test trainer
            result = db.table('trainers').delete().eq('whatsapp', '+27730564882').execute()
            
            if result.data:
                print(f"✅ Deleted {len(result.data)} test trainer record(s)")
            else:
                print("ℹ️  No test trainer records found to delete")
                
            # Also clear registration states
            state_result = db.table('registration_states').delete().eq('phone_number', '+27730564882').execute()
            
            if state_result.data:
                print(f"✅ Deleted {len(state_result.data)} registration state record(s)")
            else:
                print("ℹ️  No registration state records found to delete")
                
            print("\n🧪 Test trainer cleared - ready for fresh flow testing!")
            
    except Exception as e:
        print(f"❌ Error clearing test trainer: {str(e)}")

if __name__ == "__main__":
    print("🧹 Clearing test trainer record...\n")
    clear_test_trainer()