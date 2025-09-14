"""Refiloe AI service - Main conversation handler"""
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class RefiloeService:
    """Main Refiloe AI conversation service"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Conversation states
        self.STATES = {
            'IDLE': 'idle',
            'AWAITING_RESPONSE': 'awaiting_response',
            'REGISTRATION': 'registration',
            'BOOKING': 'booking',
            'ASSESSMENT': 'assessment',
            'HABIT_TRACKING': 'habit_tracking'
        }
    
    def get_conversation_state(self, phone: str) -> Dict:
        """Get current conversation state for user"""
        try:
            result = self.db.table('conversation_states').select('*').eq(
                'phone_number', phone
            ).single().execute()
            
            if result.data:
                return result.data
            
            # Create new state
            return self.create_conversation_state(phone)
            
        except Exception as e:
            log_error(f"Error getting conversation state: {str(e)}")
            return {'state': self.STATES['IDLE']}
    
    def create_conversation_state(self, phone: str) -> Dict:
        """Create new conversation state"""
        try:
            state_data = {
                'phone_number': phone,
                'state': self.STATES['IDLE'],
                'context': {},
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('conversation_states').insert(
                state_data
            ).execute()
            
            return result.data[0] if result.data else state_data
            
        except Exception as e:
            log_error(f"Error creating conversation state: {str(e)}")
            return {'state': self.STATES['IDLE']}
    
    def update_conversation_state(self, phone: str, state: str, 
                                 context: Dict = None) -> bool:
        """Update conversation state"""
        try:
            update_data = {
                'state': state,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if context:
                update_data['context'] = context
            
            result = self.db.table('conversation_states').update(
                update_data
            ).eq('phone_number', phone).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error updating conversation state: {str(e)}")
            return False
    
    def get_conversation_history(self, phone: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        try:
            result = self.db.table('message_history').select('*').eq(
                'phone_number', phone
            ).order('created_at', desc=True).limit(limit).execute()
            
            # Reverse to get chronological order
            return list(reversed(result.data)) if result.data else []
            
        except Exception as e:
            log_error(f"Error getting conversation history: {str(e)}")
            return []
    
    def save_message(self, phone: str, message: str, sender: str, 
                    intent: str = None) -> bool:
        """Save message to history"""
        try:
            message_data = {
                'phone_number': phone,
                'message': message,
                'sender': sender,  # 'user' or 'bot'
                'intent': intent,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('message_history').insert(
                message_data
            ).execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error saving message: {str(e)}")
            return False
    
    def clear_conversation_state(self, phone: str) -> bool:
        """Clear conversation state (reset to idle)"""
        try:
            return self.update_conversation_state(phone, self.STATES['IDLE'], {})
            
        except Exception as e:
            log_error(f"Error clearing conversation state: {str(e)}")
            return False
    
    def get_user_context(self, phone: str) -> Dict:
        """Get complete user context including trainer/client info"""
        try:
            context = {}
            
            # Check if trainer
            trainer = self.db.table('trainers').select('*').eq(
                'whatsapp', phone
            ).single().execute()
            
            if trainer.data:
                context['user_type'] = 'trainer'
                context['user_data'] = trainer.data
                
                # Get active clients count
                clients = self.db.table('clients').select('id').eq(
                    'trainer_id', trainer.data['id']
                ).eq('status', 'active').execute()
                
                context['active_clients'] = len(clients.data) if clients.data else 0
            else:
                # Check if client
                client = self.db.table('clients').select(
                    '*, trainers(name, business_name)'
                ).eq('whatsapp', phone).single().execute()
                
                if client.data:
                    context['user_type'] = 'client'
                    context['user_data'] = client.data
                    
                    if client.data.get('trainers'):
                        context['trainer_name'] = (
                            client.data['trainers'].get('business_name') or 
                            client.data['trainers'].get('name')
                        )
                else:
                    context['user_type'] = 'unknown'
                    context['user_data'] = None
            
            return context
            
        except Exception as e:
            log_error(f"Error getting user context: {str(e)}")
            return {'user_type': 'unknown', 'user_data': None}

    def handle_message(self, phone: str, text: str) -> Dict:
        """Handle incoming WhatsApp message - main entry point"""
        try:
            # Check for reset command FIRST
            if text.strip().lower() == '/reset_me':
                return self._handle_reset_command(phone)
            
            # Check for test commands (optional - for easier testing)
            if text.strip().lower().startswith('/test_'):
                return self._handle_test_command(phone, text.strip().lower())
            
            # Import services we need
            from app import app
            ai_handler = app.config['services']['ai_handler']
            whatsapp_service = app.config['services']['whatsapp']
            
            # Get user context using existing method
            context = self.get_user_context(phone)
            
            # Determine sender type and data from context
            if context['user_type'] == 'trainer':
                sender_type = 'trainer'
                sender_data = context['user_data']
            elif context['user_type'] == 'client':
                sender_type = 'client'
                sender_data = context['user_data']
            else:
                sender_type = 'unknown'
                sender_data = {'name': 'there', 'whatsapp': phone}
            
            # Get conversation history using existing method
            history = self.get_conversation_history(phone)
            history_text = [h['message'] for h in history] if history else []
            
            # Save incoming message using existing method
            self.save_message(phone, text, 'user')
            
            # Check if this is a button response for registration choice
            if sender_type == 'unknown' and self.get_conversation_state(phone).get('state') == 'AWAITING_REGISTRATION_CHOICE':
                return self._handle_registration_choice(phone, text, whatsapp_service)
            
            # Process with AI to understand intent
            intent = ai_handler.understand_message(
                text,
                sender_type,
                sender_data,
                history_text
            )
            
            # Generate smart response using the EXISTING method in AIIntentHandler
            response_text = ai_handler.generate_smart_response(
                intent,
                sender_type,
                sender_data
            )
            
            # Special handling for unknown users - Add welcome buttons after AI response
            if sender_type == 'unknown' and intent.get('primary_intent') in ['greeting', 'general_question', 'registration_inquiry']:
                import random
                
                # Transition phrases to connect AI response to buttons
                transitions = [
                    "I can help you achieve your fitness goals! 💪\n\nWhat brings you here today?",
                    "Let's get you started on your fitness journey! 🚀\n\nHow can I help you today?",
                    "I'm here to make fitness simple and effective! ✨\n\nWhat would you like to do?",
                    "Ready to transform your fitness experience? 💪\n\nTell me about yourself:"
                ]
                
                # Combine AI response with transition to buttons
                full_message = f"{response_text}\n\n{random.choice(transitions)}"
                
                # Create the 3 main option buttons
                buttons = [
                    {
                        'id': 'register_trainer',
                        'title': '💼 I\'m a Trainer'  # 14 chars
                    },
                    {
                        'id': 'register_client', 
                        'title': '🏃 Find a Trainer'  # 16 chars
                    },
                    {
                        'id': 'learn_about_me',
                        'title': '📚 Learn about me'  # 16 chars
                    }
                ]
                
                # Send message with buttons
                whatsapp_service.send_button_message(phone, full_message, buttons)
                
                # Update conversation state to track we're waiting for registration choice
                self.update_conversation_state(phone, 'AWAITING_REGISTRATION_CHOICE')
                
                # Save the full bot response with buttons
                self.save_message(phone, full_message, 'bot', 'registration_prompt')
                
                return {'success': True, 'response': full_message}
            
            # For registered users, just send the AI response normally
            whatsapp_service.send_message(phone, response_text)
            
            # Save bot response
            self.save_message(phone, response_text, 'bot', intent.get('primary_intent'))
            
            # Check if we should start specific registration flows based on explicit intent
            if sender_type == 'unknown':
                if intent.get('primary_intent') == 'registration_trainer' and intent.get('confidence', 0) > 0.8:
                    # User explicitly said they want to register as trainer
                    try:
                        from services.registration.trainer_registration import TrainerRegistration
                        reg = TrainerRegistration(self.db)
                        reg_result = reg.start_registration(phone)
                        if reg_result.get('buttons'):
                            whatsapp_service.send_button_message(
                                phone, 
                                reg_result['message'],
                                reg_result['buttons']
                            )
                        self.update_conversation_state(phone, 'REGISTRATION', {'type': 'trainer'})
                    except ImportError:
                        pass  # Registration module not available
                
                elif intent.get('primary_intent') == 'registration_client' and intent.get('confidence', 0) > 0.8:
                    # User explicitly said they want to find a trainer
                    try:
                        from services.registration.client_registration import ClientRegistration
                        reg = ClientRegistration(self.db)
                        reg_result = reg.start_registration(phone)
                        if reg_result.get('buttons'):
                            whatsapp_service.send_button_message(
                                phone,
                                reg_result['message'], 
                                reg_result['buttons']
                            )
                        self.update_conversation_state(phone, 'REGISTRATION', {'type': 'client'})
                    except ImportError:
                        pass
            
            return {'success': True, 'response': response_text}
            
        except Exception as e:
            log_error(f"Error handling message: {str(e)}")
            # Fallback to a friendly error message
            return {
                'success': False,
                'response': "Sorry, I'm having a bit of trouble right now. Please try again in a moment! 😊"
            }
    
    def _handle_reset_command(self, phone: str) -> Dict:
        """Handle /reset_me command to delete user data"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Safety check - only allow for specific test numbers
            # Add your test numbers here
            ALLOWED_RESET_NUMBERS = [
                '27731863036',  # Your test number from logs
                '27837896738',  # Add other test numbers as needed
                # Add more test numbers here
            ]
            
            # For production, you might want to allow all users to reset
            # In that case, comment out this check
            if phone not in ALLOWED_RESET_NUMBERS:
                response = "⚠️ Reset command is currently only available for test accounts.\n\nIf you need to reset your account, please contact support."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            # Delete user records from all tables
            deleted_count = 0
            
            # Delete from trainers
            result = self.db.table('trainers').delete().eq('whatsapp', phone).execute()
            if result.data:
                deleted_count += len(result.data)
                log_info(f"Deleted trainer record for {phone}")
            
            # Delete from clients
            result = self.db.table('clients').delete().eq('whatsapp', phone).execute()
            if result.data:
                deleted_count += len(result.data)
                log_info(f"Deleted client record for {phone}")
            
            # Delete conversation states
            self.db.table('conversation_states').delete().eq('phone_number', phone).execute()
            
            # Delete message history
            self.db.table('message_history').delete().eq('phone_number', phone).execute()
            
            # Delete registration sessions if exists
            try:
                self.db.table('registration_sessions').delete().eq('phone', phone).execute()
            except:
                pass  # Table might not exist
            
            # Delete processed messages (keep webhook deduplication clean)
            try:
                self.db.table('processed_messages').delete().eq('phone_number', phone).execute()
            except:
                pass
            
            log_info(f"Reset complete for {phone} - deleted {deleted_count} user records")
            
            # Send confirmation message
            response = (
                "✅ *Account Reset Complete!*\n\n"
                "Your account has been completely reset. You're now a new user! 🎉\n\n"
                "Say 'Hi' to start fresh and I'll help you get set up again.\n\n"
                "_This reset deleted all your data including:_\n"
                "• Profile information\n"
                "• Message history\n"
                "• Registration status\n"
                "• Conversation state"
            )
            
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
            
        except Exception as e:
            log_error(f"Error resetting user {phone}: {str(e)}")
            response = "❌ Sorry, couldn't reset your account. Please try again later or contact support."
            
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            whatsapp_service.send_message(phone, response)
            
            return {'success': False, 'response': response}
    
    def _handle_test_command(self, phone: str, command: str) -> Dict:
        """Handle test commands for easier testing of different user states"""
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            
            # Safety check - only for test numbers
            ALLOWED_TEST_NUMBERS = [
                '27731863036',
                '27837896738',
                # Add your test numbers
            ]
            
            if phone not in ALLOWED_TEST_NUMBERS:
                return {'success': True, 'response': "Command not recognized."}
            
            if command == '/test_trainer':
                # Make user a trainer for testing
                self.db.table('clients').delete().eq('whatsapp', phone).execute()
                self.db.table('trainers').upsert({
                    'whatsapp': phone,
                    'name': 'Test Trainer',
                    'email': f'test_trainer_{phone}@test.com',
                    'status': 'active',
                    'business_name': 'Test Fitness',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
                response = "✅ You're now registered as a trainer!\n\nYou can test trainer features like:\n• Adding clients\n• Creating workouts\n• Managing bookings"
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            elif command == '/test_client':
                # Make user a client for testing
                self.db.table('trainers').delete().eq('whatsapp', phone).execute()
                self.db.table('clients').upsert({
                    'whatsapp': phone,
                    'name': 'Test Client',
                    'email': f'test_client_{phone}@test.com',
                    'status': 'active',
                    'created_at': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
                response = "✅ You're now registered as a client!\n\nYou can test client features like:\n• Viewing workouts\n• Booking sessions\n• Tracking habits"
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            elif command == '/test_new':
                # Make user unknown (same as reset but quicker to type)
                self.db.table('trainers').delete().eq('whatsapp', phone).execute()
                self.db.table('clients').delete().eq('whatsapp', phone).execute()
                self.db.table('conversation_states').delete().eq('phone_number', phone).execute()
                
                response = "✅ You're now a new user!\n\nSay 'Hi' to see the welcome message with registration options."
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            elif command == '/test_help':
                response = (
                    "🧪 *Test Commands Available:*\n\n"
                    "*/reset_me* - Complete account reset\n"
                    "*/test_trainer* - Become a trainer\n"
                    "*/test_client* - Become a client\n"
                    "*/test_new* - Become unknown user\n"
                    "*/test_help* - Show this help\n\n"
                    "_These commands are only available for test accounts._"
                )
                whatsapp_service.send_message(phone, response)
                return {'success': True, 'response': response}
            
            return {'success': True, 'response': "Unknown test command. Try /test_help"}
            
        except Exception as e:
            log_error(f"Error handling test command: {str(e)}")
            return {'success': False, 'response': "Test command failed."}
    
    def _handle_registration_choice(self, phone: str, message: str, whatsapp_service) -> Dict:
        """Handle button clicks for registration choice"""
        try:
            # Clear the awaiting state
            self.update_conversation_state(phone, 'IDLE')
            
            # Handle "I'm a Trainer" button
            if 'register_trainer' in message.lower() or "i'm a trainer" in message.lower() or "trainer" in message.lower():
                from services.registration.trainer_registration import TrainerRegistration
                reg = TrainerRegistration(self.db)
                reg_result = reg.start_registration(phone)
                if reg_result.get('buttons'):
                    whatsapp_service.send_button_message(
                        phone,
                        reg_result['message'],
                        reg_result['buttons']
                    )
                else:
                    whatsapp_service.send_message(phone, reg_result['message'])
                
                self.update_conversation_state(phone, 'REGISTRATION', {'type': 'trainer'})
                return {'success': True}
            
            # Handle "Find a Trainer" button
            elif 'register_client' in message.lower() or "find a trainer" in message.lower() or "find trainer" in message.lower():
                from services.registration.client_registration import ClientRegistration
                reg = ClientRegistration(self.db)
                reg_result = reg.start_registration(phone)
                if reg_result.get('buttons'):
                    whatsapp_service.send_button_message(
                        phone,
                        reg_result['message'],
                        reg_result['buttons']
                    )
                else:
                    whatsapp_service.send_message(phone, reg_result['message'])
                
                self.update_conversation_state(phone, 'REGISTRATION', {'type': 'client'})
                return {'success': True}
            
            # Handle "Learn about me" button
            elif 'learn_about_me' in message.lower() or "learn about me" in message.lower():
                info_message = (
                    "🌟 *Hi! I'm Refiloe, your AI fitness assistant!*\n\n"
                    "I was created to make fitness accessible and manageable for everyone passionate about health and wellness "
                    "My name means 'we have been given' in Sesotho - and I'm here to give you the tools for success. 💪\n\n"
                    "✨ *What I Can Do?*\n\n"
                    "📱 *For Personal Trainers:*\n"
                    "• Manage all your clients in one place\n"
                    "• Schedule & track sessions\n"
                    "• Share workouts instantly\n"
                    "• Handle payments seamlessly\n"
                    "• Track client progress\n\n"
                    "🏃 *For Fitness Enthusiasts:*\n"
                    "• Match you with qualified trainers\n"
                    "• Book sessions easily\n"
                    "• Track your fitness journey\n"
                    "• Get personalized workouts\n"
                    "• Monitor your progress\n\n"
                    "I'm available 24/7 right here on WhatsApp! No apps to download, "
                    "no complicated setups - just message me anytime! 🚀\n\n"
                    "Ready to start? Let me know if you're a trainer or looking for one!"
                )
                
                # After learning about Refiloe, offer the registration options
                buttons = [
                    {
                        'id': 'register_trainer',
                        'title': '💼 I\'m a Trainer'
                    },
                    {
                        'id': 'register_client',
                        'title': '🏃 Find a Trainer'
                    }
                ]
                
                whatsapp_service.send_button_message(phone, info_message, buttons)
                
                # Keep state as awaiting choice for the follow-up buttons
                self.update_conversation_state(phone, 'AWAITING_REGISTRATION_CHOICE')
                
                return {'success': True}
            
            # If message doesn't match any button, treat as new message
            else:
                # Reset state and process as normal message
                self.update_conversation_state(phone, 'IDLE')
                return self.handle_message(phone, message)
                
        except Exception as e:
            log_error(f"Error handling registration choice: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, something went wrong. Please try again or just tell me if you're a trainer or looking for one!"
            }
