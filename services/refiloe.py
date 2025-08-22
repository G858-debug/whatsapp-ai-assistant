from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pytz
import json

from utils.logger import log_info, log_error, log_warning
from services.ai_intent_handler import AIIntentHandler
from services.workout import WorkoutService
from services.assessment import EnhancedAssessmentService
from services.habits import HabitService  # NEW IMPORT
from models.trainer import TrainerModel
from models.client import ClientModel
from models.booking import BookingModel

class RefiloeAssistant:
    """Main assistant class - now AI-powered with habit tracking"""
    
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
        self.habit_service = HabitService(config, supabase_client)  # NEW SERVICE
        
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
            log_error(f"Error processing message: {str(e)}", exc_info=True)
            return "I encountered an issue. Please try again or type 'help' for assistance."
    
    def _identify_sender(self, whatsapp_number: str) -> Optional[Dict]:
        """Identify if sender is trainer or client"""
        
        # Check if trainer
        trainer = self.trainer_model.get_by_phone(whatsapp_number)
        if trainer:
            return {
                'type': 'trainer',
                'id': trainer['id'],
                'data': trainer,
                'first_interaction': False
            }
        
        # Check if client
        client = self.client_model.get_by_phone(whatsapp_number)
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
                .order('created_at desc')\
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
        
        # Check for casual conversation intents first
        casual_intents = ['status_check', 'casual_chat', 'thanks', 'farewell', 'small_talk']
        if intent in casual_intents:
            return self.ai_handler.generate_smart_response(
                {'primary_intent': intent, 'extracted_data': extracted},
                'trainer',
                trainer
            )
        
        # Map task intents to handlers (INCLUDING HABIT HANDLERS)
        handlers = {
            'greeting': lambda: self._greeting_response(trainer, True),
            'help': lambda: self._help_menu(trainer),
            'add_client': lambda: self._add_client_flow(trainer, extracted),
            'view_schedule': lambda: self._show_schedule(trainer),
            'view_clients': lambda: self._show_clients(trainer),
            'send_workout': lambda: self._send_workout_flow(trainer, extracted, message),
            'start_assessment': lambda: self._start_assessment_flow(trainer, extracted),
            'view_dashboard': lambda: self._generate_dashboard_link(trainer),
            'check_revenue': lambda: self._show_revenue(trainer),
            'send_reminder': lambda: self._send_reminders(trainer, extracted),
            'update_availability': lambda: self._update_availability(trainer, extracted),
            # NEW HABIT HANDLERS
            'setup_habit': lambda: self._setup_habit_flow(trainer, extracted, message),
            'check_habit_compliance': lambda: self._show_habit_compliance(trainer, extracted),
            'modify_habit': lambda: self._modify_habit_flow(trainer, extracted, message),
            'send_habit_reminder': lambda: self._send_habit_reminder(trainer, extracted),
            'view_habit_report': lambda: self._view_habit_report(trainer, extracted)
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
        
        # Check for casual conversation intents first
        casual_intents = ['status_check', 'casual_chat', 'thanks', 'farewell', 'small_talk']
        if intent in casual_intents:
            return self.ai_handler.generate_smart_response(
                {'primary_intent': intent, 'extracted_data': extracted},
                'client',
                client
            )
        
        # Map task intents to handlers (INCLUDING HABIT HANDLERS)
        handlers = {
            'greeting': lambda: self._greeting_response(client, False),
            'help': lambda: self._help_menu_client(client, trainer),
            'book_session': lambda: self._book_session_flow(client, extracted),
            'view_schedule': lambda: self._show_client_schedule(client),
            'cancel_session': lambda: self._cancel_session_flow(client, extracted),
            'reschedule_session': lambda: self._reschedule_flow(client, extracted),
            'view_assessment': lambda: self._show_assessment_results(client),
            'check_progress': lambda: self._show_progress(client),
            'request_workout': lambda: self._request_workout(client, trainer),
            'payment_query': lambda: self._payment_info(client),
            # NEW HABIT HANDLERS
            'log_habits': lambda: self._log_habits_flow(client, message),
            'check_streak': lambda: self._show_streak_info(client),
            'view_habits': lambda: self._show_client_habits(client),
            'skip_habits': lambda: self._skip_habits(client),
            'modify_habit_target': lambda: self._request_habit_modification(client, extracted)
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
    
    # ==================== NEW HABIT TRACKING METHODS ====================
    
    # TRAINER HABIT METHODS
    def _setup_habit_flow(self, trainer: Dict, extracted: Dict, message: str) -> str:
        """Handle habit setup for a client"""
        
        client_name = extracted.get('client_name')
        habit_type = extracted.get('habit_type')
        target_value = extracted.get('target_value')
        
        # If we don't have a client name, ask for it
        if not client_name:
            return """Which client would you like to set up habits for?
            
Just tell me their name, like: "Set up habits for Sarah" """
        
        # Find the client
        client = self.client_model.get_by_name_and_trainer(client_name, trainer['id'])
        
        if not client:
            similar_clients = self.client_model.get_similar_names(client_name, trainer['id'])
            if similar_clients:
                names = [c['name'] for c in similar_clients[:3]]
                return f"""I couldn't find {client_name}. Did you mean:
- {chr(10).join('• ' + n for n in names)}

Please use the exact name."""
            return f"I couldn't find a client named {client_name}. Check the spelling?"
        
        # If we don't have a habit type, show options
        if not habit_type:
            return f"""What habit should {client['name']} track?

Popular options:
💧 Water intake (8 glasses/day)
🥗 Eating vegetables (with meals)
🚶 Daily steps (10,000 steps)
😴 Sleep hours (8 hours)
🏋️ Workout completion
🧘 Meditation/stretching

Just say something like: "Water tracking" or "Daily steps" """
        
        # Set up the habit
        result = self.habit_service.setup_habit(
            trainer_id=trainer['id'],
            client_id=client['id'],
            habit_type=habit_type,
            target_value=target_value
        )
        
        if result['success']:
            return f"""✅ Set up {result['habit_name']} tracking for {client['name']}!

📊 Target: {result['target']} {result['unit']}
⏰ Daily reminder: {result['reminder_time']}
🔥 Starting today

{client['name']} will get a WhatsApp reminder each day to log this habit.

Want to add another habit? Just tell me!"""
        else:
            return f"Couldn't set up that habit. {result.get('error', 'Please try again.')}"
    
    def _show_habit_compliance(self, trainer: Dict, extracted: Dict) -> str:
        """Show habit compliance for trainer's clients"""
        
        client_name = extracted.get('client_name')
        
        if client_name:
            # Show specific client's compliance
            client = self.client_model.get_by_name_and_trainer(client_name, trainer['id'])
            if not client:
                return f"I couldn't find {client_name} in your client list."
            
            compliance = self.habit_service.get_client_compliance(client['id'])
            
            if not compliance['has_habits']:
                return f"{client_name} doesn't have any habits set up yet."
            
            return f"""📊 {client_name}'s Habit Tracking:

{compliance['summary']}

This week: {compliance['weekly_percentage']}% compliance
Current streak: {compliance['best_streak']} days 🔥

{compliance['details']}"""
        
        else:
            # Show all clients' compliance
            report = self.habit_service.get_trainer_habit_report(trainer['id'])
            
            if not report['clients_with_habits']:
                return """No clients have habits set up yet!

To get started, say: "Set up water tracking for [client name]" """
            
            return f"""📊 Habit Tracking Report:

{report['summary']}

Top performers:
{report['top_performers']}

Need encouragement:
{report['needs_attention']}

Want details for a specific client? Just ask!"""
    
    def _send_habit_reminder(self, trainer: Dict, extracted: Dict) -> str:
        """Manually send habit reminders"""
        
        client_name = extracted.get('client_name')
        
        if client_name:
            # Send to specific client
            client = self.client_model.get_by_name_and_trainer(client_name, trainer['id'])
            if not client:
                return f"I couldn't find {client_name}."
            
            result = self.habit_service.send_manual_reminder(client['id'])
            if result['success']:
                return f"✅ Sent habit reminder to {client_name}!"
            else:
                return f"Couldn't send reminder: {result.get('error', 'Unknown error')}"
        
        else:
            # Send to all clients
            result = self.habit_service.send_all_reminders(trainer['id'])
            return f"""📤 Sent habit reminders!

✅ Successful: {result['sent']} clients
❌ Failed: {result['failed']} clients

Your clients will receive their daily habit check-in message."""
    
    def _view_habit_report(self, trainer: Dict, extracted: Dict) -> str:
        """View detailed habit report"""
        
        report = self.habit_service.generate_weekly_report(trainer['id'])
        
        if not report['has_data']:
            return """No habit data yet! 

Start by setting up habits for your clients:
"Set up water tracking for Sarah" """
        
        return f"""📊 Weekly Habit Report
{report['date_range']}

**Overall Stats:**
- Active trackers: {report['active_clients']}
- Avg compliance: {report['average_compliance']}%
- Total check-ins: {report['total_checkins']}

**By Habit Type:**
{report['habit_breakdown']}

**Client Highlights:**
{report['client_highlights']}

**Streaks:**
🔥 Longest: {report['longest_streak']}
📈 Most improved: {report['most_improved']}

Great work keeping your clients accountable! 💪"""
    
    def _modify_habit_flow(self, trainer: Dict, extracted: Dict, message: str) -> str:
        """Modify existing habit settings"""
        
        client_name = extracted.get('client_name')
        
        if not client_name:
            return "Which client's habits would you like to modify? Tell me their name."
        
        client = self.client_model.get_by_name_and_trainer(client_name, trainer['id'])
        if not client:
            return f"I couldn't find {client_name}."
        
        # Show current habits and ask what to change
        habits = self.habit_service.get_client_habits(client['id'])
        
        if not habits:
            return f"{client_name} doesn't have any habits set up. Want to add some?"
        
        response = f"Current habits for {client_name}:\n\n"
        for habit in habits:
            response += f"• {habit['emoji']} {habit['name']}: {habit['target_value']} {habit['unit']}\n"
        
        response += "\nWhat would you like to change? Examples:\n"
        response += "• 'Change water to 10 glasses'\n"
        response += "• 'Remove steps tracking'\n"
        response += "• 'Change reminder to 8am'"
        
        return response
    
    # CLIENT HABIT METHODS
    def _log_habits_flow(self, client: Dict, message: str) -> str:
        """Process habit check-in from client"""
        
        # Parse their response using the habit service
        result = self.habit_service.parse_habit_response(
            message=message,
            client_id=client['id']
        )
        
        if not result['success']:
            # They might not have habits or invalid response
            if result['reason'] == 'no_habits':
                return """You don't have any habits to track yet!

Your trainer will set these up for you. 🌟"""
            
            elif result['reason'] == 'invalid_format':
                habits = self.habit_service.get_client_habits(client['id'])
                
                if habits:
                    return f"""I didn't quite get that. You have {len(habits)} habits to check:

{chr(10).join(f"{h['emoji']} {h['name']}" for h in habits)}

Reply with:
- Numbers: "7 yes no" 
- Yes/no: "yes yes no"
- Or just the numbers: "7" if tracking one thing"""
                else:
                    return "I couldn't process that. Try again?"
        
        # Successfully logged habits
        response = result['feedback_message']
        
        # Add streak info if they're doing well
        if result['streak'] > 0:
            if result['streak'] == 1:
                response += f"\n\n🌱 Day 1 - Great start!"
            elif result['streak'] < 7:
                response += f"\n\n🔥 {result['streak']} day streak! Keep going!"
            elif result['streak'] < 30:
                response += f"\n\n🔥 {result['streak']} days! You're on fire!"
            else:
                response += f"\n\n👑 {result['streak']} day streak! Legendary!"
        
        # Add encouragement based on completion
        if result['completion_percentage'] == 100:
            response += "\n\nPerfect day! 🌟"
        elif result['completion_percentage'] >= 75:
            response += "\n\nGreat effort! 💪"
        elif result['completion_percentage'] >= 50:
            response += "\n\nGood progress! Keep pushing!"
        else:
            response += "\n\nEvery bit counts! Tomorrow is a new day 🌅"
        
        return response
    
    def _show_streak_info(self, client: Dict) -> str:
        """Show client's habit streaks"""
        
        streaks = self.habit_service.get_client_streaks(client['id'])
        
        if not streaks['has_habits']:
            return "You don't have any habits set up yet! Your trainer will help you get started. 🚀"
        
        response = f"🔥 Your Habit Streaks:\n\n"
        
        for habit in streaks['habits']:
            emoji = habit['emoji']
            name = habit['name']
            current = habit['current_streak']
            best = habit['best_streak']
            
            if current > 0:
                response += f"{emoji} {name}: {current} days"
                if current == best:
                    response += " (Personal best! 🏆)"
                else:
                    response += f" (Best: {best} days)"
            else:
                response += f"{emoji} {name}: No streak yet (Best was {best} days)"
            response += "\n"
        
        # Overall stats
        response += f"\n📊 This week: {streaks['weekly_compliance']}% completion"
        response += f"\n📈 This month: {streaks['monthly_compliance']}% completion"
        
        # Motivational message based on performance
        if streaks['weekly_compliance'] >= 80:
            response += "\n\nYou're crushing it! Keep up the amazing work! 💪"
        elif streaks['weekly_compliance'] >= 60:
            response += "\n\nGood consistency! Let's push for even better! 🚀"
        else:
            response += "\n\nBuilding habits takes time. Keep at it! 🌱"
        
        return response
    
    def _show_client_habits(self, client: Dict) -> str:
        """Show what habits the client is tracking"""
        
        habits = self.habit_service.get_client_habits(client['id'])
        
        if not habits:
            return """You're not tracking any habits yet!

Your trainer will set these up based on your goals. 

Common habits include:
💧 Water intake
🥗 Healthy eating
🚶 Daily steps
😴 Sleep quality

Chat with your trainer about what would help you most! 🌟"""
        
        response = "Your daily habits to track:\n\n"
        
        for habit in habits:
            response += f"{habit['emoji']} **{habit['name']}**\n"
            response += f"   Target: {habit['target_value']} {habit['unit']}\n"
            response += f"   Today: {'✅ Done' if habit['completed_today'] else '⏳ Not logged'}\n\n"
        
        response += f"⏰ Daily reminder: {habits[0]['reminder_time']}\n"
        response += "\nReady to log today's habits? Just send your numbers or yes/no!"
        
        return response
    
    def _skip_habits(self, client: Dict) -> str:
        """Handle when client wants to skip habit tracking"""
        
        result = self.habit_service.skip_habits_today(client['id'])
        
        if result['streak_broken']:
            return f"""Noted! Skipping today's habits.

Your {result['broken_streak']} day streak has ended, but don't worry! 
Tomorrow is a fresh start. 🌅

Remember: Progress, not perfection! See you tomorrow 💪"""
        else:
            return """Noted! Rest day recorded. 

Your streak is safe - everyone needs a break sometimes! 
See you tomorrow for a fresh start! 🌟"""
    
    def _request_habit_modification(self, client: Dict, extracted: Dict) -> str:
        """Handle client requesting to change their habit targets"""
        
        return f"""I'll let your trainer know you'd like to adjust your habit goals!

In the meantime, you can tell me specifically what you'd like to change:
- "Water is too much, maybe 6 glasses?"
- "Can we track workouts instead of steps?"
- "Move my reminder to 7am?"

Your trainer will review and update your targets! 💪"""
    
    # ==================== END OF HABIT TRACKING METHODS ====================
    
    def _get_clarification(self, sender_context: Dict, intent_data: Dict) -> str:
        """Ask for clarification when intent is unclear"""
        
        name = sender_context['data'].get('name', 'there')
        response_type = intent_data.get('suggested_response_type', 'task')
        
        # If it seems conversational, respond conversationally
        if response_type == 'conversational':
            return self.ai_handler.generate_smart_response(
                intent_data, 
                sender_context['type'], 
                sender_context['data']
            )
        
        # Otherwise, gently suggest options
        if sender_context['type'] == 'trainer':
            return f"""Hmm, I'm not quite sure what you need there, {name}. 

Try things like:
- "Show my schedule"
- "Add a client" 
- "Set up water tracking for Sarah"
- "Check habit compliance"

Or we can just chat! 😊"""
        else:
            return f"""I'm not quite following, {name}. 

Try things like:
- "Book a session"
- "Check my schedule"
- "Show my habits"
- "Check my streak"

Or if you just want to chat, that's cool too! 💪"""
    
    # Helper methods for trainer intents
    def _greeting_response(self, user_data: Dict, is_trainer: bool) -> str:
        """Generate greeting response"""
        import random
        name = user_data.get('name', 'there')
        
        if is_trainer:
            greetings = [
                f"Hey {name}! 👋 Good to hear from you!",
                f"Hi {name}! How's everything going?",
                f"Hello {name}! 😊",
                f"Hey there {name}! Hope you're having a great day!",
                f"Hi {name}! What's happening in your world?",
            ]
        else:
            greetings = [
                f"Hi {name}! 💪 Good to hear from you!",
                f"Hey {name}! How's it going?",
                f"Hello {name}! 😊",
                f"Hi there {name}! Hope you're doing well!",
                f"Hey {name}! How's your day been?",
            ]
        
        return random.choice(greetings)
    
    def _help_menu(self, trainer: Dict) -> str:
        """Show help menu for trainers"""
        name = trainer.get('name', 'there')
        return f"""Here's what I can do for you, {name}:

📱 **Client Management**
- Add new clients
- View all clients
- Check client balances

📅 **Scheduling**
- View your schedule
- See today's sessions
- Check weekly calendar

💪 **Workouts & Assessments**
- Send workouts to clients
- Start fitness assessments
- Track client progress

✅ **Habit Tracking** (NEW!)
- Set up daily habits for clients
- Check compliance & streaks
- Send reminders
- View habit reports

📊 **Business**
- View dashboard
- Check revenue
- Send reminders

Just tell me what you need! 🚀"""
    
    def _help_menu_client(self, client: Dict, trainer: Dict) -> str:
        """Show help menu for clients"""
        trainer_name = trainer.get('name', 'your trainer')
        return f"""I can help you with:

📅 Book training sessions
👀 View your schedule
✏️ Reschedule or cancel
📊 Check your fitness assessment
💪 Get workouts from {trainer_name}
📈 Track your progress

✅ **Daily Habits** (NEW!)
- Log your daily habits
- Check your streaks
- View your targets

What would you like to do? 😊"""
    
    # [All other existing methods remain the same...]
    # Including: _add_client_flow, _show_schedule, _show_clients, 
    # _generate_dashboard_link, _log_interaction, _handle_unknown_sender,
    # and all the placeholder methods at the end
    
    def _add_client_flow(self, trainer: Dict, extracted: Dict) -> str:
        """Handle adding a new client"""
        
        name = extracted.get('client_name')
        phone = extracted.get('phone_number')
        email = extracted.get('email')
        
        if name and phone:
            # Add the client
            result = self.client_model.add_client(
                trainer['id'],
                {
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'package': 'single'
                }
            )
            
            if result['success']:
                return f"""✅ Successfully added {name} as your client!

📱 WhatsApp: {phone}
📧 Email: {email or 'Not provided'}
💰 Sessions: Starting with 1 session

They can now:
- Book sessions
- Check their schedule
- View assessments
- Get workouts
- Track daily habits

Want to set up habits for {name}? Just say "Set up water tracking for {name}"! 🚀"""
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
- Add new clients
- Send workout programs
- Set up habit tracking
- Schedule assessments

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
            log_error(f"Error showing schedule: {str(e)}")
            return "Let me check your schedule... Please try again."
    
    def _show_clients(self, trainer: Dict) -> str:
        """Show trainer's client list"""
        try:
            clients = self.client_model.get_trainer_clients(trainer['id'])
            
            if not clients:
                return """You don't have any clients yet! 

Ready to grow your business? 
Just say: "Add client [name] [phone]"

Example: "Add Sarah Jones 0821234567" 🚀"""
            
            response = f"📱 Your clients ({len(clients)} total):\n\n"
            
            for client in clients:
                sessions = client.get('sessions_remaining', 0)
                last_session = client.get('last_session_display', 'Never')
                
                response += f"**{client['name']}**\n"
                response += f"📞 {client['whatsapp']}\n"
                response += f"💰 Sessions: {sessions}\n"
                response += f"📅 Last session: {last_session}\n\n"
            
            response += "💡 Tip: Set up habit tracking for any client!\n"
            response += 'Say: "Set up water tracking for [name]"'
            
            return response
            
        except Exception as e:
            log_error(f"Error showing clients: {str(e)}")
            return "Let me get your client list... Please try again."
    
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
- Today's schedule
- Client list & balances  
- Revenue tracking
- Habit compliance
- Quick actions

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
            # Get WhatsApp number from the data
            whatsapp_from = sender_context['data'].get('whatsapp')
            
            log_entry = {
                'message_text': message_text[:500],  # Truncate long messages
                'message_type': 'text',
                'direction': 'incoming',
                'ai_intent': intent_data.get('primary_intent'),
                'whatsapp_from': whatsapp_from,
                'whatsapp_to': 'system',
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
Your trainer will add you to the system. Once added, you can book sessions, track habits, and monitor your fitness journey!

Need help? Contact your trainer or visit our website. 💪"""
        
        return """Hi! I'm Refiloe, your fitness AI assistant. 🤖

I don't recognize your number yet. Are you:
- A trainer? Contact support to get registered
- A client? Ask your trainer to add you

Once you're in the system, I can help with scheduling, workouts, habit tracking, and more! 🚀"""
    
    # Additional handler methods would go here...
    def _send_workout_flow(self, trainer: Dict, extracted: Dict, message: str) -> str:
        """Handle sending workout to client"""
        # Implementation here
        return "Workout feature coming soon!"
    
    def _start_assessment_flow(self, trainer: Dict, extracted: Dict) -> str:
        """Handle starting assessment"""
        # Implementation here
        return "Assessment feature coming soon!"
    
    def _show_revenue(self, trainer: Dict) -> str:
        """Show revenue information"""
        # Implementation here
        return "Revenue tracking coming soon!"
    
    def _send_reminders(self, trainer: Dict, extracted: Dict) -> str:
        """Send reminders to clients"""
        # Implementation here
        return "Reminder feature coming soon!"
    
    def _update_availability(self, trainer: Dict, extracted: Dict) -> str:
        """Update trainer availability"""
        # Implementation here
        return "Availability update coming soon!"
    
    def _book_session_flow(self, client: Dict, extracted: Dict) -> str:
        """Handle session booking for client"""
        # Implementation here
        return "Booking feature coming soon!"
    
    def _show_client_schedule(self, client: Dict) -> str:
        """Show client's schedule"""
        # Implementation here
        return "Your schedule will be shown here!"
    
    def _cancel_session_flow(self, client: Dict, extracted: Dict) -> str:
        """Handle session cancellation"""
        # Implementation here
        return "Cancellation feature coming soon!"
    
    def _reschedule_flow(self, client: Dict, extracted: Dict) -> str:
        """Handle session rescheduling"""
        # Implementation here
        return "Rescheduling feature coming soon!"
    
    def _show_assessment_results(self, client: Dict) -> str:
        """Show assessment results"""
        # Implementation here
        return "Assessment results coming soon!"
    
    def _show_progress(self, client: Dict) -> str:
        """Show client progress"""
        # Implementation here
        return "Progress tracking coming soon!"
    
    def _request_workout(self, client: Dict, trainer: Dict) -> str:
        """Request workout from trainer"""
        # Implementation here
        return "Workout request feature coming soon!"
    
    def _payment_info(self, client: Dict) -> str:
        """Show payment information"""
        # Implementation here
        return "Payment info coming soon!"
