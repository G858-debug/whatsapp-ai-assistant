import re
import requests
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Tuple, List
import random
import json

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
            trainer = trainer_context['data']
            message_lower = message_text.lower()
            is_first = trainer_context.get('first_interaction', False)
            
            # Greeting for first interaction only
            greeting = f"Hi {trainer['name']}! I'm Refiloe, your AI assistant. " if is_first else ""
            
            # Check if message contains client details (phone number pattern)
            has_phone = bool(re.search(r'(?:\+27|27|0)?\d{9,10}', message_text))
            has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message_text))
            
            # If they're providing client details directly
            if has_phone or has_email or self.looks_like_client_details(message_text):
                # Try to extract and add the client
                details = self.extract_client_details_naturally(message_text)
                
                if details and details.get('name') and details.get('phone'):
                    # Add the client directly
                    return self.complete_client_addition(trainer, details)
                else:
                    # Ask for clarification
                    missing = []
                    if not details.get('name'):
                        missing.append("name")
                    if not details.get('phone'):
                        missing.append("phone number")
                    
                    return f"""I'm trying to add your client but I need their {' and '.join(missing)}.

Could you provide:
📝 Full name
📱 WhatsApp number
📧 Email (optional)
📅 Training schedule (optional)

Just give me the details! 💪"""
            
            # Natural language client addition request (without details)
            elif any(phrase in message_lower for phrase in ['add client', 'new client', 'onboard client', 'add a client', 'help me add']):
                return f"""{greeting}Let's add your new client! I'll need:

📝 Client's full name
📱 WhatsApp number (e.g., 0821234567)
📧 Email address
📅 How often they'll train (e.g., "twice a week" or "Mondays and Thursdays")

Go ahead! 💪"""
            
            # Update availability
            elif any(phrase in message_lower for phrase in ['my availability', 'available times', 'working hours', 'schedule hours']):
                return self.handle_availability_update(trainer, message_text, greeting)
            
            # Update booking preferences
            elif any(phrase in message_lower for phrase in ['booking preference', 'prefer early', 'prefer late', 'slot preference']):
                return self.handle_preference_update(trainer, message_text, greeting)
            
            # Session duration update
            elif any(phrase in message_lower for phrase in ['session length', 'session duration', 'minutes long', 'hour long']):
                return self.handle_session_duration_update(trainer, message_text, greeting)
            
            # View clients
            elif any(word in message_lower for word in ['my clients', 'list clients', 'show clients']):
                return greeting + self.get_trainer_clients_display(trainer)
            
            # Schedule
            elif any(word in message_lower for word in ['schedule', 'bookings', 'today', 'tomorrow']):
                return greeting + self.get_trainer_schedule_display(trainer)
            
            # Revenue
            elif any(word in message_lower for word in ['revenue', 'payments', 'money', 'earnings']):
                return greeting + self.get_trainer_revenue_display(trainer)
            
            # Help
            elif any(word in message_lower for word in ['help', 'commands', 'what can you do']):
                return self.get_trainer_help_menu(trainer['name'], is_first)
            
            # Just greeting
            elif any(word in message_lower for word in ['hi', 'hello', 'hey']) and len(message_text.split()) <= 3:
                if is_first:
                    return f"Hi {trainer['name']}! I'm Refiloe, your AI assistant. How can I help you today? 💪"
                else:
                    return f"Hey {trainer['name']}! What can I do for you today? 😊"
            
            # General AI response
            else:
                return self.process_with_ai(trainer, message_text, 'trainer', greeting=greeting)
                
        except Exception as e:
            log_error(f"Error handling trainer message: {str(e)}", exc_info=True)
            return "Let me try that again. What would you like help with?"
    
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
            
            # Build context
            if user_type == 'trainer':
                context = f"""You are Refiloe, an AI assistant for personal trainer "{user['name']}" who runs "{user.get('business_name', user['name'] + ' Fitness')}".
                
Keep responses under 3 sentences and WhatsApp-friendly. Don't introduce yourself again."""
            else:
                context = f"""You are Refiloe, an AI assistant helping client "{user['name']}" with their training sessions with trainer "{trainer['name'] if trainer else 'their trainer'}".
                
Client has {user.get('sessions_remaining', 0)} sessions remaining. Keep responses under 3 sentences."""
            
            # Call Claude API
            response = self.call_claude_api(context, message_text)
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

# Update the handle_trainer_message method to include dashboard handling
# Add this condition after the other checks:

# Dashboard request
elif any(phrase in message_lower for phrase in ['dashboard', 'my dashboard', 'show dashboard', 'view dashboard', 'calendar view', 'web view']):
    return self.handle_dashboard_request(trainer, greeting)
    
    # Keep all the other methods from the previous version (handle_client_message, parse_availability, etc.)
    # They remain unchanged...
