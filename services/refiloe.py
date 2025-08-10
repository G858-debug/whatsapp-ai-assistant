from services.workout import WorkoutService
import re
import requests
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Tuple, List
import random
import json
import anthropic

from models.trainer import TrainerModel
from models.client import ClientModel
from models.booking import BookingModel
from utils.logger import log_error, log_info, log_warning

class RefiloeAssistant:
    """Refiloe AI Assistant - Main business logic"""
    
    def __init__(self, config, supabase_client, whatsapp_service, logger):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.logger = logger
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.workout_service = WorkoutService(config, supabase_client)
        
        # Initialize models
        self.trainer_model = TrainerModel(supabase_client, config)
        self.client_model = ClientModel(supabase_client, config)
        self.booking_model = BookingModel(supabase_client, config)
        
        # Track conversation history for better context
        self.conversation_history = {}
    def has_previous_interaction(self, phone_number: str) -> bool:
        """Check if we've interacted with this user before"""
        try:
            # Check message history in database
            if self.db:
                result = self.db.table('messages').select('id').eq(
                    'whatsapp_from', phone_number
                ).limit(2).execute()
                
                # If more than 1 message, they've interacted before
                return len(result.data) > 1
            return False
            
        except Exception as e:
            log_error(f"Error checking interaction history: {str(e)}")
            return False

    def get_conversation_context(self, trainer_id: str, limit: int = 5) -> str:
        """Get recent conversation history for context"""
        try:
            if self.db:
                result = self.db.table('messages')\
                    .select('content, response, created_at')\
                    .eq('sender_id', trainer_id)\
                    .order('created_at', desc=True)\
                    .limit(limit)\
                    .execute()
                
                if result.data:
                    # Format for context
                    history = []
                    for msg in reversed(result.data):  # Chronological order
                        if msg.get('content'):
                            history.append(f"Trainer: {msg['content']}")
                        if msg.get('response'):
                            history.append(f"Refiloe: {msg['response'][:200]}...")  # Truncate long responses
                    
                    return '\n'.join(history) if history else "No recent messages"
            return "No conversation history available"
        except Exception as e:
            log_error(f"Error getting conversation context: {str(e)}")
            return "No conversation history available"
    
    def analyze_intent_with_ai(self, trainer: Dict, message_text: str) -> Dict:
        """Use AI to analyze message intent and extract information"""
        try:
            if not self.config.ANTHROPIC_API_KEY:
                return None
            
            # Get recent conversation for context
            conversation_history = self.get_conversation_context(trainer['id'])
            
            # Get trainer's clients for context
            clients = self.client_model.get_trainer_clients(trainer['id'])
            client_names = [c['name'] for c in clients] if clients else []
            
            # Create analysis prompt
            analysis_prompt = f"""Analyze this message from trainer {trainer['name']} and extract intent.
    
    Trainer's clients: {', '.join(client_names) if client_names else 'No clients yet'}
    
    Recent conversation:
    {conversation_history}
    
    Current message: "{message_text}"
    
    Determine:
    1. Does this message contain workout exercises? (look for patterns like "3x12", "sets", "reps", exercise names)
    2. Is a client name mentioned? (check against the client list)
    3. What is the trainer trying to do?
    4. Is this a follow-up to the previous conversation?
    
    Return ONLY valid JSON:
    {{
        "has_workout": true/false,
        "exercises_text": "extracted exercises if any",
        "client_name": "client name if mentioned",
        "intent": "send_workout|preview_workout|confirmation|greeting|help|dashboard|schedule|add_client|other",
        "is_followup": true/false,
        "confidence": 0.0-1.0
    }}"""
    
            # Call Claude
            client = anthropic.Anthropic(api_key=self.config.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Faster for intent analysis
                max_tokens=200,
                temperature=0.3,  # Lower temperature for more consistent JSON
                messages=[
                    {"role": "user", "content": analysis_prompt}
                ]
            )
            
            # Parse response
            response_text = response.content[0].text.strip()
            # Extract JSON from response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            return None
            
        except Exception as e:
            log_error(f"Error in AI intent analysis: {str(e)}")
            return None
    
    def handle_trainer_message_enhanced(self, trainer_context: Dict, message_text: str) -> str:
        """Enhanced trainer message handler with AI intent recognition"""
        try:
            trainer = trainer_context['data']
            message_lower = message_text.lower()
            is_first = trainer_context.get('first_interaction', False)
            greeting = f"Hi {trainer['name']}! I'm Refiloe, your AI assistant. " if is_first else ""
            
            # First, check for workout confirmations (these need immediate handling)
            if any(word in message_lower for word in ['yes', 'send', 'confirm', 'ok', 'go ahead', 'send it']):
                # Check for pending workout
                if self.db:
                    pending_result = self.db.table('pending_workouts')\
                        .select('*')\
                        .eq('trainer_id', trainer['id'])\
                        .execute()
                    
                    if pending_result.data:
                        return self.handle_workout_confirmation(trainer, message_text)
            
            # Try AI intent analysis for complex cases
            ai_analysis = self.analyze_intent_with_ai(trainer, message_text)
            
            if ai_analysis and ai_analysis.get('confidence', 0) > 0.7:
                # Handle based on AI-detected intent
                
                if ai_analysis.get('has_workout') and ai_analysis.get('exercises_text'):
                    # Parse the exercises
                    exercises = self.workout_service.parse_workout_text(ai_analysis['exercises_text'])
                    
                    if exercises:
                        client_name = ai_analysis.get('client_name')
                        
                        # If client mentioned, prepare workout for them
                        if client_name:
                            clients = self.client_model.get_trainer_clients(trainer['id'])
                            matching_client = None
                            
                            for client in clients:
                                if client_name.lower() in client['name'].lower():
                                    matching_client = client
                                    break
                            
                            if matching_client:
                                # Format workout
                                workout_message = self.workout_service.format_workout_for_whatsapp(
                                    exercises,
                                    matching_client['name'],
                                    matching_client.get('gender', 'male')
                                )
                                
                                # Store as pending
                                if self.db:
                                    self.db.table('pending_workouts').upsert({
                                        'trainer_id': trainer['id'],
                                        'client_id': matching_client['id'],
                                        'client_name': matching_client['name'],
                                        'client_whatsapp': matching_client['whatsapp'],
                                        'workout_message': workout_message,
                                        'exercises': json.dumps(exercises),
                                        'created_at': datetime.now(self.sa_tz).isoformat()
                                    }, on_conflict='trainer_id').execute()
                                
                                return f"""{greeting}Perfect! Here's the workout for {matching_client['name']}:
    
    {workout_message}
    
    Reply 'send' to deliver this to {matching_client['name']} ✅"""
                        
                        # No client specified
                        else:
                            preview = f"{greeting}Great workout! Here's what I've prepared:\n\n"
                            for i, ex in enumerate(exercises, 1):
                                preview += f"{i}. {ex['name']} - {ex.get('sets', 3)} sets × {ex.get('reps', '12')}\n"
                            
                            clients = self.client_model.get_trainer_clients(trainer['id'])
                            if clients:
                                preview += f"\nWho should receive this? Just say their name.\n"
                                preview += f"Your clients: {', '.join([c['name'] for c in clients])}"
                            
                            return preview
                
                # Handle requests to see what was sent
                if ai_analysis.get('intent') == 'preview_workout' and ai_analysis.get('is_followup'):
                    # Check for pending workout
                    if self.db:
                        pending_result = self.db.table('pending_workouts')\
                            .select('*')\
                            .eq('trainer_id', trainer['id'])\
                            .execute()
                        
                        if pending_result.data:
                            pending = pending_result.data[0]
                            return f"""Here's the message I would send to {pending['client_name']}:
    
    {pending['workout_message']}
    
    Reply 'send' to deliver this workout ✅"""
            
            # Fall back to your existing keyword-based logic
            # (Keep ALL your existing conditions here - greetings, help, dashboard, etc.)
            return self.handle_trainer_message(trainer_context, message_text)
            
        except Exception as e:
            log_error(f"Error in enhanced handler: {str(e)}")
            # Fall back to original handler
            return self.handle_trainer_message(trainer_context, message_text)

    def process_message(self, phone_number: str, message_text: str) -> str:
        """Main message processing logic"""
        try:
            # Log incoming message
            if self.whatsapp:
                self.whatsapp.log_message(phone_number, message_text, 'incoming')
            
            # Track if this is first interaction
            is_first_interaction = not self.has_previous_interaction(phone_number)
            
            # Identify sender
            sender_context = self.identify_sender(phone_number)
            sender_context['first_interaction'] = is_first_interaction
            
            if sender_context['type'] == 'trainer':
                return self.handle_trainer_message(sender_context, message_text)
            elif sender_context['type'] == 'client':
                return self.handle_client_message(sender_context, message_text)
            else:
                return self.handle_unknown_sender(phone_number, message_text, is_first_interaction)
                
        except Exception as e:
            log_error(f"Error in Refiloe processing: {str(e)}", exc_info=True)
            # More specific error message based on the error type
            if "NoneType" in str(e):
                return "I'm setting up. Please try again in a moment! 😊"
            else:
                return "Let me try that again. What can I help you with? 😊"
    
    def identify_sender(self, phone_number: str) -> Dict:
        """Identify if sender is trainer, client, or unknown"""
        try:
            # Check trainers first
            trainer = self.trainer_model.get_by_phone(phone_number) if self.trainer_model else None
            if trainer:
                return {'type': 'trainer', 'data': trainer}
            
            # Check clients
            client = self.client_model.get_by_phone(phone_number) if self.client_model else None
            if client:
                return {'type': 'client', 'data': client}
            
            return {'type': 'unknown', 'data': None}
            
        except Exception as e:
            log_error(f"Error identifying sender: {str(e)}")
            return {'type': 'unknown', 'data': None}
    
    def handle_trainer_message(self, trainer_context: Dict, message_text: str) -> str:
        """Handle messages from trainers"""

        try:
            # Try enhanced AI-powered handling first
            if self.config.ANTHROPIC_API_KEY:
                enhanced_response = self.handle_trainer_message_enhanced(trainer_context, message_text)
                if enhanced_response and enhanced_response != self.handle_trainer_message(trainer_context, message_text):
                    return enhanced_response
        
        try:
            trainer = trainer_context['data']
            message_lower = message_text.lower()
            is_first = trainer_context.get('first_interaction', False)
            
            # Greeting for first interaction only
            greeting = f"Hi {trainer['name']}! I'm Refiloe, your AI assistant. " if is_first else ""
            
            # 1. GREETINGS FIRST (before any other checks)
            if any(word in message_lower for word in ['hi', 'hello', 'hey', 'howzit', 'sawubona', 'molo']) and len(message_text.split()) <= 5:
                if is_first:
                    return f"Hi {trainer['name']}! I'm Refiloe, your AI assistant. How can I help you today? 💪"
                else:
                    greetings = [
                        f"Hey {trainer['name']}! What can I do for you today? 😊",
                        f"Hi there {trainer['name']}! How can I help? 💪",
                        f"Hello {trainer['name']}! Ready to manage your training business? 🏃‍♂️"
                    ]
                    import random
                    return random.choice(greetings)
            
            # 2. HELP/COMMANDS
            if any(phrase in message_lower for phrase in ['help', 'commands', 'what can you do', 'how do you work']):
                return self.get_trainer_help_menu(trainer['name'], is_first)
            
            # 3. DASHBOARD REQUEST
            if any(phrase in message_lower for phrase in ['dashboard', 'my dashboard', 'show dashboard', 'view dashboard', 'calendar view', 'web view']):
                return self.handle_dashboard_request(trainer, greeting)
            
            # 4. WORKOUT/PROGRAM REQUESTS
            if any(phrase in message_lower for phrase in ['workout', 'program', 'exercise', 'routine', 'training plan']):
                return self.handle_workout_request(trainer, message_text, greeting)
            
            # 5. VIEW CLIENTS
            if any(phrase in message_lower for phrase in ['my clients', 'list clients', 'show clients', 'all clients']):
                return greeting + self.get_trainer_clients_display(trainer)
            
            # 6. SCHEDULE/BOOKINGS
            if any(phrase in message_lower for phrase in ['schedule', 'bookings', 'appointments', 'today\'s sessions', 'tomorrow']):
                return greeting + self.get_trainer_schedule_display(trainer)
            
            # 7. REVENUE/EARNINGS
            if any(phrase in message_lower for phrase in ['revenue', 'payments', 'money', 'earnings', 'income']):
                return greeting + self.get_trainer_revenue_display(trainer)
            
            # 8. AVAILABILITY UPDATE
            if any(phrase in message_lower for phrase in ['my availability', 'available times', 'working hours', 'schedule hours', 'when i work']):
                return self.handle_availability_update(trainer, message_text, greeting)
            
            # 9. BOOKING PREFERENCES
            if any(phrase in message_lower for phrase in ['booking preference', 'prefer early', 'prefer late', 'slot preference']):
                return self.handle_preference_update(trainer, message_text, greeting)
            
            # 10. SESSION DURATION
            if any(phrase in message_lower for phrase in ['session length', 'session duration', 'minutes long', 'hour long']):
                return self.handle_session_duration_update(trainer, message_text, greeting)
            
            # 11. EXPLICIT CLIENT ADDITION REQUEST (must mention "add" or "new" with "client")
            if any(phrase in message_lower for phrase in ['add client', 'new client', 'onboard client', 'add a client', 'register client', 'sign up client']):
                return f"""{greeting}Let's add your new client! I'll need:
    
    📝 Client's full name
    📱 WhatsApp number (e.g., 0821234567)
    📧 Email address
    📅 How often they'll train (e.g., "twice a week" or "Mondays and Thursdays")
    
    Go ahead! 💪"""
            
            # 12. CHECK IF PROVIDING CLIENT DETAILS (only after explicit add request or with clear indicators)
            has_phone = bool(re.search(r'(?:\+27|27|0)?\d{9,10}', message_text))
            has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message_text))
            
            # Only try to parse as client details if:
            # - Has phone/email AND mentions client-related keywords
            # - OR looks strongly like client details
            client_keywords = ['client', 'trains', 'training', 'sessions', 'week', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            has_client_context = any(word in message_lower for word in client_keywords)
            
            if (has_phone or has_email) and has_client_context:
                # Check if this might be client details
                if self.looks_like_client_details(message_text):
                    details = self.extract_client_details_naturally(message_text)
                    
                    if details and details.get('name') and details.get('phone'):
                        # Add the client directly
                        return self.complete_client_addition(trainer, details)
                    else:
                        # Only ask for clarification if we're confident they're trying to add a client
                        if 'client' in message_lower or has_phone:
                            missing = []
                            if not details.get('name'):
                                missing.append("name")
                            if not details.get('phone'):
                                missing.append("phone number")
                            
                            return f"""I see you're trying to add a client, but I need their {' and '.join(missing)}.
    
    Could you provide:
    📝 Full name
    📱 WhatsApp number
    📧 Email (optional)
    📅 Training schedule (optional)
    
    Just give me the details! 💪"""
            
            # 13. GENERAL AI FALLBACK - for everything else
            # This should handle confusion, general questions, and unclear requests
            return self.process_with_ai(trainer, message_text, 'trainer', greeting=greeting)
            
        except Exception as e:
            log_error(f"Error handling trainer message: {str(e)}", exc_info=True)
            return "Let me try that again. What would you like help with?"

    def handle_dashboard_request(self, trainer: Dict, greeting: str = "") -> str:
        """Handle trainer's request to view dashboard"""
        try:
            # Import dashboard service
            from routes.dashboard import dashboard_service
            
            if not dashboard_service:
                return f"{greeting}Dashboard is being set up. Try again in a moment! 😊"
            
            # Generate dashboard link
            result = dashboard_service.generate_dashboard_link(trainer['id'])
            
            if result['success']:
                return f"""{greeting}📊 Here's your personal dashboard link:
    
    {result['url']}
    
    ✨ This link will work for 24 hours
    📱 Opens perfectly on your phone
    🔒 Secure and private to you
    
    Your dashboard shows:
    • Today's schedule
    • Weekly calendar
    • Client list & balances
    • Revenue tracking
    • Quick settings
    
    Just tap the link to view! 💪"""
            else:
                return f"{greeting}I had trouble generating your dashboard link. Let me try again in a moment!"
                
        except Exception as e:
            log_error(f"Error handling dashboard request: {str(e)}")
            return f"{greeting}Let me fix that dashboard link for you. Try again in a moment!"
    
    def looks_like_client_details(self, message_text: str) -> bool:
        """Check if message looks like it contains client details"""
        # Check for patterns that suggest client details
        message_lower = message_text.lower()
        
        # Multiple lines often indicate structured data
        if len(message_text.split('\n')) >= 2:
            return True
        
        # Check for common patterns
        detail_indicators = [
            'twice a week', 'three times', 'once a week',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'trains', 'sessions', 'wants to train'
        ]
        
        # If message has a name-like pattern at the start
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', message_text.strip()):
            return True
        
        return any(indicator in message_lower for indicator in detail_indicators)
    
    def complete_client_addition(self, trainer: Dict, details: Dict) -> str:
        """Complete the client addition with extracted details"""
        try:
            # Add the client
            result = self.client_model.add_client(trainer['id'], details)
            
            if result['success']:
                # Send onboarding message
                self.send_client_onboarding(
                    details['phone'],
                    details['name'],
                    trainer,
                    result['sessions']
                )
                
                package_display = details.get('package', 'single').replace('-', ' ').title()
                
                return f"""✅ Perfect! 

{details['name']} is now added to your client list!

📱 I'm sending them a welcome message right now  
📦 Package: {package_display} ({result['sessions']} sessions)  
💬 They'll get booking instructions via WhatsApp

All set, {trainer['name']}! 😊"""
            else:
                return f"I ran into an issue: {result.get('error', 'Unknown error')}. Could you try again?"
                
        except Exception as e:
            log_error(f"Error completing client addition: {str(e)}")
            return "I had trouble adding that client. Could you try again with their name and phone number?"
    
    def extract_client_details_naturally(self, text: str) -> Dict:
        """Extract client details from natural language"""
        details = {}
        
        try:
            # Phone extraction (South African numbers)
            phone_patterns = [
                r'(?:\+27|27|0)?[\s\-]?(\d{2})[\s\-]?(\d{3})[\s\-]?(\d{4})',
                r'(?:\+27|27|0)?(\d{9,10})'
            ]
            
            for pattern in phone_patterns:
                phone_match = re.search(pattern, text)
                if phone_match:
                    phone = re.sub(r'[^\d]', '', phone_match.group())
                    if phone.startswith('0'):
                        phone = '27' + phone[1:]
                    elif not phone.startswith('27') and len(phone) == 9:
                        phone = '27' + phone
                    elif not phone.startswith('27') and len(phone) == 10:
                        if phone[0] != '0':
                            phone = '27' + phone
                        else:
                            phone = '27' + phone[1:]
                    details['phone'] = phone
                    break
            
            # Email extraction
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            if email_match:
                details['email'] = email_match.group().lower()
            
            # Package/frequency extraction
            text_lower = text.lower()
            package_patterns = {
                r'\b(?:single|one|1)\s*(?:session)?\b': 'single',
                r'\b(?:4|four)[\-\s]?(?:pack|sessions?)?\b': '4-pack',
                r'\b(?:8|eight)[\-\s]?(?:pack|sessions?)?\b': '8-pack',
                r'\b(?:12|twelve)[\-\s]?(?:pack|sessions?)?\b': '12-pack',
                r'\b(?:monthly|month)\b': 'monthly',
                r'\b(?:twice\s+(?:a|per)?\s*week|2\s*(?:times?|x)\s*(?:a|per)?\s*week)\b': '8-pack',
                r'\b(?:once\s+(?:a|per)?\s*week|weekly|1\s*(?:time?|x)\s*(?:a|per)?\s*week)\b': '4-pack',
                r'\b(?:three\s+times?\s+(?:a|per)?\s*week|3\s*(?:times?|x)\s*(?:a|per)?\s*week)\b': '12-pack'
            }
            
            for pattern, package in package_patterns.items():
                if re.search(pattern, text_lower):
                    details['package'] = package
                    break
            
            # Name extraction (improved)
            # Remove email and phone from text for cleaner name extraction
            clean_text = text
            if details.get('email'):
                clean_text = clean_text.replace(details['email'], '')
            if phone_match:
                clean_text = clean_text.replace(phone_match.group(), '')
            
            # Remove common words that aren't names
            non_name_words = ['add', 'client', 'new', 'onboard', 'help', 'me', 'with', 'the', 
                              'wants', 'to', 'train', 'twice', 'week', 'times', 'sessions',
                              'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            # Look for capitalized name pattern
            lines = clean_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                # Check if line looks like a name (2+ capitalized words)
                words = line.split()
                if len(words) >= 2:
                    # Check if words are capitalized and not in non-name list
                    potential_name_words = []
                    for word in words:
                        if word and word[0].isupper() and word.lower() not in non_name_words:
                            potential_name_words.append(word)
                    
                    if len(potential_name_words) >= 2:
                        details['name'] = ' '.join(potential_name_words[:3])  # Max 3 words for name
                        break
            
            # If no name found, try first line that's not empty and doesn't contain email/phone
            if 'name' not in details:
                for line in lines:
                    line = line.strip()
                    if line and not re.search(r'[@\d]', line) and len(line.split()) >= 2:
                        # Capitalize properly
                        words = line.split()
                        name_words = []
                        for word in words[:3]:  # Max 3 words
                            if word.lower() not in non_name_words:
                                name_words.append(word.capitalize())
                        if len(name_words) >= 2:
                            details['name'] = ' '.join(name_words)
                            break
            
            log_info(f"Extracted details: {details}")
            return details
            
        except Exception as e:
            log_error(f"Error extracting client details: {str(e)}")
            return details
    
    def handle_availability_update(self, trainer: Dict, message_text: str, greeting: str) -> str:
        """Handle trainer availability updates"""
        try:
            # Parse availability from natural language
            availability = self.parse_availability(message_text)
            
            if not availability:
                return f"""{greeting}I'd love to update your availability! 

Please tell me your available hours for each day. For example:

"Monday to Thursday: 9am-12pm and 2pm-6pm
Friday: 10am-3pm
Saturday: 8am-12pm
Sunday: Closed"

You can just tell me naturally! 😊"""
            
            # Store availability in trainer settings
            trainer_settings = trainer.get('settings', {})
            if isinstance(trainer_settings, str):
                try:
                    trainer_settings = json.loads(trainer_settings)
                except:
                    trainer_settings = {}
            
            trainer_settings['availability'] = availability
            trainer_settings['updated_at'] = datetime.now(self.sa_tz).isoformat()
            
            # Update in database
            result = self.trainer_model.update_trainer(
                trainer['id'], 
                {'settings': json.dumps(trainer_settings)}
            )
            
            if result['success']:
                # Format availability for display
                schedule_text = self.format_availability_display(availability)
                return f"""{greeting}Perfect! I've updated your availability:

{schedule_text}

Your clients can now only book during these times. Need to change anything?"""
            else:
                return f"{greeting}I had trouble updating your availability. Could you try again?"
                
        except Exception as e:
            log_error(f"Error updating availability: {str(e)}")
            return f"{greeting}Let me try that again. What are your available hours?"
    
    def send_client_onboarding(self, client_phone: str, client_name: str, 
                              trainer: Dict, sessions: int):
        """Send onboarding message to new client"""
        try:
            import time
            import threading
            
            def send_delayed():
                time.sleep(2)
                
                welcome_msg = f"""Hi {client_name}! 👋

I'm Refiloe, {trainer['name']}'s AI assistant! Welcome to the team! 🎉

I'm here to make booking your training sessions super easy:

💪 Your package: {sessions} sessions a month 
💵 Per session: R{trainer.get('pricing_per_session', 300):.0f}  
📱 How it works: Just message me here!

Want to book your first session? Say something like "Book Tuesday morning" or "When are you free?" 

I'll take care of the rest! 😊"""
                
                if self.whatsapp:
                    self.whatsapp.send_message(client_phone, welcome_msg)
                
                # Follow-up with availability
                time.sleep(25)
                
                availability_msg = f"""🗓️ Here's what I have available this week:

Mon: 9am, 2pm, 5pm  
Tue: 10am, 1pm, 4pm  
Wed: 8am, 12pm, 3pm  
Thu: 9am, 2pm, 5pm  
Fri: 10am, 1pm, 4pm  

Just tell me what works! Something like "Thursday 2pm sounds good" 

Ready to get started? 💪"""
                
                if self.whatsapp:
                    self.whatsapp.send_message(client_phone, availability_msg)
            
            # Send in background thread
            threading.Thread(target=send_delayed).start()
            
        except Exception as e:
            log_error(f"Error in client onboarding: {str(e)}")
    
    def get_trainer_clients_display(self, trainer: Dict) -> str:
        """Display trainer's client list"""
        try:
            clients = self.client_model.get_trainer_clients(trainer['id']) if self.client_model else []
            
            if not clients:
                return f"You don't have any active clients yet, {trainer['name']}! Ready to add your first one? 😊"
            
            response = f"📋 Your clients, {trainer['name']}:\n\n"
            
            for client in clients:
                last_session = client.get('last_session_date')
                if last_session:
                    last_date = datetime.fromisoformat(last_session)
                    last_date = last_date.replace(tzinfo=pytz.UTC).astimezone(self.sa_tz)
                    days_ago = (datetime.now(self.sa_tz) - last_date).days
                    last_text = f"{days_ago} days ago" if days_ago > 0 else "Today"
                else:
                    last_text = "No sessions yet"
                
                response += f"• {client['name']} ({client.get('sessions_remaining', 0)} left, last: {last_text})\n"
            
            return response + "\nNeed to add someone new? Just tell me! 💪"
            
        except Exception as e:
            log_error(f"Error getting trainer clients: {str(e)}")
            return f"I'm having trouble getting your client list, {trainer['name']}. Try again?"
    
    def get_trainer_schedule_display(self, trainer: Dict) -> str:
        """Display trainer's schedule"""
        try:
            now = datetime.now(self.sa_tz)
            week_later = now + timedelta(days=7)
            
            bookings = self.booking_model.get_trainer_schedule(
                trainer['id'], now, week_later
            ) if self.booking_model else []
            
            if not bookings:
                return f"Your week is wide open, {trainer['name']}! 📅\n\nPerfect time for your clients to book sessions 😊"
            
            response = f"📅 Coming up for you, {trainer['name']}:\n\n"
            
            for booking in bookings:
                session_time = datetime.fromisoformat(booking['session_datetime'])
                session_time = session_time.replace(tzinfo=pytz.UTC).astimezone(self.sa_tz)
                day = session_time.strftime('%a %d %b')
                time = session_time.strftime('%I:%M%p').lower()
                client_name = booking.get('clients', {}).get('name', 'Unknown')
                
                response += f"• {day} at {time} - {client_name}\n"
            
            return response + "\nLooking good! 💪"
            
        except Exception as e:
            log_error(f"Error getting trainer schedule: {str(e)}")
            return f"Let me check your schedule again, {trainer['name']}..."
    
    def get_trainer_revenue_display(self, trainer: Dict) -> str:
        """Display trainer's revenue summary"""
        try:
            # For now, calculate based on bookings
            now = datetime.now(self.sa_tz)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get this month's bookings
            bookings = self.booking_model.get_trainer_schedule(
                trainer['id'], month_start, now
            ) if self.booking_model else []
            
            completed_revenue = sum(b.get('price', 0) for b in bookings if b.get('status') == 'completed')
            scheduled_revenue = sum(b.get('price', 0) for b in bookings if b.get('status') == 'scheduled')
            
            # Get active clients
            clients = self.client_model.get_trainer_clients(trainer['id']) if self.client_model else []
            active_clients = len(clients)
            
            encouragement = "Great work!" if completed_revenue > 5000 else "You're building momentum!"
            
            return f"""💰 {now.strftime('%B')} Summary for {trainer['name']}:

Completed: R{completed_revenue:.2f} ✅  
Scheduled: R{scheduled_revenue:.2f} 📅  
Active clients: {active_clients} 👥

{encouragement} 🚀"""
            
        except Exception as e:
            log_error(f"Error getting revenue: {str(e)}")
            return f"Let me check your earnings, {trainer['name']}..."
    
    def process_with_ai(self, user: Dict, message_text: str, user_type: str, 
                           trainer: Optional[Dict] = None, greeting: str = ""):
        """Process message with Claude AI"""
        try:
            if not self.config.ANTHROPIC_API_KEY:
                return self.get_fallback_response(user_type, user.get('name', 'there'))
            
            # Build context based on user type
            if user_type == 'trainer':
                context = f"""You are Refiloe, an AI assistant that works FOR personal trainer "{user['name']}" who runs "{user.get('business_name', user['name'] + ' Fitness')}".
                
    CRITICAL CONTEXT:
    - You are {user['name']}'s personal assistant, helping them manage their fitness business
    - {user['name']} OWNS all client relationships and has full authority over all communications
    - When {user['name']} asks what you sent to a client, ALWAYS share the complete details
    - All workout plans, client messages, and training schedules belong to {user['name']}
    - NEVER cite privacy or confidentiality when {user['name']} asks about their own clients
    - {user['name']} has complete visibility and control over everything you do for their business
    - You should readily provide any information about client communications, workouts, or bookings when asked
    
    Current capabilities you can mention if relevant:
    - Managing client bookings and schedules
    - Creating and sending workout programs to clients
    - Tracking client sessions and payments
    - Providing business insights and revenue tracking
    - Generating a web dashboard for business overview
    
    Keep responses under 3 sentences and WhatsApp-friendly. Be helpful and proactive in supporting {user['name']}'s business."""
            
            else:  # client context
                context = f"""You are Refiloe, an AI assistant helping client "{user['name']}" with their training sessions with trainer "{trainer['name'] if trainer else 'their trainer'}".
                
    CONTEXT:
    - You work on behalf of trainer {trainer['name'] if trainer else 'the trainer'} to help manage {user['name']}'s fitness journey
    - {user['name']} has {user.get('sessions_remaining', 0)} sessions remaining
    - You can help {user['name']} with booking sessions, viewing their workout plans, and tracking progress
    - All communications and workout plans are managed by and belong to their trainer {trainer['name'] if trainer else ''}
    
    Keep responses under 3 sentences and WhatsApp-friendly. Be encouraging and supportive."""
            
            # Add conversation history if needed for better context
            recent_context = ""
            if hasattr(self, 'get_recent_messages'):
                recent_messages = self.get_recent_messages(user['id'], limit=3)
                if recent_messages:
                    recent_context = "\n\nRecent conversation:\n"
                    for msg in recent_messages:
                        recent_context += f"{'Trainer' if user_type == 'trainer' else 'Client'}: {msg['content']}\n"
                        recent_context += f"Refiloe: {msg['response']}\n"
            
            # Combine context with recent history
            full_context = context + recent_context
            
            # Add specific instruction for the current query if it's about viewing sent content
            message_lower = message_text.lower()
            if user_type == 'trainer' and any(phrase in message_lower for phrase in 
                ['what did you send', 'show me what you sent', 'what workout', 'share what you sent', 
                 'what did you tell', 'what was sent', 'show the workout', 'display the workout']):
                full_context += f"""\n\nIMPORTANT: The trainer is asking to see what was sent to their client. 
                You MUST share the complete details of any workouts, messages, or information sent to their clients. 
                This is the trainer's business information and they have full rights to see it."""
            
            # Call Claude API with enhanced context
            response = self.call_claude_api(full_context, message_text)
            return greeting + response
            
        except Exception as e:
            log_error(f"Error with AI processing: {str(e)}")
            return self.get_fallback_response(user_type, user.get('name', 'there'))
    
    def call_claude_api(self, context: str, message: str) -> str:
        """Call Claude API with Sonnet"""
        try:
            url = "https://api.anthropic.com/v1/messages"
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": self.config.AI_MODEL if hasattr(self.config, 'AI_MODEL') else "claude-3-haiku-20240307",
                "max_tokens": 150,
                "messages": [
                    {"role": "user", "content": f"{context}\n\nUser message: {message}"}
                ]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                log_error(f"Claude API error: {response.status_code} - {response.text}")
                return "Let me help you with that! What specifically would you like to do?"
                
        except Exception as e:
            log_error(f"Error calling Claude API: {str(e)}")
            return "Let me try that again for you! 😊"
    
    def get_fallback_response(self, user_type: str, name: str) -> str:
        """Fallback response when AI is not available"""
        if user_type == 'trainer':
            return f"Hi {name}! Try 'my clients', 'schedule', or 'add client'! 😊"
        else:
            return f"Hi {name}! Try 'book session' or 'when are you free'! 😊"
    
    def get_trainer_help_menu(self, trainer_name: str, is_first: bool) -> str:
        """Get help menu for trainers"""
        greeting = f"Hi {trainer_name}! I'm Refiloe 😊\n\n" if is_first else ""
        
        return f"""{greeting}Here's what I can help with:

*Clients:*
• "Add new client" - I'll guide you through it
• "My clients" - See your client list
• "Send reminders" - Reach out to everyone

*Schedule & Settings:*
• "My schedule" - This week's sessions
• "My availability" - Set your working hours
• "Session duration" - Set default session length
• "Booking preferences" - Set how slots are filled

*Business:*
• "Revenue" - How you're doing this month

Just tell me what you need! 💪"""
    
    def handle_unknown_sender(self, phone_number: str, message_text: str, is_first: bool) -> str:
        """Handle messages from unknown senders"""
        message_lower = message_text.lower()
        
        if is_first:
            intro = "👋 Hi! I'm Refiloe, an AI assistant for personal trainers!\n\n"
        else:
            intro = ""
        
        if any(word in message_lower for word in ['trainer', 'register', 'sign up', 'join']):
            return f"""{intro}I help personal trainers manage their clients automatically via WhatsApp! 

Want to join as a trainer? Contact us at:
📧 Email: refiloe@refiloeradebe.co.za
📱 WhatsApp: [Admin number]

I'll handle all your client bookings 24/7! 💪"""
        
        else:
            return f"""{intro}**If you're a trainer:** I can manage your client bookings, scheduling, and reminders automatically!

**If you're a client:** Your trainer needs to add you to the system first, then I'll help you book sessions easily!

Reply "TRAINER" if you want to sign up! 😊"""


    def handle_workout_request(self, trainer: Dict, message_text: str, greeting: str = "") -> str:
        """Handle workout creation and sending"""
        try:
            message_lower = message_text.lower()
            
            # Check if trainer wants to generate a workout
            if any(phrase in message_lower for phrase in ['generate workout', 'create upper body', 'create lower body', 'create leg workout', 'create chest workout']):
                return self.handle_workout_generation(trainer, message_text, greeting)
            
            # Try to parse exercises from the message
            exercises = self.workout_service.parse_workout_text(message_text)
            
            # If we found exercises in the message
            if exercises:
                # Look for client name patterns
                client_patterns = [
                    r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "for Itumeleng"
                    r'to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',   # "to Itumeleng"
                ]
                
                client_name = None
                for pattern in client_patterns:
                    match = re.search(pattern, message_text)
                    if match:
                        client_name = match.group(1)
                        break
                
                # If client name is found, try to send immediately
                if client_name:
                    # Find the client
                    clients = self.client_model.get_trainer_clients(trainer['id'])
                    matching_client = None
                    
                    for client in clients:
                        if client_name.lower() in client['name'].lower() or client['name'].lower() in client_name.lower():
                            matching_client = client
                            break
                    
                    if matching_client:
                        # Get client gender
                        client_gender = matching_client.get('gender', 'male')
                        
                        # Format the workout
                        workout_message = self.workout_service.format_workout_for_whatsapp(
                            exercises, 
                            matching_client['name'],
                            client_gender
                        )
                        
                        # Store workout in session for confirmation
                        # Store in database or session for "yes" confirmation
                        if self.db:
                            self.db.table('pending_workouts').upsert({
                                'trainer_id': trainer['id'],
                                'client_id': matching_client['id'],
                                'client_name': matching_client['name'],
                                'client_whatsapp': matching_client['whatsapp'],
                                'workout_message': workout_message,
                                'exercises': json.dumps(exercises),
                                'created_at': datetime.now(self.sa_tz).isoformat()
                            }, on_conflict='trainer_id').execute()
                        
                        # Show preview and ask for confirmation
                        preview = f"""{greeting}Perfect! Here's the workout for {matching_client['name']}:
    
    {workout_message}
    
    Reply with:
    ✅ **'Send'** to deliver this to {matching_client['name']}
    ✏️ **'Edit'** to modify the workout
    ❌ **'Cancel'** to start over"""
                        
                        return preview
                    
                    else:
                        # Client not found
                        client_list = '\n'.join([f"• {c['name']}" for c in clients])
                        return f"""{greeting}I couldn't find a client named '{client_name}'.
    
    Your current clients:
    {client_list}
    
    Please specify the correct client name or add them first."""
                
                # No client specified - show workout and ask who to send to
                else:
                    preview = f"""{greeting}Great workout! Here's what I've prepared:
    
    """
                    for i, ex in enumerate(exercises, 1):
                        preview += f"{i}. {ex['name']} - {ex['sets']} sets × {ex['reps']}\n"
                    
                    clients = self.client_model.get_trainer_clients(trainer['id'])
                    if clients:
                        preview += f"\n**Who should receive this workout?**\n"
                        preview += "Just say: 'Send to [Client Name]'\n\n"
                        preview += "Your clients: " + ', '.join([c['name'] for c in clients])
                    else:
                        preview += "\nYou don't have any clients yet. Add a client first!"
                    
                    return preview
            
            # No exercises found - provide help
            return f"""{greeting}I can help you create and send workouts! 
    
    **Quick examples:**
    • Type a workout: "Squats 3x12, Lunges 2x10"
    • Send to client: "Squats 3x12 for Sarah"
    • Generate: "Create upper body workout"
    
    What would you like to do? 💪"""
            
        except Exception as e:
            log_error(f"Error handling workout request: {str(e)}")
            return f"{greeting}I had trouble with that workout. Try again?"
    
    def handle_workout_confirmation(self, trainer: Dict, message_text: str) -> str:
        """Handle workout confirmation (send/edit/cancel)"""
        try:
            message_lower = message_text.lower()
            
            # Check for pending workout
            if self.db:
                result = self.db.table('pending_workouts')\
                    .select('*')\
                    .eq('trainer_id', trainer['id'])\
                    .execute()
                
                if result.data:
                    pending = result.data[0]
                    
                    # Handle confirmation
                    if any(word in message_lower for word in ['send', 'yes', 'confirm', '✅']):
                        # Send the workout
                        self.whatsapp.send_message(
                            pending['client_whatsapp'], 
                            pending['workout_message']
                        )
                        
                        # Save to history
                        exercises = json.loads(pending.get('exercises', '[]'))
                        self.workout_service.save_workout_to_history(
                            pending['client_id'],
                            trainer['id'],
                            'Custom Workout',
                            exercises
                        )
                        
                        # Clear pending
                        self.db.table('pending_workouts')\
                            .delete()\
                            .eq('trainer_id', trainer['id'])\
                            .execute()
                        
                        return f"""✅ Workout sent to {pending['client_name']}! 
    
    They received:
    • {len(exercises)} exercises with demonstrations
    • Clear sets & reps instructions
    • Form tips and safety reminders
    
    They can reply with questions! 💪"""
                    
                    elif any(word in message_lower for word in ['cancel', 'no', '❌']):
                        # Clear pending
                        self.db.table('pending_workouts')\
                            .delete()\
                            .eq('trainer_id', trainer['id'])\
                            .execute()
                        
                        return "Workout cancelled. What would you like to do instead?"
                    
                    elif any(word in message_lower for word in ['edit', 'change', '✏️']):
                        return "Please type the updated workout (e.g., 'Squats 4x12, Lunges 3x10')"
            
            return None  # No pending workout
            
        except Exception as e:
            log_error(f"Error handling workout confirmation: {str(e)}")
            return None
    
    def handle_workout_generation(self, trainer: Dict, message_text: str, greeting: str = "") -> str:
        """Handle AI workout generation requests"""
        try:
            message_lower = message_text.lower()
            
            # Extract workout type
            workout_types = {
                'leg': 'legs', 'legs': 'legs', 'lower': 'legs',
                'chest': 'chest', 'push': 'chest',
                'back': 'back', 'pull': 'back',
                'upper': 'upper', 'upper body': 'upper',
                'full': 'full', 'full body': 'full',
                'core': 'core', 'abs': 'core'
            }
            
            workout_type = 'full'  # default
            for key, value in workout_types.items():
                if key in message_lower:
                    workout_type = value
                    break
            
            # Extract client name
            client_match = re.search(r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message_text)
            
            if client_match:
                client_name = client_match.group(1)
                
                # Find client
                clients = self.client_model.get_trainer_clients(trainer['id'])
                matching_client = None
                
                for client in clients:
                    if client_name.lower() in client['name'].lower():
                        matching_client = client
                        break
                
                if matching_client:
                    # Get client preferences
                    preferences = self.workout_service.get_client_preferences(
                        matching_client['id'], 
                        workout_type
                    )
                    
                    # Generate workout
                    exercises = self.workout_service.generate_ai_workout(
                        matching_client,
                        workout_type,
                        preferences
                    )
                    
                    # Format preview
                    preview = f"{greeting}I've generated a {workout_type} workout for {matching_client['name']}:\n\n"
                    
                    for i, ex in enumerate(exercises, 1):
                        preview += f"{i}. {ex['name']} - {ex['sets']} sets × {ex['reps']}\n"
                    
                    preview += f"\n✅ Send this workout\n✏️ Edit first\n❌ Cancel\n\nWhat would you like to do?"
                    
                    # Store pending workout in conversation
                    self.conversation_history[f"pending_workout_{trainer['id']}"] = {
                        'client': matching_client,
                        'exercises': exercises,
                        'type': workout_type
                    }
                    
                    return preview
                else:
                    return f"{greeting}I couldn't find {client_name}. Please specify which client."
            else:
                return f"{greeting}Which client is this {workout_type} workout for?\n\nExample: 'Create leg workout for Sarah'"
                
        except Exception as e:
            log_error(f"Error generating workout: {str(e)}")
            return f"{greeting}I had trouble generating that workout. Try: 'Create leg workout for [client name]'"




