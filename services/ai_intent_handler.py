"""
AI Intent Handler - Phase 1
Natural language intent detection for Phase 1 features
Uses Claude AI for accurate, context-aware understanding
"""
from typing import Dict, List, Optional
import json
import anthropic
from datetime import datetime
import pytz
from utils.logger import log_info, log_error
from config import Config


class AIIntentHandler:
    """Handles AI-powered intent detection for Phases 1-3"""
    
    def __init__(self, db_or_config, whatsapp_or_supabase=None, services_dict=None):
        """
        Initialize AIIntentHandler with flexible parameters for backward compatibility
        
        Can be called as:
        - AIIntentHandler(db, whatsapp) - Phase 1-3 style
        - AIIntentHandler(Config, supabase, services_dict) - app_core.py style
        """
        # Handle different calling conventions
        if services_dict is not None:
            # Called from app_core.py: (Config, supabase, services_dict)
            self.config = db_or_config
            self.db = whatsapp_or_supabase
            self.whatsapp = services_dict.get('whatsapp') if services_dict else None
            self.services = services_dict
        else:
            # Called from message_router: (db, whatsapp)
            self.db = db_or_config
            self.whatsapp = whatsapp_or_supabase
            self.config = None
            self.services = None
        
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize Claude client
        if Config.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            self.model = "claude-sonnet-4-20250514"
            log_info("AI Intent Handler (Phase 1) initialized with Claude")
        else:
            self.client = None
            log_error("No Anthropic API key - AI intent detection disabled")
    
    def handle_intent(self, phone: str, message: str, role: str, user_id: str,
                     recent_tasks: List[Dict], chat_history: List[Dict]) -> Dict:
        """
        Main entry point - analyze message and respond appropriately
        """
        try:
            if not self.client:
                # Fallback to simple response
                return self._fallback_response(phone, message, role)
            
            # Build context
            context = self._build_context(phone, role, user_id, recent_tasks, chat_history)
            
            # Get AI understanding
            intent = self._detect_intent(message, role, context)
            
            # Generate response based on intent
            return self._generate_response(phone, message, role, intent, context)
            
        except Exception as e:
            log_error(f"Error in AI intent handler: {str(e)}")
            return self._fallback_response(phone, message, role)
    
    def _build_context(self, phone: str, role: str, user_id: str,
                      recent_tasks: List[Dict], chat_history: List[Dict]) -> Dict:
        """Build context for AI"""
        try:
            # Get user data
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            user_data = self.db.table(table).select('*').eq(id_column, user_id).execute()
            
            context = {
                'role': role,
                'user_id': user_id,
                'phone': phone,
                'recent_tasks': [t.get('task_type') for t in recent_tasks[:3]],
                'chat_history': [h.get('message', '')[:100] for h in chat_history[-5:]],
            }
            
            if user_data.data:
                user_info = user_data.data[0]
                context['name'] = user_info.get('first_name') or user_info.get('name', '').split()[0] or 'there'
                
                if role == 'trainer':
                    context['business_name'] = user_info.get('business_name')
                    context['specialization'] = user_info.get('specialization')
                else:
                    context['fitness_goals'] = user_info.get('fitness_goals')
                    context['experience_level'] = user_info.get('experience_level')
            
            return context
            
        except Exception as e:
            log_error(f"Error building context: {str(e)}")
            return {'role': role, 'user_id': user_id}

    
    def _detect_intent(self, message: str, role: str, context: Dict) -> Dict:
        """Use Claude AI to detect user intent"""
        try:
            prompt = self._create_intent_prompt(message, role, context)
            
            response = self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            # Parse AI response
            intent_data = self._parse_ai_response(response.content[0].text)
            
            log_info(f"AI detected intent: {intent_data.get('intent')} (confidence: {intent_data.get('confidence')})")
            
            return intent_data
            
        except Exception as e:
            log_error(f"Error detecting intent: {str(e)}")
            return {
                'intent': 'general_conversation',
                'confidence': 0.3,
                'needs_action': False
            }
    
    def _create_intent_prompt(self, message: str, role: str, context: Dict) -> str:
        """Create prompt for Claude AI"""
        
        # Define available features (Phase 1 & 2)
        if role == 'trainer':
            available_features = """
Available Features (Phase 1):
- View profile (/view-profile)
- Edit profile (/edit-profile)
- Delete account (/delete-account)
- Logout (/logout)
- Switch role (/switch-role if has both roles)
- Help (/help)

Available Features (Phase 2):
- Invite existing client (/invite-trainee)
- Create new client (/create-trainee)
- View clients (/view-trainees)
- Remove client (/remove-trainee)

Coming Soon (Phase 3):
- Create habits
- Assign habits
- View client progress
"""
        else:
            available_features = """
Available Features (Phase 1):
- View profile (/view-profile)
- Edit profile (/edit-profile)
- Delete account (/delete-account)
- Logout (/logout)
- Switch role (/switch-role if has both roles)
- Help (/help)

Available Features (Phase 2):
- Search trainers (/search-trainer)
- Invite trainer (/invite-trainer)
- View trainers (/view-trainers)
- Remove trainer (/remove-trainer)

Coming Soon (Phase 3):
- View assigned habits
- Log habits
- View progress
"""
        
        prompt = f"""You are Refiloe, an AI fitness assistant. Analyze this message from a {role}.

USER: {context.get('name', 'User')} ({role})
MESSAGE: "{message}"

CONTEXT:
- Recent tasks: {', '.join(context.get('recent_tasks', [])) or 'None'}
- Recent chat: {context.get('chat_history', [])}

{available_features}

Analyze the message and return ONLY valid JSON with:
{{
    "intent": "one of: view_profile, edit_profile, delete_account, logout, switch_role, help, invite_trainee, create_trainee, view_trainees, remove_trainee, search_trainer, invite_trainer, view_trainers, remove_trainer, general_conversation, unclear",
    "confidence": 0.0-1.0,
    "needs_action": true/false,
    "suggested_command": "/command or null",
    "user_sentiment": "positive/neutral/negative/frustrated",
    "is_asking_about_phase3": true/false
}}

Examples:
- "show me my profile" → {{"intent": "view_profile", "confidence": 0.9, "needs_action": true, "suggested_command": "/view-profile"}}
- "I want to change my email" → {{"intent": "edit_profile", "confidence": 0.85, "needs_action": true, "suggested_command": "/edit-profile"}}
- "delete my account" → {{"intent": "delete_account", "confidence": 0.95, "needs_action": true, "suggested_command": "/delete-account"}}
- "remove me" → {{"intent": "delete_account", "confidence": 0.85, "needs_action": true, "suggested_command": "/delete-account"}}
- "I want to leave" → {{"intent": "delete_account", "confidence": 0.8, "needs_action": true, "suggested_command": "/delete-account"}}
- "how do I add clients?" → {{"intent": "general_conversation", "confidence": 0.8, "needs_action": false, "is_asking_about_phase2": true}}
- "hi" → {{"intent": "general_conversation", "confidence": 0.9, "needs_action": false}}

IMPORTANT: Be very sensitive to delete/remove/leave phrases - these should map to "delete_account" intent with high confidence.

Return ONLY the JSON, no other text."""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse Claude's JSON response"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            log_error(f"Failed to parse AI response: {e}")
            return {
                'intent': 'general_conversation',
                'confidence': 0.3,
                'needs_action': False
            }
    
    def _generate_response(self, phone: str, message: str, role: str, 
                          intent: Dict, context: Dict) -> Dict:
        """Generate appropriate response based on intent"""
        try:
            intent_type = intent.get('intent', 'general_conversation')
            confidence = intent.get('confidence', 0.5)
            
            # High confidence - provide action
            if confidence >= 0.7 and intent.get('needs_action'):
                return self._provide_action_response(phone, intent_type, intent, role, context)
            
            # Medium confidence - ask for clarification
            elif confidence >= 0.4:
                return self._provide_clarification_response(phone, intent_type, intent, role, context)
            
            # Low confidence - general conversation
            else:
                return self._provide_conversational_response(phone, message, role, context)
                
        except Exception as e:
            log_error(f"Error generating response: {str(e)}")
            return self._fallback_response(phone, message, role)

    
    def _provide_action_response(self, phone: str, intent_type: str, intent: Dict, 
                                role: str, context: Dict) -> Dict:
        """Provide actionable response with buttons"""
        try:
            name = context.get('name', 'there')
            suggested_command = intent.get('suggested_command')
            
            if intent_type == 'view_profile':
                msg = (
                    f"Sure {name}! I can show you your profile.\n\n"
                    f"Click the button below or type /view-profile"
                )
                buttons = [{'id': '/view-profile', 'title': '👤 View Profile'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
            elif intent_type == 'edit_profile':
                msg = (
                    f"I can help you update your profile, {name}!\n\n"
                    f"Click the button below or type /edit-profile"
                )
                buttons = [{'id': '/edit-profile', 'title': '✏️ Edit Profile'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
            elif intent_type == 'delete_account':
                msg = (
                    f"I understand you want to delete your account.\n\n"
                    f"⚠️ This is a permanent action. Are you sure?\n\n"
                    f"Click the button below or type /delete-account"
                )
                buttons = [{'id': '/delete-account', 'title': '🗑️ Delete Account'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
            elif intent_type == 'logout':
                msg = (
                    f"Ready to logout, {name}?\n\n"
                    f"Click the button below or type /logout"
                )
                buttons = [{'id': '/logout', 'title': '🚪 Logout'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
            elif intent_type == 'help':
                msg = (
                    f"I'm here to help, {name}!\n\n"
                    f"Click the button below to see all available commands."
                )
                buttons = [{'id': '/help', 'title': '📚 Show Help'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            # Phase 2: Trainer intents
            elif intent_type == 'invite_trainee':
                msg = (
                    f"Sure {name}! I can help you invite a client.\n\n"
                    f"Click the button below or type /invite-trainee"
                )
                buttons = [{'id': '/invite-trainee', 'title': '📨 Invite Client'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            elif intent_type == 'create_trainee':
                msg = (
                    f"I can help you create a new client account, {name}!\n\n"
                    f"Click the button below or type /create-trainee"
                )
                buttons = [{'id': '/create-trainee', 'title': '➕ Create Client'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            elif intent_type == 'view_trainees':
                msg = (
                    f"Let me show you your clients, {name}!\n\n"
                    f"Click the button below or type /view-trainees"
                )
                buttons = [{'id': '/view-trainees', 'title': '👥 View Clients'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            elif intent_type == 'remove_trainee':
                msg = (
                    f"I can help you remove a client, {name}.\n\n"
                    f"Click the button below or type /remove-trainee"
                )
                buttons = [{'id': '/remove-trainee', 'title': '🗑️ Remove Client'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            # Phase 2: Client intents
            elif intent_type == 'search_trainer':
                msg = (
                    f"I can help you search for trainers, {name}!\n\n"
                    f"Click the button below or type /search-trainer"
                )
                buttons = [{'id': '/search-trainer', 'title': '🔍 Search Trainers'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            elif intent_type == 'invite_trainer':
                msg = (
                    f"Sure {name}! I can help you invite a trainer.\n\n"
                    f"Click the button below or type /invite-trainer"
                )
                buttons = [{'id': '/invite-trainer', 'title': '📨 Invite Trainer'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            elif intent_type == 'view_trainers':
                msg = (
                    f"Let me show you your trainers, {name}!\n\n"
                    f"Click the button below or type /view-trainers"
                )
                buttons = [{'id': '/view-trainers', 'title': '👥 View Trainers'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            elif intent_type == 'remove_trainer':
                msg = (
                    f"I can help you remove a trainer, {name}.\n\n"
                    f"Click the button below or type /remove-trainer"
                )
                buttons = [{'id': '/remove-trainer', 'title': '🗑️ Remove Trainer'}]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
            else:
                # Generic action
                msg = (
                    f"I can help with that, {name}!\n\n"
                    f"Here are some things you can do:"
                )
                buttons = [
                    {'id': '/view-profile', 'title': '👤 View Profile'},
                    {'id': '/help', 'title': '📚 Show Help'}
                ]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'ai_intent_action'
            }
            
        except Exception as e:
            log_error(f"Error providing action response: {str(e)}")
            return self._fallback_response(phone, '', role)
    
    def _provide_clarification_response(self, phone: str, intent_type: str, intent: Dict,
                                       role: str, context: Dict) -> Dict:
        """Ask for clarification when confidence is medium"""
        try:
            name = context.get('name', 'there')
            
            # Check if asking about Phase 3 features
            if intent.get('is_asking_about_phase3'):
                msg = (
                    f"That's a great feature, {name}!\n\n"
                    f"Habit tracking is coming in Phase 3.\n\n"
                    f"For now, here's what you can do:"
                )
                buttons = [
                    {'id': '/view-profile', 'title': '👤 View Profile'},
                    {'id': '/help', 'title': '📚 Show Help'}
                ]
                self.whatsapp.send_button_message(phone, msg, buttons)
                
            else:
                # General clarification
                msg = (
                    f"I'm not quite sure what you need, {name}.\n\n"
                    f"Here are some things I can help with:"
                )
                buttons = [
                    {'id': '/view-profile', 'title': '👤 View Profile'},
                    {'id': '/edit-profile', 'title': '✏️ Edit Profile'},
                    {'id': '/help', 'title': '📚 Show Help'}
                ]
                self.whatsapp.send_button_message(phone, msg, buttons)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'ai_intent_clarification'
            }
            
        except Exception as e:
            log_error(f"Error providing clarification: {str(e)}")
            return self._fallback_response(phone, '', role)
    
    def _provide_conversational_response(self, phone: str, message: str, 
                                        role: str, context: Dict) -> Dict:
        """Provide friendly conversational response"""
        try:
            name = context.get('name', 'there')
            msg_lower = message.lower().strip()
            
            # Greetings
            if any(word in msg_lower for word in ['hi', 'hello', 'hey', 'howzit']):
                msg = (
                    f"Hi {name}! 👋\n\n"
                    f"How can I help you today?"
                )
                
            # Thanks
            elif any(word in msg_lower for word in ['thanks', 'thank you', 'appreciate']):
                msg = (
                    f"You're welcome, {name}! 😊\n\n"
                    f"Is there anything else I can help with?"
                )
                
            # Status check
            elif any(phrase in msg_lower for phrase in ['are you there', 'you there', 'still there']):
                msg = (
                    f"Yes, I'm here {name}! 👍\n\n"
                    f"What can I do for you?"
                )
                
            # General
            else:
                msg = (
                    f"I'm here to help, {name}!\n\n"
                    f"You can ask me to:\n"
                    f"• Show your profile\n"
                    f"• Edit your information\n"
                    f"• Or type /help for all commands"
                )
            
            self.whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'ai_intent_conversation'
            }
            
        except Exception as e:
            log_error(f"Error providing conversational response: {str(e)}")
            return self._fallback_response(phone, message, role)
    
    def _fallback_response(self, phone: str, message: str, role: str) -> Dict:
        """Fallback response when AI is unavailable"""
        try:
            msg = (
                "I'm here to help! Here are some things you can do:\n\n"
                "• /view-profile - View your profile\n"
                "• /edit-profile - Edit your information\n"
                "• /help - Show all commands\n\n"
                "What would you like to do?"
            )
            
            self.whatsapp.send_message(phone, msg)
            
            return {
                'success': True,
                'response': msg,
                'handler': 'ai_intent_fallback'
            }
            
        except Exception as e:
            log_error(f"Error in fallback response: {str(e)}")
            return {
                'success': False,
                'response': "Sorry, I encountered an error.",
                'handler': 'ai_intent_error'
            }
