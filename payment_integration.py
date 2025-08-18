# payment_integration.py
"""
Payment Integration for WhatsApp Bot
Integrates payment functionality into the existing WhatsApp message flow
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from payment_manager import PaymentManager
import logging

logger = logging.getLogger(__name__)

class PaymentIntegration:
    """Handles payment-related WhatsApp interactions"""
    
    def __init__(self):
        """Initialize payment integration"""
        self.payment_manager = PaymentManager()
        
        # Payment command patterns
        self.patterns = {
            'setup_payment': r'(?i)(setup payment|save card|add payment method)\s+(?:for\s+)?(.+)',
            'request_payment': r'(?i)(request payment|charge|bill)\s+(?:from\s+)?(.+)\s+(?:R?(\d+(?:\.\d{2})?))',
            'check_payments': r'(?i)(check payments?|payment status|pending payments?)',
            'payment_history': r'(?i)(payment history|past payments?|transaction history)',
            'upgrade_plan': r'(?i)(upgrade|professional plan|upgrade plan)',
            'set_reminder': r'(?i)(set payment reminder|payment reminder)\s+(?:day\s+)?(\d+)',
            'enable_auto': r'(?i)(enable auto payment|auto approve)\s+(?:R?(\d+))',
            'payment_help': r'(?i)(payment help|how to pay|payment info)'
        }

    def process_payment_message(self, phone: str, message: str, user_type: str, user_id: str) -> Optional[Dict]:
        """
        Process payment-related messages
        Returns None if not a payment command, otherwise returns response dict
        """
        try:
            # Check if it's a payment approval response
            if message.lower().strip() in ['yes', 'no']:
                result = self.payment_manager.handle_payment_response(phone, message)
                if result['success']:
                    return {
                        'type': 'payment_response',
                        'message': result['message'],
                        'processed': True
                    }
            
            # Check for payment commands
            for pattern_name, pattern in self.patterns.items():
                match = re.match(pattern, message.strip())
                if match:
                    return self._handle_payment_command(pattern_name, match, user_type, user_id, phone)
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing payment message: {str(e)}")
            return None

    def _handle_payment_command(self, command: str, match, user_type: str, user_id: str, phone: str) -> Dict:
        """
        Handle specific payment commands
        """
        try:
            if command == 'setup_payment':
                if user_type != 'trainer':
                    return {
                        'type': 'error',
                        'message': 'Only trainers can set up client payments.'
                    }
                
                client_name = match.group(2).strip()
                return self._setup_client_payment(user_id, client_name)
            
            elif command == 'request_payment':
                if user_type != 'trainer':
                    return {
                        'type': 'error',
                        'message': 'Only trainers can request payments.'
                    }
                
                client_name = match.group(2).strip()
                amount = float(match.group(3))
                return self._request_payment(user_id, client_name, amount)
            
            elif command == 'check_payments':
                return self._check_payment_status(user_type, user_id)
            
            elif command == 'payment_history':
                return self._get_payment_history(user_type, user_id)
            
            elif command == 'upgrade_plan':
                if user_type != 'trainer':
                    return {
                        'type': 'error',
                        'message': 'Only trainers can upgrade plans.'
                    }
                return self._upgrade_plan(user_id)
            
            elif command == 'set_reminder':
                if user_type != 'trainer':
                    return {
                        'type': 'error',
                        'message': 'Only trainers can set payment reminders.'
                    }
                
                day = int(match.group(2))
                return self._set_payment_reminder(user_id, day)
            
            elif command == 'enable_auto':
                if user_type != 'client':
                    return {
                        'type': 'error',
                        'message': 'Only clients can enable auto-payment.'
                    }
                
                max_amount = float(match.group(2)) if match.group(2) else 1000
                return self._enable_auto_payment(user_id, max_amount)
            
            elif command == 'payment_help':
                return self._get_payment_help(user_type)
            
            return {
                'type': 'error',
                'message': 'Unknown payment command.'
            }
            
        except Exception as e:
            logger.error(f"Error handling payment command: {str(e)}")
            return {
                'type': 'error',
                'message': f'Error processing payment command: {str(e)}'
            }

    def _setup_client_payment(self, trainer_id: str, client_name: str) -> Dict:
        """
        Set up payment method for a client
        """
        try:
            # Find client by name
            supabase = self.payment_manager.supabase
            client = supabase.table('clients').select('*').eq(
                'trainer_id', trainer_id
            ).ilike('name', f'%{client_name}%').limit(1).execute()
            
            if not client.data:
                return {
                    'type': 'error',
                    'message': f'Client "{client_name}" not found. Please check the name and try again.'
                }
            
            # Create token setup request
            result = self.payment_manager.create_token_setup_request(trainer_id, client.data[0]['id'])
            
            if result['success']:
                return {
                    'type': 'payment_setup',
                    'message': (
                        f"✅ Payment setup initiated for {client.data[0]['name']}!\n\n"
                        f"I've sent them a secure link to save their card details.\n"
                        f"Setup code: {result['setup_code']}\n\n"
                        f"They'll receive a WhatsApp message with instructions."
                    )
                }
            else:
                return {
                    'type': 'error',
                    'message': result.get('message', 'Failed to create payment setup.')
                }
                
        except Exception as e:
            logger.error(f"Error setting up client payment: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to set up client payment.'
            }

    def _request_payment(self, trainer_id: str, client_name: str, amount: float) -> Dict:
        """
        Request payment from a client
        """
        try:
            # Find client
            supabase = self.payment_manager.supabase
            client = supabase.table('clients').select('*').eq(
                'trainer_id', trainer_id
            ).ilike('name', f'%{client_name}%').limit(1).execute()
            
            if not client.data:
                return {
                    'type': 'error',
                    'message': f'Client "{client_name}" not found.'
                }
            
            # Create payment request
            description = f"Training sessions - {datetime.now().strftime('%B %Y')}"
            result = self.payment_manager.create_payment_request(
                trainer_id, 
                client.data[0]['id'], 
                amount, 
                description
            )
            
            if result['success']:
                return {
                    'type': 'payment_request',
                    'message': (
                        f"💰 Payment request created!\n\n"
                        f"Client: {client.data[0]['name']}\n"
                        f"Amount: R{amount}\n\n"
                        f"I've sent them a WhatsApp message to approve the payment."
                    )
                }
            else:
                return {
                    'type': 'error',
                    'message': result.get('message', 'Failed to create payment request.')
                }
                
        except Exception as e:
            logger.error(f"Error requesting payment: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to request payment.'
            }

    def _check_payment_status(self, user_type: str, user_id: str) -> Dict:
        """
        Check pending payments
        """
        try:
            supabase = self.payment_manager.supabase
            
            if user_type == 'trainer':
                # Get pending payments for trainer
                pending = supabase.table('payment_requests').select(
                    '*, clients(name)'
                ).eq('trainer_id', user_id).eq('status', 'pending_client').execute()
                
                if pending.data:
                    payment_list = []
                    total = 0
                    for p in pending.data:
                        payment_list.append(
                            f"• {p['clients']['name']}: R{p['amount']} (expires {p['expires_at'][:10]})"
                        )
                        total += p['amount']
                    
                    return {
                        'type': 'payment_status',
                        'message': (
                            f"📋 *Pending Payments*\n\n"
                            f"{chr(10).join(payment_list)}\n\n"
                            f"*Total pending: R{total}*"
                        )
                    }
                else:
                    return {
                        'type': 'payment_status',
                        'message': "✅ No pending payments!"
                    }
            else:
                # Get pending payments for client
                pending = supabase.table('payment_requests').select(
                    '*, trainers(name, business_name)'
                ).eq('client_id', user_id).eq('status', 'pending_client').execute()
                
                if pending.data:
                    payment_list = []
                    for p in pending.data:
                        trainer_name = p['trainers']['business_name'] or p['trainers']['name']
                        payment_list.append(
                            f"• {trainer_name}: R{p['amount']}\n  {p['description']}"
                        )
                    
                    return {
                        'type': 'payment_status',
                        'message': (
                            f"💳 *Pending Payment Requests*\n\n"
                            f"{chr(10).join(payment_list)}\n\n"
                            f"Reply YES to approve or NO to decline"
                        )
                    }
                else:
                    return {
                        'type': 'payment_status',
                        'message': "✅ No pending payment requests!"
                    }
                    
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to check payment status.'
            }

    def _get_payment_history(self, user_type: str, user_id: str) -> Dict:
        """
        Get payment history
        """
        try:
            supabase = self.payment_manager.supabase
            
            # Get last 10 payments
            if user_type == 'trainer':
                payments = supabase.table('payments').select(
                    '*, clients(name)'
                ).eq('trainer_id', user_id).eq('status', 'paid').order(
                    'paid_date', desc=True
                ).limit(10).execute()
            else:
                payments = supabase.table('payments').select(
                    '*, trainers(name, business_name)'
                ).eq('client_id', user_id).eq('status', 'paid').order(
                    'paid_date', desc=True
                ).limit(10).execute()
            
            if payments.data:
                history_list = []
                total = 0
                
                for p in payments.data:
                    if user_type == 'trainer':
                        name = p['clients']['name']
                    else:
                        name = p['trainers']['business_name'] or p['trainers']['name']
                    
                    history_list.append(
                        f"• {p['paid_date'][:10]} - {name}: R{p['amount']}"
                    )
                    total += p['amount']
                
                return {
                    'type': 'payment_history',
                    'message': (
                        f"📊 *Payment History (Last 10)*\n\n"
                        f"{chr(10).join(history_list)}\n\n"
                        f"*Total: R{total}*"
                    )
                }
            else:
                return {
                    'type': 'payment_history',
                    'message': "No payment history found."
                }
                
        except Exception as e:
            logger.error(f"Error getting payment history: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to get payment history.'
            }

    def _upgrade_plan(self, trainer_id: str) -> Dict:
        """
        Upgrade trainer to Professional plan
        """
        try:
            result = self.payment_manager.upgrade_to_professional(trainer_id)
            
            if result['success']:
                return {
                    'type': 'upgrade',
                    'message': (
                        f"🚀 *Upgrade to Professional Plan*\n\n"
                        f"• Unlimited clients (currently limited to 3)\n"
                        f"• All features included\n"
                        f"• R49/month or R360/year\n\n"
                        f"Click here to upgrade:\n"
                        f"{result['payment_url']}\n\n"
                        f"You can cancel anytime!"
                    )
                }
            else:
                return {
                    'type': 'error',
                    'message': 'Failed to generate upgrade link.'
                }
                
        except Exception as e:
            logger.error(f"Error upgrading plan: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to process upgrade.'
            }

    def _set_payment_reminder(self, trainer_id: str, day: int) -> Dict:
        """
        Set monthly payment reminder day
        """
        try:
            if day < 1 or day > 28:
                return {
                    'type': 'error',
                    'message': 'Please choose a day between 1 and 28.'
                }
            
            supabase = self.payment_manager.supabase
            
            # Update or create reminder settings
            existing = supabase.table('payment_reminders').select('*').eq(
                'trainer_id', trainer_id
            ).execute()
            
            if existing.data:
                supabase.table('payment_reminders').update({
                    'reminder_day': day,
                    'reminder_enabled': True,
                    'next_scheduled_date': self._calculate_next_date(day)
                }).eq('trainer_id', trainer_id).execute()
            else:
                supabase.table('payment_reminders').insert({
                    'trainer_id': trainer_id,
                    'reminder_day': day,
                    'reminder_enabled': True,
                    'next_scheduled_date': self._calculate_next_date(day)
                }).execute()
            
            return {
                'type': 'reminder_set',
                'message': (
                    f"✅ Payment reminder set for day {day} of each month!\n\n"
                    f"You'll receive a reminder to collect payments from your clients."
                )
            }
            
        except Exception as e:
            logger.error(f"Error setting payment reminder: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to set payment reminder.'
            }

    def _enable_auto_payment(self, client_id: str, max_amount: float) -> Dict:
        """
        Enable auto-approval for payments
        """
        try:
            supabase = self.payment_manager.supabase
            
            # Get client's trainer
            client = supabase.table('clients').select('trainer_id').eq('id', client_id).single().execute()
            
            if not client.data:
                return {
                    'type': 'error',
                    'message': 'Client record not found.'
                }
            
            # Update or create payment preferences
            existing = supabase.table('client_payment_preferences').select('*').eq(
                'client_id', client_id
            ).eq('trainer_id', client.data['trainer_id']).execute()
            
            if existing.data:
                supabase.table('client_payment_preferences').update({
                    'auto_approve_enabled': True,
                    'auto_approve_max_amount': max_amount
                }).eq('client_id', client_id).eq('trainer_id', client.data['trainer_id']).execute()
            else:
                supabase.table('client_payment_preferences').insert({
                    'client_id': client_id,
                    'trainer_id': client.data['trainer_id'],
                    'auto_approve_enabled': True,
                    'auto_approve_max_amount': max_amount
                }).execute()
            
            return {
                'type': 'auto_payment_enabled',
                'message': (
                    f"✅ Auto-payment enabled!\n\n"
                    f"Payments up to R{max_amount} will be automatically approved.\n"
                    f"You'll still receive notifications for each payment.\n\n"
                    f"To disable, type: 'disable auto payment'"
                )
            }
            
        except Exception as e:
            logger.error(f"Error enabling auto-payment: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to enable auto-payment.'
            }

    def _get_payment_help(self, user_type: str) -> Dict:
        """
        Get payment help information
        """
        if user_type == 'trainer':
            return {
                'type': 'help',
                'message': (
                    "💳 *Payment Commands for Trainers*\n\n"
                    "*Setup & Requests:*\n"
                    "• Setup payment for [client name]\n"
                    "• Request payment from [client] R[amount]\n"
                    "• Check payments\n"
                    "• Payment history\n\n"
                    "*Settings:*\n"
                    "• Set payment reminder day [1-28]\n"
                    "• Upgrade plan (for unlimited clients)\n\n"
                    "*Example:*\n"
                    "_Setup payment for Sarah_\n"
                    "_Request payment from Sarah R500_"
                )
            }
        else:
            return {
                'type': 'help',
                'message': (
                    "💳 *Payment Commands for Clients*\n\n"
                    "*Commands:*\n"
                    "• Check payments (see pending requests)\n"
                    "• Payment history\n"
                    "• Enable auto payment R[max amount]\n"
                    "• Disable auto payment\n\n"
                    "*Approving Payments:*\n"
                    "Reply *YES* to approve payment\n"
                    "Reply *NO* to decline payment\n\n"
                    "*Example:*\n"
                    "_Enable auto payment R1000_"
                )
            }

    def _calculate_next_date(self, day: int) -> str:
        """
        Calculate next occurrence of a day in the month
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        today = date.today()
        
        # Try this month first
        try:
            next_date = today.replace(day=day)
            if next_date <= today:
                # If already passed, get next month
                next_date = (today + relativedelta(months=1)).replace(day=day)
        except ValueError:
            # Day doesn't exist in this month (e.g., 31st in February)
            next_date = (today + relativedelta(months=1)).replace(day=day)
        
        return next_date.isoformat()

    def handle_monthly_reminder_response(self, trainer_id: str, response: str) -> Dict:
        """
        Handle trainer's response to monthly payment reminder
        """
        try:
            response_lower = response.lower().strip()
            
            if response_lower == 'yes':
                # Get all active clients with payment methods
                supabase = self.payment_manager.supabase
                
                clients = supabase.table('clients').select(
                    '*, client_payment_tokens(*)'
                ).eq('trainer_id', trainer_id).eq('status', 'active').execute()
                
                # Get trainer details for pricing
                trainer = supabase.table('trainers').select('*').eq('id', trainer_id).single().execute()
                
                requests_created = 0
                failed_clients = []
                
                for client in clients.data:
                    if client.get('client_payment_tokens'):
                        # Client has payment method
                        amount = trainer.data.get('pricing_per_session', 500)
                        description = f"Monthly training sessions - {datetime.now().strftime('%B %Y')}"
                        
                        result = self.payment_manager.create_payment_request(
                            trainer_id,
                            client['id'],
                            amount,
                            description
                        )
                        
                        if result['success']:
                            requests_created += 1
                        else:
                            failed_clients.append(client['name'])
                    else:
                        failed_clients.append(f"{client['name']} (no payment method)")
                
                message = f"✅ Created {requests_created} payment requests!\n"
                if failed_clients:
                    message += f"\n⚠️ Failed for:\n" + "\n".join([f"• {c}" for c in failed_clients])
                
                return {
                    'type': 'reminder_processed',
                    'message': message
                }
                
            elif response_lower == 'skip':
                return {
                    'type': 'reminder_skipped',
                    'message': "✅ Payment reminders skipped for this month."
                }
            else:
                return {
                    'type': 'invalid_response',
                    'message': "Please reply YES to send payment requests or SKIP to skip this month."
                }
                
        except Exception as e:
            logger.error(f"Error handling reminder response: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to process reminder response.'
            }
