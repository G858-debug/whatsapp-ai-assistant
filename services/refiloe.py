from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pytz
import json

from utils.logger import log_info, log_error, log_warning
from services.ai_intent_handler import AIIntentHandler
from services.workout import WorkoutService
from services.assessment import EnhancedAssessmentService
from models.trainer import TrainerModel
from models.client import ClientModel
from models.booking import BookingModel

class RefiloeAssistant:
    """Main assistant class - now AI-powered"""
    
    def __init__(self, config, supabase_client, whatsapp_service, logger):
        self.config = config
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.logger = logger
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Initialize AI Intent Handler
        self.ai_handler = AIIntentHandler(config, supabase_client)
        
        # Initialize models
        self.trainer_model = TrainerModel(supabase_client, config)
        self.client_model = ClientModel(supabase_client, config)
        self.booking_model = BookingModel(supabase_client, config)
        
        # Initialize services
        self.workout_service = WorkoutService(config, supabase_client)
        self.assessment_service = EnhancedAssessmentService(
            config, supabase_client, self.ai_handler
        )
        
        log_info("Refiloe AI Assistant initialized successfully")
    
    def process_message(self, whatsapp_number: str, message_text: str, 
                       message_id: str) -> str:
        """
        Main entry point for all messages
        Now uses AI to understand intent first
        """
        try:
            # Step 1: Identify the sender
            sender_context = self._identify_sender(whatsapp_number)
            
            if not sender_context:
                return self._handle_unknown_sender(whatsapp_number, message_text)
            
            # Step 2: Get conversation history for context
            conversation_history = self._get_recent_conversation(
                sender_context['id'], 
                sender_context['type']
            )
            
            # Step 3: Use AI to understand the message
            intent_data = self.ai_handler.understand_message(
                message=message_text,
                sender_type=sender_context['type'],
                sender_data=sender_context['data'],
                conversation_history=conversation_history
            )
            
            # Step 4: Log the interaction
            self._log_interaction(
                sender_context=sender_context,
                message_text=message_text,
                intent_data=intent_data,
                message_id=message_id
            )
            
            # Step 5: Process based on intent
            response = self._process_intent(
                intent_data=intent_data,
                sender_context=sender_context,
                original_message=message_text
            )
            
            return response
            
        except Exception as e:
            log_error(f"Error processing message: {str(e)}")
            return "I encountered an issue. Please try again or type 'help' for assistance."
    
    def _identify_sender(self, whatsapp_number: str) -> Optional[Dict]:
        """Identify if sender is trainer or client"""
        
        # Check if trainer
        trainer = self.trainer_model.get_by_whatsapp(whatsapp_number)
        if trainer:
            return {
                'type': 'trainer',
                'id': trainer['id'],
                'data': trainer,
                'first_interaction': False  # Could check message history
            }
        
        # Check if client
        client = self.client_model.get_by_whatsapp(whatsapp_number)
        if client:
            return {
                'type': 'client',
                'id': client['id'],
                'data': client,
                'first_interaction': False
            }
        
        return None
    
    def _get_recent_conversation(self, sender_id: str, sender_type: str) -> List[str]:
        """Get recent conversation history for context"""
        try:
            # Get last 10 messages
            id_field = 'trainer_id' if sender_type == 'trainer' else 'client_id'
            
            result = self.db.table('messages')\
                .select('message_text, direction, created_at')\
                .eq(id_field, sender_id)\
                .order('created_at', desc=True)\
                .limit(10)\
                .execute()
            
            if result.data:
                # Format as conversation
                messages = []
                for msg in reversed(result.data):
                    prefix = "User: " if msg['direction'] == 'incoming' else "Refiloe: "
                    messages.append(prefix + msg['message_text'][:200])
                return messages
            
            return []
            
        except Exception as e:
            log_error(f"Error getting conversation history: {str(e)}")
            return []
    
    def _process_intent(self, intent_data: Dict, sender_context: Dict, 
                       original_message: str) -> str:
        """
        Process the understood intent and generate appropriate response
        This is where we route to specific handlers
        """
        
        intent = intent_data.get('primary_intent')
        confidence = intent_data.get('confidence', 0)
        extracted = intent_data.get('extracted_data', {})
        
        # If low confidence, ask for clarification
        if confidence < 0.5:
            return self._get_clarification(sender_context, intent_data)
        
        # Route to specific handlers based on intent
        if sender_context['type'] == 'trainer':
            return self._handle_trainer_intent(
                intent, extracted, sender_context, original_message
            )
        else:
            return self._handle_client_intent(
                intent, extracted, sender_context, original_message
            )
    
    def _handle_trainer_intent(self, intent: str, extracted: Dict, 
                              context: Dict, message: str) -> str:
        """Handle trainer-specific intents"""
        
        trainer = context['data']
        
        # Map intents to handlers
        handlers = {
            'greeting': lambda: self._greeting_response(trainer, True),
            'help': lambda: self._help_menu(trainer),
            'add_client': lambda: self._add_client_flow(trainer, extracted),
            'view_schedule': lambda: self._show_schedule(trainer),
            'calendar': lambda: self._show_schedule(trainer),
            'view_clients': lambda: self._show_clients(trainer),
            'send_workout': lambda: self._send_workout_flow(trainer, extracted, message),
            'start_assessment': lambda: self._start_assessment_flow(trainer, extracted),
            'view_dashboard': lambda: self._generate_dashboard_link(trainer),
            'check_revenue': lambda: self._show_revenue(trainer),
            'send_reminder': lambda: self._send_reminders(trainer, extracted),
            'update_availability': lambda: self._update_availability(trainer, extracted)
        }
        
        # Get the appropriate handler
        handler = handlers.get(intent)
        
        if handler:
            return handler()
        else:
            # Use AI to generate a contextual response
            return self.ai_handler.generate_smart_response(
                {'primary_intent': intent, 'extracted_data': extracted},
                'trainer',
                trainer
            )
    
    def _handle_client_intent(self, intent: str, extracted: Dict, 
                             context: Dict, message: str) -> str:
        """Handle client-specific intents"""
        
        client = context['data']
        trainer = client.get('trainers', {})
        
        handlers = {
            'greeting': lambda: self._greeting_response(client, False),
            'help': lambda: self._help_menu_client(client, trainer),
            'book_session': lambda: self._book_session_flow(client, trainer, extracted),
            'view_schedule': lambda: self._show_client_schedule(client),
            'cancel_session': lambda: self._cancel_session_flow(client, extracted),
            'reschedule_session': lambda: self._reschedule_flow(client, extracted),
            'view_assessment': lambda: self._show_assessment(client, trainer),
            'check_progress': lambda: self._show_progress(client, trainer),
            'request_workout': lambda: self._request_workout(client, trainer),
            'payment_query': lambda: self._handle_payment_query(client)
        }
        
        handler = handlers.get(intent)
        
        if handler:
            return handler()
        else:
            return self.ai_handler.generate_smart_response(
                {'primary_intent': intent, 'extracted_data': extracted},
                'client',
                client
            )
    
    # Specific handler implementations
    def _greeting_response(self, user: Dict, is_trainer: bool) -> str:
        """Generate personalized greeting"""
        name = user.get('name', 'there')
        
        if is_trainer:
            greetings = [
                f"Hey {name}! Ready to build your fitness empire? 💪",
                f"Hi {name}! Let's make today productive! What's on the agenda? 🎯",
                f"Hello {name}! Your AI assistant reporting for duty! 🚀"
            ]
        else:
            greetings = [
                f"Hi {name}! Ready to crush your fitness goals? 💪",
                f"Hey {name}! How's the training going? 😊",
                f"Hello {name}! Let's keep that momentum going! 🏃‍♂️"
            ]
        
        import random
        return random.choice(greetings)
    
    def _add_client_flow(self, trainer: Dict, extracted: Dict) -> str:
        """Handle adding a new client"""
        
        # Check if we have all required info
        name = extracted.get('client_name')
        phone = extracted.get('phone_number')
        email = extracted.get('email')
        
        if name and phone:
            # Validate phone number (SA format)
            import re
            phone_clean = re.sub(r'\D', '', phone)
            if len(phone_clean) == 9:
                phone_clean = '0' + phone_clean
            elif len(phone_clean) == 11 and phone_clean.startswith('27'):
                phone_clean = '0' + phone_clean[2:]
            
            if len(phone_clean) != 10 or not phone_clean.startswith('0'):
                return f"⚠️ Please provide a valid SA phone number (10 digits starting with 0)"
            
            # Check if client already exists
            existing = self.client_model.get_by_whatsapp(phone_clean)
            if existing:
                return f"This number is already registered to {existing['name']}! 📱"
            
            # Add the client
            result = self.client_model.create({
                'trainer_id': trainer['id'],
                'name': name,
                'whatsapp': phone_clean,
                'email': email,
                'sessions_remaining': 0,
                'status': 'active'
            })
            
            if result['success']:
                return f"""✅ Successfully added {name}!

📱 WhatsApp: {phone_clean}
📧 Email: {email or 'Not provided'}
💳 Sessions: 0 (add package when ready)

I'll send them a welcome message now! They can:
- Book sessions
- Check their schedule
- View assessments
- Get workouts

Need to add another client? Just tell me! 🚀"""
            else:
                return "❌ Couldn't add the client. Please try again."
        
        else:
            # Need more information
            missing = []
            if not name:
                missing.append("name")
            if not phone:
                missing.append("WhatsApp number")
            
            return f"""Let's add your new client! I still need their {' and '.join(missing)}.

Example: "Add Sarah Jones 0821234567"

You can also include email:
"Add Sarah Jones 0821234567 sarah@email.com" 📝"""
    
    def _show_schedule(self, trainer: Dict) -> str:
        """Show trainer's schedule"""
        try:
            # Get today and next 7 days
            now = datetime.now(self.sa_tz)
            week_end = now + timedelta(days=7)
            
            bookings = self.booking_model.get_trainer_schedule(
                trainer['id'], now, week_end
            )
            
            if not bookings:
                return f"""Your schedule is clear, {trainer['name']}! 📅

Perfect time to:
• Add new clients
• Send workout programs
• Schedule assessments

Want to see your dashboard? Just ask! 📊"""
            
            # Group by day
            schedule_by_day = {}
            for booking in bookings:
                session_time = datetime.fromisoformat(booking['session_datetime'])
                session_time = session_time.replace(tzinfo=pytz.UTC).astimezone(self.sa_tz)
                day_key = session_time.strftime('%A %d %B')
                
                if day_key not in schedule_by_day:
                    schedule_by_day[day_key] = []
                
                schedule_by_day[day_key].append({
                    'time': session_time.strftime('%I:%M %p'),
                    'client': booking.get('clients', {}).get('name', 'Unknown')
                })
            
            # Format response
            response = f"📅 Your upcoming week, {trainer['name']}:\n\n"
            
            for day, sessions in schedule_by_day.items():
                response += f"**{day}**\n"
                for session in sessions:
                    response += f"• {session['time']} - {session['client']}\n"
                response += "\n"
            
            total_sessions = sum(len(s) for s in schedule_by_day.values())
            response += f"Total: {total_sessions} sessions scheduled 💪"
            
            return response
            
        except Exception as e:
            log_error(f"Error showing schedule: {str(e)}", exc_info=True)
            # More helpful error message
            return f"""📅 I'm having trouble loading your schedule right now.
            
        This might be because:
        - There's a connection issue with the database
        - Your calendar settings need updating
            
        Try asking: "Show my schedule" or "What sessions do I have this week?"
    
If this keeps happening, please contact support. 🤝"""
    
    def _send_workout_flow(self, trainer: Dict, extracted: Dict, message: str) -> str:
        """Handle workout sending with AI understanding"""
        
        client_name = extracted.get('client_name')
        exercises = extracted.get('exercises', [])
        
        # If we have exercises in the message, parse them
        if not exercises and self.workout_service:
            exercises = self.workout_service.parse_workout_text(message)
        
        if exercises and client_name:
            # Find the client
            clients = self.client_model.get_trainer_clients(trainer['id'])
            target_client = None
            
            for client in clients:
                if client_name.lower() in client['name'].lower():
                    target_client = client
                    break
            
            if target_client:
                # Format and preview workout
                workout_formatted = self.workout_service.format_workout_for_whatsapp(
                    exercises, trainer['name']
                )
                
                return f"""📋 Workout for {target_client['name']}:

{workout_formatted}

Ready to send? Reply YES to confirm! ✅"""
            else:
                return f"I couldn't find a client named '{client_name}'. Check your client list?"
        
        elif exercises and not client_name:
            # Have workout but no client
            return """I see the workout! Who should I send it to? 

Just tell me the client's name."""
        
        else:
            # Need both workout and client
            return """I'll help you send a workout! Please provide:

1. The client's name
2. The workout details

Example: "Send this workout to Sarah:
Squats 3x12
Push-ups 3x10
Plank 3x45 seconds"

I'll format it perfectly! 💪"""
    
    def _generate_dashboard_link(self, trainer: Dict) -> str:
        """Generate dashboard link for trainer"""
        try:
            from routes.dashboard import dashboard_service
            
            if not dashboard_service:
                return "Dashboard is being set up. Try again in a moment! 😊"
            
            result = dashboard_service.generate_dashboard_link(trainer['id'])
            
            if result['success']:
                return f"""📊 Your personal dashboard is ready!

{result['url']}

✨ Link expires in 24 hours
📱 Mobile-optimized
🔒 Secure & private

Your dashboard shows:
• Today's schedule
• Client list & balances  
• Revenue tracking
• Quick actions

Tap to view! 💪"""
            else:
                return "Having trouble with the dashboard. Let me try again..."
                
        except Exception as e:
            log_error(f"Error generating dashboard: {str(e)}")
            return "Dashboard temporarily unavailable. Please try again."
    
    def _log_interaction(self, sender_context: Dict, message_text: str, 
                        intent_data: Dict, message_id: str):
        """Log the interaction to database"""
        try:
            log_entry = {
                'message_text': message_text[:500],  # Truncate long messages
                'message_type': 'text',
                'direction': 'incoming',
                'ai_intent': intent_data.get('primary_intent'),
                'whatsapp_from': sender_context.get('whatsapp'),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if sender_context['type'] == 'trainer':
                log_entry['trainer_id'] = sender_context['id']
            else:
                log_entry['client_id'] = sender_context['id']
                log_entry['trainer_id'] = sender_context['data'].get('trainer_id')
            
            self.db.table('messages').insert(log_entry).execute()
            
        except Exception as e:
            log_error(f"Error logging interaction: {str(e)}")
    
    def _handle_unknown_sender(self, whatsapp_number: str, message_text: str) -> str:
        """Handle messages from unknown senders"""
        
        message_lower = message_text.lower()
        
        # Check if they're trying to register
        if any(word in message_lower for word in ['register', 'sign up', 'join', 'start']):
            return """Welcome to Refiloe! 🎉

I'm an AI assistant for personal trainers.

**For Trainers:**
To get started, ask your account manager to register you.

**For Clients:**
Your trainer will add you to the system. Once added, you can book sessions and track your fitness journey!

Need help? Contact your trainer or visit our website. 💪"""
        
        return """Hi! I'm Refiloe, your fitness AI assistant. 🤖

I don't recognize your number yet. Are you:
• A trainer? Contact support to get registered
• A client? Ask your trainer to add you

Once you're in the system, I can help with scheduling, workouts, and more! 💪"""
    
    def _get_clarification(self, sender_context: Dict, intent_data: Dict) -> str:
        """Ask for clarification when intent is unclear"""
        
        name = sender_context['data'].get('name', 'there')
        guessed_intent = intent_data.get('primary_intent', 'unknown')
        
        # Contextual clarification based on what we think they might want
        clarifications = {
            'booking': f"It seems like you want to book something, {name}. Could you be more specific? Example: 'Book Tuesday at 2pm'",
            'workout': f"Are you looking for a workout, {name}? Tell me who it's for and what exercises you want.",
            'schedule': f"Want to see your schedule, {name}? Just say 'show my schedule' or 'what's on today'",
            'assessment': f"Looking to do an assessment, {name}? Tell me which client: 'Start assessment for [name]'",
            'unknown': f"I didn't quite understand that, {name}. Could you rephrase or type 'help' to see what I can do?"
        }
        
        return clarifications.get(guessed_intent, clarifications['unknown'])
