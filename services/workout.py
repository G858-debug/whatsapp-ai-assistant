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
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip warm-up and stretch lines (we'll handle these separately)
            if any(word in line.lower() for word in ['warm up', 'warm-up', 'cooldown', 'cool down', 'stretch']):
                exercises.append({
                    'name': line,
                    'type': 'warmup' if 'warm' in line.lower() else 'cooldown',
                    'details': line
                })
                continue
            
            # Extract exercise details
            exercise = self.parse_exercise_line(line)
            if exercise:
                exercises.append(exercise)
        
        return exercises
    
    def parse_exercise_line(self, line: str) -> Optional[Dict]:
        """Parse a single exercise line"""
        try:
            # Initialize exercise dict
            exercise = {
                'original_text': line,
                'sets': None,
                'reps': None,
                'special': []
            }
            
            # Split exercise name from details (usually separated by - or :)
            parts = re.split(r'[-–—:]', line, 1)
            exercise_name = parts[0].strip()
            details = parts[1].strip() if len(parts) > 1 else ""
            
            # Clean up exercise name
            exercise['name'] = self.clean_exercise_name(exercise_name)
            
            # If no details, try to parse from the exercise name line
            if not details:
                details = exercise_name
            
            # Parse pyramid sets
            pyramid_match = re.search(self.exercise_patterns['pyramid'], details, re.IGNORECASE)
            if pyramid_match:
                reps_text = pyramid_match.group(1)
                reps = [r.strip() for r in re.split(r'[,;]', reps_text)]
                exercise['sets'] = len(reps)
                exercise['reps'] = reps
                exercise['special'].append('pyramid')
                return exercise
            
            # Parse regular sets and reps
            for pattern in self.exercise_patterns['sets_reps']:
                match = re.search(pattern, details, re.IGNORECASE)
                if match:
                    exercise['sets'] = int(match.group(1))
                    exercise['reps'] = int(match.group(2))
                    break
            
            # Check for special instructions
            if re.search(self.exercise_patterns['superset'], details, re.IGNORECASE):
                exercise['special'].append('superset')
            
            if re.search(self.exercise_patterns['to_failure'], details, re.IGNORECASE):
                exercise['special'].append('to failure')
                if not exercise['reps']:
                    exercise['reps'] = 'failure'
            
            # Parse max reps
            max_reps_match = re.search(self.exercise_patterns['max_reps'], details, re.IGNORECASE)
            if max_reps_match:
                exercise['reps'] = f"max {max_reps_match.group(1) or ''}"
            
            # Parse time-based exercises (like planks)
            time_match = re.search(self.exercise_patterns['time_based'], details, re.IGNORECASE)
            if time_match:
                time_value = time_match.group(1)
                time_value_2 = time_match.group(2) if time_match.group(2) else None
                
                if 'second' in time_match.group(0):
                    unit = 'seconds'
                else:
                    unit = 'minutes'
                
                if time_value_2:
                    exercise['reps'] = f"{time_value}-{time_value_2} {unit}"
                else:
                    exercise['reps'] = f"{time_value} {unit}"
            
            return exercise if exercise['name'] else None
            
        except Exception as e:
            log_error(f"Error parsing exercise line: {line} - {str(e)}")
            return None
    
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
    
    def find_exercise_gif(self, exercise_name: str, gender: str = 'male') -> str:
        """Find appropriate GIF for exercise"""
        try:
            # First, check our database
            if self.db:
                result = self.db.table('exercises').select('*').ilike(
                    'name', f'%{exercise_name}%'
                ).limit(1).execute()
                
                if result.data:
                    exercise = result.data[0]
                    gif_field = f'gif_url_{gender}' if gender in ['male', 'female'] else 'gif_url_male'
                    return exercise.get(gif_field, '') or exercise.get('gif_url_male', '')
            
            # If not in database, search Giphy
            if hasattr(self.config, 'GIPHY_API_KEY') and self.config.GIPHY_API_KEY:
                return self.search_giphy(exercise_name, gender)
            
            # Return placeholder if no GIF found
            return "🏋️" 
            
        except Exception as e:
            log_error(f"Error finding GIF for {exercise_name}: {str(e)}")
            return "💪"
    
    def search_giphy(self, exercise_name: str, gender: str) -> str:
        """Search Giphy for exercise GIF"""
        try:
            api_key = self.config.GIPHY_API_KEY
            search_term = f"{exercise_name} exercise {gender}"
            
            url = f"https://api.giphy.com/v1/gifs/search"
            params = {
                'api_key': api_key,
                'q': search_term,
                'limit': 1,
                'rating': 'g'
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data['data']:
                    # Return the fixed height GIF URL
                    return data['data'][0]['images']['fixed_height']['url']
            
            return "🏋️"
            
        except Exception as e:
            log_error(f"Giphy search error: {str(e)}")
            return "💪"
    
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
