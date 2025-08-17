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
            self.model = "claude-3-5-sonnet-20241022"  # Use Sonnet for better performance
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
                temperature=0.3,  # Lower temp for consistency
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
            log_error(f"AI intent understanding failed: {str(e)}")
            return self._fallback_intent_detection(message, sender_type)
    
    def _create_intent_prompt(self, message: str, sender_type: str, 
                             context: Dict, history: List[str]) -> str:
        """Create a comprehensive prompt for Claude"""
        
        prompt = f"""You are analyzing a WhatsApp message to Refiloe, an AI assistant for personal trainers.

SENDER: {sender_type} ({context.get('name', 'Unknown')})

CONTEXT:
{json.dumps(context, indent=2)}

RECENT CONVERSATION:
{chr(10).join(history[-5:]) if history else 'No recent messages'}

CURRENT MESSAGE: "{message}"

TASK: Understand what the {sender_type} wants and extract all relevant information.

Analyze and return ONLY valid JSON with this structure:
{{
    "primary_intent": "string - main action needed",
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
    "sentiment": "positive/neutral/negative/urgent",
    "requires_confirmation": true/false,
    "suggested_response_type": "string - type of response needed",
    "is_follow_up": true/false
}}

POSSIBLE PRIMARY INTENTS FOR {sender_type.upper()}:
"""
        
        if sender_type == 'trainer':
            prompt += """
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
- greeting: Just saying hello
- help: Asking for help/commands
"""
        else:  # client
            prompt += """
- book_session: Booking a training session
- view_schedule: Checking their upcoming sessions
- cancel_session: Cancelling a booking
- reschedule_session: Moving a booking
- view_assessment: Checking fitness assessment results
- check_progress: Viewing their progress
- request_workout: Asking for a workout plan
- payment_query: Question about payment
- general_question: General query
- greeting: Just saying hello
- help: Asking for help
"""
        
        prompt += """
Be precise and extract ALL mentioned information. 
Consider South African context (ZA phone numbers, Rand currency, local slang).
The message might be informal or use WhatsApp shorthand.
"""
        
        return prompt
    
    def _build_trainer_context(self, trainer: Dict) -> Dict:
        """Build context about the trainer"""
        try:
            # Get trainer's clients
            clients = self.db.table('clients').select('name, sessions_remaining')\
                .eq('trainer_id', trainer['id']).execute()
            
            # Get today's schedule
            today = datetime.now(self.sa_tz).date()
            bookings = self.db.table('bookings').select('session_datetime, clients(name)')\
                .eq('trainer_id', trainer['id'])\
                .gte('session_datetime', today.isoformat())\
                .lt('session_datetime', (today + timedelta(days=1)).isoformat())\
                .execute()
            
            return {
                'name': trainer.get('name'),
                'id': trainer.get('id'),
                'client_names': [c['name'] for c in clients.data] if clients.data else [],
                'client_count': len(clients.data) if clients.data else 0,
                'todays_sessions': len(bookings.data) if bookings.data else 0,
                'settings': trainer.get('settings', {})
            }
        except Exception as e:
            log_error(f"Error building trainer context: {str(e)}")
            return {'name': trainer.get('name'), 'id': trainer.get('id')}
    
    def _build_client_context(self, client: Dict) -> Dict:
        """Build context about the client"""
        try:
            trainer = client.get('trainers', {})
            
            # Get upcoming bookings
            bookings = self.db.table('bookings').select('session_datetime')\
                .eq('client_id', client['id'])\
                .gte('session_datetime', datetime.now(self.sa_tz).isoformat())\
                .order('session_datetime')\
                .limit(3)\
                .execute()
            
            return {
                'name': client.get('name'),
                'id': client.get('id'),
                'trainer_name': trainer.get('name', 'your trainer'),
                'sessions_remaining': client.get('sessions_remaining', 0),
                'upcoming_sessions': len(bookings.data) if bookings.data else 0,
                'next_session': bookings.data[0]['session_datetime'] if bookings.data else None
            }
        except Exception as e:
            log_error(f"Error building client context: {str(e)}")
            return {'name': client.get('name'), 'id': client.get('id')}
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse Claude's response into structured data"""
        try:
            # Extract JSON from response
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
                'sentiment': 'neutral'
            }
    
    def _validate_intent(self, intent_data: Dict, sender_data: Dict, 
                        sender_type: str) -> Dict:
        """Validate and enrich the AI's intent understanding"""
        
        # Ensure required fields
        intent_data.setdefault('primary_intent', 'general_question')
        intent_data.setdefault('confidence', 0.5)
        intent_data.setdefault('extracted_data', {})
        intent_data.setdefault('requires_confirmation', False)
        
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
        
        # Define keyword mappings
        intent_keywords = {
            'greeting': ['hi', 'hello', 'hey', 'howzit', 'sawubona', 'molo'],
            'help': ['help', 'commands', 'what can you do'],
            'schedule': ['schedule', 'bookings', 'appointments', 'sessions', 'calendar', 'week', 'my week', 'weekly', 'upcoming'],
            'add_client': ['add client', 'new client', 'register client'],
            'workout': ['workout', 'exercise', 'training plan', 'program'],
            'assessment': ['assessment', 'fitness test', 'evaluate', 'measure'],
            'dashboard': ['dashboard', 'web view', 'portal'],
            'book_session': ['book', 'appointment', 'session', 'training'],
            'cancel': ['cancel', 'remove'],
            'reschedule': ['reschedule', 'move', 'change time']
        }
        
        # Check each intent
        detected_intent = 'general_question'
        confidence = 0.3
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_intent = intent
                confidence = 0.6
                break
        
        return {
            'primary_intent': detected_intent,
            'confidence': confidence,
            'extracted_data': {},
            'sentiment': 'neutral',
            'requires_confirmation': False
        }
    
    def generate_smart_response(self, intent_data: Dict, sender_type: str, 
                               sender_data: Dict) -> str:
        """Generate an appropriate response based on intent"""
        
        intent = intent_data.get('primary_intent')
        extracted = intent_data.get('extracted_data', {})
        confidence = intent_data.get('confidence', 0)
        
        # Low confidence - ask for clarification
        if confidence < 0.5:
            return self._get_clarification_response(sender_type, sender_data)
        
        # High confidence - execute the intent
        response_methods = {
            'greeting': self._respond_to_greeting,
            'help': self._respond_with_help,
            'add_client': self._respond_to_add_client,
            'view_schedule': self._respond_with_schedule,
            'send_workout': self._respond_to_workout_request,
            'book_session': self._respond_to_booking,
            'cancel_session': self._respond_to_cancellation,
            'view_dashboard': self._respond_with_dashboard_link,
            'start_assessment': self._respond_to_assessment
        }
        
        handler = response_methods.get(intent, self._respond_to_general)
        return handler(sender_data, extracted, sender_type)
    
    def _get_clarification_response(self, sender_type: str, sender_data: Dict) -> str:
        """Ask for clarification when intent is unclear"""
        name = sender_data.get('name', 'there')
        
        if sender_type == 'trainer':
            return f"""I'm not quite sure what you need, {name}. 
            
You can try:
• "Add client John Smith 0821234567"
• "Show my schedule"
• "Send workout for Sarah"
• "View dashboard"
• "Start assessment for Mike"

What would you like to do? 😊"""
        else:
            return f"""I didn't quite catch that, {name}.
            
You can:
• "Book session for Tuesday 2pm"
• "Show my upcoming sessions"
• "Cancel my next session"
• "View my fitness results"

What would you like help with? 💪"""
    
    # Response generation methods
    def _respond_to_greeting(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        name = sender_data.get('name', 'there')
        if sender_type == 'trainer':
            return f"Hey {name}! Ready to manage your fitness empire? What can I help with today? 💪"
        else:
            return f"Hi {name}! How's your fitness journey going? What can I help you with? 😊"
    
    def _respond_with_help(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        name = sender_data.get('name', 'there')
        if sender_type == 'trainer':
            return f"""Here's what I can do for you, {name}:

📱 **Client Management**
• Add new clients
• View all clients
• Check client balances

📅 **Scheduling**
• View your schedule
• See today's sessions
• Check weekly calendar

💪 **Workouts & Assessments**
• Send workouts to clients
• Start fitness assessments
• Track client progress

📊 **Business**
• View dashboard
• Check revenue
• Send reminders

Just tell me what you need! 🚀"""
        else:
            trainer_name = sender_data.get('trainer_name', 'your trainer')
            return f"""I can help you with:

📅 Book training sessions
👀 View your schedule
✏️ Reschedule or cancel
📊 Check your fitness assessment
💪 Get workouts from {trainer_name}
📈 Track your progress

What would you like to do? 😊"""
    
    def _respond_to_add_client(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        """Handle add client intent"""
        if extracted.get('client_name') and extracted.get('phone_number'):
            # We have enough info to add
            return f"""Perfect! I'll add {extracted['client_name']} as your client.

📱 WhatsApp: {extracted['phone_number']}
📧 Email: {extracted.get('email', 'Not provided')}
💰 Sessions: Starting with 0 (you can add packages later)

Shall I send them a welcome message? Reply YES to confirm! ✅"""
        else:
            # Need more info
            missing = []
            if not extracted.get('client_name'):
                missing.append("client's name")
            if not extracted.get('phone_number'):
                missing.append("WhatsApp number")
            
            return f"""I'll help you add a new client! I still need their {' and '.join(missing)}.

Please provide:
📝 Full name
📱 WhatsApp number (10 digits)
📧 Email (optional)

Example: "Add John Smith 0821234567 john@email.com" 💪"""
    
    def _respond_with_schedule(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        """Show schedule based on intent"""
        # This would connect to your existing schedule display logic
        return "Let me get your schedule..."
    
    def _respond_to_workout_request(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        """Handle workout sending"""
        if extracted.get('exercises') and extracted.get('client_name'):
            return f"""Got it! Here's the workout for {extracted['client_name']}:

{chr(10).join(extracted['exercises'])}

Send this workout? Reply YES to confirm! 💪"""
        else:
            return "What workout would you like to send and to which client?"
    
    def _respond_to_booking(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        """Handle booking requests"""
        if extracted.get('parsed_datetime'):
            from datetime import datetime
            dt = datetime.fromisoformat(extracted['parsed_datetime'])
            return f"""Perfect! Booking request for:
            
📅 {dt.strftime('%A, %d %B')}
🕐 {dt.strftime('%I:%M %p')}

Let me check availability... ✅"""
        else:
            return """When would you like to book your session?
            
Available slots this week:
Mon-Fri: 9am, 2pm, 5pm
Saturday: 9am, 11am

Just tell me the day and time! 📅"""
    
    def _respond_to_cancellation(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        """Handle cancellation requests"""
        return "Which session would you like to cancel? Tell me the date/time or say 'next session'."
    
    def _respond_with_dashboard_link(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        """Generate dashboard link"""
        # This would connect to your dashboard service
        return "Generating your dashboard link..."
    
    def _respond_to_assessment(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        """Handle assessment requests"""
        if extracted.get('client_name'):
            return f"I'll start a fitness assessment for {extracted['client_name']}. Sending them the form now..."
        else:
            return "Which client would you like to assess? Just give me their name!"
    
    def _respond_to_general(self, sender_data: Dict, extracted: Dict, sender_type: str) -> str:
        """Handle general questions"""
        return "I understand you have a question. Let me help you with that..."
