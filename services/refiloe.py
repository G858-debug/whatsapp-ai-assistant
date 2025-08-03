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
            result = self.db.table('messages').select('id').eq(
                'whatsapp_from', phone_number
            ).limit(2).execute()
            
            # If more than 1 message, they've interacted before
            return len(result.data) > 1
            
        except Exception as e:
            log_error(f"Error checking interaction history: {str(e)}")
            return False
    
    def process_message(self, phone_number: str, message_text: str) -> str:
        """Main message processing logic"""
        try:
            # Log incoming message
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
        is_first = trainer_context.get('first_interaction', False)
        
        # Greeting for first interaction only
        greeting = f"Hi {trainer['name']}! I'm Refiloe, your AI assistant. " if is_first else ""
        
        # Natural language client addition
        if any(phrase in message_lower for phrase in ['add client', 'new client', 'onboard client', 'add a client']):
            return f"""{greeting}Let's add your new client! I'll need:

📝 Client's full name
📱 WhatsApp number (e.g., 0821234567)
📧 Email address
📅 How often they'll train (e.g., "twice a week" or "Mondays and Thursdays")

You can tell me naturally, like:
"Sarah Johnson, 0821234567, sarah@email.com, she'll train Mondays, Wednesdays and Fridays"

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
        
        # General AI response
        else:
            return self.process_with_ai(trainer, message_text, 'trainer', greeting=greeting)
    
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

Or just tell me naturally! 😊"""
            
            # Store availability in trainer settings
            trainer_settings = {
                'availability': availability,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Update in database (you'll need to add a trainer_settings field or table)
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
    
    def handle_preference_update(self, trainer: Dict, message_text: str, greeting: str) -> str:
        """Handle booking preference updates"""
        try:
            # Parse preferences
            preferences = self.parse_booking_preferences(message_text)
            
            if not preferences:
                return f"""{greeting}I can set your booking preferences!

Tell me how you'd like slots filled. For example:

"Monday to Thursday, book the earliest slots first
Friday and Saturday, prefer midday slots first"

Or: "Always book morning slots first" 

What works best for you? 😊"""
            
            # Store preferences
            trainer_settings = trainer.get('settings', {})
            if isinstance(trainer_settings, str):
                trainer_settings = json.loads(trainer_settings)
            
            trainer_settings['booking_preferences'] = preferences
            trainer_settings['updated_at'] = datetime.now(self.sa_tz).isoformat()
            
            result = self.trainer_model.update_trainer(
                trainer['id'],
                {'settings': json.dumps(trainer_settings)}
            )
            
            if result['success']:
                return f"""{greeting}Got it! Your booking preferences are set:

{self.format_preferences_display(preferences)}

I'll automatically assign slots based on these preferences! 👍"""
            
        except Exception as e:
            log_error(f"Error updating preferences: {str(e)}")
            return f"{greeting}Let me try that again. How would you like me to book your slots?"
    
    def handle_session_duration_update(self, trainer: Dict, message_text: str, greeting: str) -> str:
        """Handle session duration updates"""
        try:
            # Parse duration
            duration = self.parse_session_duration(message_text)
            
            if not duration:
                return f"""{greeting}What's your typical session duration?

Examples:
• "45 minutes"
• "90 minutes"
• "2 hours"

Default is 60 minutes. What works for you?"""
            
            # Update trainer settings
            result = self.trainer_model.update_trainer(
                trainer['id'],
                {'default_session_duration': duration}
            )
            
            if result['success']:
                hours = duration // 60
                minutes = duration % 60
                duration_text = f"{hours} hour{'s' if hours > 1 else ''}" if hours > 0 else ""
                if minutes > 0:
                    duration_text += f" {minutes} minutes" if hours > 0 else f"{minutes} minutes"
                
                return f"""{greeting}Perfect! Your default session duration is now {duration_text}.

All new bookings will use this duration. 💪"""
            
        except Exception as e:
            log_error(f"Error updating session duration: {str(e)}")
            return f"{greeting}Let me try that again. How long are your typical sessions?"
    
    def handle_client_message(self, client_context: Dict, message_text: str) -> str:
        """Handle messages from clients"""
        client = client_context['data']
        trainer = client['trainers']
        message_lower = message_text.lower()
        is_first = client_context.get('first_interaction', False)
        
        # Greeting for first interaction only
        greeting = f"Hi {client['name']}! I'm Refiloe, {trainer['name']}'s AI assistant. " if is_first else ""
        
        # Booking request with general availability (e.g., "Saturday mornings")
        if self.detect_general_availability(message_text):
            return self.handle_general_availability_booking(client, trainer, message_text, greeting)
        
        # Specific time booking (e.g., "Tuesday 2pm")
        elif self.detect_time_booking(message_text):
            return self.process_specific_time_booking(client, trainer, message_text, greeting)
        
        # Booking request
        elif any(word in message_lower for word in ['book', 'schedule', 'appointment']):
            return self.handle_client_booking(client, trainer, message_text, greeting)
        
        # Confirmation of suggested time
        elif any(word in message_lower for word in ['yes', 'confirm', 'that works', 'perfect', 'great']):
            return self.confirm_pending_booking(client, trainer, greeting)
        
        # Cancellation
        elif any(word in message_lower for word in ['cancel', "can't make it", 'sick']):
            return self.handle_client_cancellation(client, trainer, message_text, greeting)
        
        # Reschedule
        elif any(word in message_lower for word in ['reschedule', 'move', 'change time']):
            return self.handle_client_reschedule(client, trainer, message_text, greeting)
        
        # Check availability
        elif any(word in message_lower for word in ['available', 'free times', 'when']):
            return self.get_trainer_availability_display(trainer, client, greeting)
        
        # Session balance
        elif any(word in message_lower for word in ['sessions left', 'balance', 'remaining']):
            return greeting + self.get_client_session_balance(client)
        
        # Help
        elif any(word in message_lower for word in ['help', 'commands']):
            return self.get_client_help_menu(client['name'], is_first)
        
        # General AI response
        else:
            return self.process_with_ai(client, message_text, 'client', trainer, greeting)
    
    def detect_general_availability(self, message_text: str) -> bool:
        """Detect general availability like 'Saturday mornings' or 'weekday evenings'"""
        message_lower = message_text.lower()
        
        # Time periods
        periods = ['morning', 'afternoon', 'evening', 'lunch']
        
        # Days
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                'weekday', 'weekend']
        
        # Check for combination of day + period
        has_day = any(day in message_lower for day in days)
        has_period = any(period in message_lower for period in periods)
        
        # Also check for patterns like "I'm free on..."
        availability_phrases = ['free on', 'available on', 'can do', 'works for me']
        has_availability_phrase = any(phrase in message_lower for phrase in availability_phrases)
        
        return (has_day and has_period) or (has_availability_phrase and (has_day or has_period))
    
    def handle_general_availability_booking(self, client: Dict, trainer: Dict, 
                                           message_text: str, greeting: str) -> str:
        """Handle general availability like 'Saturday mornings'"""
        try:
            # Parse the general availability
            day_period = self.parse_general_availability(message_text)
            
            if not day_period:
                return f"{greeting}I couldn't understand that time. Could you be more specific? For example: 'Saturday mornings' or 'Tuesday afternoons' 😊"
            
            # Get trainer's availability for that day/period
            trainer_slots = self.get_trainer_slots_for_period(
                trainer['id'], 
                day_period['day'], 
                day_period['period']
            )
            
            if not trainer_slots:
                alternatives = self.suggest_alternative_periods(trainer['id'], day_period)
                return f"""{greeting}Unfortunately {trainer['name']} isn't available {day_period['display']}.

{alternatives}

What works better for you?"""
            
            # Pick a random available slot
            selected_slot = random.choice(trainer_slots)
            
            # Store as pending booking
            self.store_pending_booking(client['id'], trainer['id'], selected_slot)
            
            return f"""{greeting}Great! {trainer['name']} is available {day_period['display']}!

How about {selected_slot['display']}?

Reply "YES" to confirm this time, or suggest another time if this doesn't work! 😊"""
            
        except Exception as e:
            log_error(f"Error handling general availability: {str(e)}")
            return f"{greeting}Let me check {trainer['name']}'s availability. What times generally work for you?"
    
    def store_pending_booking(self, client_id: str, trainer_id: str, slot: Dict):
        """Store a pending booking for confirmation"""
        try:
            # Store in conversation history (or could use a pending_bookings table)
            key = f"pending_{client_id}"
            self.conversation_history[key] = {
                'trainer_id': trainer_id,
                'client_id': client_id,
                'slot': slot,
                'created_at': datetime.now(self.sa_tz),
                'expires_at': datetime.now(self.sa_tz) + timedelta(minutes=30)
            }
            log_info(f"Stored pending booking for client {client_id}")
            
        except Exception as e:
            log_error(f"Error storing pending booking: {str(e)}")
    
    def confirm_pending_booking(self, client: Dict, trainer: Dict, greeting: str) -> str:
        """Confirm a pending booking"""
        try:
            key = f"pending_{client['id']}"
            
            if key not in self.conversation_history:
                return f"{greeting}I don't have a pending booking to confirm. Would you like to book a new session?"
            
            pending = self.conversation_history[key]
            
            # Check if expired
            if datetime.now(self.sa_tz) > pending['expires_at']:
                del self.conversation_history[key]
                return f"{greeting}That booking offer has expired. Let me show you current availability..."
            
            # Create the actual booking
            slot = pending['slot']
            result = self.booking_model.create_booking(
                trainer_id=trainer['id'],
                client_id=client['id'],
                session_datetime=slot['datetime'],
                price=trainer.get('pricing_per_session', 300),
                duration_minutes=trainer.get('default_session_duration', 60)
            )
            
            if result['success']:
                # Clear pending booking
                del self.conversation_history[key]
                
                return f"""✅ Perfect! Your session is confirmed:

📅 {slot['display']}
👨‍🏫 With {trainer['name']}
💰 R{trainer.get('pricing_per_session', 300):.0f}
📍 {trainer.get('location', 'Location to be confirmed')}

I'll send you a reminder the day before!

Sessions remaining: {client['sessions_remaining'] - 1}

See you then! 💪"""
            else:
                return f"{greeting}Oops! That slot just got taken. Let me show you other available times..."
                
        except Exception as e:
            log_error(f"Error confirming booking: {str(e)}")
            return f"{greeting}I had trouble confirming that booking. Let's try again!"
    
    def parse_general_availability(self, message_text: str) -> Optional[Dict]:
        """Parse general availability from message"""
        try:
            message_lower = message_text.lower()
            
            # Day mappings
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6,
                'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
                'fri': 4, 'sat': 5, 'sun': 6
            }
            
            # Period mappings
            period_map = {
                'morning': {'start': 6, 'end': 12, 'name': 'morning'},
                'afternoon': {'start': 12, 'end': 17, 'name': 'afternoon'},
                'evening': {'start': 17, 'end': 21, 'name': 'evening'},
                'lunch': {'start': 12, 'end': 14, 'name': 'lunchtime'}
            }
            
            # Find day
            found_day = None
            found_day_name = None
            for day_name, day_num in day_map.items():
                if day_name in message_lower:
                    found_day = day_num
                    found_day_name = day_name.capitalize()
                    break
            
            # Find period
            found_period = None
            for period_name, period_info in period_map.items():
                if period_name in message_lower:
                    found_period = period_info
                    break
            
            if found_day is not None and found_period:
                return {
                    'day': found_day,
                    'day_name': found_day_name,
                    'period': found_period,
                    'display': f"{found_day_name} {found_period['name']}s"
                }
            
            return None
            
        except Exception as e:
            log_error(f"Error parsing general availability: {str(e)}")
            return None
    
    def get_trainer_slots_for_period(self, trainer_id: str, day: int, period: Dict) -> List[Dict]:
        """Get available trainer slots for a specific day and period"""
        try:
            # Calculate the date for the next occurrence of this day
            today = datetime.now(self.sa_tz).date()
            days_ahead = (day - today.weekday()) % 7
            if days_ahead == 0:  # Same day of week
                days_ahead = 7  # Next week
            target_date = today + timedelta(days=days_ahead)
            
            # Get trainer's availability settings
            trainer = self.trainer_model.get_by_id(trainer_id)
            settings = trainer.get('settings', {})
            if isinstance(settings, str):
                settings = json.loads(settings)
            
            availability = settings.get('availability', self.config.get_booking_slots())
            
            # Get slots for this day
            day_name = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][day]
            day_slots = availability.get(day_name, [])
            
            # Filter slots within the period
            available_slots = []
            for slot_time in day_slots:
                hour = int(slot_time.split(':')[0])
                if period['start'] <= hour < period['end']:
                    # Create datetime for this slot
                    slot_datetime = datetime.combine(
                        target_date,
                        datetime.strptime(slot_time, '%H:%M').time()
                    )
                    slot_datetime = self.sa_tz.localize(slot_datetime)
                    
                    # Check if slot is actually available
                    if self.booking_model.is_slot_available(trainer_id, slot_datetime):
                        available_slots.append({
                            'datetime': slot_datetime,
                            'display': slot_datetime.strftime('%A %d %B at %I:%M%p')
                        })
            
            return available_slots
            
        except Exception as e:
            log_error(f"Error getting trainer slots for period: {str(e)}")
            return []
    
    def parse_availability(self, message_text: str) -> Optional[Dict]:
        """Parse availability schedule from natural language"""
        try:
            availability = {}
            lines = message_text.lower().split('\n')
            
            day_patterns = {
                'monday': ['monday', 'mon'],
                'tuesday': ['tuesday', 'tue'],
                'wednesday': ['wednesday', 'wed'],
                'thursday': ['thursday', 'thu'],
                'friday': ['friday', 'fri'],
                'saturday': ['saturday', 'sat'],
                'sunday': ['sunday', 'sun']
            }
            
            for line in lines:
                # Look for day ranges (e.g., "monday to friday")
                range_match = re.search(r'(\w+)\s+to\s+(\w+)', line)
                if range_match:
                    start_day = range_match.group(1)
                    end_day = range_match.group(2)
                    
                    # Extract times from the line
                    times = self.extract_time_slots(line)
                    
                    # Apply to day range
                    if times:
                        applying = False
                        for day_name, patterns in day_patterns.items():
                            if any(p in start_day for p in patterns):
                                applying = True
                            if applying:
                                availability[day_name] = times
                            if any(p in end_day for p in patterns):
                                break
                else:
                    # Look for individual days
                    for day_name, patterns in day_patterns.items():
                        if any(pattern in line for pattern in patterns):
                            times = self.extract_time_slots(line)
                            if times:
                                availability[day_name] = times
                            elif 'closed' in line or 'off' in line:
                                availability[day_name] = []
            
            return availability if availability else None
            
        except Exception as e:
            log_error(f"Error parsing availability: {str(e)}")
            return None
    
    def extract_time_slots(self, text: str) -> List[str]:
        """Extract time slots from text"""
        slots = []
        
        # Look for time ranges (e.g., "9am-12pm")
        range_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*[-to]+\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?'
        matches = re.finditer(range_pattern, text.lower())
        
        for match in matches:
            start_hour = int(match.group(1))
            start_min = int(match.group(2) or 0)
            start_ampm = match.group(3)
            end_hour = int(match.group(4))
            end_min = int(match.group(5) or 0)
            end_ampm = match.group(6)
            
            # Convert to 24-hour format
            if start_ampm == 'pm' and start_hour < 12:
                start_hour += 12
            if end_ampm == 'pm' and end_hour < 12:
                end_hour += 12
            
            # Generate hourly slots
            current_hour = start_hour
            while current_hour < end_hour:
                slots.append(f"{current_hour:02d}:00")
                current_hour += 1
        
        # Also look for individual times
        time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)'
        if not slots:
            matches = re.finditer(time_pattern, text.lower())
            for match in matches:
                hour = int(match.group(1))
                minute = int(match.group(2) or 0)
                ampm = match.group(3)
                
                if ampm == 'pm' and hour < 12:
                    hour += 12
                
                slots.append(f"{hour:02d}:{minute:02d}")
        
        return sorted(list(set(slots)))
    
    def parse_booking_preferences(self, message_text: str) -> Optional[Dict]:
        """Parse booking preferences from natural language"""
        try:
            preferences = {}
            message_lower = message_text.lower()
            
            # Time preference patterns
            time_preferences = {
                'early': 'earliest',
                'morning': 'earliest',
                'late': 'latest',
                'evening': 'latest',
                'afternoon': 'middle',
                'midday': 'middle',
                'noon': 'middle'
            }
            
            # Day patterns
            day_groups = {
                'weekdays': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
                'weekends': ['saturday', 'sunday'],
                'monday': ['monday'],
                'tuesday': ['tuesday'],
                'wednesday': ['wednesday'],
                'thursday': ['thursday'],
                'friday': ['friday'],
                'saturday': ['saturday'],
                'sunday': ['sunday']
            }
            
            # Parse preferences
            lines = message_lower.split(',')
            for line in lines:
                # Find day references
                found_days = []
                for group_name, days in day_groups.items():
                    if group_name in line:
                        found_days.extend(days)
                
                # Also check for "monday to thursday" patterns
                range_match = re.search(r'(\w+)\s+to\s+(\w+)', line)
                if range_match:
                    start = range_match.group(1)
                    end = range_match.group(2)
                    # Add logic to expand day range
                    day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    try:
                        start_idx = day_order.index(start)
                        end_idx = day_order.index(end)
                        found_days = day_order[start_idx:end_idx+1]
                    except ValueError:
                        pass
                
                # Find time preference
                found_preference = 'earliest'  # default
                for keyword, pref in time_preferences.items():
                    if keyword in line:
                        found_preference = pref
                        break
                
                # Apply preference to found days
                for day in found_days:
                    preferences[day] = found_preference
            
            return preferences if preferences else None
            
        except Exception as e:
            log_error(f"Error parsing booking preferences: {str(e)}")
            return None
    
    def parse_session_duration(self, message_text: str) -> Optional[int]:
        """Parse session duration from natural language"""
        try:
            message_lower = message_text.lower()
            
            # Look for patterns like "45 minutes", "1 hour", "90 mins"
            patterns = [
                (r'(\d+)\s*hour', lambda x: int(x) * 60),
                (r'(\d+)\s*hr', lambda x: int(x) * 60),
                (r'(\d+)\s*minute', lambda x: int(x)),
                (r'(\d+)\s*min', lambda x: int(x)),
                (r'(\d+\.5)\s*hour', lambda x: int(float(x) * 60)),
                (r'hour\s+and\s+(\d+)', lambda x: 60 + int(x)),
                (r'(\d+)\s+and\s+a\s+half\s+hour', lambda x: int(x) * 60 + 30)
            ]
            
            for pattern, converter in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    return converter(match.group(1))
            
            return None
            
        except Exception as e:
            log_error(f"Error parsing session duration: {str(e)}")
            return None
    
    def format_availability_display(self, availability: Dict) -> str:
        """Format availability for display"""
        lines = []
        day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day in day_order:
            if day in availability:
                slots = availability[day]
                if slots:
                    # Format time slots nicely
                    formatted_slots = []
                    for slot in slots:
                        hour = int(slot.split(':')[0])
                        am_pm = 'am' if hour < 12 else 'pm'
                        display_hour = hour if hour <= 12 else hour - 12
                        if display_hour == 0:
                            display_hour = 12
                        formatted_slots.append(f"{display_hour}{am_pm}")
                    
                    lines.append(f"📅 {day.capitalize()}: {', '.join(formatted_slots)}")
                else:
                    lines.append(f"📅 {day.capitalize()}: Closed")
        
        return '\n'.join(lines)
    
    def format_preferences_display(self, preferences: Dict) -> str:
        """Format booking preferences for display"""
        lines = []
        
        # Group days by preference
        pref_groups = {}
        for day, pref in preferences.items():
            if pref not in pref_groups:
                pref_groups[pref] = []
            pref_groups[pref].append(day.capitalize())
        
        for pref, days in pref_groups.items():
            if pref == 'earliest':
                lines.append(f"⏰ {', '.join(days)}: Book earliest slots first")
            elif pref == 'latest':
                lines.append(f"🌙 {', '.join(days)}: Book latest slots first")
            elif pref == 'middle':
                lines.append(f"☀️ {', '.join(days)}: Book midday slots first")
        
        return '\n'.join(lines)
    
    def process_specific_time_booking(self, client: Dict, trainer: Dict, message_text: str, greeting: str) -> str:
        """Process specific time booking like 'Tuesday 2pm'"""
        try:
            # Parse the specific time
            booking_time = self.parse_booking_time(message_text)
            
            if not booking_time:
                return f"{greeting}I couldn't understand that time. Could you try again? For example: 'Tuesday 2pm' or 'Tomorrow morning' 😊"
            
            # Check if client has sessions
            if client['sessions_remaining'] <= 0:
                return self.handle_no_sessions_left(client, trainer)
            
            # Get trainer's session duration
            duration = trainer.get('default_session_duration', 60)
            
            # Attempt to create booking
            result = self.booking_model.create_booking(
                trainer_id=trainer['id'],
                client_id=client['id'],
                session_datetime=booking_time,
                price=trainer['pricing_per_session'],
                duration_minutes=duration
            )
            
            if result['success']:
                return f"""{greeting}✅ Perfect! Your session is confirmed:

📅 {booking_time.strftime('%A %d %B at %I:%M%p')}
⏱️ Duration: {duration} minutes
💰 R{trainer['pricing_per_session']:.0f} (from your package)
📱 I'll send a reminder the day before

Sessions remaining: {client['sessions_remaining'] - 1}

See you then! 💪"""
            else:
                # Slot not available
                alternatives_text = ""
                if result.get('alternatives'):
                    alt_list = [alt['display'] for alt in result['alternatives'][:3]]
                    alternatives_text = f"\n\nHow about:\n• " + "\n• ".join(alt_list)
                
                return f"""{greeting}Sorry, that time slot is already taken! 🙈

{alternatives_text}

Which works better for you?"""
                
        except Exception as e:
            log_error(f"Error in specific time booking: {str(e)}")
            return f"{greeting}I had trouble booking that time. Could you try again? 😊"
    
    def detect_time_booking(self, message_text: str) -> bool:
        """Detect if message contains a specific time booking request"""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 
                'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'tomorrow', 'today']
        
        message_lower = message_text.lower()
        
        # Check for day
        has_day = any(day in message_lower for day in days)
        
        # Check for specific time (not just period)
        has_specific_time = bool(re.search(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', message_lower))
        
        return has_day and has_specific_time
    
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
                        if days_ahead == 0:
                            days_ahead = 7
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
                
                if am_pm == 'pm' and hour < 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0
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
📧 Email: support@refiloe.co.za
📱 WhatsApp: [Admin number]

I'll handle all your client bookings 24/7! 💪"""
        
        else:
            return f"""{intro}**If you're a trainer:** I can manage your client bookings, scheduling, and reminders automatically!

**If you're a client:** Your trainer needs to add you to the system first, then I'll help you book sessions easily!

Reply "TRAINER" if you want to sign up! 😊"""
    
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
    
    def get_client_help_menu(self, client_name: str, is_first: bool) -> str:
        """Get help menu for clients"""
        greeting = f"Hi {client_name}! I'm Refiloe 😊\n\n" if is_first else ""
        
        return f"""{greeting}*Quick booking:*
• "Book session" - See available times
• "Tuesday 2pm" - Book specific time
• "Saturday mornings" - I'll suggest times

*Manage sessions:*
• "Reschedule" - Move your booking
• "Cancel" - Cancel if needed
• "Sessions left" - Check your balance

Just chat naturally! I understand normal conversation 💬

What can I help with? 💪"""
