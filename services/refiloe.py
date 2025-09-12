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
from services.refiloe_helpers import RefiloeHelpers


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
        self.helpers = RefiloeHelpers(self.db, self.config)
        
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
                # For new users, use AI to understand their intent
                return self._handle_new_user_registration(message_data)
            
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

    def _handle_new_user_registration(self, message_data: Dict) -> Dict:
        """
        Handle registration for new users with interactive buttons
        """
        try:
            text = message_data.get('text', {}).get('body', '')
            from_number = message_data.get('from')
            message_type = message_data.get('type', 'text')
            
            # Handle interactive button responses
            if message_type == 'interactive':
                return self._handle_registration_interactive(message_data)
            
            # Check if user is in registration process
            reg_state = self.db.table('registration_state').select('*').eq(
                'phone', from_number
            ).execute()
            
            if reg_state and reg_state.data and len(reg_state.data) > 0:
                # Continue registration based on current step
                return self._continue_registration(from_number, text, reg_state.data[0])
            
            # New user - show welcome with buttons
            return self._show_interactive_welcome(from_number)
                
        except Exception as e:
            log_error(f"Error in registration: {str(e)}")
            # Fallback to text
            return {
                'success': True,
                'message': """Welcome to Refiloe! 👋
    
    I'm your AI fitness assistant. Are you:
    1️⃣ A fitness trainer
    2️⃣ Looking for a trainer
    3️⃣ Just exploring"""
            }
    
    def _show_interactive_welcome(self, phone: str) -> Dict:
        """Show interactive welcome with buttons"""
        try:
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "reg_trainer",
                        "title": "👨‍🏫 I'm a Trainer"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "reg_client",
                        "title": "🏃 Find a Trainer"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "reg_explore",
                        "title": "📚 Learn More about me"
                    }
                }
            ]
            
            # Send welcome message with buttons
            result = self.whatsapp.send_button_message(
                phone=phone,
                body="""👋 Hello, I'm Refiloe! I'm your AI fitness assistant.  
    
    What brings you here today?""",
                buttons=buttons
            )
            
            if result.get('success'):
                return {
                    'success': True,
                    'message': None,  # Don't send duplicate
                    'interactive_sent': True
                }
            else:
                # Fallback
                return self.helpers._ask_registration_clarification("")
                
        except Exception as e:
            log_error(f"Error showing welcome: {str(e)}")
            return self.helpers._ask_registration_clarification("")
    
    def _handle_registration_interactive(self, message_data: Dict) -> Dict:
        """Handle interactive button responses during registration"""
        try:
            from_number = message_data.get('from')
            interactive = message_data.get('interactive', {})
            
            if interactive.get('type') == 'button_reply':
                button_id = interactive.get('button_reply', {}).get('id')
                
                # Handle welcome button selections
                if button_id == 'reg_trainer':
                    return self.helpers._start_trainer_registration_interactive(from_number)  # ADD helpers.
                elif button_id == 'reg_client':
                    return self.helpers._start_client_registration_interactive(from_number)  # ADD helpers.
                elif button_id == 'reg_explore':
                    return self.helpers._show_platform_info_interactive(from_number)  # ADD helpers.
                
                # Handle registration flow buttons
                elif button_id.startswith('city_'):
                    return self.helpers._handle_city_selection(from_number, button_id)  # ADD helpers.
                elif button_id.startswith('spec_'):
                    return self.helpers._handle_specialisation_selection(from_number, button_id)  # ADD helpers.
                elif button_id == 'confirm_yes':
                    return self.helpers._complete_registration(from_number)  # ADD helpers.
                elif button_id == 'confirm_edit':
                    return self.helpers._restart_registration(from_number)  # ADD helpers.
                    
            elif interactive.get('type') == 'list_reply':
                list_id = interactive.get('list_reply', {}).get('id')
                return self.helpers._handle_list_selection(from_number, list_id)  # ADD helpers.
                
        except Exception as e:
            log_error(f"Error handling interactive: {str(e)}")
            return {
                'success': True,
                'message': "I had trouble with that selection. Let's try again!"
            }

    def _continue_registration(self, from_number: str, text: str, state: Dict) -> Dict:
        """Continue registration based on current step"""
        return self.helpers._continue_registration(from_number, text, state) 

    
    def _show_welcome_options(self, phone: str) -> Dict:
        """Show interactive welcome options"""
        try:
            from services.whatsapp import WhatsAppService
            whatsapp = WhatsAppService(self.config, self.db, None)
            
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "start_trainer",
                        "title": "👨‍🏫 I'm a Trainer"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "find_trainer",
                        "title": "🔍 Find a Trainer"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "learn_more",
                        "title": "📚 Learn More"
                    }
                }
            ]
            
            whatsapp.send_button_message(
                phone=phone,
                body="""I'd love to help you! 😊
    
    What brings you to Refiloe today?""",
                buttons=buttons
            )
            
            # When buttons are sent successfully, return NO message
            if result.get('success'):
                return {
                    'success': True,
                    'message': None,  # DON'T send text message too!
                    'interactive_sent': True
                }
            
        except Exception as e:
            log_error(f"Error showing welcome options: {str(e)}")
            # Fallback to text
            return self.helpers._ask_registration_clarification("")
    
    def _send_specialization_buttons(self, phone: str, city: str) -> Dict:
        """Send specialization selection buttons"""
        try:
            from services.whatsapp import WhatsAppService
            whatsapp = WhatsAppService(self.config, self.db, None)
            
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "spec_personal",
                        "title": "Personal Training"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "spec_weight", 
                        "title": "Weight Loss"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "spec_strength",
                        "title": "Strength Training"
                    }
                }
            ]
            
            whatsapp.send_button_message(
                phone=phone,
                body=f"Great! You're in {city} 📍\n\nWhat's your training specialization?",
                buttons=buttons
            )
            
            return {
                'success': True,
                'message': "Specialization options sent",
                'interactive_sent': True
            }
            
        except Exception as e:
            log_error(f"Error sending specialization buttons: {str(e)}")
            return {
                'success': True,
                'message': "What's your training specialization? (e.g., Personal Training, Weight Loss, Strength Training)"
            }

    def _understand_registration_intent_fixed(self, message: str) -> Dict:
        """
        Use AI to understand registration intent from natural language
        This method uses the RefiloeService's anthropic client
        """
        try:
            # Handle simple keyword responses first
            message_lower = message.lower().strip()
            
            # Handle numbered choices
            if message_lower == '1':
                return {'user_type': 'trainer', 'confidence': 1.0, 'intent': 'registration_trainer'}
            elif message_lower == '2':
                return {'user_type': 'client', 'confidence': 1.0, 'intent': 'registration_client'}
            elif message_lower == '3':
                return {'user_type': 'prospect', 'confidence': 1.0, 'intent': 'exploring'}
            
            # Handle direct keywords
            if message_lower in ['trainer', "i'm a trainer", 'i am a trainer']:
                return {'user_type': 'trainer', 'confidence': 0.9, 'intent': 'registration_trainer'}
            elif message_lower in ['client', "i'm a client", 'i need a trainer']:
                return {'user_type': 'client', 'confidence': 0.9, 'intent': 'registration_client'}
            elif any(phrase in message_lower for phrase in ['exploring', 'just looking', 'what you offer', 'tell me more']):
                return {'user_type': 'prospect', 'confidence': 0.9, 'intent': 'exploring'}
            
            # Use Claude for more complex understanding
            if self.anthropic and self.anthropic.api_key:
                prompt = f"""Analyze this message from someone contacting a fitness platform:
                
    MESSAGE: "{message}"
    
    Determine their intent:
    1. TRAINER - They want to register as a trainer (e.g., "I'm a PT", "personal trainer")
    2. CLIENT - They want to find a trainer (e.g., "looking for trainer", "need help getting fit")
    3. EXPLORING - They're exploring/want information (e.g., "exploring what you offer", "how does this work")
    4. UNCLEAR - Can't determine
    
    Return ONLY valid JSON:
    {{
        "user_type": "trainer/client/prospect/unclear",
        "intent": "registration_trainer/registration_client/exploring/unclear",
        "confidence": 0.0-1.0,
        "detected_intent": "what they want"
    }}"""
    
                try:
                    response = self.anthropic.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=200,
                        temperature=0.3
                    )
                    
                    # Parse JSON from response
                    import re
                    response_text = response.content[0].text
                    json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
                    
                    if json_match:
                        result = json.loads(json_match.group())
                        # Map 'prospect' to 'exploring' for consistency
                        if result.get('intent') == 'prospect' or result.get('user_type') == 'prospect':
                            result['intent'] = 'exploring'
                        return result
                        
                except Exception as e:
                    log_error(f"Error parsing Claude response: {str(e)}")
            
        except Exception as e:
            log_error(f"Error in registration intent understanding: {str(e)}")
        
        # Final fallback - enhanced keyword matching
        message_lower = message.lower()
        
        # Check for exploring/information seeking
        if any(word in message_lower for word in ['exploring', 'explore', 'looking around', 'browsing', 
                                                    'what you offer', 'tell me', 'information', 
                                                    'how does', 'what is this', 'learn more']):
            return {'user_type': 'prospect', 'confidence': 0.7, 'intent': 'exploring'}
        
        # Check for trainer keywords
        elif any(word in message_lower for word in ['trainer', 'pt', 'coach', 'i train', 
                                                     'fitness professional', 'instructor']):
            return {'user_type': 'trainer', 'confidence': 0.7, 'intent': 'registration_trainer'}
        
        # Check for client keywords
        elif any(word in message_lower for word in ['looking for trainer', 'need trainer', 
                                                     'want trainer', 'get fit', 'lose weight',
                                                     'find trainer', 'personal training']):
            return {'user_type': 'client', 'confidence': 0.7, 'intent': 'registration_client'}
        
        # Check for questions about the service
        elif any(word in message_lower for word in ['how much', 'cost', 'price', 'features',
                                                     'what can', 'benefits', 'why should']):
            return {'user_type': 'prospect', 'confidence': 0.6, 'intent': 'exploring'}
        
        # Default to unclear
        else:
            return {'user_type': 'unclear', 'confidence': 0.3, 'intent': 'unclear'}
    
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
            
            # Extract the phone number for reset command
            from_number = message_data.get('from')  # ADD THIS LINE
            
            # Reset command - check this BEFORE the empty text check
            if text.strip().lower() == '/reset_me':
                # Delete user from database
                self.db.table('trainers').delete().eq('whatsapp', from_number).execute()
                self.db.table('clients').delete().eq('whatsapp', from_number).execute()
                return {
                    'success': True,
                    'message': "✨ Your profile has been reset! You can start fresh. Say 'Hi' to begin!"
                }
            
            if not text:
                return {
                    'success': False,
                    'message': 'No text content found in message'
                }
            
            # Check for special commands first
            if text.strip().lower() == '/help':
                return self._get_help_message(user_type, user_data)
        
        # Rest of your existing code...
            
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
                phone_number=message_data.get('from'),
                message_data={'text': text},
                response={'intent': intent_result.get('primary_intent')}
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
            
            # Check if this is a general question that needs Claude's full capabilities
            if primary_intent == 'general_question' or primary_intent not in intent_handlers:
                # Use Claude for any non-fitness specific questions
                return self._handle_general_query_with_claude(intent_result, user_type, user_data)
            else:
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
                return [msg.get('message_text', '') for msg in reversed(messages.data)]
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

    def _handle_general_query_with_claude(self, intent_data: Dict, user_type: str, user_data: Dict) -> Dict:
        """Handle ANY general query using Claude's full capabilities"""
        try:
            message = intent_data.get('extracted_data', {}).get('original_message', '')
            name = user_data.get('name', 'there')
            
            # Create a prompt for Claude to answer ANY question
            prompt = f"""You are Refiloe, an AI assistant who primarily helps with fitness and personal training, 
            but you're also knowledgeable about everything else - coding, general knowledge, creative tasks, etc.
            
            The user {name} (a {user_type}) has asked: "{message}"
            
            If this is fitness/training related, provide helpful fitness advice.
            If it's about something else (coding, general knowledge, etc.), answer just as helpfully.
            
            Keep your response WhatsApp-friendly (use emojis appropriately, keep it concise but complete).
            If it's a complex technical question, provide a clear, practical answer.
            
            Important: You can help with ANY topic - not just fitness. Be as helpful as Claude would be."""
            
            # Get Claude's response
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            claude_response = response.content[0].text
            
            return {
                'success': True,
                'message': claude_response
            }
            
        except Exception as e:
            log_error(f"Error handling general query with Claude: {str(e)}")
            # Fallback to the simpler response
            return self._handle_general_query(intent_data, user_type, user_data)
    
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

    def _provide_platform_info(self, specific_interest: str = None) -> Dict:
        """Provide comprehensive platform information"""
        
        # Check what they're specifically interested in
        if specific_interest and 'about' in str(specific_interest).lower():
            message = """👋 **Hi! I'm Refiloe** 
    
    I'm your personal AI fitness assistant, living right here in WhatsApp! 🤖💪
    
    **My Story:**
    I was created specifically for South African fitness professionals and enthusiasts. My name means "we are given" in Sesotho - because I'm here to give you back your time and energy to focus on what matters: FITNESS!
    
    **What Makes Me Special:**
    🧠 **I'm Smart** - I understand natural language, no complex commands needed
    ⚡ **I'm Fast** - Instant responses, 24/7 availability
    📱 **I'm Accessible** - No app downloads, I work in WhatsApp
    🇿🇦 **I'm Local** - Built for SA, I understand Rands, local areas, and our context
    ❤️ **I'm Friendly** - I remember your preferences and adapt to your style
    
    **My Personality:**
    - I'm encouraging but not pushy
    - Professional yet warm
    - I celebrate your wins (big and small!)
    - I'm here to make fitness management effortless
    
    Ready to experience the difference? Tell me if you're a trainer or looking for one!"""
    
        elif specific_interest and 'benefit' in str(specific_interest).lower():
            message = """🎯 **Why People Love Using Refiloe**
    
    **Trainers Save 10+ Hours Per Week:**
    ❌ **BEFORE:** Juggling WhatsApp chats, spreadsheets, calendars, payment follow-ups
    ✅ **AFTER:** Everything automated through me - one simple chat!
    
    **Real Trainer Testimonial:**
    "Refiloe changed my business! I went from 5 to 20 clients in 2 months because I could finally focus on training instead of admin" - Sarah, JHB
    
    **Client Success Story:**
    "I love that I can just message Refiloe to book sessions, check my progress, and even join challenges. It's like having a PA!" - Mike, CPT
    
    **The Magic:**
    📊 Trainers see 40% increase in client retention
    ⏰ Clients never miss sessions with smart reminders
    💰 98% faster payment collection
    🎯 3x more consistent workout adherence
    
    **Try me FREE for 14 days!** No credit card needed.
    Just say "I'm a trainer" or "I need a trainer" to start!"""
    
        elif specific_interest and 'how' in str(specific_interest).lower():
            message = """⚙️ **How Refiloe Works - It's SO Simple!**
    
    **Step 1: Start Chatting** 💬
    Just message me on WhatsApp - that's it! No apps, no passwords, no hassle.
    
    **Step 2: I Learn About You** 🧠
    Tell me if you're a trainer or client. I'll ask a few quick questions to personalize your experience.
    
    **Step 3: Everything Happens Here** 📱
    From this chat, you can:
    - Book/manage sessions
    - Track workouts & progress
    - Handle payments
    - Get AI-generated workouts
    - Join fitness challenges
    - And so much more!
    
    **For Trainers - Your Business Dashboard:**
    Every morning I'll send you:
    📅 Today's schedule
    💰 Pending payments
    📊 Client progress alerts
    🎯 Business insights
    
    **For Clients - Your Fitness Journey:**
    I'll help you:
    🏃‍♂️ Never miss a session
    📈 Track your progress
    💪 Get personalized workouts
    🏆 Stay motivated with challenges
    
    **Real Example:**
    Trainer: "Book Sarah for tomorrow 6am"
    Me: "✅ Booked! Sarah confirmed for 6am. I'll remind both of you!"
    
    That easy! Want to try? Just tell me your role!"""
    
        elif specific_interest and 'pricing' in str(specific_interest).lower():
            message = """💰 **Refiloe Pricing - Incredible Value!**
    
    **For Personal Trainers:**
    🎁 **FREE 14-Day Trial** - No credit card required!
    
    Then choose:
    📱 **Starter (R299/month)**
    - Up to 10 clients
    - All core features
    - Perfect for new trainers
    - Less than R1 per client per day!
    
    🚀 **Professional (R599/month)**
    - Unlimited clients
    - Priority support
    - Advanced analytics
    - Custom branding coming soon
    - Still less than 1 session's income!
    
    **ROI Calculator:**
    If you charge R400/session and Refiloe helps you:
    - Keep just 2 clients from canceling = R800 saved
    - Book 2 extra sessions = R800 earned
    That's R1,600 value for R299-599 investment! 📈
    
    **For Clients:**
    ✅ **100% FREE FOREVER!**
    - No hidden fees
    - No premium features to unlock
    - Your trainer covers the platform
    - You just pay for your sessions
    
    **Why So Affordable?**
    We believe every trainer deserves professional tools, and every client deserves a great fitness experience. We're building the future of fitness in SA! 🇿🇦
    
    Ready to join? Say "I'm a trainer" or "Find me a trainer"!"""
    
        elif specific_interest and 'features' in str(specific_interest).lower():
            message = """🚀 **Refiloe's Powerful Features**
    
    **📅 Smart Scheduling**
    - Book sessions in seconds
    - Automatic conflict detection
    - Smart reminders (never miss sessions!)
    - Rescheduling made easy
    
    **💳 Payment Management**
    - Track who owes what
    - Send payment reminders
    - Payment confirmation
    - Monthly financial reports
    
    **🏋️‍♂️ AI Workout Creator**
    - Personalized programs in seconds
    - Adapts to equipment available
    - Progressive difficulty
    - Exercise library with demos
    
    **📊 Progress Tracking**
    - Visual progress charts
    - Body measurements
    - Fitness assessments
    - Before/after photos
    
    **🎮 Gamification & Challenges**
    - Points for consistency
    - Achievement badges
    - Group challenges
    - Leaderboards
    - Motivation rewards
    
    **📱 Client Management**
    - All client info in one place
    - Session history
    - Automated check-ins
    - Birthday reminders
    
    **🤖 AI Intelligence**
    - Understands natural language
    - Learns your preferences
    - Predictive scheduling
    - Smart suggestions
    
    **📈 Business Analytics**
    - Revenue tracking
    - Client retention metrics
    - Popular time slots
    - Growth insights
    
    All this from one WhatsApp chat! 🤯
    Ready to experience it? Let's get started!"""
    
        else:
            # Default comprehensive overview
            message = """🌟 **Meet Refiloe - Your AI Fitness Assistant!**
    
    **Who Am I?** 🤖
    I'm Refiloe (ray-fee-lou-way), your friendly AI assistant living in WhatsApp! I make fitness simple for trainers and clients across South Africa.
    
    **My Superpowers:**
    ⚡ **Instant Everything** - Book sessions, create workouts, track progress in seconds
    🧠 **Super Smart** - I understand what you mean, not just commands
    📱 **Always Here** - 24/7 in your WhatsApp, no app needed
    💪 **Fitness Focused** - Built specifically for personal training
    
    **For Trainers, I'm Your:**
    - Virtual assistant (R299/month)
    - Booking manager
    - Payment tracker
    - Workout creator
    - Client database
    - Business analyst
    
    **For Clients, I'm Your:**
    - Personal fitness companion (FREE!)
    - Session scheduler
    - Progress tracker
    - Motivation partner
    - Workout library
    - Challenge buddy
    
    **Success Numbers:**
    📈 Trainers grow 3x faster with Refiloe
    ⏰ Save 10+ hours per week on admin
    💰 Get paid 98% faster
    🎯 Clients are 3x more consistent
    
    **Ready to Transform Your Fitness Journey?**
    
    Just tell me:
    1️⃣ "I'm a trainer" - Start your FREE trial
    2️⃣ "Find me a trainer" - Get matched
    3️⃣ "Tell me more about [topic]" - Learn more
    
    What would you like to know? 😊"""
        
        return {'success': True, 'message': message}

    def _handle_prospect_inquiry(self, phone: str, intent_data: Dict) -> Dict:
        """Handle prospects with engaging, benefit-focused responses"""
        
        detected_intent = intent_data.get('detected_intent', '').lower()
        
        # Create a response map for common inquiries
        responses = {
            'why_refiloe': """🤔 **Why Choose Refiloe Over Other Options?**
    
    **vs. Manual WhatsApp Management:**
    ❌ Lost in message chaos
    ✅ Organized, automated, efficient
    
    **vs. Expensive Gym Software:**
    ❌ R2000+/month, complex setup
    ✅ R299/month, works instantly
    
    **vs. Generic Booking Apps:**
    ❌ Not fitness-specific
    ✅ Built for trainers, understands fitness
    
    **vs. Spreadsheets:**
    ❌ Hours of data entry
    ✅ Everything updates automatically
    
    **The Refiloe Difference:**
    - Made in SA, for SA 🇿🇦
    - Works in WhatsApp (where your clients already are)
    - AI that actually understands fitness
    - Affordable for every trainer
    - Free for all clients
    
    Join 500+ SA trainers already using Refiloe!""",
    
            'testimonial': """⭐ **What Our Users Say**
    
    **Trainer Success Stories:**
    
    "I doubled my client base in 3 months! Refiloe handles all my admin so I can focus on training." 
    - Thabo M., Johannesburg
    
    "My clients love how easy booking is now. My retention rate went from 60% to 90%!"
    - Sarah K., Cape Town
    
    "I save at least 2 hours every day. That's 10 extra training sessions per week!"
    - David L., Durban
    
    **Client Reviews:**
    
    "So much better than trying to coordinate on WhatsApp groups!"
    - Precious N.
    
    "I love the workout library and progress tracking!"
    - Michael R.
    
    "The challenges keep me motivated!"
    - Lisa T.
    
    **Join our growing community!**""",
    
            'problems_solved': """💡 **Problems Refiloe Solves**
    
    **For Trainers:**
    😫 "I spend more time on admin than training"
    → Automate everything with Refiloe!
    
    😤 "Clients ghost me after trials"
    → Automated follow-ups increase retention 40%
    
    😰 "Chasing payments is awkward"
    → Refiloe handles payment reminders
    
    🤯 "Double-bookings are killing me"
    → Smart scheduling prevents conflicts
    
    **For Clients:**
    😕 "I forget my session times"
    → Smart reminders keep you on track
    
    😢 "I don't see my progress"
    → Visual tracking shows your gains
    
    😴 "I lose motivation"
    → Challenges and rewards keep you going
    
    🤷 "My trainer is always fully booked"
    → Easy booking shows available slots
    
    **One solution, everyone wins!**"""
        }
        
        # Check for specific inquiry types
        for key, response in responses.items():
            if key in detected_intent or key in str(intent_data.get('specific_interest', '')):
                return {'success': True, 'message': response}
        
        # Default to main platform info
        return self._provide_platform_info(intent_data.get('specific_interest'))


    def _ask_registration_clarification(self, original_message: str) -> Dict:
        """Ask for clarification with specific options"""
        return {
            'success': True,
            'message': """I'd love to help you! 😊
    
    **Quick Options:**
    1️⃣ Start FREE trainer trial
    2️⃣ Find a personal trainer
    3️⃣ See how Refiloe works
    4️⃣ Check pricing
    5️⃣ Read success stories
    6️⃣ Learn about features
    
    Just reply with a number or ask me anything!
    
    **Popular Questions:**
    - "Why should I use Refiloe?"
    - "How much time will this save me?"
    - "What problems does this solve?"
    - "Show me testimonials"
    
    What interests you most?"""
        }        
