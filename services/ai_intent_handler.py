"""
AI-First Intent Handler for Refiloe
This replaces keyword matching with intelligent intent understanding
"""

import json
from anthropic import Anthropic
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
            self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
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
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse the response
            intent_data = self._parse_ai_response(response.content[0].text)
            intent_data.setdefault('extracted_data', {})
            intent_data['extracted_data']['original_message'] = message
            
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
- Refiloe can help with ANY topic, not just fitness
- Detect if they're asking about coding, general knowledge, or creative tasks
- Sometimes people just want to chat or check in
- Not every message needs a fitness-related response
- Be conversational and natural
- If someone asks about web development, coding, or technical topics, mark it as 'technical_question'
- If someone asks general knowledge questions, mark it as 'knowledge_question'
- Recognize habit tracking responses (numbers, yes/no patterns, done/skip)

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
        "custom_price": "if setting client price",
        "phone_number": "if mentioned",
        "email": "if mentioned",
        "habit_type": "if setting up habit (water/steps/sleep/veggies/etc)",
        "habit_responses": ["array of habit check responses if logging"],
        "habit_values": ["numeric values for habits if provided"],
        "target_value": "if mentioned for habit setup"
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
- set_client_price: Setting custom price for a client (e.g., "Set Sarah's rate to R450")
- view_client_price: Checking a client's custom price (e.g., "What is John's rate?")
- setup_habit: Setting up habit tracking for a client (water, steps, sleep, etc)
- check_habit_compliance: Viewing client habit progress/compliance
- modify_habit: Changing habit targets or settings
- send_habit_reminder: Manually trigger habit check for clients
- view_habit_report: Get habit tracking summary/reports
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
- general_question: General query about fitness or training
- technical_question: Programming, coding, technical help
- knowledge_question: General knowledge, facts, explanations
- creative_request: Writing, ideas, creative content
- other_assistance: Any other non-fitness help needed
- help: Asking for help/commands

HABIT SETUP PATTERNS:
- "Set up water tracking for [client]"
- "Add habit for [client]"
- "[client] needs to track [habit]"
- "Start [client] on [habit] tracking"
"""
        else:  # client
            prompt += """
- casual_chat: Just checking in, casual conversation
- greeting: Just saying hello (no task needed)
- status_check: Asking if Refiloe is there/working
- thanks: Expressing gratitude
- farewell: Saying goodbye
- small_talk: Weather, how are you, etc.
- log_habits: Recording daily habit completion (responding to habit check)
- check_streak: Asking about their habit streak
- view_habits: What habits they need to track
- skip_habits: Skipping today's habit tracking
- modify_habit_target: Requesting to change their habit goals
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

HABIT LOGGING PATTERNS:
- Simple responses: "yes yes no", "7 yes no", "done done skip"
- Numbers: "6", "8 glasses", "10000 steps"
- Natural language: "I drank 6 glasses and ate my veggies"
- Emojis: "✅ ✅ ❌", "👍 👍 👎"
- Mixed: "6/8 water, veggies yes, no walk"
"""
        
        prompt += """
Be precise and extract ALL mentioned information. 
Consider South African context (ZA phone numbers, Rand currency, local slang).
The message might be informal or use WhatsApp shorthand.
Recognize casual conversation - not everything needs a task response.

For habit tracking:
- Detect when someone is responding to a habit check
- Extract specific values (numbers for water, steps, etc)
- Understand various response formats (yes/no, numbers, done/skip, emojis)
- Identify which habits are being set up or tracked
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
        
        # Process habit responses if present
        if intent_data['extracted_data'].get('habit_responses'):
            processed_responses = self._process_habit_responses(
                intent_data['extracted_data']['habit_responses']
            )
            intent_data['extracted_data']['processed_habit_responses'] = processed_responses
        
        return intent_data
    
    def _process_habit_responses(self, responses: List) -> List[Dict]:
        """Process various habit response formats into structured data"""
        processed = []
        
        for response in responses:
            response_lower = str(response).lower()
            
            # Check for yes/no/done/skip
            if response_lower in ['yes', '✅', 'done', 'complete', '👍']:
                processed.append({'completed': True, 'value': None})
            elif response_lower in ['no', '❌', 'skip', 'missed', '👎']:
                processed.append({'completed': False, 'value': None})
            # Check for numeric values
            elif response_lower.replace('.', '').isdigit():
                processed.append({'completed': True, 'value': float(response_lower)})
            # Check for fractions like "6/8"
            elif '/' in response_lower:
                parts = response_lower.split('/')
                if len(parts) == 2 and parts[0].isdigit():
                    processed.append({'completed': True, 'value': float(parts[0])})
            else:
                # Try to extract numbers from text
                import re
                numbers = re.findall(r'\d+', response_lower)
                if numbers:
                    processed.append({'completed': True, 'value': float(numbers[0])})
                else:
                    processed.append({'completed': False, 'value': None})
        
        return processed
    
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
        
        # Check for habit-related keywords first
        habit_keywords = {
            'setup_habit': ['habit', 'track', 'water tracking', 'steps tracking', 'sleep tracking'],
            'log_habits': ['yes yes', 'yes no', 'done done', 'glasses', 'steps', '✅', '❌'],
            'check_streak': ['streak', 'how many days', 'consecutive'],
            'view_habits': ['what habits', 'my habits', 'tracking what'],
        }
        
        # Check habit intents
        for intent, keywords in habit_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    # Extract habit responses for logging
                    extracted_data = {}
                    if intent == 'log_habits':
                        extracted_data = self._extract_habit_responses(message)
                    elif intent == 'setup_habit':
                        extracted_data = self._extract_habit_setup(message)
                    
                    return {
                        'primary_intent': intent,
                        'secondary_intents': [],
                        'confidence': 0.75,
                        'extracted_data': extracted_data,
                        'sentiment': 'neutral',
                        'requires_confirmation': False,
                        'suggested_response_type': 'task',
                        'conversation_tone': 'friendly',
                        'is_follow_up': False
                    }
        
        # Check for casual conversation
        casual_keywords = {
            'status_check': ['are you there', 'you there', 'still there', 'are you working', 'you alive', 'you up'],
            'greeting': ['hi', 'hello', 'hey', 'howzit', 'sawubona', 'molo', 'morning', 'afternoon', 'evening'],
            'thanks': ['thanks', 'thank you', 'appreciate', 'cheers', 'shot', 'dankie'],
            'farewell': ['bye', 'goodbye', 'see you', 'later', 'cheers', 'chat soon'],
            'casual_chat': ['how are you', 'what\'s up', 'wassup', 'how\'s it', 'you good'],
        }
        
        # Check casual intents
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
    
    def _extract_habit_responses(self, message: str) -> Dict:
        """Extract habit logging responses from message"""
        import re
        
        extracted = {
            'habit_responses': [],
            'habit_values': []
        }
        
        message_lower = message.lower()
        
        # Pattern 1: yes/no responses
        yes_no_pattern = r'\b(yes|no|done|skip|complete|missed)\b'
        yes_no_matches = re.findall(yes_no_pattern, message_lower)
        if yes_no_matches:
            extracted['habit_responses'] = yes_no_matches
        
        # Pattern 2: numeric values
        number_pattern = r'\b(\d+)\b'
        numbers = re.findall(number_pattern, message)
        if numbers:
            extracted['habit_values'] = [int(n) for n in numbers]
        
        # Pattern 3: emojis
        if '✅' in message or '❌' in message or '👍' in message or '👎' in message:
            emoji_responses = []
            for char in message:
                if char in ['✅', '👍']:
                    emoji_responses.append('yes')
                elif char in ['❌', '👎']:
                    emoji_responses.append('no')
            extracted['habit_responses'] = emoji_responses
        
        return extracted
    
    def _extract_habit_setup(self, message: str) -> Dict:
        """Extract habit setup information from message"""
        extracted = {}
        message_lower = message.lower()
        
        # Extract habit type
        habit_types = {
            'water': ['water', 'hydration', 'drink'],
            'steps': ['steps', 'walking', 'walk'],
            'sleep': ['sleep', 'rest'],
            'vegetables': ['vegetables', 'veggies', 'greens'],
            'exercise': ['exercise', 'workout', 'training'],
            'meditation': ['meditation', 'mindfulness', 'meditate']
        }
        
        for habit_type, keywords in habit_types.items():
            for keyword in keywords:
                if keyword in message_lower:
                    extracted['habit_type'] = habit_type
                    break
        
        # Extract target value if mentioned
        import re
        number_pattern = r'\b(\d+)\b'
        numbers = re.findall(number_pattern, message)
        if numbers:
            extracted['target_value'] = int(numbers[0])
        
        # Extract client name if mentioned
        if 'for' in message_lower:
            parts = message_lower.split('for')
            if len(parts) > 1:
                potential_name = parts[1].strip().split()[0:2]
                if potential_name:
                    extracted['client_name'] = ' '.join(potential_name).title()
        
        return extracted
    
    def generate_smart_response(self, intent_data: Dict, sender_type: str, 
                               sender_data: Dict) -> str:
        """Generate a contextual response when no specific handler exists"""
        
        intent = intent_data.get('primary_intent')
        name = sender_data.get('name', 'there')
        tone = intent_data.get('conversation_tone', 'friendly')
        response_type = intent_data.get('suggested_response_type', 'conversational')
        sentiment = intent_data.get('sentiment', 'neutral')
        
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
        
        # Handle responses to "I'm doing good thanks" type messages
        positive_sentiment_responses = [
            "I'm doing well",
            "I'm good",
            "doing good",
            "great thanks",
            "all good",
            "can't complain",
            "not bad"
        ]
        
        message_lower = intent_data.get('extracted_data', {}).get('original_message', '').lower()
        
        # Check if this is a response to "how are you" type question
        if any(phrase in message_lower for phrase in positive_sentiment_responses):
            helpful_responses = [
                f"That's great to hear, {name}! 😊 Is there anything I can help you with today?",
                f"Glad you're doing well! What can I do for you today, {name}?",
                f"Awesome! 💪 How can I assist you today?",
                f"Good to hear! Is there something specific you'd like help with?",
                f"That's wonderful! What brings you to chat with me today?"
            ]
            return random.choice(helpful_responses)
        
        # Default responses based on response type
        if response_type == 'conversational':
            if intent == 'greeting':
                greetings = [
                    f"Hey {name}! 👋 How can I help you today?",
                    f"Hi {name}! Good to hear from you 😊 What can I do for you?",
                    f"Hello {name}! How's it going? What brings you here today?",
                    f"Hey there {name}! 🙌 What's on your fitness agenda?"
                ]
                return random.choice(greetings)
            elif intent == 'unclear':
                clarification_responses = [
                    f"I didn't quite catch that, {name}. Could you rephrase that for me?",
                    f"Hmm, not sure I understood that correctly. What would you like help with?",
                    f"Sorry {name}, I'm a bit confused. What can I help you with today?"
                ]
                return random.choice(clarification_responses)
            elif sentiment in ['neutral', 'positive'] and intent == 'general_question':
                # For general chat that seems to be winding down
                pivot_responses = [
                    f"That's interesting, {name}! By the way, is there anything specific I can help you with today?",
                    f"Cool! So {name}, what can I assist you with? Bookings, workouts, or something else?",
                    f"Nice! How can I make your fitness journey easier today?",
                    f"Got it! What would you like to work on today - scheduling, habits, or something else?"
                ]
                return random.choice(pivot_responses)
            else:
                # Fallback that still pivots to help
                return f"I see! So {name}, what can I help you with today? I can assist with bookings, workouts, habits, and more!"
        
        # Task-based but still friendly
        if sender_type == 'trainer':
            return f"Let me help you with that, {name}. Are you looking to manage clients, check your schedule, or something else?"
        else:
            return f"Let me help you with that, {name}. Would you like to book a session, check your progress, or something else?"
