from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import re
from anthropic import Anthropic
from config import Config
from utils.logger import log_error, log_info
from services.whatsapp import WhatsAppService
from services.scheduler import SchedulerService
from services.workout import WorkoutService
from services.assessment import EnhancedAssessmentService
from services.habits import HabitTrackingService
from services.analytics import AnalyticsService
from services.subscription_manager import SubscriptionManager
from services.ai_intent_handler import AIIntentHandler
from payment_manager import PaymentManager


class RefiloeService:
    """Main service orchestrator for Refiloe AI assistant"""
    
    def __init__(self, supabase_client):
        """Initialize Refiloe with all required services"""
        self.db = supabase_client
        self.config = Config
        
        # Initialize core services
        self.whatsapp = WhatsAppService(supabase_client)
        self.scheduler = SchedulerService(supabase_client)
        self.workout = WorkoutService(supabase_client)
        self.assessment = EnhancedAssessmentService(supabase_client)
        self.habits = HabitTrackingService(supabase_client)
        self.analytics = AnalyticsService(supabase_client)
        self.subscription = SubscriptionManager(supabase_client)
        self.payment = PaymentManager(supabase_client)
        self.ai_handler = AIIntentHandler(supabase_client)
        
        # Initialize Anthropic client
        self.anthropic = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        
        log_info("RefiloeService initialized successfully")
    
    def process_message(self, message_data: Dict) -> Dict:
        """Process incoming WhatsApp message"""
        try:
            # Extract message details
            from_number = message_data.get('from')
            message_type = message_data.get('type', 'text')
            
            # Get or create user context
            user_context = self._get_user_context(from_number)
            
            # Route based on message type
            if message_type == 'text':
                response = self._handle_text_message(message_data, user_context)
            elif message_type == 'audio':
                response = self._handle_voice_message(message_data, user_context)
            elif message_type == 'image':
                response = self._handle_image_message(message_data, user_context)
            elif message_type == 'interactive':
                response = self._handle_interactive_message(message_data, user_context)
            else:
                response = {
                    'success': False,
                    'message': "I don't understand that type of message yet. Please send text or voice notes."
                }
            
            # Log interaction
            self._log_interaction(from_number, message_data, response)
            
            return response
            
        except Exception as e:
            log_error(f"Error processing message: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I encountered an error. Please try again."
            }
    
    def _handle_text_message(self, message_data: Dict, user_context: Dict) -> Dict:
        """Handle text message"""
        try:
            text = message_data.get('text', {}).get('body', '')
            from_number = message_data.get('from')
            
            # Check for commands
            if text.lower().startswith('/'):
                return self._handle_command(text, from_number, user_context)
            
            # Use AI to understand intent
            intent_result = self.ai_handler.process_message(text, user_context)
            
            # Route based on intent
            if intent_result['intent'] == 'booking':
                return self._handle_booking_intent(intent_result, from_number, user_context)
            elif intent_result['intent'] == 'payment':
                return self._handle_payment_intent(intent_result, from_number, user_context)
            elif intent_result['intent'] == 'workout':
                return self._handle_workout_intent(intent_result, from_number, user_context)
            elif intent_result['intent'] == 'assessment':
                return self._handle_assessment_intent(intent_result, from_number, user_context)
            elif intent_result['intent'] == 'habit':
                return self._handle_habit_intent(intent_result, from_number, user_context)
            elif intent_result['intent'] == 'general':
                return self._handle_general_query(text, user_context)
            else:
                return {
                    'success': True,
                    'message': intent_result.get('response', "I'm not sure how to help with that. Try asking about bookings, workouts, or assessments.")
                }
                
        except Exception as e:
            log_error(f"Error handling text message: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your message. Please try again."
            }
    
    def _handle_voice_message(self, message_data: Dict, user_context: Dict) -> Dict:
        """Handle voice message"""
        try:
            # For now, return a placeholder response
            # TODO: Implement voice transcription
            return {
                'success': True,
                'message': "🎤 I received your voice message! Voice processing is coming soon. For now, please send text messages."
            }
        except Exception as e:
            log_error(f"Error handling voice message: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your voice message."
            }
    
    def _handle_image_message(self, message_data: Dict, user_context: Dict) -> Dict:
        """Handle image message"""
        try:
            # Check if this is for an assessment
            if user_context.get('expecting_assessment_photo'):
                return self._process_assessment_photo(message_data, user_context)
            
            return {
                'success': True,
                'message': "📸 Thanks for the image! To submit assessment photos, please start an assessment first."
            }
        except Exception as e:
            log_error(f"Error handling image: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your image."
            }
    
    def _handle_interactive_message(self, message_data: Dict, user_context: Dict) -> Dict:
        """Handle interactive button/list responses"""
        try:
            interactive = message_data.get('interactive', {})
            response_type = interactive.get('type')
            
            if response_type == 'button_reply':
                button_id = interactive.get('button_reply', {}).get('id')
                return self._handle_button_click(button_id, user_context)
            elif response_type == 'list_reply':
                list_id = interactive.get('list_reply', {}).get('id')
                return self._handle_list_selection(list_id, user_context)
            
            return {
                'success': False,
                'message': "I couldn't understand your selection."
            }
            
        except Exception as e:
            log_error(f"Error handling interactive message: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your selection."
            }
    
    def _handle_command(self, command: str, from_number: str, user_context: Dict) -> Dict:
        """Handle slash commands"""
        try:
            cmd = command.lower().strip()
            
            if cmd == '/help':
                return self._get_help_message(user_context)
            elif cmd == '/book':
                return self._start_booking_flow(from_number, user_context)
            elif cmd == '/cancel':
                return self._cancel_current_action(user_context)
            elif cmd == '/status':
                return self._get_user_status(from_number, user_context)
            elif cmd == '/workout':
                return self._start_workout_flow(from_number, user_context)
            elif cmd == '/assess':
                return self._start_assessment_flow(from_number, user_context)
            elif cmd == '/pay':
                return self._check_payment_status(from_number, user_context)
            else:
                return {
                    'success': True,
                    'message': f"Unknown command: {cmd}\n\nAvailable commands:\n/help - Show help\n/book - Book a session\n/workout - Get workout\n/assess - Start assessment\n/status - Check status\n/pay - Payment info"
                }
                
        except Exception as e:
            log_error(f"Error handling command: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process that command."
            }
    
    def _handle_booking_intent(self, intent_result: Dict, from_number: str, user_context: Dict) -> Dict:
        """Handle booking-related intents"""
        try:
            entities = intent_result.get('entities', {})
            
            # Check if we have enough info to book
            if entities.get('date') and entities.get('time'):
                return self.scheduler.book_session(
                    client_phone=from_number,
                    date=entities['date'],
                    time=entities['time'],
                    trainer_id=user_context.get('trainer_id')
                )
            else:
                # Start booking flow
                return self._start_booking_flow(from_number, user_context)
                
        except Exception as e:
            log_error(f"Error handling booking intent: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your booking request."
            }
    
    def _handle_payment_intent(self, intent_result: Dict, from_number: str, user_context: Dict) -> Dict:
        """Handle payment-related intents"""
        try:
            # Check outstanding payments
            outstanding = self.payment.check_payment_status(from_number)
            
            if outstanding.get('has_outstanding'):
                return {
                    'success': True,
                    'message': f"💰 You have an outstanding balance of R{outstanding['amount']:.2f}\n\nTo pay: {outstanding.get('payment_link', 'Contact your trainer for payment details')}"
                }
            else:
                return {
                    'success': True,
                    'message': "✅ You're all paid up! No outstanding payments."
                }
                
        except Exception as e:
            log_error(f"Error handling payment intent: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't check your payment status."
            }
    
    def _handle_workout_intent(self, intent_result: Dict, from_number: str, user_context: Dict) -> Dict:
        """Handle workout-related intents"""
        try:
            entities = intent_result.get('entities', {})
            muscle_group = entities.get('muscle_group', 'full body')
            
            workout = self.workout.generate_workout(
                client_id=user_context.get('client_id'),
                muscle_group=muscle_group
            )
            
            if workout.get('success'):
                return {
                    'success': True,
                    'message': workout['workout_text'],
                    'media_url': workout.get('gif_url')
                }
            else:
                return {
                    'success': False,
                    'message': "Sorry, I couldn't generate a workout right now."
                }
                
        except Exception as e:
            log_error(f"Error handling workout intent: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your workout request."
            }
    
    def _handle_assessment_intent(self, intent_result: Dict, from_number: str, user_context: Dict) -> Dict:
        """Handle assessment-related intents"""
        try:
            # Check for pending assessment
            assessments = self.assessment.get_client_assessments(
                user_context.get('client_id')
            )
            
            pending = [a for a in assessments if a['status'] == 'pending']
            
            if pending:
                return {
                    'success': True,
                    'message': f"📋 You have a pending assessment!\n\nDue: {pending[0]['due_date']}\n\nReply 'start assessment' to begin."
                }
            else:
                return {
                    'success': True,
                    'message': "No pending assessments. Your trainer will schedule one when needed."
                }
                
        except Exception as e:
            log_error(f"Error handling assessment intent: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't check your assessments."
            }
    
    def _handle_habit_intent(self, intent_result: Dict, from_number: str, user_context: Dict) -> Dict:
        """Handle habit tracking intents"""
        try:
            entities = intent_result.get('entities', {})
            habit_type = entities.get('habit_type')
            value = entities.get('value')
            
            if habit_type and value:
                result = self.habits.log_habit(
                    client_id=user_context.get('client_id'),
                    habit_type=habit_type,
                    value=value
                )
                
                if result.get('success'):
                    return {
                        'success': True,
                        'message': f"✅ Logged: {habit_type} - {value}\n\nGreat job staying consistent!"
                    }
            
            return {
                'success': True,
                'message': "📊 Track your habits! Just tell me:\n• Water intake (e.g., '2 liters water')\n• Sleep (e.g., '8 hours sleep')\n• Steps (e.g., '10000 steps')\n• Workouts (e.g., 'completed workout')"
            }
            
        except Exception as e:
            log_error(f"Error handling habit intent: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't log that habit."
            }
    
    def _handle_general_query(self, text: str, user_context: Dict) -> Dict:
        """Handle general queries with AI"""
        try:
            # Use Claude for general fitness advice
            response = self.anthropic.messages.create(
                model=Config.AI_MODEL,
                max_tokens=500,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Refiloe, a friendly South African fitness AI assistant. Provide helpful, encouraging fitness and health advice. Keep responses concise and practical."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            )
            
            return {
                'success': True,
                'message': response.content[0].text
            }
            
        except Exception as e:
            log_error(f"Error with AI response: {str(e)}")
            return {
                'success': True,
                'message': "I'm here to help with bookings, workouts, assessments, and tracking your fitness journey. What would you like to do?"
            }
    
    def _get_user_context(self, phone_number: str) -> Dict:
        """Get or create user context"""
        try:
            # Try to get existing client
            result = self.db.table('clients').select('*').eq(
                'phone_number', phone_number
            ).single().execute()
            
            if result.data:
                return {
                    'client_id': result.data['id'],
                    'trainer_id': result.data.get('trainer_id'),
                    'name': result.data.get('name'),
                    'is_new': False
                }
            else:
                # New user
                return {
                    'phone_number': phone_number,
                    'is_new': True
                }
                
        except Exception as e:
            log_error(f"Error getting user context: {str(e)}")
            return {'phone_number': phone_number, 'is_new': True}
    
    def _log_interaction(self, phone_number: str, message_data: Dict, response: Dict):
        """Log interaction for analytics"""
        try:
            self.db.table('message_logs').insert({
                'phone_number': phone_number,
                'message_type': message_data.get('type'),
                'message_content': json.dumps(message_data),
                'response': json.dumps(response),
                'timestamp': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            log_error(f"Error logging interaction: {str(e)}")
    
    def _get_help_message(self, user_context: Dict) -> Dict:
        """Get help message"""
        help_text = """🏋️ *Refiloe Fitness Assistant* 🏋️

Here's what I can help you with:

📅 *Bookings*
• "Book a session for tomorrow at 3pm"
• "Show my upcoming sessions"
• "Cancel my booking"

💪 *Workouts*
• "Give me a leg workout"
• "Show chest exercises"
• "I need a 30-minute workout"

📊 *Assessments*
• "Start my assessment"
• "Check assessment status"

💰 *Payments*
• "Check my balance"
• "Payment status"

📈 *Progress Tracking*
• "Log 2 liters water"
• "Completed workout"
• "8 hours sleep"

*Quick Commands:*
/book - Book a session
/workout - Get a workout
/assess - Start assessment
/status - Check your status
/help - Show this message

How can I help you today?"""
        
        return {
            'success': True,
            'message': help_text
        }
    
    def _start_booking_flow(self, from_number: str, user_context: Dict) -> Dict:
        """Start the booking flow"""
        try:
            # Get available slots
            slots = self.scheduler.get_available_slots(
                trainer_id=user_context.get('trainer_id')
            )
            
            if not slots:
                return {
                    'success': True,
                    'message': "No available slots at the moment. Please check back later or contact your trainer directly."
                }
            
            # Format slots message
            message = "📅 *Available Session Times*\n\n"
            for date, times in slots.items():
                message += f"*{date}*\n"
                for time in times:
                    message += f"• {time}\n"
                message += "\n"
            
            message += "Reply with your preferred date and time (e.g., 'Tomorrow at 3pm')"
            
            return {
                'success': True,
                'message': message
            }
            
        except Exception as e:
            log_error(f"Error starting booking flow: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't start the booking process."
            }
    
    def _start_workout_flow(self, from_number: str, user_context: Dict) -> Dict:
        """Start workout selection flow"""
        return {
            'success': True,
            'message': "💪 *Choose Your Workout Focus*\n\n• Chest\n• Back\n• Legs\n• Shoulders\n• Arms\n• Core\n• Full Body\n\nReply with the muscle group you want to work on!",
            'buttons': [
                {'id': 'workout_chest', 'title': 'Chest'},
                {'id': 'workout_legs', 'title': 'Legs'},
                {'id': 'workout_full', 'title': 'Full Body'}
            ]
        }
    
    def _start_assessment_flow(self, from_number: str, user_context: Dict) -> Dict:
        """Start assessment flow"""
        try:
            # Create new assessment
            result = self.assessment.create_assessment(
                trainer_id=user_context.get('trainer_id'),
                client_id=user_context.get('client_id')
            )
            
            if result.get('success'):
                return {
                    'success': True,
                    'message': "📋 *Fitness Assessment Started*\n\nI'll guide you through a series of questions about your health and fitness.\n\nLet's start with your current health status.\n\n*Do you have any medical conditions?*\nReply with any conditions or 'none'"
                }
            else:
                return {
                    'success': False,
                    'message': "Sorry, I couldn't start the assessment."
                }
                
        except Exception as e:
            log_error(f"Error starting assessment: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't start the assessment process."
            }
    
    def _check_payment_status(self, from_number: str, user_context: Dict) -> Dict:
        """Check payment status for user"""
        try:
            # Get payment info
            result = self.db.table('payment_requests').select('*').eq(
                'client_phone', from_number
            ).eq('status', 'pending').execute()
            
            if result.data:
                total = sum([p['amount'] for p in result.data])
                return {
                    'success': True,
                    'message': f"💰 *Payment Status*\n\nOutstanding: R{total:.2f}\n{len(result.data)} pending payment(s)\n\nYour trainer will send payment details soon."
                }
            else:
                return {
                    'success': True,
                    'message': "✅ All payments up to date!"
                }
                
        except Exception as e:
            log_error(f"Error checking payment status: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't check your payment status."
            }
    
    def _cancel_current_action(self, user_context: Dict) -> Dict:
        """Cancel current action/flow"""
        # Clear any session state
        return {
            'success': True,
            'message': "❌ Action cancelled. How else can I help you?"
        }
    
    def _get_user_status(self, from_number: str, user_context: Dict) -> Dict:
        """Get comprehensive user status"""
        try:
            status_parts = []
            
            # Get upcoming bookings
            bookings = self.scheduler.get_client_bookings(from_number)
            if bookings:
                status_parts.append(f"📅 Next session: {bookings[0]['date']} at {bookings[0]['time']}")
            
            # Get recent workout
            last_workout = self.workout.get_last_workout(user_context.get('client_id'))
            if last_workout:
                status_parts.append(f"💪 Last workout: {last_workout['date']}")
            
            # Get assessment status
            assessment = self.assessment.get_latest_assessment(user_context.get('client_id'))
            if assessment:
                status_parts.append(f"📋 Last assessment: {assessment['completed_at'][:10]}")
            
            # Get habit streak
            streak = self.habits.get_current_streak(user_context.get('client_id'))
            if streak:
                status_parts.append(f"🔥 Current streak: {streak} days")
            
            if status_parts:
                message = "📊 *Your Status*\n\n" + "\n".join(status_parts)
            else:
                message = "Welcome! Let's get started with your fitness journey. Try booking a session or requesting a workout!"
            
            return {
                'success': True,
                'message': message
            }
            
        except Exception as e:
            log_error(f"Error getting user status: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't get your status."
            }
    
    def _handle_button_click(self, button_id: str, user_context: Dict) -> Dict:
        """Handle button click interactions"""
        try:
            if button_id.startswith('workout_'):
                muscle_group = button_id.replace('workout_', '')
                return self._handle_workout_intent(
                    {'entities': {'muscle_group': muscle_group}},
                    user_context.get('phone_number'),
                    user_context
                )
            elif button_id.startswith('book_'):
                # Handle booking selection
                slot = button_id.replace('book_', '')
                return self.scheduler.confirm_booking(slot, user_context)
            else:
                return {
                    'success': False,
                    'message': "I didn't understand that selection."
                }
                
        except Exception as e:
            log_error(f"Error handling button click: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your selection."
            }
    
    def _handle_list_selection(self, list_id: str, user_context: Dict) -> Dict:
        """Handle list selection interactions"""
        try:
            # Similar to button handling but for list items
            return self._handle_button_click(list_id, user_context)
        except Exception as e:
            log_error(f"Error handling list selection: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your selection."
            }
    
    def _process_assessment_photo(self, message_data: Dict, user_context: Dict) -> Dict:
        """Process assessment photo submission"""
        try:
            # Store photo reference
            photo_id = message_data.get('image', {}).get('id')
            
            # Update assessment with photo
            self.assessment.add_photo_to_assessment(
                assessment_id=user_context.get('current_assessment_id'),
                photo_id=photo_id,
                photo_type=user_context.get('expected_photo_type', 'general')
            )
            
            return {
                'success': True,
                'message': "📸 Photo received! Continue with your assessment or send another photo."
            }
            
        except Exception as e:
            log_error(f"Error processing assessment photo: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your photo."
            }