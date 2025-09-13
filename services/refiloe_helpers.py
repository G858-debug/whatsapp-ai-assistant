"""Helper functions for Refiloe service - client registration flows"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_error, log_info

class RefiloeHelpers:
    """Helper functions for client registration flows"""
    
    def __init__(self, supabase_client, whatsapp_service, config):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def _handle_client_goal_selection(self, session_id: str, goal: str) -> Dict:
        """Process fitness goal and show training preference buttons"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over by saying "hi"'
                }
            
            # Update session with goal
            session_data = session.data.get('data', {})
            session_data['fitness_goal'] = goal
            
            self.db.table('registration_sessions').update({
                'data': session_data,
                'step': 'training_preference',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            # Create training preference buttons
            buttons = [
                {'id': 'pref_gym', 'title': '🏋️ Gym Training'},
                {'id': 'pref_home', 'title': '🏠 Home Workouts'},
                {'id': 'pref_outdoor', 'title': '🌳 Outdoor'}
            ]
            
            return {
                'success': True,
                'message': f"Great! Your goal is {goal}. 🎯\n\nWhat's your preferred training style?",
                'buttons': buttons,
                'session_id': session_id
            }
            
        except Exception as e:
            log_error(f"Error handling goal selection: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing your goal. Please try again.'
            }
    
    def _handle_client_training_preference(self, session_id: str, preference: str) -> Dict:
        """Process training preference and ask for city"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over by saying "hi"'
                }
            
            # Map preference ID to readable format
            preference_map = {
                'pref_gym': 'Gym Training',
                'pref_home': 'Home Workouts',
                'pref_outdoor': 'Outdoor Training'
            }
            
            # Update session with preference
            session_data = session.data.get('data', {})
            session_data['training_preference'] = preference_map.get(preference, preference)
            
            self.db.table('registration_sessions').update({
                'data': session_data,
                'step': 'city',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return {
                'success': True,
                'message': f"Perfect! You prefer {preference_map.get(preference, preference)}. 💪\n\nWhich city are you in? (e.g., Cape Town, Johannesburg, Durban)",
                'session_id': session_id
            }
            
        except Exception as e:
            log_error(f"Error handling training preference: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing your preference. Please try again.'
            }
    
    def _handle_client_city_input(self, session_id: str, city: str) -> Dict:
        """Process city and ask for personal information"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over by saying "hi"'
                }
            
            # Update session with city
            session_data = session.data.get('data', {})
            session_data['city'] = city.strip().title()
            
            self.db.table('registration_sessions').update({
                'data': session_data,
                'step': 'personal_info',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            return {
                'success': True,
                'message': f"Great! I'll find trainers in {city.strip().title()}. 📍\n\nNow I need a few personal details:\n\n• Your full name\n• Your age\n• Your email (optional)\n\nPlease share in this format:\nJohn Doe, 28, john@email.com",
                'session_id': session_id
            }
            
        except Exception as e:
            log_error(f"Error handling city input: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing your location. Please try again.'
            }
    
    def _handle_client_personal_info(self, session_id: str, info_text: str) -> Dict:
        """Process personal info and show confirmation"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over by saying "hi"'
                }
            
            # Parse personal info
            parts = [p.strip() for p in info_text.split(',')]
            
            if len(parts) < 2:
                return {
                    'success': False,
                    'message': 'Please provide at least your name and age, separated by commas.\n\nExample: John Doe, 28, john@email.com'
                }
            
            # Extract info
            name = parts[0]
            age = None
            email = None
            
            # Try to extract age
            for part in parts[1:]:
                if part.isdigit():
                    age = int(part)
                elif '@' in part:
                    email = part
                elif not age and any(c.isdigit() for c in part):
                    # Try to extract age from text like "28 years"
                    import re
                    age_match = re.search(r'\d+', part)
                    if age_match:
                        age = int(age_match.group())
            
            if not age:
                return {
                    'success': False,
                    'message': 'Please include your age. Example: John Doe, 28, john@email.com'
                }
            
            # Update session with personal info
            session_data = session.data.get('data', {})
            session_data['name'] = name
            session_data['age'] = age
            if email:
                session_data['email'] = email
            
            self.db.table('registration_sessions').update({
                'data': session_data,
                'step': 'confirmation',
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }).eq('id', session_id).execute()
            
            # Build confirmation message
            confirmation = f"""📋 *Registration Summary*

*Name:* {name}
*Age:* {age}
*Email:* {email if email else 'Not provided'}
*City:* {session_data.get('city', 'Not specified')}
*Goal:* {session_data.get('fitness_goal', 'Not specified')}
*Training:* {session_data.get('training_preference', 'Not specified')}

Is this information correct?"""
            
            # Create confirmation buttons
            buttons = [
                {'id': 'confirm_yes', 'title': '✅ Yes, Find Trainers'},
                {'id': 'confirm_edit', 'title': '✏️ Edit Info'},
                {'id': 'confirm_cancel', 'title': '❌ Cancel'}
            ]
            
            return {
                'success': True,
                'message': confirmation,
                'buttons': buttons,
                'session_id': session_id
            }
            
        except Exception as e:
            log_error(f"Error handling personal info: {str(e)}")
            return {
                'success': False,
                'message': 'Error processing your information. Please try again.'
            }
    
    def confirm_client_registration(self, session_id: str, confirmation: str) -> Dict:
        """Handle final confirmation and create client record"""
        try:
            # Get session
            session = self.db.table('registration_sessions').select('*').eq(
                'id', session_id
            ).single().execute()
            
            if not session.data:
                return {
                    'success': False,
                    'message': 'Session expired. Please start over by saying "hi"'
                }
            
            session_data = session.data.get('data', {})
            phone = session.data.get('phone')
            
            # Handle different confirmation responses
            if confirmation.lower() in ['yes', 'confirm', 'confirm_yes', '✅']:
                # Find matching trainers
                trainers = self._find_matching_trainers(session_data)
                
                if trainers:
                    # Create client record
                    client_record = {
                        'name': session_data.get('name'),
                        'whatsapp': phone,
                        'email': session_data.get('email'),
                        'age': session_data.get('age'),
                        'city': session_data.get('city'),
                        'fitness_goal': session_data.get('fitness_goal'),
                        'training_preference': session_data.get('training_preference'),
                        'status': 'searching',
                        'created_at': datetime.now(self.sa_tz).isoformat()
                    }
                    
                    # Check if client already exists
                    existing = self.db.table('clients').select('id').eq(
                        'whatsapp', phone
                    ).execute()
                    
                    if not existing.data:
                        result = self.db.table('clients').insert(client_record).execute()
                        
                        if result.data:
                            client_id = result.data[0]['id']
                            log_info(f"Client registered: {client_id}")
                    
                    # Complete session
                    self.db.table('registration_sessions').update({
                        'status': 'completed',
                        'updated_at': datetime.now(self.sa_tz).isoformat()
                    }).eq('id', session_id).execute()
                    
                    # Format trainer list
                    trainer_list = self._format_trainer_list(trainers[:3])
                    
                    return {
                        'success': True,
                        'message': f"""🎉 *Registration Complete!*

I found {len(trainers)} trainers in {session_data.get('city')} that match your needs:

{trainer_list}

Would you like to:
• Contact a trainer
• See more options
• Get more info

Just let me know! 💪""",
                        'trainers': trainers
                    }
                else:
                    return {
                        'success': True,
                        'message': f"""I couldn't find trainers in {session_data.get('city')} yet, but I've saved your information.

I'll notify you as soon as trainers become available in your area!

In the meantime, would you like to:
• Search in a nearby city
• Start with online training
• Get workout tips

What would help you most? 🤔"""
                    }
            
            elif confirmation.lower() in ['edit', 'confirm_edit', '✏️']:
                return {
                    'success': True,
                    'message': "What would you like to edit?\n\n• Name\n• Age\n• Email\n• City\n• Goal\n• Training preference\n\nJust tell me what to change!"
                }
            
            elif confirmation.lower() in ['cancel', 'confirm_cancel', '❌', 'no']:
                # Cancel session
                self.db.table('registration_sessions').update({
                    'status': 'cancelled',
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', session_id).execute()
                
                return {
                    'success': True,
                    'message': "No problem! Registration cancelled. 👍\n\nFeel free to come back anytime you're ready to find a trainer. Just say 'hi' to start again!"
                }
            
            else:
                return {
                    'success': False,
                    'message': "Please click one of the buttons or reply: Yes, Edit, or Cancel"
                }
            
        except Exception as e:
            log_error(f"Error confirming registration: {str(e)}")
            return {
                'success': False,
                'message': 'Error completing registration. Please try again.'
            }
    
    def _find_matching_trainers(self, client_data: Dict) -> list:
        """Find trainers matching client preferences"""
        try:
            city = client_data.get('city', '').lower()
            
            # Query trainers
            query = self.db.table('trainers').select('*').eq('status', 'active')
            
            # Filter by location if specified
            if city:
                query = query.or_(
                    f"location.ilike.%{city}%,city.ilike.%{city}%"
                )
            
            result = query.execute()
            
            if not result.data:
                return []
            
            # Score and rank trainers
            scored_trainers = []
            for trainer in result.data:
                score = self._calculate_trainer_match_score(trainer, client_data)
                trainer['match_score'] = score
                scored_trainers.append(trainer)
            
            # Sort by score
            scored_trainers.sort(key=lambda x: x['match_score'], reverse=True)
            
            return scored_trainers
            
        except Exception as e:
            log_error(f"Error finding trainers: {str(e)}")
            return []
    
    def _calculate_trainer_match_score(self, trainer: Dict, client_data: Dict) -> int:
        """Calculate match score between trainer and client"""
        score = 0
        
        # Location match (highest priority)
        if trainer.get('location', '').lower() == client_data.get('city', '').lower():
            score += 50
        elif client_data.get('city', '').lower() in trainer.get('location', '').lower():
            score += 30
        
        # Specialization match
        goal = client_data.get('fitness_goal', '').lower()
        specialization = trainer.get('specialization', '').lower()
        
        if goal in specialization:
            score += 30
        
        # Training type match
        preference = client_data.get('training_preference', '').lower()
        if 'gym' in preference and 'gym' in trainer.get('training_location', '').lower():
            score += 20
        elif 'home' in preference and 'home' in trainer.get('services', '').lower():
            score += 20
        elif 'outdoor' in preference and 'outdoor' in trainer.get('services', '').lower():
            score += 20
        
        # Availability bonus
        if trainer.get('accepting_clients', True):
            score += 10
        
        return score
    
    def _format_trainer_list(self, trainers: list) -> str:
        """Format trainer list for WhatsApp display"""
        formatted = []
        
        for i, trainer in enumerate(trainers, 1):
            name = trainer.get('name', 'Unknown')
            business = trainer.get('business_name', '')
            location = trainer.get('location', 'Location not specified')
            specialization = trainer.get('specialization', 'General fitness')
            price = trainer.get('pricing_per_session', 0)
            
            trainer_info = f"""*{i}. {name}*{f' - {business}' if business else ''}
📍 {location}
🎯 {specialization}
💰 R{price}/session"""
            
            formatted.append(trainer_info)
        
        return '\n\n'.join(formatted)