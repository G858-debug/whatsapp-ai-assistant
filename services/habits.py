from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
import re
from utils.logger import log_info, log_error

class HabitService:
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        
    def create_default_habits(self):
        """Create the standard habit templates"""
        default_habits = [
            {
                'name': 'Water Intake',
                'category': 'hydration',
                'emoji': '💧',
                'measurement_type': 'count',
                'target_value': 8,
                'unit': 'glasses'
            },
            {
                'name': 'Eat Vegetables',
                'category': 'nutrition',
                'emoji': '🥗',
                'measurement_type': 'yes_no',
                'target_value': 1,
                'unit': 'daily'
            },
            {
                'name': 'Daily Steps',
                'category': 'exercise',
                'emoji': '🚶',
                'measurement_type': 'count',
                'target_value': 10000,
                'unit': 'steps'
            },
            {
                'name': 'Sleep 8 Hours',
                'category': 'sleep',
                'emoji': '😴',
                'measurement_type': 'yes_no',
                'target_value': 1,
                'unit': 'daily'
            }
        ]
        # Add more as needed
        
    def parse_habit_setup(self, message: str, trainer_id: str) -> Dict:
        """Parse trainer's habit setup message"""
        # This will extract:
        # - Client name
        # - Habit type
        # - Target value (if mentioned)
        # Return extracted data
        
    def format_habit_reminder(self, client_id: str) -> str:
        """Generate the daily habit check message"""
        # Get client's active habits
        habits = self.get_client_habits(client_id)
        
        if not habits:
            return None
            
        # Get current streak
        streak = self.get_current_streak(client_id)
        
        # Build message
        message = f"Morning! 🌞 Let's check your habits:\n\n"
        
        for habit in habits:
            message += f"{habit['emoji']} {habit['name']}"
            if habit['measurement_type'] == 'count':
                message += f" ({habit['target_value']} {habit['unit']})"
            message += " - ?\n"
        
        message += f"\nReply with yes/no or numbers!"
        
        if streak > 0:
            message += f"\n🔥 Current streak: {streak} days!"
            
        return message
        
    def parse_habit_response(self, message: str, client_id: str) -> str:
        """Parse and process client's habit check-in"""
        
        # Get today's habits for this client
        habits = self.get_client_habits(client_id)
        
        # Parse the response - handle multiple formats
        responses = self.extract_responses(message, len(habits))
        
        # Save to database
        results = []
        for i, habit in enumerate(habits):
            if i < len(responses):
                self.log_habit(habit['id'], client_id, responses[i])
                results.append(responses[i])
        
        # Generate response
        return self.generate_feedback(habits, results, client_id)
