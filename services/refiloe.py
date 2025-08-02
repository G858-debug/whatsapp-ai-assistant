import re
import requests
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Tuple

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
    
    def process_message(self, phone_number: str, message_text: str) -> str:
        """Main message processing logic"""
        try:
            # Log incoming message
            self.whatsapp.log_message(phone_number, message_text, 'incoming')
            
            # Identify sender
            sender_context = self.identify_sender(phone_number)
            
            if sender_context['type'] == 'trainer':
                return self.handle_trainer_message(sender_context, message_text)
            elif sender_context['type'] == 'client':
                return self.handle_client_message(sender_context, message_text)
            else:
                return self.handle_unknown_sender(phone_number, message_text)
                
        except Exception as e:
            log_error(f"Error in Refiloe processing: {str(e)}", exc_info=True)
            return "I'm having a quick tech moment. Try that again? 😊"
    
    def identify_sender(self, phone_number: str) -> Dict:
        """Identify if sender is trainer, client, or unknown"""
        try:
            # Check trainers first
            trainer = self.trainer_model.get_by_phone(phone_number)
            if trainer:
                return {'type': 'trainer', 'data': trainer}
            
            # Check clients
            client = self.client_model.get_by_phone(phone_number)
            if client:
                return {'type': 'client', 'data': client}
            
            return {'type': 'unknown', 'data': None}
            
        except Exception as e:
            log_error(f"Error identifying sender: {str(e)}")
            return {'type': 'unknown', 'data': None}
    
    def handle_trainer_message(self, trainer_context: Dict, message_text: str) -> str:
        """Handle messages from trainers"""
        trainer = trainer_context['data']
        message_lower = message_text.lower()
        
        # Natural language client addition
        if any(phrase in message_lower for phrase in ['add client', 'new client', 'onboard client']):
            return self.handle_natural_client_addition(trainer, message_text)
        
        # View clients
        elif any(word in message_lower for word in ['my clients', 'list clients', 'show clients']):
            return self.get_trainer_clients_display(trainer)
        
        # Schedule
        elif any(word in message_lower for word in ['schedule', 'bookings', 'today', 'tomorrow']):
            return self.get_trainer_schedule_display(trainer)
        
        # Revenue
        elif any(word in message_lower for word in ['revenue', 'payments', 'money', 'earnings']):
            return self.get_trainer_revenue_display(trainer)
        
        # Help
        elif any(word in message_lower for word in ['help', 'commands', 'what can you do']):
            return self.get_trainer_help_menu(trainer['name'])
        
        # General AI response
        else:
            return self.process_with_ai(trainer, message_text, 'trainer')
    
    def handle_client_message(self, client_context: Dict, message_text: str) -> str:
        """Handle messages from clients"""
        client = client_context['data']
        trainer = client['trainers']
        message_lower = message_text.lower()
        
        # Booking request
        if any(word in message_lower for word in ['book', 'schedule', 'appointment']):
            return self.handle_client_booking(client, trainer, message_text)
        
        # Natural time booking (e.g., "Tuesday 2pm")
        elif self.detect_time_booking(message_text):
            return self.process_natural_time_booking(client, trainer, message_text)
        
        # Cancellation
        elif any(word in message_lower for word in ['cancel', "can't make it", 'sick']):
            return self.handle_client_cancellation(client, trainer, message_text)
        
        # Reschedule
        elif any(word in message_lower for word in ['reschedule', 'move', 'change time']):
            return self.handle_client_reschedule(client, trainer, message_text)
        
        # Check availability
        elif any(word in message_lower for word in ['available', 'free times', 'when']):
            return self.get_trainer_availability_display(trainer, client)
        
        # Session balance
        elif any(word in message_lower for word in ['sessions left', 'balance', 'remaining']):
            return self.get_client_session_balance(client)
        
        # Help
        elif any(word in message_lower for word in ['help', 'commands']):
            return self.get_client_help_menu(client['name'])
        
        # General AI response
        else:
            return self.process_with_ai(client, message_text, 'client', trainer)
    
    def handle_natural_client_addition(self, trainer: Dict, message_text: str) -> str:
        """Handle natural language client addition"""
        
        # Extract client details
        details = self.extract_client_details_naturally(message_text)
        
        if details and details.get('name') and details.get('phone'):
            # We have enough details, add the client
            result = self.client_model.add_client(trainer['id'], details)
            
            if result['success']:
                # Send onboarding message
                self.send_client_onboarding(
                    details['phone'], 
                    details['name'], 
                    trainer, 
                    result['sessions']
                )
                
                return f"""✅ Perfect! 

{details['name']} is now added to your client list!

📱 I'm sending them a welcome message right now  
📦 Package: {details.get('package', 'single').title()} ({result['sessions']} sessions)  
💬 They'll get booking instructions via WhatsApp

All set, {trainer['name']}! 😊"""
            else:
                return f"I ran into an issue: {result['error']}. Could you try again?"
        
        else:
            # Ask for details
            return f"""Hi {trainer['name']}! 😊

I'd love to help you add a new client! 

Could you give me their details? You can just tell me naturally, like:

"Sarah Johnson, her number is 083 123 4567, email sarah@gmail.com, she wants twice a week"

Or however feels natural to you! I'll figure out the rest. 💪"""
    
    def extract_client_details_naturally(self, text: str) -> Dict:
        """Extract client details from natural language"""
        details = {}
        
        # Phone extraction
        phone_patterns = [
            r'(\+27|27|0)[\s\-]?(\d{2})[\s\-]?(\d{3})[\s\-]?(\d{4})',
            r'(\d{3})[\s\-]?(\d{3})[\s\-]?(\d{4})',
            r'(\d{10})'
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                phone = re.sub(r'[^\d]', '', phone_match.group())
                if phone.startswith('0'):
                    phone = '27' + phone[1:]
                elif not phone.startswith('27') and len(phone) == 10:
                    phone = '27' + phone
                details['phone'] = phone
                break
        
        # Email extraction
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            details['email'] = email_match.group()
        
        # Package extraction
        text_lower = text.lower()
        package_patterns = {
            r'\b(single|one|1)\b': 'single',
            r'\b(4[\-\s]?pack|four|4)\b': '4-pack',
            r'\b(8[\-\s]?pack|eight|8)\b': '8-pack',
            r'\b(12[\-\s]?pack|twelve|12)\b': '12-pack',
            r'\b(monthly|month)\b': 'monthly',
            r'\b(twice\s+a?\s*week|2\s*times?\s+a?\s*week|2x\s*week)\b': '8-pack',
            r'\b(once\s+a?\s*week|1\s*time?\s+a?\s*week|weekly)\b': '4-pack',
            r'\b(three\s+times?\s+a?\s*week|3x\s*week)\b': '12-pack'
        }
        
        for pattern, package in package_patterns.items():
            if re.search(pattern, text_lower):
                details['package'] = package
                break
        
        # Name extraction (improved)
        # Remove phone, email, and package info from text
        clean_text = text
        if details.get('phone'):
            clean_text = re.sub(r'[\d\s\-\+()]+', ' ', clean_text)
        if details.get('email'):
            clean_text = clean_text.replace(details['email'], '')
        
        # Look for capitalized names
        name_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', clean_text)
        if name_match:
            potential_name = name_match.group(1)
            # Avoid common words
            if not any(word in potential_name.lower() for word in 
                      ['email', 'phone', 'client', 'add', 'new', 'week', 'pack']):
                details['name'] = potential_name
        
        log_info(f"Extracted client details: {details}")
        return details
    
    def detect_time_booking(self, message_text: str) -> bool:
        """Detect if message contains a time booking request"""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 
                'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'tomorrow', 'today']
        times = ['morning', 'afternoon', 'evening', 'am', 'pm', ':', 'oclock', 'o\'clock']
        
        message_lower = message_text.lower()
        
        has_day = any(day in message_lower for day in days)
        has_time = any(time in message_lower for time in times) or re.search(r'\d{1,2}(?::\d{2})?', message_text)
        
        return has_day and has_time
    
    def process_natural_time_booking(self, client: Dict, trainer: Dict, message_text: str) -> str:
        """Process natural language time booking"""
        try:
            # Parse the time from message
            booking_time = self.parse_booking_time(message_text)
            
            if not booking_time:
                return "I couldn't understand that time. Could you try again? For example: 'Tuesday 2pm' or 'Tomorrow morning' 😊"
            
            # Check if client has sessions
            if client['sessions_remaining'] <= 0:
                return self.handle_no_sessions_left(client, trainer)
            
            # Attempt to create booking
            result = self.booking_model.create_booking(
                trainer_id=trainer['id'],
                client_id=client['id'],
                session_datetime=booking_time,
                price=trainer['pricing_per_session']
            )
            
            if result['success']:
                return f"""Perfect, {client['name']}! 

✅ Session confirmed for {booking_time.strftime('%A %d %B at %I:%M%p')}
💰 R{trainer['pricing_per_session']:.0f} (from your package)  
📱 I'll send a reminder the day before  

Sessions remaining: {client['sessions_remaining'] - 1} 

Looking forward to your workout! 💪"""
            else:
                # Slot not available
                alternatives_text = ""
                if result.get('alternatives'):
                    alt_list = [alt['display'] for alt in result['alternatives'][:3]]
                    alternatives_text = f"\n\nHow about:\n• " + "\n• ".join(alt_list)
                
                return f"""Sorry {client['name']}, that time slot is already taken! 🙈

{alternatives_text}

Which works better for you?"""
                
        except Exception as e:
            log_error(f"Error in natural time booking: {str(e)}")
            return "I had trouble booking that time. Could you try again? 😊"
    
    def parse_booking_time(self, message_text: str) -> Optional[datetime]:
        """Parse natural language time into datetime"""
        try:
            now = datetime.now(self.sa_tz)
            message_lower = message_text.lower()
            
            # Handle relative days
            target_date = None
            if 'today' in message_lower:
                target_date = now.date()
            elif 'tomorrow' in message_lower:
                target_date = now.date() + timedelta(days=1)
            else:
                # Look for day names
                days = {
                    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                    'friday': 4, 'saturday': 5, 'sunday': 6,
                    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
                    'fri': 4, 'sat': 5, 'sun': 6
                }
                
                for day_name, day_num in days.items():
                    if day_name in message_lower:
                        days_ahead = (day_num - now.weekday()) % 7
                        if days_ahead == 0:  # Same day of week
                            days_ahead = 7  # Next week
                        target_date = now.date() + timedelta(days=days_ahead)
                        break
            
            if not target_date:
                return None
            
            # Parse time
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', message_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                am_pm = time_match.group(3)
                
                # Handle AM/PM
                if am_pm == 'pm' and hour < 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0
                
                # Handle "morning", "afternoon", "evening"
            elif 'morning' in message_lower:
                hour, minute = 9, 0
            elif 'afternoon' in message_lower:
                hour, minute = 14, 0
            elif 'evening' in message_lower:
                hour, minute = 17, 0
            else:
                return None
            
            # Create datetime
            booking_time = datetime.combine(
                target_date,
                datetime.min.time().replace(hour=hour, minute=minute)
            )
            booking_time = self.sa_tz.localize(booking_time)
            
            # Don't allow past bookings
            if booking_time < now:
                return None
            
            return booking_time
            
        except Exception as e:
            log_error(f"Error parsing booking time: {str(e)}")
            return None
    
    def handle_no_sessions_left(self, client: Dict, trainer: Dict) -> str:
        """Handle when client has no sessions left"""
        return f"""Hey {client['name']}! 

You've used up all your sessions from your {client['package_type']} package! 🎉

Want to continue? Here are your options:
• Another {client['package_type']} package
• Try a different package
• Book individual sessions at R{trainer['pricing_per_session']:.0f} each

Should I let {trainer['name']} know you're ready for more? 😊"""
    
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

💪 Your package: {sessions} sessions  
💵 Per session: R{trainer['pricing_per_session']:.0f}  
📱 How it works: Just message me here!

Want to book your first session? Say something like "Book Tuesday morning" or "When are you free?" 

I'll take care of the rest! 😊"""
                
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
                
                self.whatsapp.send_message(client_phone, availability_msg)
            
            # Send in background thread
            threading.Thread(target=send_delayed).start()
            
        except Exception as e:
            log_error(f"Error in client onboarding: {str(e)}")
    
    def get_trainer_clients_display(self, trainer: Dict) -> str:
        """Display trainer's client list"""
        try:
            clients = self.client_model.get_trainer_clients(trainer['id'])
            
            if not clients:
                return f"You don't have any active clients yet, {trainer['name']}! Ready to add your first one? 😊"
            
            response = f"📋 Your clients, {trainer['name']}:\n\n"
            
            for client in clients:
                last_session = client.get('last_session_date')
                if last_session:
                    last_date = datetime.fromisoformat(last_session)
                    days_ago = (datetime.now(self.sa_tz) - last_date).days
                    last_text = f"{days_ago} days ago" if days_ago > 0 else "Today"
                else:
                    last_text = "No sessions yet"
                
                response += f"• {client['name']} ({client['sessions_remaining']} left, last: {last_text})\n"
            
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
            )
            
            if not bookings:
                return f"Your week is wide open, {trainer['name']}! 📅\n\nPerfect time for your clients to book sessions 😊"
            
            response = f"📅 Coming up for you, {trainer['name']}:\n\n"
            
            for booking in bookings:
                session_time = datetime.fromisoformat(booking['session_datetime'])
                day = session_time.strftime('%a %d %b')
                time = session_time.strftime('%I:%M%p').lower()
                client_name = booking['clients']['name']
                
                response += f"• {day} at {time} - {client_name}\n"
            
            return response + "\nLooking good! 💪"
            
        except Exception as e:
            log_error(f"Error getting trainer schedule: {str(e)}")
            return f"Let me check your schedule again, {trainer['name']}..."
    
    def get_trainer_revenue_display(self, trainer: Dict) -> str:
        """Display trainer's revenue summary"""
        try:
            # For now, calculate based on bookings
            # TODO: Implement proper payment tracking
            
            now = datetime.now(self.sa_tz)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get this month's bookings
            bookings = self.booking_model.get_trainer_schedule(
                trainer['id'], month_start, now
            )
            
            completed_revenue = sum(b['price'] for b in bookings if b['status'] == 'completed')
            scheduled_revenue = sum(b['price'] for b in bookings if b['status'] == 'scheduled')
            
            # Get active clients
            clients = self.client_model.get_trainer_clients(trainer['id'])
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
                       trainer: Optional[Dict] = None) -> str:
        """Process message with Claude AI"""
        try:
            if not self.config.ANTHROPIC_API_KEY:
                return self.get_fallback_response(user_type, user.get('name', 'there'))
            
            # Build context
            if user_type == 'trainer':
                context = f"""You are Refiloe, an AI assistant for personal trainer "{user['name']}" who runs "{user.get('business_name', user['name'] + ' Fitness')}".
                
Keep responses under 3 sentences and WhatsApp-friendly."""
            else:
                context = f"""You are Refiloe, an AI assistant helping client "{user['name']}" with their training sessions with trainer "{trainer['name']}".
                
Client has {user['sessions_remaining']} sessions remaining."""
            
            # Call Claude API
            response = self.call_claude_api(context, message_text)
            return response
            
        except Exception as e:
            log_error(f"Error with AI processing: {str(e)}")
            return self.get_fallback_response(user_type, user.get('name', 'there'))
    
    def call_claude_api(self, context: str, message: str) -> str:
        """Call Claude API with Sonnet 4"""
        try:
            url = "https://api.anthropic.com/v1/messages"
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": self.config.AI_MODEL,  # Now using Sonnet 4
                "max_tokens": 150,
                "messages": [
                    {"role": "user", "content": f"{context}\n\nUser message: {message}"}
                ]
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                log_error(f"Claude API error: {response.status_code} - {response.text}")
                return "I'm having a quick tech moment. Try that again? 😊"
                
        except Exception as e:
            log_error(f"Error calling Claude API: {str(e)}")
            return "Let me try that again for you! 😊"
    
    def get_fallback_response(self, user_type: str, name: str) -> str:
        """Fallback response when AI is not available"""
        if user_type == 'trainer':
            return f"Hi {name}! I'm getting set up to help you better. For now, try 'my clients', 'schedule', or 'add client'! 😊"
        else:
            return f"Hi {name}! I'm here to help with your training sessions. Try 'book session' or 'when are you free'! 😊"
    
    def get_trainer_help_menu(self, trainer_name: str) -> str:
        """Get help menu for trainers"""
        return f"""Hi {trainer_name}! I'm Refiloe 😊

Here's what I can help with:

*Clients:*  
• "Add new client" - I'll ask for details  
• "My clients" - See your client list  
• "Send reminders" - Reach out to everyone  

*Schedule:*  
• "My schedule" - This week's sessions  
• "Revenue" - How you're doing this month  

*Natural chat:*  
Just tell me what you need! I understand normal conversation 💬

What can I help you with? 💪"""
    
    def get_client_help_menu(self, client_name: str) -> str:
        """Get help menu for clients"""
        return f"""Hi {client_name}! I'm Refiloe 😊

*Quick booking:*  
• "Book session" - See available times  
• "Tuesday 2pm" - Book specific time  
• "When are you free?" - Check availability  

*Manage sessions:*  
• "Reschedule" - Move your booking  
• "Cancel" - Cancel if needed  
• "Sessions left" - Check your balance  

*Just chat naturally!*  
I understand normal conversation 💬

What can I help with? 💪"""
    
    def handle_unknown_sender(self, phone_number: str, message_text: str) -> str:
        """Handle messages from unknown senders"""
        message_lower = message_text.lower()
        
        if any(word in message_lower for word in ['trainer', 'register', 'sign up', 'join']):
            return """👋 Hi there! I'm Refiloe!

I help personal trainers manage their clients automatically via WhatsApp! 

Want to join as a trainer? Here's how:
• Visit our website (coming soon!)
• Or message: "REGISTER TRAINER [Your Name] [Email]"

Example: "REGISTER TRAINER John Smith john@email.com"

I'll handle all your client bookings 24/7! 💪"""
        
        else:
            return """👋 Hi! I'm Refiloe, an AI assistant for personal trainers! 

**If you're a trainer:** I can manage your client bookings, scheduling, and reminders automatically!

**If you're a client:** Your trainer needs to add you to the system first, then I'll help you book sessions easily!

Reply "TRAINER" if you want to sign up! 😊"""
    
    def add_trainer(self, data: Dict) -> Dict:
        """Add a new trainer (admin function)"""
        try:
            trainer_data = {
                'name': data['name'],
                'whatsapp': data['whatsapp'],
                'email': data['email'],
                'business_name': data.get('business_name', data['name'] + ' Fitness'),
                'pricing_per_session': data.get('pricing_per_session', self.config.DEFAULT_SESSION_PRICE)
            }
            
            result = self.trainer_model.create_trainer(trainer_data)
            
            if result['success']:
                # Send welcome message
                welcome_msg = f"""Welcome to Refiloe, {data['name']}! 🎉

I'm your AI assistant and I'm here to help manage your fitness business!

Here's what I can do:
• Manage client bookings 24/7
• Send automatic reminders
• Track your revenue
• Handle rescheduling & cancellations

To get started, just add your first client by saying:
"Add new client [Name] [Phone] [Email] [Package]"

Example: "Add new client Sarah 0821234567 sarah@email.com 8-pack"

I'm here whenever you need me! 💪"""
                
                self.whatsapp.send_message(data['whatsapp'], welcome_msg)
                
                return {
                    'success': True,
                    'trainer_id': result['trainer_id'],
                    'message': f"Trainer {data['name']} added successfully!"
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to add trainer')
                }
                
        except Exception as e:
            log_error(f"Error adding trainer: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to add trainer'
            }
