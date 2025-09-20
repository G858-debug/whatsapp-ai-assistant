#!/usr/bin/env python3
"""
Clean up test data from Supabase after tests
"""

import os
from supabase import create_client, Client
from datetime import datetime, timedelta
import pytz


class TestDataCleaner:
    """Clean up test data from Supabase"""
    
    def __init__(self):
        url = os.environ.get('SUPABASE_URL')
        key = os.environ.get('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            print("Supabase credentials not found")
            self.db = None
        else:
            self.db = create_client(url, key)
        
        self.test_phone = os.environ.get('TEST_PHONE', '27731863036')
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def clean_test_trainers(self):
        """Remove test trainers"""
        
        if not self.db:
            return
        
        try:
            # Delete trainers with test phone or test emails
            self.db.table('trainers').delete().or_(
                f"whatsapp.eq.{self.test_phone}",
                "email.like.%test@test.com%",
                "name.like.Test Trainer%"
            ).execute()
            
            print("✅ Cleaned test trainers")
        
        except Exception as e:
            print(f"Error cleaning trainers: {str(e)}")
    
    def clean_test_clients(self):
        """Remove test clients"""
        
        if not self.db:
            return
        
        try:
            # Delete test clients
            test_phones = [
                '27821234567', '27831234567', '27841234567',
                '27851234567', '27861234567'
            ]
            
            for phone in test_phones:
                self.db.table('clients').delete().eq('whatsapp', phone).execute()
            
            # Also delete clients with test names
            self.db.table('clients').delete().or_(
                "name.like.Test Client%",
                "name.eq.Sarah",
                "name.eq.John",
                "name.eq.Mike",
                "name.eq.Mary Jones",
                "name.eq.Peter"
            ).execute()
            
            print("✅ Cleaned test clients")
        
        except Exception as e:
            print(f"Error cleaning clients: {str(e)}")
    
    def clean_test_bookings(self):
        """Remove test bookings"""
        
        if not self.db:
            return
        
        try:
            # Get test trainer IDs
            trainers = self.db.table('trainers').select('id').or_(
                f"whatsapp.eq.{self.test_phone}",
                "name.like.Test Trainer%"
            ).execute()
            
            if trainers.data:
                trainer_ids = [t['id'] for t in trainers.data]
                
                for trainer_id in trainer_ids:
                    self.db.table('bookings').delete().eq(
                        'trainer_id', trainer_id
                    ).execute()
            
            print("✅ Cleaned test bookings")
        
        except Exception as e:
            print(f"Error cleaning bookings: {str(e)}")
    
    def clean_registration_states(self):
        """Clean up registration states"""
        
        if not self.db:
            return
        
        try:
            # Delete test registration states
            self.db.table('registration_states').delete().or_(
                f"phone_number.eq.{self.test_phone}",
                "phone_number.like.2782123%",
                "phone_number.like.2783123%"
            ).execute()
            
            print("✅ Cleaned registration states")
        
        except Exception as e:
            print(f"Error cleaning registration states: {str(e)}")
    
    def clean_conversation_states(self):
        """Clean up conversation states"""
        
        if not self.db:
            return
        
        try:
            # Delete test conversation states
            self.db.table('conversation_states').delete().or_(
                f"phone_number.eq.{self.test_phone}",
                "phone_number.like.2782123%",
                "phone_number.like.2783123%"
            ).execute()
            
            print("✅ Cleaned conversation states")
        
        except Exception as e:
            print(f"Error cleaning conversation states: {str(e)}")
    
    def clean_all(self):
        """Clean all test data"""
        
        print("🧹 Cleaning up test data...")
        
        if not self.db:
            print("⚠️  Skipping cleanup - no database connection")
            return
        
        # Clean in order (due to foreign key constraints)
        self.clean_test_bookings()
        self.clean_test_clients()
        self.clean_test_trainers()
        self.clean_registration_states()
        self.clean_conversation_states()
        
        print("✅ All test data cleaned")


if __name__ == "__main__":
    cleaner = TestDataCleaner()
    cleaner.clean_all()
