"""Handler methods for RefiloeService - processes different types of requests"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_error, log_info

class RefiloeHandlers:
    """Handles specific message intents and actions"""
    
    def __init__(self, db, config, services):
        self.db = db
        self.config = config
        self.services = services
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def handle_greeting(self, sender_type: str, sender_data: Dict) -> str:
        """Handle greeting messages"""
        name = sender_data.get('name', 'there')
        hour = datetime.now(self.sa_tz).hour
        
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        
        if sender_type == 'trainer':
            return f"{greeting}, {name}! 💪 Ready to manage your fitness business today? How can I help?"
        else:
            return f"{greeting}, {name}! 🏋️ Ready to crush your fitness goals? What can I do for you?"
    
    def handle_help(self, sender_type: str) -> str:
        """Handle help requests"""
        if sender_type == 'trainer':
            return self._get_trainer_help()
        else:
            return self._get_client_help()
    
    def handle_add_client(self, trainer_id: str, extracted_data: Dict) -> Dict:
        """Handle adding a new client"""
        if not extracted_data.get('client_name'):
            return {
                'success': True,
                'message': "To add a client, please provide their name and phone number.\n\nExample: Add client Sarah 0821234567"
            }
        
        # Extract client details
        client_details = {
            'name': extracted_data.get('client_name'),
            'phone': extracted_data.get('phone_number', ''),
            'email': extracted_data.get('email', ''),
            'package': extracted_data.get('package', 'single'),
            'price': extracted_data.get('custom_price')
        }
        
        # Validate phone number
        if not client_details['phone']:
            return {
                'success': True,
                'message': "Please include the client's phone number.\n\nExample: Add client Sarah 0821234567"
            }
        
        # Add client using the client model
        from models.client import ClientModel
        client_model = ClientModel(self.db, self.config)
        result = client_model.add_client(trainer_id, client_details)
        
        if result['success']:
            sessions = result.get('sessions', 1)
            message = f"✅ Client added successfully!\n\n"
            message += f"Name: {client_details['name']}\n"
            message += f"Phone: {client_details['phone']}\n"
            message += f"Package: {client_details['package']} ({sessions} sessions)\n"
            if client_details.get('price'):
                message += f"Custom rate: R{client_details['price']}\n"
            message += f"\nThey can now book sessions by messaging me!"
            
            return {'success': True, 'message': message}
        else:
            return {
                'success': True,
                'message': f"❌ Could not add client: {result.get('error', 'Unknown error')}"
            }
    
    def handle_view_schedule(self, user_type: str, user_id: str, extracted_data: Dict) -> Dict:
        """Handle schedule viewing requests"""
        from models.booking import BookingModel
        booking_model = BookingModel(self.db, self.config)
        
        # Determine date range
        date_str = extracted_data.get('parsed_datetime')
        if date_str:
            target_date = datetime.fromisoformat(date_str).date()
            date_description = target_date.strftime("%A, %d %B")
        else:
            target_date = datetime.now(self.sa_tz).date()
            date_description = "today"
        
        if user_type == 'trainer':
            # Get trainer's bookings for the day
            bookings = booking_model.get_trainer_bookings(
                user_id,
                target_date.isoformat(),
                target_date.isoformat()
            )
            
            if not bookings:
                return {
                    'success': True,
                    'message': f"📅 No sessions scheduled for {date_description}.\n\nYour schedule is clear! 🎉"
                }
            
            # Format schedule
            message = f"📅 *Your schedule for {date_description}:*\n\n"
            
            for booking in bookings:
                client_name = booking.get('clients', {}).get('name', 'Unknown')
                time = booking.get('session_time', 'TBD')
                status = booking.get('status', 'unknown')
                
                status_emoji = {
                    'confirmed': '✅',
                    'completed': '✓',
                    'cancelled': '❌',
                    'rescheduled': '🔄'
                }.get(status, '•')
                
                message += f"{status_emoji} {time} - {client_name}\n"
            
            message += f"\nTotal: {len(bookings)} sessions"
            
        else:  # Client
            # Get client's upcoming bookings
            bookings = booking_model.get_client_bookings(user_id, 'confirmed')
            
            if not bookings:
                return {
                    'success': True,
                    'message': "📅 You have no upcoming sessions scheduled.\n\nReply 'book' to schedule your next workout! 💪"
                }
            
            # Format upcoming sessions
            message = "📅 *Your upcoming sessions:*\n\n"
            
            for i, booking in enumerate(bookings[:5], 1):  # Show max 5
                date_str = booking.get('session_date', '')
                time = booking.get('session_time', 'TBD')
                trainer_name = booking.get('trainers', {}).get('name', 'Your trainer')
                
                # Format date
                if date_str:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    formatted_date = date_obj.strftime("%a, %d %b")
                else:
                    formatted_date = 'TBD'
                
                message += f"{i}. {formatted_date} at {time}\n"
            
            if len(bookings) > 5:
                message += f"\n...and {len(bookings) - 5} more"
        
        return {'success': True, 'message': message}
    
    def handle_book_session(self, client_data: Dict, extracted_data: Dict) -> Dict:
        """Handle session booking request"""
        from models.booking import BookingModel
        booking_model = BookingModel(self.db, self.config)
        
        trainer_id = client_data.get('trainer_id')
        client_id = client_data.get('id')
        
        if not trainer_id:
            return {
                'success': True,
                'message': "❌ You're not linked to a trainer yet. Please contact your trainer to get set up."
            }
        
        # Check if specific date/time provided
        if extracted_data.get('parsed_datetime'):
            # Parse the datetime
            requested_datetime = datetime.fromisoformat(extracted_data['parsed_datetime'])
            date = requested_datetime.date().isoformat()
            time = requested_datetime.strftime('%H:%M')
            
            # Check availability
            if booking_model.check_booking_conflict(trainer_id, date, time):
                # Get available slots for that day
                available = booking_model.get_available_slots(trainer_id, date)
                
                if available:
                    message = f"❌ {time} is not available on {date}.\n\n"
                    message += "*Available times:*\n"
                    for slot in available[:5]:
                        message += f"• {slot}\n"
                    message += "\nWhich time would you prefer?"
                else:
                    message = f"❌ No slots available on {date}.\n\nWould you like to check another day?"
                
                return {'success': True, 'message': message}
            
            # Create booking
            booking_data = {
                'session_date': date,
                'session_time': time,
                'notes': extracted_data.get('notes', '')
            }
            
            result = booking_model.create_booking(trainer_id, client_id, booking_data)
            
            if result['success']:
                message = f"✅ *Session booked!*\n\n"
                message += f"📅 Date: {requested_datetime.strftime('%A, %d %B')}\n"
                message += f"⏰ Time: {time}\n"
                message += f"\nSee you there! 💪"
                
                return {'success': True, 'message': message}
            else:
                return {
                    'success': True,
                    'message': f"❌ Booking failed: {result.get('error', 'Unknown error')}"
                }
        
        else:
            # No specific time provided - show available slots
            today = datetime.now(self.sa_tz).date()
            tomorrow = today + timedelta(days=1)
            
            # Get available slots for next few days
            message = "*Available training slots:*\n\n"
            
            for i in range(3):  # Show 3 days
                check_date = today + timedelta(days=i)
                available = booking_model.get_available_slots(trainer_id, check_date.isoformat())
                
                if available:
                    day_name = "Today" if i == 0 else "Tomorrow" if i == 1 else check_date.strftime('%A')
                    message += f"*{day_name} ({check_date.strftime('%d %b')}):*\n"
                    
                    for slot in available[:4]:  # Show max 4 slots per day
                        message += f"• {slot}\n"
                    
                    if len(available) > 4:
                        message += f"...and {len(available) - 4} more\n"
                    
                    message += "\n"
            
            message += "Reply with your preferred day and time!\nExample: 'Book tomorrow at 9am'"
            
            return {'success': True, 'message': message}
    
    def handle_send_workout(self, trainer_id: str, extracted_data: Dict) -> Dict:
        """Handle sending workout to client"""
        client_name = extracted_data.get('client_name')
        
        if not client_name:
            return {
                'success': True,
                'message': "Which client would you like to send a workout to?\n\nExample: Send workout to Sarah"
            }
        
        # Find client
        from models.client import ClientModel
        client_model = ClientModel(self.db, self.config)
        
        clients = self.db.table('clients').select('*').eq(
            'trainer_id', trainer_id
        ).ilike('name', f'%{client_name}%').execute()
        
        if not clients.data:
            return {
                'success': True,
                'message': f"❌ No client found with name '{client_name}'.\n\nTry 'view clients' to see your client list."
            }
        
        client = clients.data[0]
        
        # Check for exercises in extracted data
        exercises = extracted_data.get('exercises', [])
        
        if exercises:
            # Create custom workout
            workout_text = "*Today's Workout:*\n\n"
            for i, exercise in enumerate(exercises, 1):
                workout_text += f"{i}. {exercise}\n"
            
            # Send to client via WhatsApp
            self.services['whatsapp'].send_message(client['whatsapp'], workout_text)
            
            message = f"✅ Custom workout sent to {client['name']}!"
        else:
            # Send template workout
            workout_template = self._get_workout_template()
            self.services['whatsapp'].send_message(client['whatsapp'], workout_template)
            
            message = f"✅ Workout template sent to {client['name']}!\n\n"
            message += "💡 Tip: You can create custom workouts by listing exercises.\n"
            message += "Example: Send workout to Sarah - 3x10 squats, 3x12 pushups, 5km run"
        
        return {'success': True, 'message': message}
    
    def handle_view_clients(self, trainer_id: str) -> Dict:
        """Handle viewing client list"""
        from models.client import ClientModel
        client_model = ClientModel(self.db, self.config)
        
        clients = client_model.get_trainer_clients(trainer_id, 'active')
        
        if not clients:
            return {
                'success': True,
                'message': "You don't have any active clients yet.\n\nAdd your first client:\nExample: Add client Sarah 0821234567"
            }
        
        message = f"*Your Active Clients ({len(clients)}):*\n\n"
        
        for i, client in enumerate(clients, 1):
            sessions = client.get('sessions_remaining', 0)
            last_session = client.get('last_session_date', 'Never')
            
            message += f"{i}. *{client['name']}*\n"
            message += f"   📱 {client.get('whatsapp', 'No phone')}\n"
            message += f"   🎫 Sessions: {sessions}\n"
            
            if last_session != 'Never':
                message += f"   📅 Last: {last_session}\n"
            
            message += "\n"
        
        message += "💡 Send workouts, book sessions, or check assessments for any client!"
        
        return {'success': True, 'message': message}
    
    def _get_trainer_help(self) -> str:
        """Get help text for trainers"""
        return """*Trainer Commands:* 🏋️‍♂️

*Client Management:*
• Add client [name] [phone]
• View clients
• Set [client]'s rate to R[amount]

*Scheduling:*
• View schedule / today / tomorrow
• My bookings this week

*Workouts & Assessments:*
• Send workout to [client]
• Start assessment for [client]
• View [client] progress

*Business:*
• Check revenue
• Payment from [client] R[amount]
• View dashboard

*Habits & Challenges:*
• Setup habit for [client]
• Create challenge
• View leaderboard

Type any command naturally!"""
    
    def _get_client_help(self) -> str:
        """Get help text for clients"""
        return """*Client Commands:* 💪

*Bookings:*
• Book session
• View my schedule
• Cancel booking
• Reschedule

*Progress:*
• Log workout
• Track habits
• View progress
• My assessment

*Challenges:*
• View challenges
• Join challenge
• My stats
• Leaderboard

*Payments:*
• Check payments
• Payment history

Just type what you need - I understand natural language! 😊"""
    
    def _get_workout_template(self) -> str:
        """Get a basic workout template"""
        return """*Today's Workout* 💪

*Warm-up (5-10 min):*
• Light cardio
• Dynamic stretching

*Main Workout:*
1. Squats - 3 sets x 12 reps
2. Push-ups - 3 sets x 10 reps
3. Lunges - 3 sets x 10 each leg
4. Plank - 3 sets x 30 seconds
5. Mountain climbers - 3 sets x 20

*Cool-down (5-10 min):*
• Static stretching
• Deep breathing

Rest 60-90 seconds between sets.
Hydrate well! 💧

Let me know when you're done! 🎯"""