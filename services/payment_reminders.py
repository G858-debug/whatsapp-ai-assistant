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