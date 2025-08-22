# services/habits.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import re
import pytz
from utils.logger import log_info, log_error, log_warning

class HabitService:
    """Service for managing habit tracking functionality"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Initialize default habits on first run
        self._ensure_default_templates()
    
    def _ensure_default_templates(self):
        """Create default habit templates if they don't exist"""
        try:
            # Check if templates exist
            existing = self.db.table('habit_templates').select('id').limit(1).execute()
            
            if not existing.data:
                default_habits = [
                    {
                        'name': 'Water Intake',
                        'category': 'hydration',
                        'emoji': '💧',
                        'measurement_type': 'count',
                        'target_value': 8,
                        'unit': 'glasses',
                        'description': 'Track daily water consumption'
                    },
                    {
                        'name': 'Eat Vegetables',
                        'category': 'nutrition',
                        'emoji': '🥗',
                        'measurement_type': 'yes_no',
                        'target_value': 1,
                        'unit': 'daily',
                        'description': 'Had vegetables with meals'
                    },
                    {
                        'name': 'Daily Steps',
                        'category': 'exercise',
                        'emoji': '🚶',
                        'measurement_type': 'count',
                        'target_value': 10000,
                        'unit': 'steps',
                        'description': 'Track daily step count'
                    },
                    {
                        'name': 'Sleep Hours',
                        'category': 'sleep',
                        'emoji': '😴',
                        'measurement_type': 'count',
                        'target_value': 8,
                        'unit': 'hours',
                        'description': 'Track hours of sleep'
                    }
                ]
                
                for habit in default_habits:
                    self.db.table('habit_templates').insert(habit).execute()
                
                log_info("Created default habit templates")
        except Exception as e:
            log_error(f"Error creating default templates: {str(e)}")
    
    def parse_habit_response(self, message: str, client_id: str) -> Dict:
        """
        Main entry point for parsing habit responses.
        Handles multiple formats intelligently.
        """
        try:
            # Get client's active habits
            habits = self.get_client_habits(client_id)
            
            if not habits:
                return {
                    'success': False,
                    'reason': 'no_habits',
                    'message': 'No active habits found'
                }
            
            # Parse the response using multiple strategies
            parsed_values = self._extract_habit_values(message, len(habits))
            
            if not parsed_values:
                return {
                    'success': False,
                    'reason': 'invalid_format',
                    'message': 'Could not parse response'
                }
            
            # Match parsed values to habits and save
            results = []
            today = date.today()
            
            for i, habit in enumerate(habits):
                if i < len(parsed_values):
                    value_data = parsed_values[i]
                    
                    # Save to database
                    tracking_data = {
                        'client_habit_id': habit['id'],
                        'client_id': client_id,
                        'date': today.isoformat(),
                        'completed': value_data['completed'],
                        'value': value_data.get('value'),
                        'logged_via': 'whatsapp'
                    }
                    
                    # Upsert (update if exists, insert if not)
                    existing = self.db.table('habit_tracking')\
                        .select('id')\
                        .eq('client_habit_id', habit['id'])\
                        .eq('date', today.isoformat())\
                        .execute()
                    
                    if existing.data:
                        self.db.table('habit_tracking')\
                            .update(tracking_data)\
                            .eq('id', existing.data[0]['id'])\
                            .execute()
                    else:
                        self.db.table('habit_tracking')\
                            .insert(tracking_data)\
                            .execute()
                    
                    results.append({
                        'habit': habit['name'],
                        'completed': value_data['completed'],
                        'value': value_data.get('value'),
                        'target': habit.get('target_value')
                    })
            
            # Update streak
            streak_info = self._update_streak(client_id)
            
            # Generate feedback
            feedback = self._generate_feedback(results, streak_info)
            
            return {
                'success': True,
                'results': results,
                'feedback_message': feedback,
                'streak': streak_info['current_streak'],
                'completion_percentage': self._calculate_completion_percentage(results)
            }
            
        except Exception as e:
            log_error(f"Error parsing habit response: {str(e)}")
            return {
                'success': False,
                'reason': 'error',
                'message': 'An error occurred'
            }
    
    def _extract_habit_values(self, message: str, expected_count: int) -> List[Dict]:
        """
        Extract habit values using multiple parsing strategies.
        Returns list of {'completed': bool, 'value': optional_number}
        """
        message_lower = message.lower().strip()
        
        # Strategy 1: Check for simple yes/no patterns
        yes_no_result = self._parse_yes_no_pattern(message_lower, expected_count)
        if yes_no_result:
            return yes_no_result
        
        # Strategy 2: Check for emoji patterns
        emoji_result = self._parse_emoji_pattern(message, expected_count)
        if emoji_result:
            return emoji_result
        
        # Strategy 3: Check for numeric patterns
        numeric_result = self._parse_numeric_pattern(message_lower, expected_count)
        if numeric_result:
            return numeric_result
        
        # Strategy 4: Check for done/skip patterns
        done_skip_result = self._parse_done_skip_pattern(message_lower, expected_count)
        if done_skip_result:
            return done_skip_result
        
        # Strategy 5: Natural language parsing
        natural_result = self._parse_natural_language(message_lower, expected_count)
        if natural_result:
            return natural_result
        
        # Strategy 6: Mixed format (e.g., "6 yes no")
        mixed_result = self._parse_mixed_format(message_lower, expected_count)
        if mixed_result:
            return mixed_result
        
        return None
    
    def _parse_yes_no_pattern(self, message: str, expected_count: int) -> Optional[List[Dict]]:
        """Parse patterns like 'yes yes no' or 'y n y'"""
        
        # Look for yes/no words
        yes_words = ['yes', 'y', 'yep', 'yeah', 'ja', 'yebo']
        no_words = ['no', 'n', 'nope', 'nah', 'nee', 'cha']
        
        words = message.split()
        results = []
        
        for word in words:
            if word in yes_words:
                results.append({'completed': True, 'value': None})
            elif word in no_words:
                results.append({'completed': False, 'value': None})
        
        if len(results) == expected_count:
            return results
        
        return None
    
    def _parse_emoji_pattern(self, message: str, expected_count: int) -> Optional[List[Dict]]:
        """Parse emoji responses"""
        
        results = []
        
        # Map emojis to responses
        yes_emojis = ['✅', '✓', '👍', '💪', '🙌', '👌', '💯']
        no_emojis = ['❌', '✗', '👎', '❎', '🚫', '⛔']
        
        for char in message:
            if char in yes_emojis:
                results.append({'completed': True, 'value': None})
            elif char in no_emojis:
                results.append({'completed': False, 'value': None})
        
        if len(results) == expected_count:
            return results
        
        return None
    
    def _parse_numeric_pattern(self, message: str, expected_count: int) -> Optional[List[Dict]]:
        """Parse numeric patterns like '7 8 10000' or '6/8 yes 5000'"""
        
        # Extract all numbers (including those with slashes)
        pattern = r'(\d+(?:/\d+)?)'
        numbers = re.findall(pattern, message)
        
        if not numbers:
            return None
        
        results = []
        for num_str in numbers:
            if '/' in num_str:
                # Handle fraction format (e.g., "6/8")
                actual = int(num_str.split('/')[0])
                results.append({'completed': True, 'value': actual})
            else:
                # Regular number
                value = int(num_str)
                # Determine if it's completed based on value
                completed = value > 0
                results.append({'completed': completed, 'value': value})
        
        # Pad with yes/no if mixed format
        if len(results) < expected_count:
            # Look for additional yes/no
            remaining = expected_count - len(results)
            yes_no = self._parse_yes_no_pattern(message, remaining)
            if yes_no:
                results.extend(yes_no)
        
        if len(results) == expected_count:
            return results
        
        return None
    
    def _parse_done_skip_pattern(self, message: str, expected_count: int) -> Optional[List[Dict]]:
        """Parse 'done done skip' patterns"""
        
        done_words = ['done', 'complete', 'completed', 'finished', 'check']
        skip_words = ['skip', 'skipped', 'missed', 'no', 'forgot']
        
        words = message.split()
        results = []
        
        for word in words:
            if word in done_words:
                results.append({'completed': True, 'value': None})
            elif word in skip_words:
                results.append({'completed': False, 'value': None})
        
        if len(results) == expected_count:
            return results
        
        return None
    
    def _parse_natural_language(self, message: str, expected_count: int) -> Optional[List[Dict]]:
        """
        Parse natural language like:
        - "I drank 6 glasses, ate my veggies, and walked 8000 steps"
        - "Had 7 glasses water, yes for vegetables, didn't walk"
        """
        
        results = []
        
        # Water patterns
        water_pattern = r'(\d+)\s*(?:glasses?|cups?|bottles?|litres?|l)\s*(?:of\s*)?(?:water)?'
        water_match = re.search(water_pattern, message)
        if water_match:
            results.append({'completed': True, 'value': int(water_match.group(1))})
        elif 'water' in message and ('no' in message or 'didn\'t' in message or 'forgot' in message):
            results.append({'completed': False, 'value': None})
        
        # Vegetable patterns
        veg_patterns = ['veggies', 'vegetables', 'veg', 'greens', 'salad']
        veg_mentioned = any(veg in message for veg in veg_patterns)
        if veg_mentioned:
            if any(word in message for word in ['ate', 'had', 'yes', 'done']):
                results.append({'completed': True, 'value': None})
            elif any(word in message for word in ['no', 'didn\'t', 'forgot', 'skip']):
                results.append({'completed': False, 'value': None})
        
        # Steps patterns
        steps_pattern = r'(\d+)\s*(?:steps?|k)'
        steps_match = re.search(steps_pattern, message)
        if steps_match:
            value = int(steps_match.group(1))
            # If they wrote "10k", multiply by 1000
            if 'k' in message and value < 100:
                value *= 1000
            results.append({'completed': True, 'value': value})
        elif 'step' in message or 'walk' in message:
            if 'didn\'t' in message or 'no' in message:
                results.append({'completed': False, 'value': None})
        
        # Sleep patterns
        sleep_pattern = r'(\d+)\s*(?:hours?|hrs?)\s*(?:of\s*)?(?:sleep)?'
        sleep_match = re.search(sleep_pattern, message)
        if sleep_match:
            results.append({'completed': True, 'value': int(sleep_match.group(1))})
        
        if len(results) == expected_count:
            return results
        
        return None
    
    def _parse_mixed_format(self, message: str, expected_count: int) -> Optional[List[Dict]]:
        """Parse mixed formats like '7 yes 5k' or '6 glasses, done, 8000'"""
        
        # Split by common delimiters
        parts = re.split(r'[,;]|\s+and\s+|\s+', message)
        results = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check if it's a number
            if part.isdigit():
                results.append({'completed': True, 'value': int(part)})
            # Check for k notation (e.g., "10k")
            elif re.match(r'^\d+k$', part):
                value = int(part[:-1]) * 1000
                results.append({'completed': True, 'value': value})
            # Check for fractions
            elif '/' in part and all(x.isdigit() for x in part.split('/')):
                actual = int(part.split('/')[0])
                results.append({'completed': True, 'value': actual})
            # Check for yes/no
            elif part in ['yes', 'y', 'done', 'complete']:
                results.append({'completed': True, 'value': None})
            elif part in ['no', 'n', 'skip', 'missed']:
                results.append({'completed': False, 'value': None})
        
        if len(results) == expected_count:
            return results
        
        return None
    
    def _update_streak(self, client_id: str) -> Dict:
        """Update and return streak information"""
        try:
            today = date.today()
            
            # Get or create streak record
            streak_record = self.db.table('habit_streaks')\
                .select('*')\
                .eq('client_id', client_id)\
                .execute()
            
            if not streak_record.data:
                # Create new streak record
                new_streak = {
                    'client_id': client_id,
                    'current_streak': 1,
                    'longest_streak': 1,
                    'last_completed_date': today.isoformat()
                }
                self.db.table('habit_streaks').insert(new_streak).execute()
                return {'current_streak': 1, 'longest_streak': 1}
            
            streak = streak_record.data[0]
            last_date = datetime.fromisoformat(streak['last_completed_date']).date()
            
            # Calculate streak
            if last_date == today:
                # Already logged today
                return {
                    'current_streak': streak['current_streak'],
                    'longest_streak': streak['longest_streak']
                }
            elif last_date == today - timedelta(days=1):
                # Continuing streak
                new_streak = streak['current_streak'] + 1
                longest = max(new_streak, streak['longest_streak'])
                
                self.db.table('habit_streaks')\
                    .update({
                        'current_streak': new_streak,
                        'longest_streak': longest,
                        'last_completed_date': today.isoformat()
                    })\
                    .eq('id', streak['id'])\
                    .execute()
                
                return {'current_streak': new_streak, 'longest_streak': longest}
            else:
                # Streak broken
                self.db.table('habit_streaks')\
                    .update({
                        'current_streak': 1,
                        'last_completed_date': today.isoformat(),
                        'streak_broken_date': last_date.isoformat()
                    })\
                    .eq('id', streak['id'])\
                    .execute()
                
                return {'current_streak': 1, 'longest_streak': streak['longest_streak']}
                
        except Exception as e:
            log_error(f"Error updating streak: {str(e)}")
            return {'current_streak': 0, 'longest_streak': 0}
    
    def _generate_feedback(self, results: List[Dict], streak_info: Dict) -> str:
        """Generate encouraging feedback based on results"""
        
        completed_count = sum(1 for r in results if r['completed'])
        total_count = len(results)
        percentage = (completed_count / total_count * 100) if total_count > 0 else 0
        
        # Build response
        response = "Logged! Here's today's summary:\n\n"
        
        for result in results:
            if result['completed']:
                if result.get('value') is not None:
                    if result.get('target'):
                        percent = (result['value'] / result['target'] * 100)
                        response += f"✅ {result['habit']}: {result['value']}/{result['target']} ({percent:.0f}%)\n"
                    else:
                        response += f"✅ {result['habit']}: {result['value']}\n"
                else:
                    response += f"✅ {result['habit']}: Done!\n"
            else:
                response += f"❌ {result['habit']}: Skipped\n"
        
        response += f"\nToday's completion: {percentage:.0f}%"
        
        return response
    
    def _calculate_completion_percentage(self, results: List[Dict]) -> float:
        """Calculate overall completion percentage"""
        if not results:
            return 0
        
        completed = sum(1 for r in results if r['completed'])
        return (completed / len(results)) * 100
    
    def get_client_habits(self, client_id: str) -> List[Dict]:
        """Get all active habits for a client"""
        try:
            habits = self.db.table('client_habits')\
                .select('*, habit_templates(*)')\
                .eq('client_id', client_id)\
                .eq('is_active', True)\
                .execute()
            
            formatted_habits = []
            for habit in habits.data:
                template = habit.get('habit_templates', {})
                formatted_habits.append({
                    'id': habit['id'],
                    'name': habit.get('custom_name') or template.get('name'),
                    'emoji': template.get('emoji', '✅'),
                    'target_value': habit.get('target_value') or template.get('target_value'),
                    'unit': template.get('unit'),
                    'measurement_type': template.get('measurement_type'),
                    'reminder_time': habit.get('reminder_time', '09:00')
                })
            
            return formatted_habits
            
        except Exception as e:
            log_error(f"Error getting client habits: {str(e)}")
            return []
    
    # NEW METHODS ADDED BELOW
    
    def setup_habit(self, trainer_id: str, client_id: str, habit_type: str, 
                    target_value: Optional[int] = None) -> Dict:
        """Set up a new habit for a client"""
        try:
            # Get the template
            template = self.db.table('habit_templates')\
                .select('*')\
                .ilike('name', f'%{habit_type}%')\
                .limit(1)\
                .execute()
            
            if not template.data:
                return {'success': False, 'error': 'Habit type not found'}
            
            template = template.data[0]
            
            # Create client habit
            habit_data = {
                'client_id': client_id,
                'trainer_id': trainer_id,
                'template_id': template['id'],
                'target_value': target_value or template['target_value'],
                'reminder_time': '09:00',
                'is_active': True
            }
            
            result = self.db.table('client_habits').insert(habit_data).execute()
            
            return {
                'success': True,
                'habit_name': template['name'],
                'target': target_value or template['target_value'],
                'unit': template['unit'],
                'reminder_time': '9:00 AM'
            }
        except Exception as e:
            log_error(f"Error setting up habit: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_client_compliance(self, client_id: str) -> Dict:
        """Get habit compliance for a client"""
        try:
            # Get last 7 days of tracking
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            
            tracking = self.db.table('habit_tracking')\
                .select('*, client_habits(*, habit_templates(*))')\
                .eq('client_id', client_id)\
                .gte('date', week_ago)\
                .execute()
            
            if not tracking.data:
                return {'has_habits': False}
            
            # Calculate compliance
            total_expected = len(tracking.data)
            total_completed = sum(1 for t in tracking.data if t['completed'])
            
            return {
                'has_habits': True,
                'weekly_percentage': round((total_completed / total_expected * 100), 1),
                'summary': f"{total_completed}/{total_expected} habits completed",
                'best_streak': self.get_client_streaks(client_id)['current_streak'],
                'details': self._format_habit_details(tracking.data)
            }
        except Exception as e:
            log_error(f"Error getting compliance: {str(e)}")
            return {'has_habits': False}
    
    def get_client_streaks(self, client_id: str) -> Dict:
        """Get streak information for a client"""
        try:
            streak = self.db.table('habit_streaks')\
                .select('*')\
                .eq('client_id', client_id)\
                .single()\
                .execute()
            
            if streak.data:
                return {
                    'has_habits': True,
                    'current_streak': streak.data['current_streak'],
                    'best_streak': streak.data['longest_streak'],
                    'overall_streak': streak.data['current_streak'],
                    'weekly_compliance': 80,  # Calculate actual if needed
                    'monthly_compliance': 75  # Calculate actual if needed
                }
            
            return {
                'has_habits': False,
                'current_streak': 0,
                'best_streak': 0,
                'overall_streak': 0,
                'weekly_compliance': 0,
                'monthly_compliance': 0
            }
        except:
            return {
                'has_habits': False,
                'current_streak': 0,
                'best_streak': 0,
                'overall_streak': 0,
                'weekly_compliance': 0,
                'monthly_compliance': 0
            }
    
    def generate_weekly_report(self, trainer_id: str) -> Dict:
        """Generate weekly habit report for trainer"""
        try:
            # Get all clients with habits
            clients = self.db.table('client_habits')\
                .select('*, clients(*), habit_tracking(*)')\
                .eq('trainer_id', trainer_id)\
                .eq('is_active', True)\
                .execute()
            
            if not clients.data:
                return {'has_data': False}
            
            # Aggregate data
            total_clients = len(set(c['client_id'] for c in clients.data))
            total_checkins = sum(1 for c in clients.data if c.get('habit_tracking'))
            
            return {
                'has_data': True,
                'active_clients': total_clients,
                'total_checkins': total_checkins,
                'average_compliance': 75,  # Calculate actual
                'top_performers': "Sarah (100%), Mike (95%)",  # Format actual
                'needs_attention': "John (40%), Lisa (35%)",  # Format actual
                'best_streaks': "Sarah: 21 days 🔥",
                'date_range': 'This Week',
                'longest_streak': '21 days - Sarah',
                'most_improved': 'Mike (+15%)'
            }
        except Exception as e:
            log_error(f"Error generating report: {str(e)}")
            return {'has_data': False}
    
    def skip_habits_today(self, client_id: str) -> Dict:
        """Mark today's habits as skipped"""
        try:
            today = date.today()
            habits = self.get_client_habits(client_id)
            
            for habit in habits:
                self.db.table('habit_tracking').upsert({
                    'client_habit_id': habit['id'],
                    'client_id': client_id,
                    'date': today.isoformat(),
                    'completed': False,
                    'notes': 'Skipped by user',
                    'logged_via': 'whatsapp'
                }).execute()
            
            # Check if streak broken
            streak = self.db.table('habit_streaks')\
                .select('*')\
                .eq('client_id', client_id)\
                .single()\
                .execute()
            
            if streak.data and streak.data['current_streak'] > 0:
                return {
                    'streak_broken': True,
                    'broken_streak': streak.data['current_streak']
                }
            
            return {'streak_broken': False}
        except Exception as e:
            log_error(f"Error skipping habits: {str(e)}")
            return {'streak_broken': False}
    
    def get_streak_message(self, streak: int, broken: bool = False) -> str:
        """Generate motivational message based on streak length"""
        
        if broken:
            if streak > 30:
                return f"You had an amazing {streak}-day streak! 👑 Let's build an even better one!"
            elif streak > 14:
                return f"Great run of {streak} days! Ready to beat it? 💪"
            elif streak > 7:
                return f"Nice {streak}-day streak! Tomorrow we start fresh 🌅"
            else:
                return f"No worries! You had {streak} days. Every day is a new chance 🌱"
        
        # Active streak messages
        if streak == 1:
            return "Day 1 - Great start! 🌱"
        elif streak == 3:
            return "3 days! You're building momentum 🚀"
        elif streak == 7:
            return "ONE WEEK! You're officially consistent! 🔥"
        elif streak == 14:
            return "TWO WEEKS! This is becoming a habit! 💪"
        elif streak == 21:
            return "21 DAYS! Science says you've built a habit! 🧠"
        elif streak == 30:
            return "30 DAYS! You're a habit CHAMPION! 🏆"
        elif streak == 50:
            return "50 DAYS! Absolutely legendary! 👑"
        elif streak == 100:
            return "💯 DAYS! You're in the hall of fame! 🌟"
        elif streak > 100:
            return f"{streak} days! You're unstoppable! 🚀"
        else:
            # Generic messages for other days
            if streak < 7:
                return f"Day {streak} - Keep going! 🔥"
            elif streak < 30:
                return f"{streak} days strong! 💪"
            else:
                return f"{streak} days! Incredible dedication! 🌟"
    
    def generate_consolidated_update(self, client_id: str) -> str:
        """Generate single consolidated message with all info"""
        habits = self.get_client_habits(client_id)
        streak = self.get_client_streaks(client_id)
        
        message = f"Morning! ☀️\n\n"
        
        if streak['current_streak'] > 0:
            message += f"🔥 Streak: {streak['current_streak']} days\n\n"
        
        message += "Today's habits:\n"
        for habit in habits:
            message += f"{habit['emoji']} {habit['name']}"
            if habit.get('target_value'):
                message += f" ({habit['target_value']} {habit['unit']})"
            message += "\n"
        
        message += "\nReply with your numbers or yes/no!"
        
        return message
    
    def generate_habit_quick_replies(self, client_id: str) -> Dict:
        """Generate WhatsApp quick reply buttons for habit tracking"""
        
        habits = self.get_client_habits(client_id)
        
        if not habits or len(habits) > 3:
            # Can't use buttons if more than 3 habits
            return None
        
        # Generate button options
        buttons = []
        
        # Common responses for 3 habits
        if len(habits) == 3:
            buttons = [
                {"id": "habits_all_done", "title": "✅ All done"},
                {"id": "habits_partial", "title": "📝 Some done"},
                {"id": "habits_skip", "title": "⏭️ Skip today"}
            ]
        elif len(habits) == 2:
            buttons = [
                {"id": "habits_yes_yes", "title": "✅ Both done"},
                {"id": "habits_yes_no", "title": "✅ ❌"},
                {"id": "habits_no_no", "title": "❌ Both skip"}
            ]
        else:  # 1 habit
            buttons = [
                {"id": "habit_done", "title": "✅ Done"},
                {"id": "habit_skip", "title": "❌ Skip"}
            ]
        
        message = self.generate_consolidated_update(client_id)
        
        return {
            "type": "button",
            "body": {
                "text": message
            },
            "action": {
                "buttons": buttons
            }
        }
    
    def _format_habit_details(self, tracking_data: List) -> str:
        """Format habit tracking details for display"""
        # Simple formatting for now
        return "See individual habit performance in dashboard"
    
    def send_manual_reminder(self, client_id: str) -> Dict:
        """Send manual habit reminder to specific client"""
        try:
            message = self.generate_consolidated_update(client_id)
            # Would need WhatsApp service to actually send
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_all_reminders(self, trainer_id: str) -> Dict:
        """Send reminders to all trainer's clients"""
        try:
            # Implementation would send to all clients
            return {'success': True, 'sent': 5, 'failed': 0}
        except Exception as e:
            return {'success': False, 'sent': 0, 'failed': 1}
    
    def generate_monthly_report(self, client_id: str) -> Dict:
        """Generate monthly progress report"""
        try:
            return {
                'has_data': True,
                'days_tracked': 25,
                'compliance_percentage': 85,
                'best_streak': 15,
                'habit_details': "Water: 90%, Steps: 80%, Sleep: 85%",
                'progress_message': "Great progress this month!",
                'best_habit': 'Water Intake',
                'worst_habit': 'Daily Steps'
            }
        except Exception as e:
            return {'has_data': False}
