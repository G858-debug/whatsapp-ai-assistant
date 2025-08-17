# services/ai_intent_handler.py
"""
AI-First Intent Handler for Refiloe
This replaces keyword matching with intelligent intent understanding
"""

import json
import anthropic
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error, log_warning

class AIIntentHandler:
    """Handle all message understanding through AI first"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Initialize Claude
        if config.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            self.model = "claude-3-5-sonnet-20241022"
            log_info("AI Intent Handler initialized with Claude")
        else:
            self.client = None
            log_warning("No Anthropic API key - falling back to keyword matching")
    
    def understand_message(self, 
                          message: str, 
                          sender_type: str,  # 'trainer' or 'client'
                          sender_data: Dict,
                          conversation_history: List[str] = None) -> Dict:
        """
        Main entry point - understands any message using AI
        Returns structured intent and extracted data
        """
        
        if not self.client:
            log_info(f"Using fallback intent detection for: {message[:50]}")
            return self._fallback_intent_detection(message, sender_type)
        
        try:
            # Build context based on sender type
            if sender_type == 'trainer':
                context = self._build_trainer_context(sender_data)
            else:
                context = self._build_client_context(sender_data)
            
            # Create the AI prompt
            prompt = self._create_intent_prompt(
                message, 
                sender_type, 
                context, 
                conversation_history
            )
            
            # Get AI understanding
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse the response
            intent_data = self._parse_ai_response(response.content[0].text)
            
            # Validate and enrich the intent
            validated_intent = self._validate_intent(intent_data, sender_data, sender_type)
            
            log_info(f"AI Intent detected: {validated_intent.get('primary_intent')} "
                    f"with confidence {validated_intent.get('confidence')}")
            
            return validated_intent
            
        except Exception as e:
            log_error(f"AI intent understanding failed: {str(e)}", exc_info=True)
            return self._fallback_intent_detection(message, sender_type)
    
    def _build_trainer_context(self, trainer_data: Dict) -> Dict:
        """Build context for trainer"""
        return {
            'name': trainer_data.get('name', 'Trainer'),
            'id': trainer_data.get('id'),
            'whatsapp': trainer_data.get('whatsapp'),
            'business_name': trainer_data.get('business_name'),
            'active_clients': trainer_data.get('active_clients', 0)
        }
    
    def _build_client_context(self, client_data: Dict) -> Dict:
        """Build context for client"""
        return {
            'name': client_data.get('name', 'Client'),
            'id': client_data.get('id'),
            'whatsapp': client_data.get('whatsapp'),
            'trainer_name': client_data.get('trainer_name', 'your trainer'),
            'sessions_remaining': client_data.get('sessions_remaining', 0)
        }
    
    def _create_intent_prompt(self, message: str, sender_type: str, 
                             context: Dict, history: List[str]) -> str:
        """Create a comprehensive prompt for Claude"""
        
        prompt = f"""You are analyzing a WhatsApp message to Refiloe, a friendly AI assistant for personal trainers. 
Refiloe should be conversational and human-like, not always task-focused.

SENDER: {sender_type} ({context.get('name', 'Unknown')})

CONTEXT:
{json.dumps(context, indent=2)}

RECENT CONVERSATION:
{chr(10).join(history[-5:]) if history else 'No recent messages'}

CURRENT MESSAGE: "{message}"

TASK: Understand what the {sender_type} wants. Remember:
- Sometimes people just want to chat or check in
- Not every message needs a task response
- Be conversational and natural

Analyze and return ONLY valid JSON with this structure:
{{
    "primary_intent": "string - main action or conversation type",
    "secondary_intents": ["list of other detected intents"],
    "confidence": 0.0-1.0,
    "extracted_data": {{
        "client_name": "if mentioned",
        "date_time": "if mentioned",
        "exercises": ["if workout mentioned"],
        "duration": "if mentioned",
        "price": "if mentioned",
        "phone_number": "if mentioned",
        "email": "if mentioned"
    }},
    "sentiment": "positive/neutral/negative/urgent/casual/friendly",
    "requires_confirmation": true/false,
    "suggested_response_type": "task/conversational/mixed",
    "is_follow_up": true/false,
    "conversation_tone": "casual/business/friendly/concerned"
}}

POSSIBLE PRIMARY INTENTS FOR {sender_type.upper()}:
"""
        
        if sender_type == 'trainer':
            prompt += """
- casual_chat: Just checking in, casual conversation
- greeting: Just saying hello (no task needed)
- status_check: Asking if Refiloe is there/working
- thanks: Expressing gratitude
- farewell: Saying goodbye
- small_talk: Weather, how are you, etc.
- add_client: Adding a new client
- view_schedule: Checking their schedule/bookings
- send_workout: Sending a workout to a client
- start_assessment: Starting a fitness assessment
- view_dashboard: Accessing their dashboard
- check_revenue: Checking payments/earnings
- send_reminder: Sending reminders to clients
- update_availability: Changing available times
- view_clients: Listing all clients
- general_question: General query
- help: Asking for help/commands
"""
        else:  # client
            prompt += """
- casual_chat: Just checking in, casual conversation
- greeting: Just saying hello (no task needed)
- status_check: Asking if Refiloe is there/working
- thanks: Expressing gratitude
- farewell: Saying goodbye
- small_talk: Weather, how are you, etc.
- book_session: Booking a training session
- view_schedule: Checking their upcoming sessions
- cancel_session: Cancelling a booking
- reschedule_session: Moving a booking
- view_assessment: Checking fitness assessment results
- check_progress: Viewing their progress
- request_workout: Asking for a workout plan
- payment_query: Question about payment
- general_question: General query
- help: Asking for help
"""
        
        prompt += """
Be precise and extract ALL mentioned information. 
Consider South African context (ZA phone numbers, Rand currency, local slang).
The message might be informal or use WhatsApp shorthand.
Recognize casual conversation - not everything needs a task response.
"""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse the AI's JSON response"""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # If no JSON found, try to parse the whole response
            return json.loads(response_text.strip())
            
        except json.JSONDecodeError as e:
            log_error(f"Failed to parse AI response: {e}")
            # Return a basic structure
            return {
                'primary_intent': 'unclear',
                'confidence': 0.3,
                'extracted_data': {},
                'sentiment': 'neutral',
                'suggested_response_type': 'conversational'
            }
    
    def _validate_intent(self, intent_data: Dict, sender_data: Dict, 
                        sender_type: str) -> Dict:
        """Validate and enrich the AI's intent understanding"""
        
        # Ensure required fields
        intent_data.setdefault('primary_intent', 'general_question')
        intent_data.setdefault('confidence', 0.5)
        intent_data.setdefault('extracted_data', {})
        intent_data.setdefault('requires_confirmation', False)
        intent_data.setdefault('suggested_response_type', 'conversational')
        intent_data.setdefault('conversation_tone', 'friendly')
        
        # Validate client names against actual clients
        if sender_type == 'trainer' and intent_data['extracted_data'].get('client_name'):
            client_name = intent_data['extracted_data']['client_name']
            clients = self.db.table('clients').select('id, name')\
                .eq('trainer_id', sender_data['id']).execute()
            
            if clients.data:
                # Fuzzy match client name
                matched_client = self._fuzzy_match_client(client_name, clients.data)
                if matched_client:
                    intent_data['extracted_data']['client_id'] = matched_client['id']
                    intent_data['extracted_data']['client_name'] = matched_client['name']
                else:
                    intent_data['extracted_data']['client_name_unmatched'] = client_name
                    del intent_data['extracted_data']['client_name']
        
        # Parse dates/times to SA timezone
        if intent_data['extracted_data'].get('date_time'):
            parsed_time = self._parse_datetime(intent_data['extracted_data']['date_time'])
            if parsed_time:
                intent_data['extracted_data']['parsed_datetime'] = parsed_time.isoformat()
        
        return intent_data
    
    def _fuzzy_match_client(self, search_name: str, clients: List[Dict]) -> Optional[Dict]:
        """Find best matching client name"""
        search_lower = search_name.lower()
        
        for client in clients:
            client_lower = client['name'].lower()
            # Exact match
            if search_lower == client_lower:
                return client
            # Partial match
            if search_lower in client_lower or client_lower in search_lower:
                return client
            # First name match
            if search_lower.split()[0] == client_lower.split()[0]:
                return client
        
        return None
    
    def _parse_datetime(self, time_str: str) -> Optional[datetime]:
        """Parse various datetime formats to SA timezone"""
        from dateutil import parser
        import re
        
        try:
            # Handle relative times
            time_lower = time_str.lower()
            now = datetime.now(self.sa_tz)
            
            if 'tomorrow' in time_lower:
                base_date = now + timedelta(days=1)
            elif 'today' in time_lower:
                base_date = now
            elif 'monday' in time_lower:
                # Find next Monday
                days_ahead = 0 - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                base_date = now + timedelta(days=days_ahead)
            else:
                # Try to parse directly
                parsed = parser.parse(time_str, fuzzy=True)
                return self.sa_tz.localize(parsed) if parsed.tzinfo is None else parsed
            
            # Extract time from string
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                meridiem = time_match.group(3)
                
                if meridiem == 'pm' and hour < 12:
                    hour += 12
                elif meridiem == 'am' and hour == 12:
                    hour = 0
                
                return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return base_date.replace(hour=9, minute=0, second=0, microsecond=0)  # Default to 9am
            
        except Exception as e:
            log_error(f"Error parsing datetime '{time_str}': {str(e)}")
            return None
    
    def _fallback_intent_detection(self, message: str, sender_type: str) -> Dict:
        """Basic keyword-based intent detection when AI is unavailable"""
        message_lower = message.lower()
        
        # Check for casual conversation first
        casual_keywords = {
            'status_check': ['are you there', 'you there', 'still there', 'are you working', 'you alive', 'you up'],
            'greeting': ['hi', 'hello', 'hey', 'howzit', 'sawubona', 'molo', 'morning', 'afternoon', 'evening'],
            'thanks': ['thanks', 'thank you', 'appreciate', 'cheers', 'shot', 'dankie'],
            'farewell': ['bye', 'goodbye', 'see you', 'later', 'cheers', 'chat soon'],
            'casual_chat': ['how are you', 'what\'s up', 'wassup', 'how\'s it', 'you good'],
        }
        
        # Check casual intents first
        for intent, keywords in casual_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return {
                        'primary_intent': intent,
                        'secondary_intents': [],
                        'confidence': 0.8,
                        'extracted_data': {},
                        'sentiment': 'friendly',
                        'requires_confirmation': False,
                        'suggested_response_type': 'conversational',
                        'conversation_tone': 'casual',
                        'is_follow_up': False
                    }
        
        # Then check task-based keywords
        intent_keywords = {
            'help': ['help', 'commands', 'what can you do', 'menu'],
            'view_schedule': ['schedule', 'bookings', 'appointments', 'sessions', 'calendar', 'week', 'today'],
            'add_client': ['add client', 'new client', 'register client'],
            'view_clients': ['view clients', 'show clients', 'list clients', 'my clients'],
            'view_dashboard': ['dashboard', 'stats', 'overview'],
            'send_workout': ['workout', 'exercise', 'training program'],
            'start_assessment': ['assessment', 'fitness test', 'evaluate'],
            'check_revenue': ['revenue', 'earnings', 'income', 'payments'],
            'book_session': ['book', 'booking', 'schedule session'],
            'cancel_session': ['cancel', 'cancel booking'],
            'general_question': ['what', 'when', 'where', 'why', 'how']
        }
        
        # Detect primary intent
        primary_intent = 'general_question'
        highest_confidence = 0.3
        response_type = 'task'
        
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    primary_intent = intent
                    highest_confidence = 0.7
                    break
        
        # Extract basic data
        extracted_data = {}
        
        # Extract phone numbers (South African format)
        import re
        phone_pattern = r'(?:0|27)?[678]\d{8}'
        phone_match = re.search(phone_pattern, message)
        if phone_match:
            extracted_data['phone_number'] = phone_match.group()
        
        # Extract times
        time_pattern = r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)?\b'
        time_match = re.search(time_pattern, message)
        if time_match:
            extracted_data['date_time'] = time_match.group()
        
        # Look for client names (basic)
        if 'for' in message_lower:
            parts = message_lower.split('for')
            if len(parts) > 1:
                potential_name = parts[1].strip().split()[0:2]
                if potential_name:
                    extracted_data['client_name'] = ' '.join(potential_name).title()
        
        return {
            'primary_intent': primary_intent,
            'secondary_intents': [],
            'confidence': highest_confidence,
            'extracted_data': extracted_data,
            'sentiment': 'neutral',
            'requires_confirmation': False,
            'suggested_response_type': response_type,
            'conversation_tone': 'friendly',
            'is_follow_up': False
        }
    
    def generate_smart_response(self, intent_data: Dict, sender_type: str, 
                               sender_data: Dict) -> str:
        """Generate a contextual response when no specific handler exists"""
        
        intent = intent_data.get('primary_intent')
        name = sender_data.get('name', 'there')
        tone = intent_data.get('conversation_tone', 'friendly')
        response_type = intent_data.get('suggested_response_type', 'conversational')
        
        # Handle casual conversation intents
        casual_responses = {
            'status_check': [
                f"Yes {name}, I'm here! 😊 Just chilling in the cloud, ready when you need me.",
                f"I'm always here for you, {name}! 24/7, rain or shine ☀️",
                f"Yep, still here {name}! Not going anywhere 😄",
                f"Present and accounted for! What's on your mind, {name}?"
            ],
            'casual_chat': [
                f"I'm doing great, {name}! Just here helping trainers and clients stay fit. How are things with you?",
                f"All good on my end! How's your day going, {name}?",
                f"Can't complain - living the AI dream! 😄 How are you doing?",
                f"I'm well, thanks for asking! How's the fitness world treating you?"
            ],
            'thanks': [
                f"You're welcome, {name}! Always happy to help 😊",
                f"My pleasure! That's what I'm here for 💪",
                f"Anytime, {name}! 🙌",
                f"No worries at all! Glad I could help."
            ],
            'farewell': [
                f"Chat soon, {name}! Have an awesome day! 👋",
                f"Later, {name}! Stay strong! 💪",
                f"Bye {name}! Catch you later 😊",
                f"See you soon! Don't be a stranger!"
            ]
        }
        
        # Check if we have a casual response
        import random
        if intent in casual_responses:
            return random.choice(casual_responses[intent])
        
        # Default responses based on response type
        if response_type == 'conversational':
            if intent == 'greeting':
                greetings = [
                    f"Hey {name}! 👋",
                    f"Hi {name}! Good to hear from you 😊",
                    f"Hello {name}! How's it going?",
                    f"Hey there {name}! 🙌"
                ]
                return random.choice(greetings)
            elif intent == 'unclear':
                return f"I didn't quite catch that, {name}. Could you rephrase that for me?"
            else:
                return f"Interesting, {name}! Tell me more about that."
        
        # Task-based but still friendly
        return f"Let me help you with that, {name}. What specifically would you like to know?"
