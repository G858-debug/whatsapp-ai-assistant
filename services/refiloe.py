from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import json
import re
from anthropic import Anthropic
from config import Config
from utils.logger import log_error, log_info, setup_logger
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
        
        # Setup logger
        self.logger = setup_logger()
        
        # Initialize core services with proper parameters
        self.whatsapp = WhatsAppService(self.config, supabase_client, self.logger)
        self.scheduler = SchedulerService(supabase_client, self.whatsapp)
        self.workout = WorkoutService(self.config, supabase_client)
        self.assessment = EnhancedAssessmentService(supabase_client)
        self.habits = HabitTrackingService(supabase_client)
        self.analytics = AnalyticsService(supabase_client)
        self.subscription = SubscriptionManager(supabase_client)
        self.payment = PaymentManager(supabase_client)
        self.ai_handler = AIIntentHandler(self.config, supabase_client)
        
        # Initialize Anthropic client
        self.anthropic = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        
        log_info("RefiloeService initialized successfully")
    
    # [Keep all the methods from the document above up to _handle_workout_intent]
    # ... (all the code from the document remains the same) ...
    
    def _handle_workout_intent(self, intent_result: Dict, from_number: str, user_context: Dict) -> Dict:
        """Handle workout-related intents"""
        try:
            if user_context.get('trainer_id'):
                # Trainer sending workout
                return self._start_workout_flow(from_number, user_context)
            else:
                # Client requesting workout
                return {
                    'success': True,
                    'message': "💪 Your trainer will send you a personalized workout soon!"
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
            if user_context.get('trainer_id'):
                # Trainer starting assessment
                return self._start_assessment_flow(from_number, user_context)
            else:
                # Client checking assessment
                return {
                    'success': True,
                    'message': "📊 Your next assessment will be scheduled by your trainer."
                }
                
        except Exception as e:
            log_error(f"Error handling assessment intent: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your assessment request."
            }
    
    def _handle_habit_intent(self, intent_result: Dict, from_number: str, user_context: Dict) -> Dict:
        """Handle habit tracking intents"""
        try:
            extracted_data = intent_result.get('extracted_data', {})
            
            # Check if logging habits
            if extracted_data.get('habit_responses'):
                return self._log_habits(extracted_data['habit_responses'], from_number, user_context)
            
            # Check if setting up habits
            if extracted_data.get('habit_type'):
                return self._setup_habit(extracted_data, from_number, user_context)
            
            # Default: show habit status
            return self._get_habit_status(from_number, user_context)
            
        except Exception as e:
            log_error(f"Error handling habit intent: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your habit tracking request."
            }
    
    def _handle_general_query(self, text: str, user_context: Dict) -> Dict:
        """Handle general queries using AI"""
        try:
            # Create context for AI
            context = f"""
            User is a {'trainer' if user_context.get('trainer_id') else 'client'}.
            Name: {user_context.get('name', 'User')}
            """
            
            # Generate response using Claude
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": f"""You are Refiloe, a friendly AI fitness assistant for personal trainers and their clients in South Africa.
                        
                        Context: {context}
                        
                        User message: {text}
                        
                        Respond in a friendly, helpful manner. Keep response under 200 words.
                        Use WhatsApp-friendly formatting (*bold*, _italic_) and emojis.
                        If relevant, mention available commands like /book, /workout, /assess, /points, /badges.
                        """
                    }
                ]
            )
            
            return {
                'success': True,
                'message': response.content[0].text
            }
            
        except Exception as e:
            log_error(f"Error generating AI response: {str(e)}")
            return {
                'success': True,
                'message': "I understand you're asking about that. How can I help you specifically? Try /help for available commands."
            }
    
    def _get_user_context(self, phone_number: str) -> Dict:
        """Get or create user context"""
        try:
            # Check if trainer
            trainer = self.db.table('trainers').select('*').eq(
                'whatsapp', phone_number
            ).single().execute()
            
            if trainer.data:
                return {
                    'trainer_id': trainer.data['id'],
                    'name': trainer.data['name'],
                    'is_trainer': True,
                    'subscription_status': trainer.data.get('subscription_status', 'trial')
                }
            
            # Check if client
            client = self.db.table('clients').select('*').eq(
                'whatsapp', phone_number
            ).single().execute()
            
            if client.data:
                return {
                    'client_id': client.data['id'],
                    'trainer_id': client.data.get('trainer_id'),
                    'name': client.data['name'],
                    'is_client': True,
                    'status': client.data.get('status', 'active')
                }
            
            # New user
            return {
                'is_new': True,
                'phone_number': phone_number
            }
            
        except Exception as e:
            log_error(f"Error getting user context: {str(e)}")
            return {'phone_number': phone_number}
    
    def _get_help_message(self, user_context: Dict) -> Dict:
        """Get help message based on user type"""
        if user_context.get('is_trainer'):
            message = """🤖 *Refiloe AI Assistant - Trainer Commands*

*Session Management:*
- Book a session - "Book John for Tuesday 3pm"
- View schedule - "Show my schedule"
- Cancel booking - "Cancel tomorrow's session"

*Client Management:*
- Add client - "Add client Sarah 0821234567"
- View clients - "Show my clients"
- Send workout - /workout

*Assessments:*
- Start assessment - /assess
- View results - "Show Sarah's assessment"

*Gamification:* 🎮
- View points - /points
- Check badges - /badges
- Game stats - /stats
- Create challenge - "Create water challenge"

*Other:*
- Payment status - /pay
- Analytics - "Show my stats"
- Help - /help

Just message naturally, I understand context! 💪"""
        
        elif user_context.get('is_client'):
            message = """🤖 *Refiloe AI Assistant - Client Commands*

*Sessions:*
- View schedule - "When is my next session?"
- Request reschedule - "Can I move Tuesday's session?"

*Progress:*
- Track habits - "Water: 8 glasses, Steps: 10000"
- View assessment - "Show my assessment"
- Request workout - "Send me a workout"

*Gamification:* 🎮
- View points - /points
- Check badges - /badges
- Game stats - /stats
- Join challenges - "Show challenges"

*Other:*
- Payment info - /pay
- Help - /help

Just message naturally, I understand! 💪"""
        
        else:
            message = """🤖 *Welcome to Refiloe AI Assistant!*

I help personal trainers and clients manage fitness training.

*For Trainers:*
Register by sending: "I'm a trainer"

*For Clients:*
Your trainer will add you to the system.

*Features:*
- Session scheduling 📅
- Workout programs 💪
- Progress tracking 📊
- Habit monitoring 💧
- Gamification 🎮
- Payment management 💰

Visit refiloe.ai to learn more!"""
        
        return {
            'success': True,
            'message': message
        }
    
    def _start_booking_flow(self, from_number: str, user_context: Dict) -> Dict:
        """Start booking flow"""
        try:
            if not user_context.get('trainer_id'):
                return {
                    'success': True,
                    'message': "You need to be registered to book sessions. Contact your trainer to get started!"
                }
            
            # Get available slots
            # TODO: Implement actual booking flow
            return {
                'success': True,
                'message': "📅 *Book a Session*\n\nWhen would you like to book?\nExample: 'Tuesday at 3pm' or 'Tomorrow morning'"
            }
            
        except Exception as e:
            log_error(f"Error starting booking flow: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't start the booking process."
            }
    
    def _cancel_current_action(self, user_context: Dict) -> Dict:
        """Cancel current action/flow"""
        # Clear any session state
        return {
            'success': True,
            'message': "✅ Action cancelled. How can I help you?"
        }
    
    def _get_user_status(self, from_number: str, user_context: Dict) -> Dict:
        """Get user status summary"""
        try:
            if user_context.get('is_trainer'):
                # Get trainer stats
                clients_count = self.db.table('clients').select(
                    'id', count='exact'
                ).eq('trainer_id', user_context['trainer_id']).execute()
                
                today_sessions = self.db.table('bookings').select(
                    'id', count='exact'
                ).eq('trainer_id', user_context['trainer_id']).eq(
                    'session_date', datetime.now().date().isoformat()
                ).execute()
                
                message = f"""📊 *Your Status*

👥 Clients: {clients_count.count if clients_count else 0}
📅 Sessions today: {today_sessions.count if today_sessions else 0}
💳 Subscription: {user_context.get('subscription_status', 'trial')}

Type /help for available commands."""
            
            elif user_context.get('is_client'):
                # Get client stats
                next_session = self.db.table('bookings').select('*').eq(
                    'client_id', user_context['client_id']
                ).gte('session_date', datetime.now().date().isoformat()).order(
                    'session_date'
                ).limit(1).execute()
                
                message = f"""📊 *Your Status*

👋 Hi {user_context.get('name', 'there')}!
📅 Next session: {next_session.data[0]['session_date'] if next_session.data else 'None scheduled'}
💪 Status: {user_context.get('status', 'active')}

Type /help for available commands."""
            
            else:
                message = "You're not registered yet. Contact your trainer to get started!"
            
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
    
    def _start_workout_flow(self, from_number: str, user_context: Dict) -> Dict:
        """Start workout creation/sending flow"""
        try:
            if not user_context.get('is_trainer'):
                return {
                    'success': True,
                    'message': "💪 Your trainer will send you personalized workouts. Stay tuned!"
                }
            
            # Get trainer's clients
            clients = self.db.table('clients').select('id, name').eq(
                'trainer_id', user_context['trainer_id']
            ).eq('status', 'active').execute()
            
            if not clients.data:
                return {
                    'success': True,
                    'message': "You don't have any active clients yet. Add clients first!"
                }
            
            # Format client list
            client_list = "\n".join([
                f"{i+1}. {c['name']}" for i, c in enumerate(clients.data)
            ])
            
            return {
                'success': True,
                'message': f"""💪 *Send Workout*

Select a client:
{client_list}

Reply with the number or client name."""
            }
            
        except Exception as e:
            log_error(f"Error starting workout flow: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't start the workout process."
            }
    
    def _start_assessment_flow(self, from_number: str, user_context: Dict) -> Dict:
        """Start assessment flow"""
        try:
            if not user_context.get('is_trainer'):
                return {
                    'success': True,
                    'message': "📊 Your trainer will schedule your fitness assessments."
                }
            
            return {
                'success': True,
                'message': """📊 *Start Assessment*

Choose option:
1. Send assessment form to client
2. Record assessment results
3. View past assessments

Reply with your choice (1-3)."""
            }
            
        except Exception as e:
            log_error(f"Error starting assessment flow: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't start the assessment process."
            }
    
    def _check_payment_status(self, from_number: str, user_context: Dict) -> Dict:
        """Check payment status"""
        try:
            if user_context.get('is_trainer'):
                # Get trainer's pending payments
                pending = self.db.table('payment_requests').select(
                    'amount'
                ).eq('trainer_id', user_context['trainer_id']).eq(
                    'status', 'pending'
                ).execute()
                
                total_pending = sum(p['amount'] for p in (pending.data or []))
                
                message = f"""💰 *Payment Status*

Pending payments: R{total_pending:.2f}
This month received: R0.00

To request payment from client:
"Request R500 from John""""
            
            else:
                # Get client's payment status
                outstanding = self.db.table('payment_requests').select(
                    'amount, due_date'
                ).eq('client_phone', from_number).eq(
                    'status', 'pending'
                ).execute()
                
                if outstanding.data:
                    total = sum(p['amount'] for p in outstanding.data)
                    message = f"""💰 *Payment Status*

Outstanding: R{total:.2f}

Contact your trainer for payment details."""
                else:
                    message = "✅ You're all paid up! No outstanding payments."
            
            return {
                'success': True,
                'message': message
            }
            
        except Exception as e:
            log_error(f"Error checking payment status: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't check payment status."
            }
    
    def _log_habits(self, responses: List, from_number: str, user_context: Dict) -> Dict:
        """Log habit responses"""
        try:
            if not user_context.get('client_id'):
                return {
                    'success': True,
                    'message': "You need to be a registered client to track habits."
                }
            
            # Process habit responses
            result = self.habits.process_habit_response(
                user_context['client_id'],
                responses
            )
            
            if result['success']:
                # Award gamification points
                self._award_habit_points(user_context['client_id'], len(responses))
                
                return {
                    'success': True,
                    'message': f"""✅ *Habits Logged!*

{result.get('summary', 'Great job staying on track!')}

+{len(responses) * 10} points earned! 🎯

Keep up the great work! 💪"""
                }
            else:
                return {
                    'success': False,
                    'message': "Sorry, I couldn't log your habits. Please try again."
                }
                
        except Exception as e:
            log_error(f"Error logging habits: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't log your habits."
            }
    
    def _setup_habit(self, data: Dict, from_number: str, user_context: Dict) -> Dict:
        """Setup new habit tracking"""
        try:
            if not user_context.get('is_trainer'):
                return {
                    'success': True,
                    'message': "Your trainer will set up habit tracking for you."
                }
            
            habit_type = data.get('habit_type')
            target_value = data.get('target_value')
            
            return {
                'success': True,
                'message': f"""🎯 *Setting up {habit_type} tracking*

Target: {target_value} daily

Which client? Reply with their name."""
            }
            
        except Exception as e:
            log_error(f"Error setting up habit: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't set up habit tracking."
            }
    
    def _get_habit_status(self, from_number: str, user_context: Dict) -> Dict:
        """Get habit tracking status"""
        try:
            if not user_context.get('client_id'):
                return {
                    'success': True,
                    'message': "You need to be registered to track habits."
                }
            
            # Get today's habits
            habits = self.habits.get_client_habits_for_today(user_context['client_id'])
            
            if not habits:
                return {
                    'success': True,
                    'message': "No habits to track today! Enjoy your rest day 😊"
                }
            
            # Format habit list
            habit_text = "\n".join([
                f"{'✅' if h['logged'] else '⭕'} {h['name']}: {h['target']}"
                for h in habits
            ])
            
            return {
                'success': True,
                'message': f"""📊 *Today's Habits*

{habit_text}

To log: "Water 8, Steps 10000"

Keep going! 💪"""
            }
            
        except Exception as e:
            log_error(f"Error getting habit status: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't get your habit status."
            }
    
    def _award_habit_points(self, client_id: str, habits_count: int):
        """Award points for habit logging"""
        try:
            # Award 10 points per habit logged
            points = habits_count * 10
            
            # Add to points ledger
            self.db.table('points_ledger').insert({
                'user_id': client_id,
                'user_type': 'client',
                'points': points,
                'reason': f'Logged {habits_count} habits',
                'created_at': datetime.now().isoformat()
            }).execute()
            
            # Update gamification profile
            profile = self.db.table('gamification_profiles').select('*').eq(
                'client_id', client_id
            ).single().execute()
            
            if profile.data:
                new_total = profile.data['points_total'] + points
                self.db.table('gamification_profiles').update({
                    'points_total': new_total
                }).eq('client_id', client_id).execute()
            else:
                # Create profile
                self.db.table('gamification_profiles').insert({
                    'client_id': client_id,
                    'points_total': points,
                    'is_public': True,
                    'opted_in_global': True,
                    'opted_in_trainer': True
                }).execute()
            
            log_info(f"Awarded {points} points to client {client_id} for habit logging")
            
        except Exception as e:
            log_error(f"Error awarding habit points: {str(e)}")
    
    def _handle_button_click(self, button_id: str, user_context: Dict) -> Dict:
        """Handle button click from interactive message"""
        try:
            # Route based on button ID
            if button_id.startswith('book_'):
                slot = button_id.replace('book_', '')
                return {
                    'success': True,
                    'message': f"📅 Booking session for {slot}..."
                }
            elif button_id.startswith('confirm_'):
                return {
                    'success': True,
                    'message': "✅ Confirmed!"
                }
            elif button_id.startswith('cancel_'):
                return {
                    'success': True,
                    'message': "❌ Cancelled."
                }
            else:
                return {
                    'success': True,
                    'message': "Button clicked!"
                }
                
        except Exception as e:
            log_error(f"Error handling button click: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your selection."
            }
    
    def _handle_list_selection(self, list_id: str, user_context: Dict) -> Dict:
        """Handle list selection from interactive message"""
        try:
            return {
                'success': True,
                'message': f"You selected: {list_id}"
            }
        except Exception as e:
            log_error(f"Error handling list selection: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your selection."
            }
    
    def _process_assessment_photo(self, message_data: Dict, user_context: Dict) -> Dict:
        """Process assessment photo upload"""
        try:
            return {
                'success': True,
                'message': "📸 Photo received! Please complete the assessment form sent to you."
            }
        except Exception as e:
            log_error(f"Error processing assessment photo: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I couldn't process your photo."
            }
    
    def _log_interaction(self, phone_number: str, message_data: Dict, response: Dict):
        """Log interaction for analytics"""
        try:
            self.db.table('messages').insert({
                'whatsapp_from': phone_number,
                'whatsapp_to': 'system',
                'message_text': json.dumps(message_data),
                'response': json.dumps(response),
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            log_error(f"Error logging interaction: {str(e)}")
