import re
import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pytz

from utils.logger import log_error, log_info

class WorkoutService:
    """Handle workout program generation and delivery"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Exercise patterns for parsing
        self.exercise_patterns = {
            'sets_reps': [
                r'(\d+)\s*sets?\s*(?:of\s*)?(\d+)\s*reps?',  # "3 sets of 12 reps"
                r'(\d+)\s*x\s*(\d+)',  # "3x12"
                r'(\d+)\s*sets?\s*x\s*(\d+)',  # "3 sets x 12"
            ],
            'pyramid': r'pyramid\s*(?:sets?)?\s*\(?([\d,;\s]+)\)?',  # "pyramid (12,10,8)"
            'superset': r'superset|super\s*set',
            'max_reps': r'max\s*reps?\s*(\d+)?',
            'to_failure': r'to\s*failure|until\s*failure',
            'time_based': r'(\d+)\s*(?:-\s*(\d+))?\s*seconds?|mins?|minutes?'
        }
    
    def parse_workout_text(self, text: str) -> List[Dict]:
        """Parse natural language workout into structured format"""
        exercises = []
        
        # First, split by newlines to get lines
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip lines that are just headers or instructions
            if any(word in line.lower() for word in ['workout', 'program', 'day', 'week']) and len(line.split()) <= 3:
                continue
                
            # Handle warm-up and cooldown lines
            if any(word in line.lower() for word in ['warm up', 'warm-up', 'warmup', 'cooldown', 'cool down', 'cool-down', 'stretch']):
                exercises.append({
                    'name': line,
                    'type': 'warmup' if 'warm' in line.lower() else 'cooldown',
                    'details': line
                })
                continue
            
            # Check if the line contains multiple exercises separated by commas or semicolons
            # Split by common separators: comma, semicolon, or 'and'
            potential_exercises = []
            
            # First try splitting by commas
            if ',' in line:
                potential_exercises = line.split(',')
            # Then try semicolons
            elif ';' in line:
                potential_exercises = line.split(';')
            # Try splitting by ' and ' (but not 'band' or 'hand')
            elif ' and ' in line.lower():
                # Make sure 'and' is not part of an exercise name
                parts = re.split(r'\s+and\s+', line, flags=re.IGNORECASE)
                # Check if the split makes sense (each part should have numbers)
                if all(any(char.isdigit() for char in part) for part in parts):
                    potential_exercises = parts
                else:
                    potential_exercises = [line]
            else:
                potential_exercises = [line]
            
            # Parse each potential exercise
            for exercise_text in potential_exercises:
                exercise_text = exercise_text.strip()
                if not exercise_text:
                    continue
                
                # Remove leading numbers like "1." or "1)" if present
                exercise_text = re.sub(r'^\d+[\.\)]\s*', '', exercise_text)
                
                # Extract exercise details
                exercise = self.parse_exercise_line(exercise_text)
                if exercise:
                    exercises.append(exercise)
        
        return exercises
    
    def clean_exercise_name(self, name: str) -> str:
        """Clean and standardize exercise name"""
        # Remove numbers and special characters from the beginning
        name = re.sub(r'^\d+\.\s*', '', name)
        name = re.sub(r'^\W+', '', name)
        
        # Remove sets/reps info from name
        name = re.sub(r'\d+\s*(?:sets?|x|reps?).*$', '', name, flags=re.IGNORECASE)
        
        # Title case and clean up
        name = name.strip()
        
        # Standardize common exercise names
        exercise_map = {
            'squats': 'Squats',
            'squat': 'Squats',
            'bench': 'Bench Press',
            'bench press': 'Bench Press',
            'deadlift': 'Deadlifts',
            'deadlifts': 'Deadlifts',
            'pull up': 'Pull-ups',
            'pullup': 'Pull-ups',
            'pull ups': 'Pull-ups',
            'push up': 'Push-ups',
            'pushup': 'Push-ups',
            'push ups': 'Push-ups',
            'leg press': 'Leg Press',
            'leg extension': 'Leg Extensions',
            'leg curl': 'Leg Curls',
            'calf raise': 'Calf Raises',
            'calf raises': 'Calf Raises'
        }
        
        name_lower = name.lower()
        if name_lower in exercise_map:
            return exercise_map[name_lower]
        
        # Title case if not in map
        return ' '.join(word.capitalize() for word in name.split())
    
    # In services/workout.py, replace the find_exercise_gif method with this:

    def find_exercise_gif(self, exercise_name: str, gender: str = 'male') -> str:
        """Find exercise GIF/video from database ONLY - no more Giphy"""
        try:
            if not self.db:
                return "💪"  # Return emoji if no database
            
            # Clean the exercise name for better matching
            exercise_clean = exercise_name.strip().lower()
            
            # Try exact match first
            result = self.db.table('exercises')\
                .select('name, gif_url_male, gif_url_female, gif_url_neutral, instructions')\
                .ilike('name', exercise_clean)\
                .eq('is_active', True)\
                .limit(1)\
                .execute()
            
            # If no exact match, try partial match
            if not result.data:
                result = self.db.table('exercises')\
                    .select('name, gif_url_male, gif_url_female, gif_url_neutral, instructions')\
                    .ilike('name', f'%{exercise_clean}%')\
                    .eq('is_active', True)\
                    .limit(1)\
                    .execute()
            
            if result.data:
                exercise = result.data[0]
                
                # Get the appropriate URL based on gender
                url = None
                if gender == 'female' and exercise.get('gif_url_female'):
                    url = exercise['gif_url_female']
                elif gender == 'male' and exercise.get('gif_url_male'):
                    url = exercise['gif_url_male']
                elif exercise.get('gif_url_neutral'):
                    url = exercise['gif_url_neutral']
                # Fallback to any available URL
                elif exercise.get('gif_url_male'):
                    url = exercise['gif_url_male']
                elif exercise.get('gif_url_female'):
                    url = exercise['gif_url_female']
                
                if url:
                    return url
                elif exercise.get('instructions'):
                    # Return text instructions if no video
                    return f"📝 {exercise['instructions'][:100]}..."
            
            # Exercise not in database - return instructions emoji
            return "💪"
            
        except Exception as e:
            log_error(f"Error finding exercise demo: {str(e)}")
            return "💪"
  
    def parse_exercise_line(self, line: str) -> Dict:
        """Parse a single exercise line into structured format"""
        
        exercise = {}
        line = line.strip()
        
        # Skip lines that are instructions or headers
        skip_phrases = ['create', 'workout', 'for', 'program', 'routine']
        if any(phrase in line.lower() and ':' in line for phrase in skip_phrases):
            return None  # Skip header lines like "Create leg workout for Itumeleng:"
        
        # Remove leading numbers and bullets
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        line = re.sub(r'^[\*\-•]\s*', '', line)
        
        # Pattern 1: Exercise name followed by sets/reps
        # Matches: "Squats 3x12", "Lunges 3 x 10"
        pattern1 = r'^([A-Za-z][A-Za-z\s\-]*?)[\s\-:]+(\d+)\s*[xX×]\s*(\d+)'
        match1 = re.match(pattern1, line)
        
        if match1:
            exercise['name'] = match1.group(1).strip().title()
            exercise['sets'] = int(match1.group(2))
            exercise['reps'] = match1.group(3)
            
            # Check for "each leg", "each arm", etc.
            if any(phrase in line.lower() for phrase in ['each', 'per side', 'per leg', 'per arm']):
                exercise['reps'] += ' each side'
            
            return exercise
        
        # Pattern 2: Sets/reps followed by exercise name
        # Matches: "3x12 Squats"
        pattern2 = r'^(\d+)\s*[xX×]\s*(\d+)\s+([A-Za-z][A-Za-z\s\-]+)'
        match2 = re.match(pattern2, line)
        
        if match2:
            exercise['sets'] = int(match2.group(1))
            exercise['reps'] = match2.group(2)
            exercise['name'] = match2.group(3).strip().title()
            
            if any(phrase in line.lower() for phrase in ['each', 'per side', 'per leg', 'per arm']):
                exercise['reps'] += ' each side'
            
            return exercise
        
        # Pattern 3: "sets of" format
        pattern3 = r'^([A-Za-z][A-Za-z\s\-]*?)[\s\-:]+(\d+)\s*sets?\s*of\s*(\d+)'
        match3 = re.match(pattern3, line, re.IGNORECASE)
        
        if match3:
            exercise['name'] = match3.group(1).strip().title()
            exercise['sets'] = int(match3.group(2))
            exercise['reps'] = match3.group(3)
            
            if any(phrase in line.lower() for phrase in ['each', 'per side', 'per leg', 'per arm']):
                exercise['reps'] += ' each side'
            
            return exercise
        
        # Pattern 4: Time-based exercises
        pattern4 = r'^([A-Za-z][A-Za-z\s\-]*?)[\s\-:]+(\d+)\s*[xX×]\s*(\d+)\s*(seconds?|secs?|minutes?|mins?)'
        match4 = re.match(pattern4, line, re.IGNORECASE)
        
        if match4:
            exercise['name'] = match4.group(1).strip().title()
            exercise['sets'] = int(match4.group(2))
            time_unit = 'seconds' if 'sec' in match4.group(4).lower() else 'minutes'
            exercise['reps'] = f"{match4.group(3)} {time_unit}"
            return exercise
        
        return None
    
    def format_workout_for_whatsapp(self, exercises: List[Dict], client_name: str, 
                                   client_gender: str = 'male') -> str:
        """Format workout for WhatsApp delivery"""
        
        header = f"""🏋️ **WORKOUT PROGRAM** 🏋️
*For:* {client_name}
*Date:* {datetime.now(self.sa_tz).strftime('%d %B %Y')}

━━━━━━━━━━━━━━━━━━━━"""
        
        sections = {
            'warmup': [],
            'main': [],
            'cooldown': []
        }
        
        # Categorize exercises
        for exercise in exercises:
            if exercise.get('type') == 'warmup':
                sections['warmup'].append(exercise)
            elif exercise.get('type') == 'cooldown':
                sections['cooldown'].append(exercise)
            else:
                sections['main'].append(exercise)
        
        # Build message
        message_parts = [header]
        
        # Warm-up section
        if sections['warmup']:
            message_parts.append("\n🔥 *WARM-UP*")
            for ex in sections['warmup']:
                message_parts.append(f"• {ex['details']}")
        
        # Main workout
        if sections['main']:
            message_parts.append("\n💪 *MAIN WORKOUT*")
            for i, exercise in enumerate(sections['main'], 1):
                # Get GIF
                gif = self.find_exercise_gif(exercise['name'], client_gender)
                
                # Format exercise
                ex_text = f"\n*{i}. {exercise['name']}*"
                
                # Add sets and reps
                if exercise.get('sets') and exercise.get('reps'):
                    if isinstance(exercise['reps'], list):  # Pyramid
                        reps_text = ' → '.join(str(r) for r in exercise['reps'])
                        ex_text += f"\n   📊 Pyramid: {reps_text} reps"
                    else:
                        ex_text += f"\n   📊 {exercise['sets']} sets × {exercise['reps']} reps"
                elif exercise.get('original_text'):
                    # Use original text if parsing wasn't perfect
                    details = exercise['original_text'].split('-', 1)
                    if len(details) > 1:
                        ex_text += f"\n   📊 {details[1].strip()}"
                
                # Add special instructions
                if exercise.get('special'):
                    special_text = ', '.join(exercise['special'])
                    ex_text += f"\n   ⚡ {special_text}"
                
                # Add GIF link if it's a URL
                if gif.startswith('http'):
                    ex_text += f"\n   👁️ Demo: {gif}"
                
                message_parts.append(ex_text)
        
        # Cool-down section
        if sections['cooldown']:
            message_parts.append("\n🧘 *COOL-DOWN*")
            for ex in sections['cooldown']:
                message_parts.append(f"• {ex['details']}")
        
        # Footer
        footer = """
━━━━━━━━━━━━━━━━━━━━

💡 *Tips:*
• Rest 60-90 seconds between sets
• Focus on proper form
• Stay hydrated
• Stop if you feel pain

Questions? Reply here! 💬"""
        
        message_parts.append(footer)
        
        return '\n'.join(message_parts)
    
    def save_workout_to_history(self, client_id: str, trainer_id: str, 
                               workout_name: str, exercises: List[Dict]) -> bool:
        """Save workout to history"""
        try:
            if self.db:
                self.db.table('workout_history').insert({
                    'client_id': client_id,
                    'trainer_id': trainer_id,
                    'workout_name': workout_name or 'Custom Workout',
                    'exercises': json.dumps(exercises),
                    'sent_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
                log_info(f"Saved workout to history for client {client_id}")
                return True
                
        except Exception as e:
            log_error(f"Error saving workout: {str(e)}")
            return False
    
    def get_client_preferences(self, client_id: str, muscle_group: str = None) -> Dict:
        """Get client's exercise preferences"""
        try:
            if self.db:
                query = self.db.table('client_exercise_preferences').select('*').eq(
                    'client_id', client_id
                )
                
                if muscle_group:
                    query = query.eq('muscle_group', muscle_group)
                
                result = query.execute()
                
                if result.data:
                    return {
                        'preferred': result.data[0].get('preferred_exercises', []),
                        'avoided': result.data[0].get('avoided_exercises', []),
                        'notes': result.data[0].get('notes', '')
                    }
            
            return {'preferred': [], 'avoided': [], 'notes': ''}
            
        except Exception as e:
            log_error(f"Error getting preferences: {str(e)}")
            return {'preferred': [], 'avoided': [], 'notes': ''}
    
    def generate_ai_workout(self, client_info: Dict, workout_type: str, 
                           trainer_preferences: Dict = None) -> List[Dict]:
        """Generate AI-powered workout based on client history and preferences"""
        # This would integrate with Claude API to generate smart workouts
        # For now, return a template
        
        templates = {
            'legs': [
                {'name': 'Squats', 'sets': 4, 'reps': 12},
                {'name': 'Leg Press', 'sets': 3, 'reps': 15},
                {'name': 'Lunges', 'sets': 3, 'reps': 12},
                {'name': 'Leg Curls', 'sets': 3, 'reps': 15},
                {'name': 'Calf Raises', 'sets': 4, 'reps': 20}
            ],
            'chest': [
                {'name': 'Bench Press', 'sets': 4, 'reps': 10},
                {'name': 'Incline Dumbbell Press', 'sets': 3, 'reps': 12},
                {'name': 'Cable Flyes', 'sets': 3, 'reps': 15},
                {'name': 'Push-ups', 'sets': 3, 'reps': 'failure'}
            ],
            'back': [
                {'name': 'Pull-ups', 'sets': 4, 'reps': 10},
                {'name': 'Bent-Over Rows', 'sets': 4, 'reps': 12},
                {'name': 'Lat Pulldowns', 'sets': 3, 'reps': 12},
                {'name': 'Cable Rows', 'sets': 3, 'reps': 15}
            ]
        }
        
        return templates.get(workout_type, templates['legs'])
