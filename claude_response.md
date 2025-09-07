<!-- Model: Opus 4.1 -->
<!-- Cost: $1.5301 -->
<!-- Max Tokens: 16000 -->
## ANALYSIS

Continuing from Step 3, I need to split the remaining large files:
- `payment_integration.py` (746 lines) - needs splitting into smaller modules
- `services/dashboard_sync.py` (640 lines) - needs splitting into smaller modules

These files exceed the 600-line limit and should be refactored into focused, manageable modules.

## CHANGES NEEDED

### SPLIT FILE: payment_integration.py

Split into two logical modules:

### NEW FILE: services/payment_commands.py
```python
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
```

### NEW FILE: services/payment_reminders.py
```python
"""Payment reminder and monthly billing service"""
from datetime import datetime, timedelta
from typing import Dict, List
from utils.logger import log_error, log_info

class PaymentReminderService:
    """Handles payment reminders and monthly billing"""
    
    def __init__(self, payment_manager):
        """Initialize with payment manager"""
        self.payment_manager = payment_manager
        self.supabase = payment_manager.supabase
    
    def handle_monthly_reminder_response(self, trainer_id: str, response: str) -> Dict:
        """Handle trainer's response to monthly payment reminder"""
        try:
            response_lower = response.lower().strip()
            
            if response_lower == 'yes':
                clients = self.supabase.table('clients').select(
                    '*, client_payment_tokens(*)'
                ).eq('trainer_id', trainer_id).eq('status', 'active').execute()
                
                trainer = self.supabase.table('trainers').select('*').eq('id', trainer_id).single().execute()
                
                requests_created = 0
                failed_clients = []
                
                for client in clients.data:
                    if client.get('client_payment_tokens'):
                        if client.get('custom_price_per_session'):
                            amount = float(client['custom_price_per_session'])
                        else:
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
            log_error(f"Error handling reminder response: {str(e)}")
            return {
                'type': 'error',
                'message': 'Failed to process reminder response.'
            }
    
    def send_payment_reminders(self) -> Dict:
        """Send scheduled payment reminders"""
        try:
            today = datetime.now().date()
            
            reminders = self.supabase.table('payment_reminders').select(
                '*, trainers(*)'
            ).eq('reminder_enabled', True).eq(
                'reminder_day', today.day
            ).execute()
            
            sent_count = 0
            failed_count = 0
            
            for reminder in (reminders.data or []):
                try:
                    trainer = reminder['trainers']
                    message = self._create_reminder_message(trainer['id'])
                    
                    # Send via WhatsApp (would need WhatsApp service)
                    # whatsapp_service.send_message(trainer['whatsapp'], message)
                    
                    sent_count += 1
                    
                    # Update next scheduled date
                    next_month = today.replace(day=1) + timedelta(days=32)
                    next_date = next_month.replace(day=reminder['reminder_day'])
                    
                    self.supabase.table('payment_reminders').update({
                        'last_sent': today.isoformat(),
                        'next_scheduled_date': next_date.isoformat()
                    }).eq('id', reminder['id']).execute()
                    
                except Exception as e:
                    log_error(f"Failed to send reminder: {str(e)}")
                    failed_count += 1
            
            return {
                'success': True,
                'sent': sent_count,
                'failed': failed_count
            }
            
        except Exception as e:
            log_error(f"Error sending payment reminders: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_reminder_message(self, trainer_id: str) -> str:
        """Create payment reminder message"""
        try:
            # Get active clients with payment methods
            clients = self.supabase.table('clients').select(
                'name, custom_price_per_session, client_payment_tokens(id)'
            ).eq('trainer_id', trainer_id).eq('status', 'active').execute()
            
            clients_with_payment = []
            clients_without_payment = []
            
            for client in (clients.data or []):
                if client.get('client_payment_tokens'):
                    clients_with_payment.append(client['name'])
                else:
                    clients_without_payment.append(client['name'])
            
            message = "💰 *Monthly Payment Reminder*\n\n"
            
            if clients_with_payment:
                message += f"Ready to charge ({len(clients_with_payment)} clients):\n"
                for name in clients_with_payment[:5]:
                    message += f"• {name}\n"
                if len(clients_with_payment) > 5:
                    message += f"...and {len(clients_with_payment) - 5} more\n"
                message += "\nReply YES to send payment requests\n"
            
            if clients_without_payment:
                message += f"\n⚠️ No payment method ({len(clients_without_payment)} clients):\n"
                for name in clients_without_payment[:3]:
                    message += f"• {name}\n"
                if len(clients_without_payment) > 3:
                    message += f"...and {len(clients_without_payment) - 3} more\n"
            
            message += "\nReply SKIP to skip this month"
            
            return message
            
        except Exception as e:
            log_error(f"Error creating reminder message: {str(e)}")
            return "💰 Monthly payment reminder - Reply YES to send payment requests or SKIP to skip"
```

### EDIT: payment_integration.py

**Change 1:** Replace entire file with simplified integration
Location: Lines 1-746
```python
# REMOVE (lines 1-746):
[entire current content]

# ADD:
"""Payment Integration for WhatsApp Bot"""
from typing import Dict, Optional
from services.payment_commands import PaymentCommandHandler
from services.payment_reminders import PaymentReminderService
from payment_manager import PaymentManager
import logging

logger = logging.getLogger(__name__)

class PaymentIntegration:
    """Main payment integration class"""
    
    def __init__(self):
        """Initialize payment integration"""
        self.payment_manager = PaymentManager()
        self.command_handler = PaymentCommandHandler(self.payment_manager)
        self.reminder_service = PaymentReminderService(self.payment_manager)
    
    def process_payment_message(self, phone: str, message: str, 
                               user_type: str, user_id: str) -> Optional[Dict]:
        """Process payment-related messages"""
        return self.command_handler.process_payment_message(
            phone, message, user_type, user_id
        )
    
    def handle_monthly_reminder_response(self, trainer_id: str, response: str) -> Dict:
        """Handle trainer's response to monthly payment reminder"""
        return self.reminder_service.handle_monthly_reminder_response(
            trainer_id, response
        )
    
    def send_scheduled_reminders(self) -> Dict:
        """Send scheduled payment reminders"""
        return self.reminder_service.send_payment_reminders()
```

### NEW FILE: services/dashboard_sync_core.py
```python
"""Core dashboard synchronization functionality"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
import secrets
from utils.logger import log_error, log_info, log_warning

class DashboardSyncCore:
    """Core synchronization between dashboard and WhatsApp"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.dashboard_base_url = config.DASHBOARD_URL if hasattr(config, 'DASHBOARD_URL') else 'https://refiloe.ai/dashboard'
        
        # Cache for user preferences
        self.preference_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def generate_deep_link(self, page: str, user_id: str, user_type: str, 
                          token: str = None, params: Dict = None) -> str:
        """Generate specific dashboard URLs for WhatsApp messages"""
        if not token:
            token = self._generate_dashboard_token(user_id, user_type)
        
        if page == 'challenges':
            url = f"{self.dashboard_base_url}/challenges"
        elif page == 'challenge':
            challenge_id = params.get('challenge_id') if params else None
            url = f"{self.dashboard_base_url}/challenges/{challenge_id}" if challenge_id else f"{self.dashboard_base_url}/challenges"
        elif page == 'leaderboard':
            highlight = params.get('highlight') if params else user_id
            url = f"{self.dashboard_base_url}/leaderboard?highlight={highlight}"
        elif page == 'pre-book':
            challenge_id = params.get('challenge_id') if params else None
            url = f"{self.dashboard_base_url}/pre-book/{challenge_id}" if challenge_id else f"{self.dashboard_base_url}/challenges"
        elif page == 'stats':
            url = f"{self.dashboard_base_url}/stats"
        else:
            url = self.dashboard_base_url
        
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}token={token}"
        
        return url
    
    def _generate_dashboard_token(self, user_id: str, user_type: str) -> str:
        """Generate secure token for dashboard access"""
        try:
            existing = self.db.table('dashboard_tokens').select('*').eq(
                f'{user_type}_id', user_id
            ).eq('is_valid', True).execute()
            
            if existing.data:
                created_at = datetime.fromisoformat(existing.data[0]['created_at'])
                if (datetime.now(pytz.UTC) - created_at).total_seconds() < 86400:
                    return existing.data[0]['token']
            
            token = secrets.token_urlsafe(32)
            
            if user_type == 'trainer':
                token_data = {'trainer_id': user_id}
            else:
                token_data = {'client_id': user_id}
            
            token_data.update({
                'token': token,
                'is_valid': True,
                'created_at': datetime.now(pytz.UTC).isoformat()
            })
            
            self.db.table('dashboard_tokens').insert(token_data).execute()
            
            return token
            
        except Exception as e:
            log_error(f"Error generating dashboard token: {str(e)}")
            return secrets.token_urlsafe(32)
    
    def get_cached_preferences(self, user_id: str, user_type: str) -> Optional[Dict]:
        """Get cached user preferences to reduce database calls"""
        cache_key = f"{user_type}:{user_id}"
        
        if cache_key in self.preference_cache:
            cached = self.preference_cache[cache_key]
            if (datetime.now() - cached['cached_at']).total_seconds() < self.cache_ttl:
                return cached['data']
        
        try:
            profile = self.db.table('gamification_profiles').select('*').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            if profile.data:
                self.preference_cache[cache_key] = {
                    'data': profile.data,
                    'cached_at': datetime.now()
                }
                return profile.data
                
        except Exception as e:
            log_error(f"Error loading preferences: {str(e)}")
        
        return None
    
    def get_user_phone(self, user_id: str, user_type: str) -> Optional[str]:
        """Get user's WhatsApp phone number"""
        try:
            if user_type == 'trainer':
                result = self.db.table('trainers').select('whatsapp').eq(
                    'id', user_id
                ).single().execute()
            else:
                result = self.db.table('clients').select('whatsapp').eq(
                    'id', user_id
                ).single().execute()
            
            return result.data.get('whatsapp') if result.data else None
            
        except Exception as e:
            log_error(f"Error getting user phone: {str(e)}")
            return None
    
    def trigger_dashboard_update(self, user_id: str, user_type: str, action: str):
        """Trigger dashboard update"""
        try:
            log_info(f"Dashboard update triggered for {user_type} {user_id}: {action}")
            
            self.db.table('dashboard_updates').insert({
                'user_id': user_id,
                'user_type': user_type,
                'action': action,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
        except Exception as e:
            log_error(f"Error triggering dashboard update: {str(e)}")
    
    def get_next_digest_time(self, user_id: str, user_type: str) -> datetime:
        """Get next digest time for user"""
        prefs = self.get_cached_preferences(user_id, user_type)
        
        if prefs:
            digest_time = prefs.get('digest_time', '07:00')
        else:
            digest_time = '07:00'
        
        hour, minute = map(int, digest_time.split(':'))
        
        now = datetime.now(self.sa_tz)
        next_digest = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_digest <= now:
            next_digest += timedelta(days=1)
        
        return next_digest
```

### EDIT: services/dashboard_sync.py

**Change 1:** Replace entire file with handler logic only
Location: Lines 1-640
```python
# REMOVE (lines 1-640):
[entire current content]

# ADD:
"""Dashboard and WhatsApp synchronization service"""
from typing import Dict, Optional
from datetime import datetime
from collections import defaultdict
from services.dashboard_sync_core import DashboardSyncCore
from utils.logger import log_error, log_info

class DashboardSyncService:
    """Handles synchronization between dashboard actions and WhatsApp notifications"""
    
    def __init__(self, supabase_client, config, whatsapp_service):
        self.db = supabase_client
        self.config = config
        self.whatsapp = whatsapp_service
        self.core = DashboardSyncCore(supabase_client, config)
        
        # Pending notifications queue for digest
        self.digest_queue = defaultdict(list)
    
    def handle_dashboard_action(self, user_id: str, user_type: str, 
                               action: str, data: Dict) -> Dict:
        """Handle actions from dashboard and determine WhatsApp notification strategy"""
        try:
            if action == 'pre_book_challenge':
                return self._handle_pre_book(user_id, user_type, data)
            elif action == 'join_challenge':
                return self._handle_join_challenge(user_id, user_type, data)
            elif action == 'log_progress':
                return self._handle_progress_log(user_id, user_type, data)
            elif action == 'change_preferences':
                return self._handle_preference_change(user_id, user_type, data)
            elif action == 'leave_challenge':
                return self._handle_leave_challenge(user_id, user_type, data)
            else:
                log_warning(f"Unknown dashboard action: {action}")
                return {'success': False, 'error': 'Unknown action'}
                
        except Exception as e:
            log_error(f"Error handling dashboard action: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_pre_book(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle challenge pre-booking - add to digest only"""
        try:
            challenge_name = data.get('challenge_name', 'challenge')
            
            self.digest_queue[user_id].append({
                'type': 'pre_book',
                'message': f"✓ Pre-booked for {challenge_name}",
                'timestamp': datetime.now().isoformat()
            })
            
            self.db.table('notification_queue').insert({
                'user_id': user_id,
                'user_type': user_type,
                'notification_type': 'pre_book',
                'content': f"✓ Pre-booked for {challenge_name}",
                'scheduled_for': self.core.get_next_digest_time(user_id, user_type).isoformat(),
                'created_at': datetime.now().isoformat()
            }).execute()
            
            return {
                'success': True,
                'whatsapp_sent': False,
                'queued_for_digest': True
            }
            
        except Exception as e:
            log_error(f"Error handling pre-book: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_join_challenge(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle joining challenge - no WhatsApp notification"""
        return {
            'success': True,
            'whatsapp_sent': False,
            'message': 'Successfully joined challenge!'
        }
    
    def _handle_progress_log(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle progress logging - update dashboard only"""
        try:
            progress_type = data.get('type', 'progress')
            value = data.get('value', '')
            
            self.digest_queue[user_id].append({
                'type': 'progress',
                'message': f"Logged: {progress_type} - {value}",
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'whatsapp_sent': False,
                'included_in_summary': True
            }
            
        except Exception as e:
            log_error(f"Error handling progress log: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_preference_change(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle preference change - send ONE confirmation"""
        try:
            cache_key = f"{user_type}:{user_id}"
            if cache_key in self.core.preference_cache:
                del self.core.preference_cache[cache_key]
            
            phone = self.core.get_user_phone(user_id, user_type)
            
            if phone:
                message = "✅ Your notification preferences have been updated."
                self.whatsapp.send_message(phone, message)
                
                return {
                    'success': True,
                    'whatsapp_sent': True,
                    'message': 'Preferences updated and confirmed via WhatsApp'
                }
            
            return {
                'success': True,
                'whatsapp_sent': False,
                'message': 'Preferences updated'
            }
            
        except Exception as e:
            log_error(f"Error handling preference change: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_leave_challenge(self, user_id: str, user_type: str, data: Dict) -> Dict:
        """Handle leaving challenge - no immediate notification"""
        return {
            'success': True,
            'whatsapp_sent': False,
            'message': 'Left challenge successfully'
        }
    
    def handle_quick_command(self, command: str, user_id: str, 
                           user_type: str, phone: str) -> Optional[Dict]:
        """Handle WhatsApp quick commands that redirect to dashboard"""
        command_lower = command.lower().strip()
        
        token = self.core._generate_dashboard_token(user_id, user_type)
        
        if command_lower in ['challenges', 'challenge']:
            link = self.core.generate_deep_link('challenges', user_id, user_type, token)
            return {
                'success': True,
                'message': f"🎮 View all challenges and your progress:\n{link}\n\nTap to open in your browser.",
                'type': 'redirect'
            }
        
        elif command_lower in ['leaderboard', 'rankings', 'rank']:
            link = self.core.generate_deep_link('leaderboard', user_id, user_type, token, 
                                              {'highlight': user_id})
            return {
                'success': True,
                'message': f"🏆 See the full leaderboard:\n{link}\n\nYour position is highlighted!",
                'type': 'redirect'
            }
        
        elif command_lower in ['stats', 'statistics', 'my stats']:
            link = self.core.generate_deep_link('stats', user_id, user_type, token)
            return {
                'success': True,
                'message': f"📊 View your detailed statistics:\n{link}\n\nIncludes points, badges, and progress!",
                'type': 'redirect'
            }
        
        elif command_lower in ['dashboard', 'website', 'web']:
            link = self.core.generate_deep_link('home', user_id, user_type, token)
            return {
                'success': True,
                'message': f"🖥️ Open your dashboard:\n{link}",
                'type': 'redirect'
            }
        
        return None
    
    def send_daily_digest(self, user_id: str, user_type: str) -> Dict:
        """Send consolidated daily digest"""
        try:
            phone = self.core.get_user_phone(user_id, user_type)
            if not phone:
                return {'success': False, 'error': 'No phone number found'}
            
            queued = self.db.table('notification_queue').select('*').eq(
                'user_id', user_id
            ).eq('user_type', user_type).eq(
                'sent', False
            ).execute()
            
            if not queued.data:
                return {'success': True, 'message': 'No notifications to send'}
            
            pre_bookings = []
            progress_logs = []
            other = []
            
            for notif in queued.data:
                if notif['notification_type'] == 'pre_book':
                    pre_bookings.append(notif['content'])
                elif notif['notification_type'] == 'progress':
                    progress_logs.append(notif['content'])
                else:
                    other.append(notif['content'])
            
            message_parts = ["📋 *Your Daily Summary*\n"]
            
            if pre_bookings:
                message_parts.append("*Pre-booked Challenges:*")
                for booking in pre_bookings[:3]:
                    message_parts.append(booking)
                if len(pre_bookings) > 3:
                    message_parts.append(f"...and {len(pre_bookings) - 3} more")
            
            if progress_logs:
                message_parts.append("\n*Progress Today:*")
                message_parts.append(f"✓ {len(progress_logs)} activities logged")
            
            if other:
                message_parts.append("\n*Other Updates:*")
                for update in other[:2]:
                    message_parts.append(update)
            
            token = self.core._generate_dashboard_token(user_id, user_type)
            link = self.core.generate_deep_link('home', user_id, user_type, token)
            message_parts.append(f"\n📱 View full details:\n{link}")
            
            full_message = "\n".join(message_parts)
            self.whatsapp.send_message(phone, full_message)
            
            notification_ids = [n['id'] for n in queued.data]
            self.db.table('notification_queue').update({
                'sent': True,
                'sent_at': datetime.now().isoformat()
            }).in_('id', notification_ids).execute()
            
            return {
                'success': True,
                'notifications_sent': len(queued.data)
            }
            
        except Exception as e:
            log_error(f"Error sending daily digest: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # Public methods that delegate to core
    def generate_deep_link(self, page: str, user_id: str, user_type: str, 
                          token: str = None, params: Dict = None) -> str:
        """Generate deep link - delegates to core"""
        return self.core.generate_deep_link(page, user_id, user_type, token, params)
    
    def get_cached_preferences(self, user_id: str, user_type: str) -> Optional[Dict]:
        """Get cached preferences - delegates to core"""
        return self.core.get_cached_preferences(user_id, user_type)
```

## SUMMARY

✅ **Completed splitting all large files:**

1. **Split `payment_integration.py` (746 lines) into:**
   - `services/payment_commands.py` - Command handling logic
   - `services/payment_reminders.py` - Reminder and billing logic
   - `payment_integration.py` - Main integration (reduced to ~30 lines)

2. **Split `services/dashboard_sync.py` (640 lines) into:**
   - `services/dashboard_sync_core.py` - Core functionality
   - `services/dashboard_sync.py` - Handler logic (reduced to ~280 lines)

All files are now under 600 lines, properly modularized and focused on specific responsibilities. The codebase is now more maintainable and follows the project's file size requirements.