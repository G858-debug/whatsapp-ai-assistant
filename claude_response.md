<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5485 -->
<!-- Max Tokens: 32000 -->
## ANALYSIS

Looking at the project structure and the previous continuation work, I can see that the main utility files have been created (logger, rate_limiter, input_sanitizer). Now I need to create the remaining missing service files that are imported in the main application files but don't exist yet. The key missing files are:
- services/whatsapp.py
- services/refiloe.py  
- services/scheduler.py
- services/subscription_manager.py
- services/workout.py

## CHANGES NEEDED

### NEW FILE: services/whatsapp.py
```python
"""WhatsApp messaging service"""
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error, log_warning

class WhatsAppService:
    """Handle WhatsApp message sending and receiving"""
    
    def __init__(self, config, supabase_client, logger):
        self.config = config
        self.db = supabase_client
        self.logger = logger
        self.api_url = config.WHATSAPP_API_URL
        self.api_token = config.WHATSAPP_API_TOKEN
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def send_message(self, phone_number: str, message: str, 
                    buttons: List[Dict] = None) -> Dict:
        """Send WhatsApp message"""
        try:
            # Format phone number
            phone = self._format_phone_number(phone_number)
            
            # Build message payload
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }
            
            # Add buttons if provided
            if buttons:
                payload["type"] = "interactive"
                payload["interactive"] = {
                    "type": "button",
                    "body": {"text": message},
                    "action": {"buttons": buttons[:3]}  # Max 3 buttons
                }
            
            # Send request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Message sent to {phone}")
                return {'success': True, 'message_id': response.json().get('messages', [{}])[0].get('id')}
            else:
                log_error(f"Failed to send message: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending WhatsApp message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_template_message(self, phone_number: str, template_name: str, 
                             parameters: List[str] = None) -> Dict:
        """Send WhatsApp template message"""
        try:
            phone = self._format_phone_number(phone_number)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"}
                }
            }
            
            if parameters:
                payload["template"]["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in parameters]
                }]
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Template {template_name} sent to {phone}")
                return {'success': True}
            else:
                log_error(f"Failed to send template: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending template message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_media_message(self, phone_number: str, media_url: str, 
                          media_type: str = 'image', caption: str = None) -> Dict:
        """Send media message (image, document, etc)"""
        try:
            phone = self._format_phone_number(phone_number)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": media_type,
                media_type: {
                    "link": media_url
                }
            }
            
            if caption and media_type in ['image', 'video']:
                payload[media_type]["caption"] = caption
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                log_info(f"Media sent to {phone}")
                return {'success': True}
            else:
                log_error(f"Failed to send media: {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            log_error(f"Error sending media message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark message as read"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.api_url}/messages",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            log_error(f"Error marking message as read: {str(e)}")
            return False
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number to WhatsApp format"""
        # Remove all non-digits
        digits = ''.join(filter(str.isdigit, phone))
        
        # Handle South African numbers
        if digits.startswith('0'):
            digits = '27' + digits[1:]
        elif not digits.startswith('27'):
            digits = '27' + digits
        
        return digits
    
    def send_bulk_messages(self, recipients: List[Dict], message: str) -> Dict:
        """Send bulk messages to multiple recipients"""
        results = {
            'sent': [],
            'failed': []
        }
        
        for recipient in recipients:
            phone = recipient.get('phone')
            name = recipient.get('name', 'User')
            
            # Personalize message
            personalized = message.replace('{name}', name)
            
            result = self.send_message(phone, personalized)
            
            if result['success']:
                results['sent'].append(phone)
            else:
                results['failed'].append({'phone': phone, 'error': result.get('error')})
        
        return results
```

### NEW FILE: services/refiloe.py
```python
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
```

### NEW FILE: services/scheduler.py
```python
"""Scheduling service for reminders and automated tasks"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error

class SchedulerService:
    """Handle scheduling of reminders and automated messages"""
    
    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def check_and_send_reminders(self) -> Dict:
        """Check and send due reminders"""
        try:
            results = {
                'workout_reminders': self._send_workout_reminders(),
                'payment_reminders': self._send_payment_reminders(),
                'assessment_reminders': self._send_assessment_reminders(),
                'habit_reminders': self._send_habit_reminders()
            }
            
            return results
            
        except Exception as e:
            log_error(f"Error checking reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_workout_reminders(self) -> Dict:
        """Send workout reminders"""
        try:
            tomorrow = (datetime.now(self.sa_tz) + timedelta(days=1)).date()
            
            # Get tomorrow's bookings
            bookings = self.db.table('bookings').select(
                '*, clients(name, whatsapp), trainers(name, business_name)'
            ).eq('session_date', tomorrow.isoformat()).eq(
                'status', 'confirmed'
            ).execute()
            
            sent_count = 0
            
            for booking in (bookings.data or []):
                client = booking.get('clients', {})
                trainer = booking.get('trainers', {})
                
                if client.get('whatsapp'):
                    message = (
                        f"🏋️ *Workout Reminder*\n\n"
                        f"Hi {client.get('name', 'there')}! Just a reminder about "
                        f"your training session tomorrow:\n\n"
                        f"📅 Date: {booking['session_date']}\n"
                        f"⏰ Time: {booking['session_time']}\n"
                        f"👤 Trainer: {trainer.get('name', 'Your trainer')}\n\n"
                        f"See you there! 💪"
                    )
                    
                    result = self.whatsapp.send_message(
                        client['whatsapp'], 
                        message
                    )
                    
                    if result['success']:
                        sent_count += 1
                        
                        # Log reminder
                        self.db.table('reminder_logs').insert({
                            'booking_id': booking['id'],
                            'reminder_type': 'workout',
                            'sent_to': client['whatsapp'],
                            'sent_at': datetime.now(self.sa_tz).isoformat()
                        }).execute()
            
            return {'sent': sent_count, 'total': len(bookings.data or [])}
            
        except Exception as e:
            log_error(f"Error sending workout reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_payment_reminders(self) -> Dict:
        """Send payment reminders"""
        try:
            # Get overdue payments
            cutoff_date = (datetime.now(self.sa_tz) - timedelta(days=7)).date()
            
            payments = self.db.table('payment_requests').select(
                '*, clients(name, whatsapp), trainers(name, business_name)'
            ).eq('status', 'pending').lte(
                'created_at', cutoff_date.isoformat()
            ).execute()
            
            sent_count = 0
            
            for payment in (payments.data or []):
                client = payment.get('clients', {})
                
                if client.get('whatsapp'):
                    message = (
                        f"💳 *Payment Reminder*\n\n"
                        f"Hi {client.get('name', 'there')}! You have a pending "
                        f"payment request:\n\n"
                        f"Amount: R{payment['amount']}\n"
                        f"Description: {payment.get('description', 'Training sessions')}\n\n"
                        f"Please complete the payment at your earliest convenience."
                    )
                    
                    result = self.whatsapp.send_message(
                        client['whatsapp'],
                        message
                    )
                    
                    if result['success']:
                        sent_count += 1
            
            return {'sent': sent_count, 'total': len(payments.data or [])}
            
        except Exception as e:
            log_error(f"Error sending payment reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_assessment_reminders(self) -> Dict:
        """Send assessment reminders"""
        try:
            # Get due assessments
            result = self.db.table('fitness_assessments').select(
                '*, clients(name, whatsapp)'
            ).eq('status', 'pending').lte(
                'due_date', datetime.now(self.sa_tz).isoformat()
            ).execute()
            
            sent_count = 0
            
            for assessment in (result.data or []):
                client = assessment.get('clients', {})
                
                if client.get('whatsapp'):
                    message = (
                        f"📋 *Assessment Reminder*\n\n"
                        f"Hi {client.get('name', 'there')}! Your fitness assessment "
                        f"is due. Please complete it to track your progress.\n\n"
                        f"Reply 'start assessment' to begin."
                    )
                    
                    result = self.whatsapp.send_message(
                        client['whatsapp'],
                        message
                    )
                    
                    if result['success']:
                        sent_count += 1
            
            return {'sent': sent_count}
            
        except Exception as e:
            log_error(f"Error sending assessment reminders: {str(e)}")
            return {'error': str(e)}
    
    def _send_habit_reminders(self) -> Dict:
        """Send daily habit tracking reminders"""
        try:
            # Get clients with habit tracking enabled
            clients = self.db.table('clients').select(
                'id, name, whatsapp'
            ).eq('habit_tracking_enabled', True).execute()
            
            sent_count = 0
            current_hour = datetime.now(self.sa_tz).hour
            
            # Only send between 7am and 8pm
            if 7 <= current_hour <= 20:
                for client in (clients.data or []):
                    # Check if already logged today
                    today = datetime.now(self.sa_tz).date()
                    
                    logged = self.db.table('habit_tracking').select('id').eq(
                        'client_id', client['id']
                    ).eq('date', today.isoformat()).execute()
                    
                    if not logged.data and client.get('whatsapp'):
                        message = (
                            f"📊 *Daily Check-in*\n\n"
                            f"Hi {client.get('name', 'there')}! Time to log your "
                            f"daily habits:\n\n"
                            f"• Water intake (liters)\n"
                            f"• Sleep hours\n"
                            f"• Steps taken\n"
                            f"• Workout completed (yes/no)\n\n"
                            f"Reply with your numbers separated by commas.\n"
                            f"Example: 2.5, 7, 8000, yes"
                        )
                        
                        result = self.whatsapp.send_message(
                            client['whatsapp'],
                            message
                        )
                        
                        if result['success']:
                            sent_count += 1
            
            return {'sent': sent_count}
            
        except Exception as e:
            log_error(f"Error sending habit reminders: {str(e)}")
            return {'error': str(e)}
    
    def schedule_message(self, phone: str, message: str, 
                        send_at: datetime) -> Dict:
        """Schedule a message for future sending"""
        try:
            scheduled_data = {
                'phone_number': phone,
                'message': message,
                'scheduled_for': send_at.isoformat(),
                'status': 'pending',
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('scheduled_messages').insert(
                scheduled_data
            ).execute()
            
            if result.data:
                return {'success': True, 'scheduled_id': result.data[0]['id']}
            
            return {'success': False, 'error': 'Failed to schedule message'}
            
        except Exception as e:
            log_error(f"Error scheduling message: {str(e)}")
            return {'success': False, 'error': str(e)}
```

### NEW FILE: services/subscription_manager.py
```python
"""Subscription management service"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error

class SubscriptionManager:
    """Manage trainer subscriptions"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Subscription plans
        self.PLANS = {
            'free': {
                'name': 'Free',
                'price': 0,
                'max_clients': 3,
                'features': ['basic_scheduling', 'whatsapp_bot']
            },
            'professional': {
                'name': 'Professional',
                'price': 49,
                'max_clients': None,  # Unlimited
                'features': ['all_features', 'priority_support', 'analytics']
            }
        }
    
    def get_trainer_subscription(self, trainer_id: str) -> Dict:
        """Get trainer's current subscription"""
        try:
            result = self.db.table('trainer_subscriptions').select('*').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').single().execute()
            
            if result.data:
                return result.data
            
            # Return free plan by default
            return {
                'plan': 'free',
                'status': 'active',
                'max_clients': self.PLANS['free']['max_clients']
            }
            
        except Exception as e:
            log_error(f"Error getting subscription: {str(e)}")
            return {
                'plan': 'free',
                'status': 'active',
                'max_clients': 3
            }
    
    def can_add_client(self, trainer_id: str) -> bool:
        """Check if trainer can add more clients"""
        try:
            subscription = self.get_trainer_subscription(trainer_id)
            
            # Unlimited for professional
            if subscription['plan'] == 'professional':
                return True
            
            # Check current client count
            clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            current_count = len(clients.data) if clients.data else 0
            max_clients = subscription.get('max_clients', 3)
            
            return current_count < max_clients
            
        except Exception as e:
            log_error(f"Error checking client limit: {str(e)}")
            return False
    
    def upgrade_subscription(self, trainer_id: str, plan: str) -> Dict:
        """Upgrade trainer subscription"""
        try:
            if plan not in self.PLANS:
                return {'success': False, 'error': 'Invalid plan'}
            
            # Deactivate current subscription
            self.db.table('trainer_subscriptions').update({
                'status': 'inactive',
                'ended_at': datetime.now(self.sa_tz).isoformat()
            }).eq('trainer_id', trainer_id).eq('status', 'active').execute()
            
            # Create new subscription
            subscription_data = {
                'trainer_id': trainer_id,
                'plan': plan,
                'status': 'active',
                'price': self.PLANS[plan]['price'],
                'start_date': datetime.now(self.sa_tz).isoformat(),
                'end_date': (datetime.now(self.sa_tz) + timedelta(days=30)).isoformat(),
                'auto_renew': True
            }
            
            result = self.db.table('trainer_subscriptions').insert(
                subscription_data
            ).execute()
            
            if result.data:
                log_info(f"Trainer {trainer_id} upgraded to {plan}")
                return {'success': True, 'subscription': result.data[0]}
            
            return {'success': False, 'error': 'Failed to create subscription'}
            
        except Exception as e:
            log_error(f"Error upgrading subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def cancel_subscription(self, trainer_id: str) -> Dict:
        """Cancel trainer subscription"""
        try:
            result = self.db.table('trainer_subscriptions').update({
                'auto_renew': False,
                'cancelled_at': datetime.now(self.sa_tz).isoformat()
            }).eq('trainer_id', trainer_id).eq('status', 'active').execute()
            
            if result.data:
                return {'success': True, 'message': 'Subscription will end at the end of the billing period'}
            
            return {'success': False, 'error': 'No active subscription found'}
            
        except Exception as e:
            log_error(f"Error cancelling subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_subscription_limits(self, trainer_id: str) -> Dict:
        """Check current usage against subscription limits"""
        try:
            subscription = self.get_trainer_subscription(trainer_id)
            
            # Get current usage
            clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            current_clients = len(clients.data) if clients.data else 0
            max_clients = subscription.get('max_clients')
            
            return {
                'plan': subscription['plan'],
                'current_clients': current_clients,
                'max_clients': max_clients,
                'can_add_clients': max_clients is None or current_clients < max_clients,
                'usage_percentage': (current_clients / max_clients * 100) if max_clients else 0
            }
            
        except Exception as e:
            log_error(f"Error checking limits: {str(e)}")
            return {
                'plan': 'free',
                'current_clients': 0,
                'max_clients': 3,
                'can_add_clients': True
            }
```

### NEW FILE: services/workout.py
```python
"""Workout management service"""
from typing import Dict, List, Optional
from datetime import datetime
import pytz
from utils.logger import log_info, log_error

class WorkoutService:
    """Handle workout creation and management"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def create_workout(self, trainer_id: str, workout_data: Dict) -> Dict:
        """Create a new workout"""
        try:
            workout = {
                'trainer_id': trainer_id,
                'name': workout_data.get('name', 'Workout'),
                'description': workout_data.get('description'),
                'exercises': workout_data.get('exercises', []),
                'duration_minutes': workout_data.get('duration', 60),
                'difficulty': workout_data.get('difficulty', 'intermediate'),
                'category': workout_data.get('category', 'general'),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('workouts').insert(workout).execute()
            
            if result.data:
                log_info(f"Workout created: {workout['name']}")
                return {'success': True, 'workout_id': result.data[0]['id']}
            
            return {'success': False, 'error': 'Failed to create workout'}
            
        except Exception as e:
            log_error(f"Error creating workout: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def assign_workout(self, trainer_id: str, client_id: str, 
                      workout_id: str, scheduled_date: str = None) -> Dict:
        """Assign workout to client"""
        try:
            # Verify workout belongs to trainer
            workout = self.db.table('workouts').select('id').eq(
                'id', workout_id
            ).eq('trainer_id', trainer_id).single().execute()
            
            if not workout.data:
                return {'success': False, 'error': 'Workout not found'}
            
            assignment = {
                'workout_id': workout_id,
                'client_id': client_id,
                'trainer_id': trainer_id,
                'scheduled_date': scheduled_date or datetime.now(self.sa_tz).date().isoformat(),
                'status': 'assigned',
                'assigned_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('workout_assignments').insert(
                assignment
            ).execute()
            
            if result.data:
                log_info(f"Workout assigned to client {client_id}")
                return {'success': True, 'assignment_id': result.data[0]['id']}
            
            return {'success': False, 'error': 'Failed to assign workout'}
            
        except Exception as e:
            log_error(f"Error assigning workout: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_client_workouts(self, client_id: str, status: str = None) -> List[Dict]:
        """Get workouts assigned to client"""
        try:
            query = self.db.table('workout_assignments').select(
                '*, workouts(*)'
            ).eq('client_id', client_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('scheduled_date', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting client workouts: {str(e)}")
            return []
    
    def mark_workout_completed(self, assignment_id: str, 
                              feedback: Dict = None) -> Dict:
        """Mark workout as completed"""
        try:
            update_data = {
                'status': 'completed',
                'completed_at': datetime.now(self.sa_tz).isoformat()
            }
            
            if feedback:
                update_data['feedback'] = feedback
            
            result = self.db.table('workout_assignments').update(
                update_data
            ).eq('id', assignment_id).execute()
            
            if result.data:
                log_info(f"Workout {assignment_id} marked as completed")
                return {'success': True}
            
            return {'success': False, 'error': 'Assignment not found'}
            
        except Exception as e:
            log_error(f"Error marking workout completed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_workout_library(self, trainer_id: str, 
                          category: str = None) -> List[Dict]:
        """Get trainer's workout library"""
        try:
            query = self.db.table('workouts').select('*').eq(
                'trainer_id', trainer_id
            )
            
            if category:
                query = query.eq('category', category)
            
            result = query.order('created_at', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error getting workout library: {str(e)}")
            return []
    
    def format_workout_for_whatsapp(self, workout: Dict) -> str:
        """Format workout for WhatsApp message"""
        try:
            message = f"🏋️ *{workout['name']}*\n\n"
            
            if workout.get('description'):
                message += f"_{workout['description']}_\n\n"
            
            message += f"⏱ Duration: {workout.get('duration_minutes', 60)} minutes\n"
            message += f"💪 Difficulty: {workout.get('difficulty', 'intermediate').title()}\n\n"
            
            if workout.get('exercises'):
                message += "*Exercises:*\n"
                for i, exercise in enumerate(workout['exercises'], 1):
                    message += f"{i}. {exercise.get('name', 'Exercise')}"
                    
                    if exercise.get('sets') and exercise.get('reps'):
                        message += f" - {exercise['sets']} sets x {exercise['reps']} reps"
                    elif exercise.get('duration'):
                        message += f" - {exercise['duration']}"
                    
                    message += "\n"
            
            return message
            
        except Exception as e:
            log_error(f"Error formatting workout: {str(e)}")
            return "Workout details unavailable"
```

## SUMMARY

Created 5 essential service files that were missing from the project:
1. **services/whatsapp.py** - WhatsApp messaging service for sending messages, templates, and media
2. **services/refiloe.py** - Main Refiloe AI conversation handler with state management
3. **services/scheduler.py** - Scheduling service for automated reminders and tasks
4. **services/subscription_manager.py** - Manages trainer subscription plans and limits
5. **services/workout.py** - Workout creation, assignment, and management service

All files are under 300 lines each and provide the core functionality needed by the application. The services integrate with Supabase for data persistence and include proper error handling and logging.