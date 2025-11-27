"""Payment command processing for WhatsApp messages"""
import re
from datetime import datetime
from typing import Dict, Optional
from utils.logger import log_error

class PaymentCommandHandler:
    """Handles payment-related WhatsApp commands"""
    
    def __init__(self, payment_manager):
        """Initialize with payment manager"""
        self.payment_manager = payment_manager
        
        # Payment command patterns
        self.patterns = {
            'setup_payment': r'(?i)(setup payment|save card|add payment method)\s+(?:for\s+)?(.+)',
            'request_payment': r'(?i)(request payment|charge|bill)\s+(?:from\s+)?(.+)\s+(?:R?(\d+(?:\.\d{2})?))',
            'check_payments': r'(?i)(check payments?|payment status|pending payments?)',
            'payment_history': r'(?i)(payment history|past payments?|transaction history)',
            'upgrade_plan': r'(?i)(upgrade|professional plan|upgrade plan)',
            'set_reminder': r'(?i)(set payment reminder|payment reminder)\s+(?:day\s+)?(\d+)',
            'enable_auto': r'(?i)(enable auto payment|auto approve)\s+(?:R?(\d+))',
            'payment_help': r'(?i)(payment help|how to pay|payment info)',
            'set_client_price': r'(?i)(?:set|change|update)\s+(.+?)(?:\'s)?\s+(?:rate|price|cost)\s+(?:to\s+)?R?(\d+(?:\.\d{2})?)',
            'view_client_price': r'(?i)(?:what|show|check)\s+(?:is\s+)?(.+?)(?:\'s)?\s+(?:rate|price|cost)'
        }
    
    def process_payment_message(self, phone: str, message: str, user_type: str, user_id: str) -> Optional[Dict]:
        """Process payment-related messages"""
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
            log_error(f"Error processing payment message: {str(e)}")
            return None
    
    def _handle_payment_command(self, command: str, match, user_type: str, user_id: str, phone: str) -> Dict:
        """Handle specific payment commands"""
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

            elif command == 'set_client_price':
                if user_type != 'trainer':
                    return {
                        'type': 'error',
                        'message': 'Only trainers can set client prices.'
                    }
                
                client_name = match.group(1).strip()
                new_price = float(match.group(2))
                return self._set_client_price(user_id, client_name, new_price)
            
            elif command == 'view_client_price':
                if user_type != 'trainer':
                    return {
                        'type': 'error',
                        'message': 'Only trainers can view client prices.'
                    }
                
                client_name = match.group(1).strip()
                return self._view_client_price(user_id, client_name)
            
            return {
                'type': 'error',
                'message': 'Unknown payment command.'
            }
            
        except Exception as e:
            log_error(f"Error handling payment command: {str(e)}")
            return {
                'type': 'error',
                'message': f'Error processing payment command: {str(e)}'
            }
    
    def _setup_client_payment(self, trainer_id: str, client_name: str) -> Dict:
        """Set up payment method for a client"""
        try:
            supabase = self.payment_manager.supabase
            client = supabase.table('clients').select('*').eq(
                'trainer_id', trainer_id
            ).ilike('name', f'%{client_name}%').limit(1).execute()
            
            if not client.data:
                return {
                    'type': 'error',
                    'message': f'Client "{client_name}" not found. Please check the name and try again.'
                }
            
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
            log_error(f"Error setting up client payment: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to set up client payment.'
            }
    
    def _request_payment(self, trainer_id: str, client_name: str, amount: float) -> Dict:
        """Request payment from a client"""
        try:
            supabase = self.payment_manager.supabase
            client = supabase.table('clients').select('*, custom_price_per_session').eq(
                'trainer_id', trainer_id
            ).ilike('name', f'%{client_name}%').limit(1).execute()
            
            if not client.data:
                return {
                    'type': 'error',
                    'message': f'Client "{client_name}" not found.'
                }
            
            client_data = client.data[0]
            if client_data.get('custom_price_per_session'):
                amount = float(client_data['custom_price_per_session'])
            
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
            log_error(f"Error requesting payment: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to request payment.'
            }
    
    def _check_payment_status(self, user_type: str, user_id: str) -> Dict:
        """Check pending payments"""
        try:
            supabase = self.payment_manager.supabase
            
            if user_type == 'trainer':
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
            log_error(f"Error checking payment status: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to check payment status.'
            }
    
    def _get_payment_history(self, user_type: str, user_id: str) -> Dict:
        """Get payment history"""
        try:
            supabase = self.payment_manager.supabase
            
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
            log_error(f"Error getting payment history: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to get payment history.'
            }
    
    def _upgrade_plan(self, trainer_id: str) -> Dict:
        """Upgrade trainer to Professional plan"""
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
            log_error(f"Error upgrading plan: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to process upgrade.'
            }
    
    def _set_payment_reminder(self, trainer_id: str, day: int) -> Dict:
        """Set monthly payment reminder day"""
        try:
            if day < 1 or day > 28:
                return {
                    'type': 'error',
                    'message': 'Please choose a day between 1 and 28.'
                }
            
            supabase = self.payment_manager.supabase
            
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
            log_error(f"Error setting payment reminder: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to set payment reminder.'
            }
    
    def _enable_auto_payment(self, client_id: str, max_amount: float) -> Dict:
        """Enable auto-approval for payments"""
        try:
            supabase = self.payment_manager.supabase
            
            client = supabase.table('clients').select('trainer_id').eq('id', client_id).single().execute()
            
            if not client.data:
                return {
                    'type': 'error',
                    'message': 'Client record not found.'
                }
            
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
            log_error(f"Error enabling auto-payment: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to enable auto-payment.'
            }
    
    def _get_payment_help(self, user_type: str) -> Dict:
        """Get payment help information"""
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
        """Calculate next occurrence of a day in the month"""
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        today = date.today()
        
        try:
            next_date = today.replace(day=day)
            if next_date <= today:
                next_date = (today + relativedelta(months=1)).replace(day=day)
        except ValueError:
            next_date = (today + relativedelta(months=1)).replace(day=day)
        
        return next_date.isoformat()
    
    def _set_client_price(self, trainer_id: str, client_name: str, new_price: float) -> Dict:
        """Set custom price for a specific client"""
        try:
            supabase = self.payment_manager.supabase
            
            client = supabase.table('clients').select('*').eq(
                'trainer_id', trainer_id
            ).ilike('name', f'%{client_name}%').limit(1).execute()
            
            if not client.data:
                return {
                    'type': 'error',
                    'message': f'Client "{client_name}" not found.'
                }
            
            update_result = supabase.table('clients').update({
                'custom_price_per_session': new_price
            }).eq('id', client.data[0]['id']).execute()
            
            if update_result.data:
                return {
                    'type': 'price_updated',
                    'message': (
                        f"✅ Updated pricing for {client.data[0]['name']}!\n\n"
                        f"New rate: R{new_price} per session\n"
                        f"This will apply to all future bookings and payments."
                    )
                }
            else:
                return {
                    'type': 'error',
                    'message': 'Failed to update price. Please try again.'
                }
                
        except Exception as e:
            log_error(f"Error setting client price: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to update client price.'
            }
    
    def _view_client_price(self, trainer_id: str, client_name: str) -> Dict:
        """View custom price for a specific client"""
        try:
            supabase = self.payment_manager.supabase
            
            client = supabase.table('clients').select('*, custom_price_per_session').eq(
                'trainer_id', trainer_id
            ).ilike('name', f'%{client_name}%').limit(1).execute()
            
            if not client.data:
                return {
                    'type': 'error',
                    'message': f'Client "{client_name}" not found.'
                }
            
            client_data = client.data[0]
            
            trainer = supabase.table('trainers').select('pricing_per_session').eq(
                'id', trainer_id
            ).single().execute()
            
            default_price = trainer.data.get('pricing_per_session', 300) if trainer.data else 300
            
            if client_data.get('custom_price_per_session'):
                custom_price = client_data['custom_price_per_session']
                return {
                    'type': 'price_info',
                    'message': (
                        f"💰 Pricing for {client_data['name']}:\n\n"
                        f"Custom rate: R{custom_price} per session\n"
                        f"(Your default rate: R{default_price})"
                    )
                }
            else:
                return {
                    'type': 'price_info',
                    'message': (
                        f"💰 Pricing for {client_data['name']}:\n\n"
                        f"Using your default rate: R{default_price} per session\n"
                        f"💡 Tip: You can set a custom rate with:\n"
                        f"'Set {client_data['name']}'s rate to R[amount]'"
                    )
                }
                
        except Exception as e:
            log_error(f"Error viewing client price: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to get client price.'
            }