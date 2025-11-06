"""Client registration handler with friendly UX"""
from typing import Dict, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from services.helpers.validation_helpers import ValidationHelpers

class ClientRegistrationHandler:
    """Handle client registration with encouraging experience"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        self.validator = ValidationHelpers()
        
        self.STEPS = {
            0: {'field': 'name', 'prompt': self._get_name_prompt},
            1: {'field': 'email', 'prompt': self._get_email_prompt},
            2: {'field': 'fitness_goals', 'prompt': self._get_goals_prompt},
            3: {'field': 'experience_level', 'prompt': self._get_experience_prompt},
            4: {'field': 'health_conditions', 'prompt': self._get_health_prompt},
            5: {'field': 'availability', 'prompt': self._get_availability_prompt}
        }
    
    def start_registration(self, phone: str, trainer_id: str = None) -> str:
        """Start client registration with warm welcome"""
        if trainer_id:
            # Get trainer name for personalized message
            trainer = self.db.table('trainers').select('name, business_name').eq(
                'id', trainer_id
            ).single().execute()
            
            trainer_name = 'your trainer'
            if trainer.data:
                trainer_name = trainer.data.get('business_name') or trainer.data.get('name')
            
            return (
                f"🌟 *Welcome to {trainer_name}'s training program!*\n\n"
                "I'm Refiloe, your AI fitness assistant! I'm here to help you "
                "crush your fitness goals! 💪\n\n"
                "Let's get you registered in just 6 quick steps.\n\n"
                "📝 *Step 1 of 6*\n\n"
                "What's your name? 😊"
            )
        else:
            return (
                "🌟 *Welcome to your fitness journey!*\n\n"
                "I'm Refiloe, your AI fitness assistant! Let's find you an amazing "
                "trainer and start transforming your life! 💪\n\n"
                "📝 *Step 1 of 6*\n\n"
                "First, what's your name? 😊"
            )
    
    def handle_registration_response(self, phone: str, message: str, 
                                   current_step: int, data: Dict) -> Dict:
        """Handle registration step response"""
        try:
            step_info = self.STEPS.get(current_step)
            if not step_info:
                return self._complete_registration(phone, data)
            
            # Validate input
            field = step_info['field']
            validated = self._validate_field(field, message)
            
            if not validated['valid']:
                return {
                    'success': False,
                    'message': validated['error'],
                    'continue': True
                }
            
            # Store data
            data[field] = validated['value']
            
            # Add encouragement based on responses
            encouragement = self._get_encouragement(field, validated['value'])
            
            # Move to next step
            next_step = current_step + 1
            
            if next_step >= len(self.STEPS):
                return self._complete_registration(phone, data)
            
            # Get next prompt
            next_prompt = self.STEPS[next_step]['prompt'](next_step + 1)
            
            # Combine encouragement with next prompt
            full_message = f"{encouragement}\n\n{next_prompt}" if encouragement else next_prompt
            
            return {
                'success': True,
                'message': full_message,
                'next_step': next_step,
                'data': data,
                'continue': True
            }
            
        except Exception as e:
            log_error(f"Error handling registration: {str(e)}")
            return {
                'success': False,
                'message': "😅 Oops! Let's try that again. What was your answer?",
                'continue': True
            }
    
    def _get_name_prompt(self, step_num: int) -> str:
        """Already shown in start"""
        return ""
    
    def _get_email_prompt(self, step_num: int) -> str:
        return (
            f"📝 *Step {step_num} of 6*\n\n"
            "What's your email address? 📧\n"
            "(Optional - type 'skip' if you prefer not to share)"
        )
    
    def _get_goals_prompt(self, step_num: int) -> str:
        return (
            f"📝 *Step {step_num} of 6*\n\n"
            "What are your main fitness goals? 🎯\n\n"
            "Choose one or more:\n"
            "1️⃣ Lose weight\n"
            "2️⃣ Build muscle\n"
            "3️⃣ Get stronger\n"
            "4️⃣ Improve fitness\n"
            "5️⃣ Train for event\n\n"
            "Reply with numbers (e.g., 1,3) or describe your goals"
        )
    
    def _get_experience_prompt(self, step_num: int) -> str:
        return (
            f"📝 *Step {step_num} of 6*\n\n"
            "What's your current fitness level? 📊\n\n"
            "1️⃣ Beginner (new to exercise)\n"
            "2️⃣ Intermediate (exercise sometimes)\n"
            "3️⃣ Advanced (exercise regularly)\n"
            "4️⃣ Athlete (competitive sports)"
        )
    
    def _get_health_prompt(self, step_num: int) -> str:
        return (
            f"📝 *Step {step_num} of 6*\n\n"
            "Any health conditions or injuries I should know about? 🏥\n\n"
            "This helps keep you safe! Type 'none' if you're all good."
        )
    
    def _get_availability_prompt(self, step_num: int) -> str:
        return (
            f"📝 *Step {step_num} of 6* (Last one!)\n\n"
            "When do you prefer to train? ⏰\n\n"
            "1️⃣ Early morning (5-8am)\n"
            "2️⃣ Morning (8-12pm)\n"
            "3️⃣ Afternoon (12-5pm)\n"
            "4️⃣ Evening (5-8pm)\n"
            "5️⃣ Flexible\n\n"
            "Choose all that work for you (e.g., 1,2,5)"
        )
    
    def _get_encouragement(self, field: str, value: any) -> str:
        """Get encouraging message based on response"""
        if field == 'name':
            return f"Nice to meet you, {value}! 🤝"
        elif field == 'fitness_goals':
            if 'weight' in str(value).lower():
                return "Weight loss is a great goal! We'll help you get there! 🔥"
            elif 'muscle' in str(value).lower():
                return "Building muscle? Awesome! Let's get you strong! 💪"
            else:
                return "Those are fantastic goals! 🌟"
        elif field == 'experience_level':
            if value in ['Beginner', '1']:
                return "Everyone starts somewhere! You're making a great choice! 🌱"
            elif value in ['Advanced', 'Athlete', '3', '4']:
                return "Impressive! Let's take your fitness to the next level! 🚀"
            else:
                return "Perfect! We'll build from where you are! 📈"
        elif field == 'health_conditions':
            if value.lower() != 'none':
                return "Thanks for sharing! Safety first, always! 🛡️"
        return ""
    
    def _validate_field(self, field: str, value: str) -> Dict:
        """Validate registration field"""
        value = value.strip()
        
        if field == 'name':
            if len(value) < 2:
                return {
                    'valid': False,
                    'error': "😊 Please enter your name (at least 2 characters)"
                }
            return {'valid': True, 'value': value}
        
        elif field == 'email':
            if value.lower() == 'skip':
                return {'valid': True, 'value': None}
            if not self.validator.validate_email(value):
                return {
                    'valid': False,
                    'error': "📧 That doesn't look quite right. Please enter a valid email or type 'skip'"
                }
            return {'valid': True, 'value': value.lower()}
        
        elif field == 'fitness_goals':
            goals_map = {
                '1': 'Lose weight',
                '2': 'Build muscle',
                '3': 'Get stronger',
                '4': 'Improve fitness',
                '5': 'Train for event'
            }
            
            # Handle multiple selections
            if ',' in value:
                selected = []
                for num in value.split(','):
                    num = num.strip()
                    if num in goals_map:
                        selected.append(goals_map[num])
                if selected:
                    return {'valid': True, 'value': ', '.join(selected)}
            elif value in goals_map:
                return {'valid': True, 'value': goals_map[value]}
            elif len(value) >= 3:
                return {'valid': True, 'value': value}
            
            return {
                'valid': False,
                'error': "Please choose numbers (1-5) or describe your goals"
            }
        
        elif field == 'experience_level':
            level_map = {
                '1': 'Beginner',
                '2': 'Intermediate',
                '3': 'Advanced',
                '4': 'Athlete'
            }
            
            if value in level_map:
                return {'valid': True, 'value': level_map[value]}
            elif value.title() in level_map.values():
                return {'valid': True, 'value': value.title()}
            else:
                return {
                    'valid': False,
                    'error': "Please choose a number (1-4) for your fitness level"
                }
        
        elif field == 'health_conditions':
            if len(value) < 2:
                return {
                    'valid': False,
                    'error': "Please describe any conditions or type 'none'"
                }
            return {'valid': True, 'value': value}
        
        elif field == 'availability':
            time_map = {
                '1': 'Early morning',
                '2': 'Morning',
                '3': 'Afternoon',
                '4': 'Evening',
                '5': 'Flexible'
            }
            
            # Handle multiple selections
            if ',' in value:
                selected = []
                for num in value.split(','):
                    num = num.strip()
                    if num in time_map:
                        selected.append(time_map[num])
                if selected:
                    return {'valid': True, 'value': ', '.join(selected)}
            elif value in time_map:
                return {'valid': True, 'value': time_map[value]}
            
            return {
                'valid': False,
                'error': "Please choose your preferred times (e.g., 1,2 or just 5 for flexible)"
            }
        
        return {'valid': True, 'value': value}
    
    def _complete_registration(self, phone: str, data: Dict) -> Dict:
        """Complete registration with celebration"""
        try:
            # Create client record with enhanced fields
            client_data = {
                'name': data['name'],
                'whatsapp': phone,
                'email': data.get('email'),
                'fitness_goals': data.get('fitness_goals'),
                'experience_level': data.get('experience_level'),
                'health_conditions': data.get('health_conditions'),
                'preferred_training_times': data.get('availability'),  # Use new field name
                'trainer_id': data.get('trainer_id'),  # If assigned
                'connection_status': 'active' if data.get('trainer_id') else 'no_trainer',
                'requested_by': data.get('requested_by', 'client'),
                'approved_at': datetime.now(self.sa_tz).isoformat() if data.get('trainer_id') else None,
                'status': 'active',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('clients').insert(client_data).execute()
            
            if result.data:
                client_id = result.data[0]['id']
                log_info(f"Client registered: {data['name']} ({client_id})")
                
                # Create personalized celebration based on trainer connection
                trainer_id = data.get('trainer_id')
                
                if trainer_id:
                    # Client has a trainer - get trainer info
                    trainer_result = self.db.table('trainers').select('name, business_name, email').eq('id', trainer_id).execute()
                    
                    if trainer_result.data:
                        trainer_info = trainer_result.data[0]
                        trainer_name = trainer_info.get('name', 'Your trainer')
                        business_name = trainer_info.get('business_name', f"{trainer_name}'s Training")
                        trainer_email = trainer_info.get('email', '')
                        
                        celebration = (
                            f"🎉 *Welcome to {business_name}!*\n\n"
                            f"Your registration is complete! Here's what happens next:\n\n"
                            f"👨‍💼 **Your Trainer:** {trainer_name}\n"
                            f"🏢 **Business:** {business_name}\n"
                            f"📧 **Contact:** {trainer_email}\n\n"
                            f"🎯 *Build Healthy Habits:*\n"
                            f"• Type `/habits` to start tracking your progress\n"
                            f"• Use `/log_habit` to log daily habits\n"
                            f"• Check your streaks with `/habit_streak`\n\n"
                            f"🚀 **Next Steps:**\n"
                            f"• Your trainer will contact you within 24 hours\n"
                            f"• Schedule your first assessment session\n"
                            f"• Start your personalized fitness journey!\n\n"
                            f"💡 *Tip:* Consistent habit tracking is key to reaching your fitness goals!\n\n"
                            f"💬 Questions? Just message me anytime!"
                        )
                        
                        # Notify trainer of completed registration
                        try:
                            trainer_phone = self.db.table('trainers').select('whatsapp').eq('id', trainer_id).execute()
                            if trainer_phone.data:
                                trainer_notification = (
                                    f"🎉 *New Client Registered!*\n\n"
                                    f"{data['name']} has completed registration and is ready to start training!\n\n"
                                    f"📋 **Client Details:**\n"
                                    f"• Name: {data['name']}\n"
                                    f"• Goals: {data.get('fitness_goals', 'Not specified')}\n"
                                    f"• Experience: {data.get('experience_level', 'Not specified')}\n"
                                    f"• Availability: {data.get('availability', 'Not specified')}\n\n"
                                    f"💡 **Next Steps:**\n"
                                    f"• Contact them to schedule first session\n"
                                    f"• Plan their fitness assessment\n"
                                    f"• Start building their program!\n\n"
                                    f"Great job growing your business! 💪"
                                )
                                
                                self.whatsapp.send_message(trainer_phone.data[0]['whatsapp'], trainer_notification)
                        except Exception as e:
                            log_warning(f"Could not notify trainer of registration completion: {str(e)}")
                    else:
                        celebration = (
                            "🎉🎊 *YOU DID IT!* 🎊🎉\n\n"
                            f"Welcome to your fitness transformation, {data['name']}! "
                            "This is the beginning of something amazing! 🌟\n\n"
                            "Your trainer will be in touch soon!"
                        )
                else:
                    # Client has no trainer yet
                    celebration = (
                        "🎉🎊 *YOU DID IT!* 🎊🎉\n\n"
                        f"Welcome to your fitness transformation, {data['name']}! "
                        "This is the beginning of something amazing! 🌟\n\n"
                        "🎯 *Start Building Healthy Habits:*\n"
                        "• Type `/habits` to start tracking your progress\n"
                        "• Use `/log_habit` to log daily habits\n"
                        "• Check your streaks with `/habit_streak`\n\n"
                        "🔍 **Ready to find your perfect trainer?**\n"
                        "• Say 'find a trainer' to search for trainers\n"
                        "• Ask friends for trainer recommendations\n"
                        "• If you know a trainer's email, say 'trainer [email]'\n\n"
                        "💡 *Tip:* Start tracking habits now, even before finding a trainer!\n\n"
                        "Your fitness journey starts now! 💪"
                    )
                
                # Create appropriate buttons based on trainer status
                if trainer_id:
                    buttons = [
                        {'id': 'book_session', 'title': '📅 Book Session'},
                        {'id': 'view_progress', 'title': '📊 My Progress'},
                        {'id': 'contact_trainer', 'title': '💬 Contact Trainer'}
                    ]
                else:
                    buttons = [
                        {'id': 'find_trainer', 'title': '🔍 Find Trainer'},
                        {'id': 'view_trainers', 'title': '👥 Browse Trainers'},
                        {'id': 'start_assessment', 'title': '📋 Fitness Check'}
                    ]
                
                return {
                    'success': True,
                    'message': celebration,
                    'buttons': buttons,
                    'continue': False,
                    'client_id': client_id
                }
            else:
                return {
                    'success': False,
                    'message': "😔 Registration failed. Please try again or contact support.",
                    'continue': False
                }
                
        except Exception as e:
            log_error(f"Error completing registration: {str(e)}")
            return {
                'success': False,
                'message': "😅 Almost there! Let's try once more.",
                'continue': False
            }