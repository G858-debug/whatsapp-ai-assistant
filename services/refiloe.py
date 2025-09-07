# -*- coding: utf-8 -*-
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
    
    def __init__(self, supabase_client, dashboard_sync_service=None):
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
    
    def process_message(self, message_data: Dict) -> Dict:
        """
        Process incoming WhatsApp message
        
        Args:
            message_data: Dictionary containing message information
            
        Returns:
            Dictionary with success status and response message
        """
        try:
            # Extract phone number
            from_number = message_data.get('from')
            if not from_number:
                return {
                    'success': False,
                    'message': 'No phone number provided',
                    'error': 'Missing sender information'
                }
            
            # Get user context
            user_type, user_data = self._get_user_context(from_number)
            
            if not user_data:
                return {
                    'success': True,
                    'message': "👋 Welcome to Refiloe! I'm your AI fitness assistant.\n\nAre you a trainer or a client?\n\nReply 'trainer' to set up your business or 'client' if you're looking for a trainer.",
                    'buttons': [
                        {'id': 'register_trainer', 'title': 'I\'m a Trainer'},
                        {'id': 'register_client', 'title': 'I\'m a Client'}
                    ]
                }
            
            # Handle different message types
            message_type = message_data.get('type', 'text')
            
            if message_type == 'text':
                return self._handle_text_message(message_data, user_type, user_data)
            elif message_type == 'interactive':
                return self._handle_interactive_message(message_data, user_type, user_data)
            elif message_type == 'image':
                return self._handle_image_message(message_data, user_type, user_data)
            elif message_type == 'button':
                return self._handle_button_message(message_data, user_type, user_data)
            else:
                return {
                    'success': True,
                    'message': f"I received your {message_type} message, but I can only process text, images, and button responses right now."
                }
                
        except Exception as e:
            log_error(f"Error processing message: {str(e)}")
            return {
                'success': False,
                'message': "Sorry, I encountered an error processing your message. Please try again.",
                'error': str(e)
            }
    
    def _get_user_context(self, phone_number: str) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Identify if user is trainer or client
        
        Args:
            phone_number: WhatsApp phone number
            
        Returns:
            Tuple of (user_type, user_data)
        """
        try:
            # Check if trainer
            trainer = self.db.table('trainers').select('*').eq(
                'whatsapp', phone_number
            ).execute()
            
            if trainer.data and len(trainer.data) > 0:
                return ('trainer', trainer.data[0])
            
            # Check if client
            client = self.db.table('clients').select('*, trainers(*)').eq(
                'whatsapp', phone_number
            ).execute()
            
            if client.data and len(client.data) > 0:
                return ('client', client.data[0])
            
            return (None, None)
            
        except Exception as e:
            log_error(f"Error getting user context: {str(e)}")
            return (None, None)

    def _get_user_context_dict(self, phone_number: str) -> Dict:
        """Get user context as dictionary for backward compatibility"""
        user_type, user_data = self._get_user_context(phone_number)
        
        context = {
            'phone_number': phone_number,
            'is_trainer': user_type == 'trainer',
            'is_client': user_type == 'client',
            'is_new_user': user_type is None,
            'user_type': user_type
        }
        
        if user_data:
            context['user_data'] = user_data
            context['user_id'] = user_data.get('id')
            context['user_name'] = user_data.get('name')
            context['trainer_id'] = user_data.get('id') if user_type == 'trainer' else user_data.get('trainer_id')
            context['client_id'] = user_data.get('id') if user_type == 'client' else None
            context['name'] = user_data.get('name', 'User')
        
        return context
    
    def _handle_text_message(self, message_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle text messages"""
        try:
            # Extract text from message
            text = message_data.get('text', {}).get('body', '')
            
            if not text:
                return {
                    'success': False,
                    'message': 'No text content found in message'
                }
            
            # Check for special commands first
            if text.strip().lower() == '/help':
                return self._get_help_message(user_type, user_data)
            
            # Use AI to understand intent
            conversation_history = self._get_conversation_history(user_data.get('id'), user_type)
            
            intent_result = self.ai_handler.understand_message(
                message=text,
                sender_type=user_type,
                sender_data=user_data,
                conversation_history=conversation_history
            )
            
            # Log the interaction
            self._log_interaction(
                user_id=user_data.get('id'),
                user_type=user_type,
                message=text,
                intent=intent_result.get('primary_intent'),
                response_type='text'
            )
            
            # Route to appropriate handler based on intent
            primary_intent = intent_result.get('primary_intent', 'general_question')
            
            # Handle conversational intents
            if primary_intent in ['greeting', 'casual_chat', 'thanks', 'farewell', 'status_check']:
                response = self.ai_handler.generate_smart_response(intent_result, user_type, user_data)
                return {
                    'success': True,
                    'message': response
                }
            
            # Handle task-based intents
            intent_handlers = {
                'book_session': self._handle_booking_intent,
                'add_client': self._handle_client_management_intent,
                'view_schedule': self._handle_schedule_intent,
                'request_payment': self._handle_payment_intent,
                'check_revenue': self._handle_analytics_intent,
                'send_workout': self._handle_workout_intent,
                'log_habits': self._handle_habit_intent,
                'setup_habit': self._handle_habit_setup_intent,
                'start_assessment': self._handle_assessment_intent,
                'challenges': self._handle_gamification_intent,
                'leaderboard': self._handle_gamification_intent,
                'set_client_price': self._handle_pricing_intent,
                'view_client_price': self._handle_pricing_intent
            }
            
            handler = intent_handlers.get(primary_intent, self._handle_general_query)
            return handler(intent_result, user_type, user_data)
            
        except Exception as e:
            log_error(f"Error handling text message: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble understanding that. Please try again.'
            }
    
    def _handle_interactive_message(self, message_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle interactive messages (buttons and lists)"""
        try:
            interactive = message_data.get('interactive', {})
            interactive_type = interactive.get('type')
            
            if interactive_type == 'button_reply':
                return self._handle_button_click(interactive, user_type, user_data)
            elif interactive_type == 'list_reply':
                return self._handle_list_selection(interactive, user_type, user_data)
            else:
                return {
                    'success': True,
                    'message': 'I received your selection.'
                }
                
        except Exception as e:
            log_error(f"Error handling interactive message: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I couldn\'t process your selection.'
            }
    
    def _handle_image_message(self, message_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle image messages"""
        try:
            image_data = message_data.get('image', {})
            
            # Check if this is an assessment photo
            if self._is_assessment_context(user_data.get('id'), user_type):
                return self._process_assessment_photo(image_data, user_type, user_data)
            
            return {
                'success': True,
                'message': '📸 Thanks for the image! If this is for an assessment, please use the assessment link I sent you.'
            }
            
        except Exception as e:
            log_error(f"Error handling image message: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I couldn\'t process your image.'
            }
    
    def _handle_button_message(self, message_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle button response messages"""
        try:
            button = message_data.get('button', {})
            button_text = button.get('text', '')
            button_payload = button.get('payload', '')
            
            return self._handle_button_click(
                {'button_reply': {'id': button_payload, 'title': button_text}},
                user_type,
                user_data
            )
            
        except Exception as e:
            log_error(f"Error handling button message: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I couldn\'t process your selection.'
            }
    
    def _handle_booking_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle booking-related intents"""
        try:
            extracted_data = intent_data.get('extracted_data', {})
            
            if user_type == 'client':
                # Client wants to book a session
                return {
                    'success': True,
                    'message': "Let's book your session! 📅\n\nWhen would you like to train?",
                    'buttons': [
                        {'id': 'book_tomorrow', 'title': 'Tomorrow'},
                        {'id': 'book_this_week', 'title': 'This Week'},
                        {'id': 'book_specific', 'title': 'Specific Date'}
                    ]
                }
            else:
                # Trainer managing bookings
                client_name = extracted_data.get('client_name')
                if client_name:
                    return {
                        'success': True,
                        'message': f"Creating booking for {client_name}. Please specify the date and time."
                    }
                else:
                    return {
                        'success': True,
                        'message': "Which client would you like to book a session for?"
                    }
                    
        except Exception as e:
            log_error(f"Error handling booking intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble processing your booking request.'
            }
    
    def _handle_payment_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle payment-related intents"""
        try:
            if user_type == 'trainer':
                return {
                    'success': True,
                    'message': "💰 Payment Management\n\nWhat would you like to do?",
                    'buttons': [
                        {'id': 'request_payment', 'title': 'Request Payment'},
                        {'id': 'view_pending', 'title': 'View Pending'},
                        {'id': 'payment_history', 'title': 'Payment History'}
                    ]
                }
            else:
                return {
                    'success': True,
                    'message': "Let me check your payment status..."
                }
                
        except Exception as e:
            log_error(f"Error handling payment intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble accessing payment information.'
            }
    
    def _handle_analytics_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle analytics/revenue intents"""
        try:
            if user_type == 'trainer':
                # Get basic stats
                from services.analytics import AnalyticsService
                analytics = AnalyticsService(self.db)
                metrics = analytics.get_trainer_dashboard_metrics(user_data['id'], 30)
                
                overview = metrics.get('overview', {})
                revenue = metrics.get('revenue', {})
                
                return {
                    'success': True,
                    'message': f"""📊 Your 30-Day Overview:

💰 Revenue: R{revenue.get('total', 0):,.2f}
👥 Active Clients: {overview.get('active_clients', 0)}
📅 Sessions Completed: {overview.get('completed_sessions', 0)}
✅ Completion Rate: {overview.get('completion_rate', 0):.1f}%

Type 'detailed analytics' for more insights."""
                }
            else:
                return {
                    'success': True,
                    'message': "Let me get your training statistics..."
                }
                
        except Exception as e:
            log_error(f"Error handling analytics intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I couldn\'t retrieve your analytics.'
            }
    
    def _handle_client_management_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle client management intents"""
        try:
            if user_type != 'trainer':
                return {
                    'success': True,
                    'message': "This feature is only available for trainers."
                }
            
            extracted_data = intent_data.get('extracted_data', {})
            client_name = extracted_data.get('client_name')
            
            if client_name:
                # Adding a new client
                return {
                    'success': True,
                    'message': f"Adding {client_name} as a new client. Please provide their phone number (WhatsApp)."
                }
            else:
                # List clients
                from models.client import ClientModel
                client_model = ClientModel(self.db, self.config)
                clients = client_model.get_trainer_clients(user_data['id'])
                
                if clients:
                    client_list = "\n".join([f"• {c['name']}" for c in clients[:10]])
                    return {
                        'success': True,
                        'message': f"Your clients:\n\n{client_list}\n\nTotal: {len(clients)} clients"
                    }
                else:
                    return {
                        'success': True,
                        'message': "You don't have any clients yet. Reply 'add client [name]' to add your first client!"
                    }
                    
        except Exception as e:
            log_error(f"Error handling client management: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble managing client information.'
            }
    
    def _handle_schedule_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle schedule viewing intents"""
        try:
            from datetime import datetime, timedelta
            from models.booking import BookingModel
            booking_model = BookingModel(self.db, self.config)
            
            today = datetime.now().date()
            
            if user_type == 'trainer':
                bookings = booking_model.get_trainer_bookings(
                    user_data['id'],
                    today.isoformat(),
                    (today + timedelta(days=7)).isoformat()
                )
            else:
                bookings = booking_model.get_client_bookings(user_data['id'], 'confirmed')
            
            if bookings:
                schedule_text = "📅 Your upcoming sessions:\n\n"
                for booking in bookings[:5]:
                    client_name = booking.get('clients', {}).get('name', 'Client') if user_type == 'trainer' else 'You'
                    schedule_text += f"• {booking['session_date']} at {booking['session_time']} - {client_name}\n"
                
                return {
                    'success': True,
                    'message': schedule_text
                }
            else:
                return {
                    'success': True,
                    'message': "You don't have any upcoming sessions scheduled."
                }
                
        except Exception as e:
            log_error(f"Error handling schedule intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I couldn\'t retrieve your schedule.'
            }
    
    def _handle_workout_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle workout-related intents"""
        try:
            if user_type == 'trainer':
                extracted_data = intent_data.get('extracted_data', {})
                client_name = extracted_data.get('client_name')
                
                if client_name:
                    return {
                        'success': True,
                        'message': f"I'll help you create a workout for {client_name}. What type of workout?",
                        'buttons': [
                            {'id': 'workout_strength', 'title': 'Strength'},
                            {'id': 'workout_cardio', 'title': 'Cardio'},
                            {'id': 'workout_hiit', 'title': 'HIIT'}
                        ]
                    }
                else:
                    return {
                        'success': True,
                        'message': "Which client would you like to send a workout to?"
                    }
            else:
                return {
                    'success': True,
                    'message': "I'll ask your trainer to send you a workout plan!"
                }
                
        except Exception as e:
            log_error(f"Error handling workout intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble processing the workout request.'
            }
    
    def _handle_habit_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle habit logging intents"""
        try:
            from services.habits import HabitTrackingService
            habit_service = HabitTrackingService(self.db)
            
            extracted_data = intent_data.get('extracted_data', {})
            
            # Check for habit responses
            if extracted_data.get('processed_habit_responses'):
                # Process each habit response
                responses = extracted_data['processed_habit_responses']
                logged_habits = []
                
                for i, response in enumerate(responses):
                    # Map response to habit type (this is simplified, you'd need better mapping)
                    habit_types = ['water_intake', 'vegetables', 'workout_completed']
                    if i < len(habit_types):
                        habit_type = habit_types[i]
                        value = response.get('value', 1 if response.get('completed') else 0)
                        
                        result = habit_service.log_habit(
                            client_id=user_data['id'],
                            habit_type=habit_type,
                            value=value
                        )
                        
                        if result.get('success'):
                            logged_habits.append(habit_type)
                
                if logged_habits:
                    return {
                        'success': True,
                        'message': f"✅ Habits logged: {', '.join(logged_habits)}\n\nGreat job staying consistent! 💪"
                    }
            
            return {
                'success': True,
                'message': "Please log your habits for today:\n\n💧 Water (glasses)?\n🥗 Vegetables (yes/no)?\n💪 Workout (yes/no)?"
            }
            
        except Exception as e:
            log_error(f"Error handling habit intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble logging your habits.'
            }
    
    def _handle_habit_setup_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle habit setup intents"""
        try:
            if user_type != 'trainer':
                return {
                    'success': True,
                    'message': "Please ask your trainer to set up habit tracking for you."
                }
            
            extracted_data = intent_data.get('extracted_data', {})
            client_name = extracted_data.get('client_name')
            habit_type = extracted_data.get('habit_type')
            
            if client_name and habit_type:
                return {
                    'success': True,
                    'message': f"Setting up {habit_type} tracking for {client_name}. What's the daily target?"
                }
            else:
                return {
                    'success': True,
                    'message': "To set up habit tracking, please specify: 'Set up [habit] for [client name]'\n\nAvailable habits: water, steps, sleep, vegetables"
                }
                
        except Exception as e:
            log_error(f"Error handling habit setup: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble setting up habit tracking.'
            }
    
    def _handle_assessment_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle assessment-related intents"""
        try:
            if user_type == 'trainer':
                extracted_data = intent_data.get('extracted_data', {})
                client_name = extracted_data.get('client_name')
                
                if client_name:
                    return {
                        'success': True,
                        'message': f"I'll create an assessment for {client_name}. They'll receive a link to complete it.",
                        'buttons': [
                            {'id': 'send_assessment', 'title': 'Send Now'},
                            {'id': 'schedule_assessment', 'title': 'Schedule'},
                            {'id': 'cancel', 'title': 'Cancel'}
                        ]
                    }
                else:
                    return {
                        'success': True,
                        'message': "Which client needs an assessment?"
                    }
            else:
                return {
                    'success': True,
                    'message': "Let me check if you have any pending assessments..."
                }
                
        except Exception as e:
            log_error(f"Error handling assessment intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble processing the assessment request.'
            }
    
    def _handle_gamification_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle gamification-related intents (challenges, leaderboard)"""
        try:
            from services.dashboard_sync import DashboardSyncService
            from services.whatsapp import WhatsAppService
            
            # Initialize services
            whatsapp = WhatsAppService(self.config, self.db, None)
            sync_service = DashboardSyncService(self.db, self.config, whatsapp)
            
            # Use the sync service to handle the command
            phone = user_data.get('whatsapp', '')
            primary_intent = intent_data.get('primary_intent')
            
            if primary_intent == 'challenges':
                result = sync_service.handle_quick_command('challenges', user_data['id'], user_type, phone)
            elif primary_intent == 'leaderboard':
                result = sync_service.handle_quick_command('leaderboard', user_data['id'], user_type, phone)
            else:
                result = None
            
            if result:
                return result
            
            return {
                'success': True,
                'message': "🎮 Check out the challenges and leaderboard on your dashboard!"
            }
            
        except Exception as e:
            log_error(f"Error handling gamification intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble accessing challenge information.'
            }
    
    def _handle_pricing_intent(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle client pricing intents"""
        try:
            if user_type != 'trainer':
                return {
                    'success': True,
                    'message': "This feature is only available for trainers."
                }
            
            from payment_integration import PaymentIntegration
            payment_integration = PaymentIntegration()
            
            extracted_data = intent_data.get('extracted_data', {})
            primary_intent = intent_data.get('primary_intent')
            
            if primary_intent == 'set_client_price':
                client_name = extracted_data.get('client_name')
                price = extracted_data.get('custom_price')
                
                if client_name and price:
                    result = payment_integration._set_client_price(user_data['id'], client_name, float(price))
                    return result
                else:
                    return {
                        'success': True,
                        'message': "To set a client's price, say: 'Set [client name]'s rate to R[amount]'"
                    }
            
            elif primary_intent == 'view_client_price':
                client_name = extracted_data.get('client_name')
                
                if client_name:
                    result = payment_integration._view_client_price(user_data['id'], client_name)
                    return result
                else:
                    return {
                        'success': True,
                        'message': "Which client's pricing would you like to view?"
                    }
            
            return {
                'success': True,
                'message': "I can help you set or view client pricing. What would you like to do?"
            }
            
        except Exception as e:
            log_error(f"Error handling pricing intent: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I had trouble processing the pricing request.'
            }
    
    def _handle_button_click(self, interactive_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle button click interactions"""
        try:
            button_reply = interactive_data.get('button_reply', {})
            button_id = button_reply.get('id', '')
            
            # Route based on button ID
            if button_id.startswith('book_'):
                return self._handle_booking_button(button_id, user_type, user_data)
            elif button_id.startswith('workout_'):
                return self._handle_workout_button(button_id, user_type, user_data)
            elif button_id.startswith('payment_'):
                return self._handle_payment_button(button_id, user_type, user_data)
            elif button_id == 'register_trainer':
                return {
                    'success': True,
                    'message': "Great! Let's set up your trainer account. Please provide your name and business name."
                }
            elif button_id == 'register_client':
                return {
                    'success': True,
                    'message': "Welcome! To connect you with a trainer, please provide your name."
                }
            else:
                return {
                    'success': True,
                    'message': f"You selected: {button_reply.get('title', 'an option')}"
                }
                
        except Exception as e:
            log_error(f"Error handling button click: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I couldn\'t process your selection.'
            }
    
    def _handle_list_selection(self, interactive_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle list selection interactions"""
        try:
            list_reply = interactive_data.get('list_reply', {})
            selected_id = list_reply.get('id', '')
            
            return {
                'success': True,
                'message': f"You selected: {list_reply.get('title', 'an option')}"
            }
            
        except Exception as e:
            log_error(f"Error handling list selection: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I couldn\'t process your selection.'
            }
    
    def _process_assessment_photo(self, image_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Process assessment photos"""
        try:
            # Store the image reference for the assessment
            return {
                'success': True,
                'message': "📸 Assessment photo received! Please complete your assessment using the link I sent you."
            }
            
        except Exception as e:
            log_error(f"Error processing assessment photo: {str(e)}")
            return {
                'success': False,
                'message': 'Sorry, I couldn\'t process your assessment photo.'
            }
    
    def _handle_booking_button(self, button_id: str, user_type: str, user_data: Dict) -> Dict:
        """Handle booking-related button clicks"""
        if button_id == 'book_tomorrow':
            return {
                'success': True,
                'message': "Great! What time works best for you tomorrow?",
                'buttons': [
                    {'id': 'time_morning', 'title': 'Morning (6-12)'},
                    {'id': 'time_afternoon', 'title': 'Afternoon (12-17)'},
                    {'id': 'time_evening', 'title': 'Evening (17-20)'}
                ]
            }
        elif button_id == 'book_this_week':
            return {
                'success': True,
                'message': "Which day this week works for you?"
            }
        else:
            return {
                'success': True,
                'message': "Please specify your preferred date and time."
            }
    
    def _handle_workout_button(self, button_id: str, user_type: str, user_data: Dict) -> Dict:
        """Handle workout-related button clicks"""
        workout_type = button_id.replace('workout_', '')
        return {
            'success': True,
            'message': f"Creating a {workout_type} workout. How many exercises would you like to include?"
        }
    
    def _handle_payment_button(self, button_id: str, user_type: str, user_data: Dict) -> Dict:
        """Handle payment-related button clicks"""
        if button_id == 'request_payment':
            return {
                'success': True,
                'message': "Which client would you like to request payment from?"
            }
        elif button_id == 'view_pending':
            return {
                'success': True,
                'message': "Checking pending payments..."
            }
        else:
            return {
                'success': True,
                'message': "Loading payment history..."
            }
    
    def _get_help_message(self, user_type: str, user_data: Dict) -> Dict:
        """Get help message based on user type"""
        if user_type == 'trainer':
            return {
                'success': True,
                'message': """📚 *Trainer Commands*

*Client Management:*
• Add client [name]
• View clients
• Set [client]'s rate to R[amount]

*Scheduling:*
• View schedule
• Book session for [client]
• Cancel booking

*Payments:*
• Request payment from [client]
• Check payments
• Payment history

*Workouts & Assessments:*
• Send workout to [client]
• Start assessment for [client]
• View [client] progress

*Analytics:*
• Check revenue
• View analytics
• Client stats

*Challenges:*
• View challenges
• Check leaderboard

Type any command naturally, I'll understand! 😊"""
            }
        else:
            return {
                'success': True,
                'message': """📚 *Client Commands*

*Sessions:*
• Book session
• View schedule
• Cancel booking
• Reschedule

*Progress:*
• Log habits
• View progress
• Check streak
• Assessment results

*Challenges:*
• View challenges
• Check leaderboard
• My stats

*Payments:*
• Check payments
• Payment history

Just type what you need naturally! 💪"""
            }
    
    def _get_conversation_history(self, user_id: str, user_type: str, limit: int = 5) -> List[str]:
        """Get recent conversation history for context"""
        try:
            # Get recent messages from the database
            messages = self.db.table('messages').select('message_text').eq(
                f'{user_type}_id', user_id
            ).order('created_at', desc=True).limit(limit).execute()
            
            if messages.data:
                return [msg['content'] for msg in reversed(messages.data)]
            return []
            
        except Exception as e:
            log_error(f"Error getting conversation history: {str(e)}")
            return []
    
    def _log_interaction(self, user_id: str, user_type: str, message: str, 
                        intent: str, response_type: str):
        """Log the interaction for analytics and history"""
        try:
            self.db.table('messages').insert({
                f'{user_type}_id': user_id,
                'content': message,
                'intent': intent,
                'response_type': response_type,
                'created_at': datetime.now().isoformat()
            }).execute()
            
        except Exception as e:
            log_error(f"Error logging interaction: {str(e)}")
    
    def _is_assessment_context(self, user_id: str, user_type: str) -> bool:
        """Check if user is in assessment context"""
        try:
            # Check if there's a pending assessment for this user
            result = self.db.table('fitness_assessments').select('id').eq(
                f'{user_type}_id', user_id
            ).eq('status', 'pending').execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error checking assessment context: {str(e)}")
            return False
    
    def _handle_general_query(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle general queries that don't match specific intents"""
        try:
            # Use AI to generate a contextual response
            response = self.ai_handler.generate_smart_response(intent_data, user_type, user_data)
            
            return {
                'success': True,
                'message': response
            }
            
        except Exception as e:
            log_error(f"Error handling general query: {str(e)}")
            return {
                'success': True,
                'message': "I'm not sure how to help with that. Type '/help' to see what I can do!"
            }
    
    def _get_help_message(self, user_type: str, user_data: Dict) -> Dict:
        """Get help message based on user type"""
        if user_type == 'trainer':
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
            
        elif user_type == 'client':
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
                
                message = (
                    f"*Payment Status*\n\n"
                    f"Pending payments: R{total_pending:.2f}\n"
                    f"This month received: R0.00\n\n"
                    f"To request payment from client:\n"
                    f'"Request R500 from John"'
            )
            
            else:
                # Get client's payment status
                outstanding = self.db.table('payment_requests').select(
                    'amount, due_date'
                ).eq('client_phone', from_number).eq(
                    'status', 'pending'
                ).execute()
                
                if outstanding.data:
                    total = sum(p['amount'] for p in outstanding.data)
                    message = (
                        f"*Payment Status*\n\n"
                        f"Outstanding: R{total:.2f}\n\n"
                        f"Contact your trainer for payment details."
                    )
                else:
                    message = "You're all paid up! No outstanding payments."
            
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
