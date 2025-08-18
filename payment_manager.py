# payment_manager.py
"""
Payment Manager Module for Refiloe
Handles all payment operations including PayFast integration and WhatsApp notifications
"""

import os
import hashlib
import urllib.parse
import requests
import json
import uuid
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Tuple
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentManager:
    """Manages all payment operations for Refiloe"""
    
    def __init__(self):
        """Initialize Payment Manager with Supabase and PayFast credentials"""
        # Supabase setup
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # PayFast configuration (Test credentials for development)
        self.payfast_config = {
            'merchant_id': os.environ.get('PAYFAST_MERCHANT_ID', '10000100'),
            'merchant_key': os.environ.get('PAYFAST_MERCHANT_KEY', '46f0cd694581a'),
            'passphrase': os.environ.get('PAYFAST_PASSPHRASE', ''),
            'test_mode': os.environ.get('PAYFAST_TEST_MODE', 'true').lower() == 'true'
        }
        
        # Set PayFast URLs based on mode
        if self.payfast_config['test_mode']:
            self.payfast_url = 'https://sandbox.payfast.co.za/eng/process'
            self.payfast_api_url = 'https://api.sandbox.payfast.co.za'
        else:
            self.payfast_url = 'https://www.payfast.co.za/eng/process'
            self.payfast_api_url = 'https://api.payfast.co.za'
            
        # WhatsApp configuration
        self.whatsapp_token = os.environ.get("ACCESS_TOKEN")
        self.phone_number_id = os.environ.get("PHONE_NUMBER_ID")
        self.whatsapp_api_url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"

    # ==========================================
    # TRAINER SUBSCRIPTION MANAGEMENT
    # ==========================================
    
    def upgrade_to_professional(self, trainer_id: str) -> Dict:
        """
        Upgrade trainer from Starter to Professional plan
        Returns PayFast payment URL for subscription
        """
        try:
            # Get trainer details
            trainer = self.supabase.table('trainers').select('*').eq('id', trainer_id).single().execute()
            
            # Get Professional plan details
            plan = self.supabase.table('subscription_plans').select('*').eq('plan_code', 'professional').single().execute()
            
            # Create PayFast subscription URL
            payment_data = {
                'merchant_id': self.payfast_config['merchant_id'],
                'merchant_key': self.payfast_config['merchant_key'],
                'return_url': f"{os.environ.get('BASE_URL', 'https://web-production-26de5.up.railway.app')}/payment/success",
                'cancel_url': f"{os.environ.get('BASE_URL', 'https://web-production-26de5.up.railway.app')}/payment/cancel",
                'notify_url': f"{os.environ.get('BASE_URL', 'https://web-production-26de5.up.railway.app')}/webhooks/payfast",
                'name_first': trainer.data['name'].split()[0] if trainer.data['name'] else '',
                'name_last': trainer.data['name'].split()[-1] if len(trainer.data['name'].split()) > 1 else '',
                'email_address': trainer.data['email'],
                'cell_number': trainer.data['whatsapp'],
                'm_payment_id': f"SUB_{trainer_id}",
                'amount': str(plan.data['price_monthly']),
                'item_name': f"Refiloe Professional Plan - {trainer.data['name']}",
                'subscription_type': '1',  # Recurring subscription
                'recurring_amount': str(plan.data['price_monthly']),
                'frequency': '3',  # Monthly
                'cycles': '0'  # Indefinite
            }
            
            # Generate signature
            signature = self._generate_payfast_signature(payment_data)
            payment_data['signature'] = signature
            
            # Create payment URL
            payment_url = f"{self.payfast_url}?{urllib.parse.urlencode(payment_data)}"
            
            return {
                'success': True,
                'payment_url': payment_url,
                'message': 'Upgrade link generated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error upgrading trainer: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==========================================
    # CLIENT PAYMENT TOKEN MANAGEMENT
    # ==========================================
    
    def create_token_setup_request(self, trainer_id: str, client_id: str) -> Dict:
        """
        Create a token setup request for a client to save their card
        """
        try:
            # Get client and trainer details
            client = self.supabase.table('clients').select('*').eq('id', client_id).single().execute()
            trainer = self.supabase.table('trainers').select('*').eq('id', trainer_id).single().execute()
            
            # Check if token already exists
            existing_token = self.supabase.table('client_payment_tokens').select('*').eq(
                'client_id', client_id
            ).eq('trainer_id', trainer_id).eq('payfast_token_status', 'active').execute()
            
            if existing_token.data:
                return {
                    'success': False,
                    'message': 'Payment method already exists for this client'
                }
            
            # Create token setup request
            setup_code = str(uuid.uuid4())[:8].upper()
            
            # Create PayFast tokenization URL
            payment_data = {
                'merchant_id': self.payfast_config['merchant_id'],
                'merchant_key': self.payfast_config['merchant_key'],
                'return_url': f"{os.environ.get('BASE_URL')}/payment/token-success",
                'cancel_url': f"{os.environ.get('BASE_URL')}/payment/token-cancel",
                'notify_url': f"{os.environ.get('BASE_URL')}/webhooks/payfast-token",
                'name_first': client.data['name'].split()[0],
                'name_last': client.data['name'].split()[-1] if len(client.data['name'].split()) > 1 else '',
                'email_address': client.data.get('email', f"{client.data['whatsapp']}@refiloe.co.za"),
                'cell_number': client.data['whatsapp'],
                'm_payment_id': f"TOKEN_{client_id}_{trainer_id}",
                'amount': '5.00',  # Small verification amount
                'item_name': f"Save payment method for {trainer.data['business_name'] or trainer.data['name']}",
                'custom_str1': setup_code,
                'subscription_type': '2'  # Tokenization
            }
            
            # Generate signature
            signature = self._generate_payfast_signature(payment_data)
            payment_data['signature'] = signature
            
            # Create payment URL
            setup_url = f"{self.payfast_url}?{urllib.parse.urlencode(payment_data)}"
            
            # Store setup request in database
            setup_request = self.supabase.table('token_setup_requests').insert({
                'client_id': client_id,
                'trainer_id': trainer_id,
                'status': 'pending',
                'setup_url': setup_url,
                'setup_code': setup_code,
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
            }).execute()
            
            # Send WhatsApp message to client
            message = (
                f"💳 *Payment Setup for {trainer.data['business_name'] or trainer.data['name']}*\n\n"
                f"Hi {client.data['name']}! 👋\n\n"
                f"To enable quick and easy payments, please save your payment method:\n\n"
                f"🔗 {setup_url}\n\n"
                f"✅ This is a one-time setup\n"
                f"✅ Your card details are secured by PayFast\n"
                f"✅ You'll approve each payment via WhatsApp\n"
                f"✅ R5 verification will be refunded\n\n"
                f"Setup code: *{setup_code}*\n"
                f"Link expires in 7 days."
            )
            
            self._send_whatsapp_message(client.data['whatsapp'], message)
            
            return {
                'success': True,
                'setup_url': setup_url,
                'setup_code': setup_code,
                'message': 'Token setup request created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating token setup: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==========================================
    # PAYMENT REQUEST MANAGEMENT
    # ==========================================
    
    def create_payment_request(self, trainer_id: str, client_id: str, amount: float, description: str) -> Dict:
        """
        Create a payment request from trainer to client
        """
        try:
            # Check if client has saved payment method
            token = self.supabase.table('client_payment_tokens').select('*').eq(
                'client_id', client_id
            ).eq('trainer_id', trainer_id).eq('payfast_token_status', 'active').single().execute()
            
            if not token.data:
                return {
                    'success': False,
                    'message': 'Client has no saved payment method. Please set up payment first.'
                }
            
            # Check client's auto-approval settings
            preferences = self.supabase.table('client_payment_preferences').select('*').eq(
                'client_id', client_id
            ).eq('trainer_id', trainer_id).single().execute()
            
            auto_approved = False
            if preferences.data:
                if preferences.data['auto_approve_enabled'] and amount <= preferences.data['auto_approve_max_amount']:
                    auto_approved = True
            
            # Create payment request
            payment_request = self.supabase.table('payment_requests').insert({
                'trainer_id': trainer_id,
                'client_id': client_id,
                'payment_token_id': token.data['id'],
                'amount': amount,
                'description': description,
                'status': 'approved' if auto_approved else 'pending_client',
                'auto_approved': auto_approved,
                'trainer_approved': True,
                'trainer_approved_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=48)).isoformat()
            }).execute()
            
            if auto_approved:
                # Process payment immediately
                return self.process_tokenized_payment(payment_request.data[0]['id'])
            else:
                # Send approval request to client
                return self._send_payment_approval_request(payment_request.data[0]['id'])
                
        except Exception as e:
            logger.error(f"Error creating payment request: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_tokenized_payment(self, payment_request_id: str) -> Dict:
        """
        Process a payment using saved token
        """
        try:
            # Get payment request details
            request = self.supabase.table('payment_requests').select(
                '*, client_payment_tokens(*), clients(*), trainers(*)'
            ).eq('id', payment_request_id).single().execute()
            
            if not request.data:
                return {'success': False, 'message': 'Payment request not found'}
            
            token = request.data['client_payment_tokens']
            client = request.data['clients']
            trainer = request.data['trainers']
            
            # Call PayFast API to charge the token
            headers = {
                'merchant-id': self.payfast_config['merchant_id'],
                'version': 'v1',
                'timestamp': datetime.now().isoformat(),
                'signature': self._generate_api_signature()
            }
            
            charge_data = {
                'token': token['payfast_token'],
                'amount': int(request.data['amount'] * 100),  # Convert to cents
                'item_name': request.data['description']
            }
            
            response = requests.post(
                f"{self.payfast_api_url}/subscriptions/{token['payfast_token']}/charge",
                headers=headers,
                json=charge_data
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Create payment record
                payment = self.supabase.table('payments').insert({
                    'trainer_id': request.data['trainer_id'],
                    'client_id': request.data['client_id'],
                    'payment_request_id': payment_request_id,
                    'payment_token_id': token['id'],
                    'amount': request.data['amount'],
                    'payment_method': 'token',
                    'status': 'paid',
                    'paid_date': datetime.now().isoformat(),
                    'payfast_payment_id': result.get('payment_id'),
                    'auto_payment': request.data['auto_approved']
                }).execute()
                
                # Update payment request status
                self.supabase.table('payment_requests').update({
                    'status': 'paid',
                    'payment_completed_at': datetime.now().isoformat(),
                    'payment_id': payment.data[0]['id']
                }).eq('id', payment_request_id).execute()
                
                # Send confirmation messages
                self._send_payment_confirmation(payment.data[0]['id'])
                
                return {'success': True, 'payment_id': payment.data[0]['id']}
            else:
                # Payment failed
                self.supabase.table('payment_requests').update({
                    'status': 'failed',
                    'payment_failed_at': datetime.now().isoformat(),
                    'failure_reason': response.text
                }).eq('id', payment_request_id).execute()
                
                return {'success': False, 'message': 'Payment failed', 'error': response.text}
                
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==========================================
    # PAYMENT REMINDERS
    # ==========================================
    
    def send_monthly_payment_reminders(self) -> None:
        """
        Send monthly payment reminders to trainers (run as scheduled job)
        """
        try:
            today = date.today()
            
            # Get all reminders due today
            reminders = self.supabase.table('payment_reminders').select(
                '*, trainers(*)'
            ).eq('reminder_day', today.day).eq('reminder_enabled', True).execute()
            
            for reminder in reminders.data:
                trainer = reminder['trainers']
                
                # Get active clients with amounts due
                clients = self.supabase.table('clients').select(
                    '*, client_payment_tokens(*)'
                ).eq('trainer_id', trainer['id']).eq('status', 'active').execute()
                
                if not clients.data:
                    continue
                
                # Build reminder message
                client_list = []
                total_amount = 0
                
                for client in clients.data:
                    # Check if client has token
                    has_token = bool(client.get('client_payment_tokens'))
                    
                    # Get typical session price
                    price = trainer.get('pricing_per_session', 500)
                    
                    client_list.append(
                        f"• {client['name']}: R{price} "
                        f"{'✅' if has_token else '❌ (no payment method)'}"
                    )
                    
                    if has_token:
                        total_amount += price
                
                message = (
                    f"💰 *Monthly Payment Reminder*\n\n"
                    f"Hi {trainer['name']}! It's time for monthly payments.\n\n"
                    f"*Clients to bill:*\n"
                    f"{chr(10).join(client_list)}\n\n"
                    f"*Total: R{total_amount}*\n\n"
                    f"Reply *YES* to send payment requests to all clients with saved cards\n"
                    f"Reply *SKIP* to skip this month"
                )
                
                self._send_whatsapp_message(trainer['whatsapp'], message)
                
                # Update reminder record
                self.supabase.table('payment_reminders').update({
                    'last_sent_date': today.isoformat(),
                    'reminder_sent_at': datetime.now().isoformat(),
                    'total_clients': len(clients.data),
                    'clients_to_bill': len([c for c in clients.data if c.get('client_payment_tokens')]),
                    'next_scheduled_date': (today + timedelta(days=30)).isoformat()
                }).eq('id', reminder['id']).execute()
                
        except Exception as e:
            logger.error(f"Error sending reminders: {str(e)}")

    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    def _generate_payfast_signature(self, data: Dict) -> str:
        """Generate PayFast signature for data integrity"""
        # Remove signature if present
        data_copy = {k: v for k, v in data.items() if k != 'signature'}
        
        # Create parameter string
        param_string = urllib.parse.urlencode(data_copy)
        
        # Add passphrase if set
        if self.payfast_config['passphrase']:
            param_string += f"&passphrase={self.payfast_config['passphrase']}"
        
        # Generate MD5 hash
        return hashlib.md5(param_string.encode()).hexdigest()
    
    def _generate_api_signature(self) -> str:
        """Generate signature for PayFast API calls"""
        # This would need proper implementation based on PayFast API docs
        return "api_signature_here"
    
    def _send_whatsapp_message(self, phone: str, message: str) -> bool:
        """Send WhatsApp message via Meta API"""
        try:
            # Format phone number (remove any non-digits and add country code if needed)
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('27'):
                phone = '27' + phone.lstrip('0')
            
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }
            
            response = requests.post(self.whatsapp_api_url, headers=headers, json=data)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp message sent to {phone}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    def _send_payment_approval_request(self, payment_request_id: str) -> Dict:
        """Send payment approval request to client via WhatsApp"""
        try:
            # Get request details
            request = self.supabase.table('payment_requests').select(
                '*, client_payment_tokens(*), clients(*), trainers(*)'
            ).eq('id', payment_request_id).single().execute()
            
            client = request.data['clients']
            trainer = request.data['trainers']
            token = request.data['client_payment_tokens']
            
            message = (
                f"💳 *Payment Request*\n\n"
                f"From: {trainer['business_name'] or trainer['name']}\n"
                f"Amount: *R{request.data['amount']}*\n"
                f"Description: {request.data['description']}\n"
                f"Card: {token['card_brand']} ****{token['card_last_four']}\n\n"
                f"Reply *YES* to approve payment\n"
                f"Reply *NO* to decline\n\n"
                f"This request expires in 48 hours."
            )
            
            self._send_whatsapp_message(client['whatsapp'], message)
            
            # Update request status
            self.supabase.table('payment_requests').update({
                'status': 'pending_client'
            }).eq('id', payment_request_id).execute()
            
            return {'success': True, 'message': 'Approval request sent to client'}
            
        except Exception as e:
            logger.error(f"Error sending approval request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_payment_confirmation(self, payment_id: str) -> None:
        """Send payment confirmation to both trainer and client"""
        try:
            # Get payment details
            payment = self.supabase.table('payments').select(
                '*, clients(*), trainers(*)'
            ).eq('id', payment_id).single().execute()
            
            client = payment.data['clients']
            trainer = payment.data['trainers']
            
            # Calculate fees
            payfast_fee = round(payment.data['amount'] * 0.035 + 2, 2)
            platform_fee = 5.00
            net_amount = payment.data['amount'] - payfast_fee - platform_fee
            
            # Message to client
            client_message = (
                f"✅ *Payment Successful*\n\n"
                f"Amount: R{payment.data['amount']}\n"
                f"To: {trainer['business_name'] or trainer['name']}\n"
                f"Date: {datetime.now().strftime('%d %B %Y')}\n"
                f"Reference: {payment.data['id'][:8].upper()}\n\n"
                f"Thank you for your payment! 💪"
            )
            
            # Message to trainer
            trainer_message = (
                f"💰 *Payment Received*\n\n"
                f"From: {client['name']}\n"
                f"Amount: R{payment.data['amount']}\n"
                f"Fees: R{payfast_fee + platform_fee:.2f}\n"
                f"Net: R{net_amount:.2f}\n"
                f"Reference: {payment.data['id'][:8].upper()}\n\n"
                f"Funds will be paid out to your account soon."
            )
            
            self._send_whatsapp_message(client['whatsapp'], client_message)
            self._send_whatsapp_message(trainer['whatsapp'], trainer_message)
            
        except Exception as e:
            logger.error(f"Error sending confirmations: {str(e)}")

    def handle_payment_response(self, phone: str, message: str) -> Dict:
        """
        Handle YES/NO responses for payment approvals
        """
        try:
            message_lower = message.lower().strip()
            
            # Check if this is a payment approval response
            if message_lower not in ['yes', 'no']:
                return {'success': False, 'message': 'Not a payment response'}
            
            # Find pending payment request for this client
            client = self.supabase.table('clients').select('id').eq('whatsapp', phone).single().execute()
            
            if not client.data:
                return {'success': False, 'message': 'Client not found'}
            
            # Get most recent pending request
            pending_request = self.supabase.table('payment_requests').select('*').eq(
                'client_id', client.data['id']
            ).eq('status', 'pending_client').order('created_at', desc=True).limit(1).execute()
            
            if not pending_request.data:
                return {'success': False, 'message': 'No pending payment requests'}
            
            request = pending_request.data[0]
            
            if message_lower == 'yes':
                # Update request as approved
                self.supabase.table('payment_requests').update({
                    'client_approved': True,
                    'client_approved_at': datetime.now().isoformat(),
                    'client_whatsapp_response': message,
                    'status': 'approved'
                }).eq('id', request['id']).execute()
                
                # Process the payment
                result = self.process_tokenized_payment(request['id'])
                
                if result['success']:
                    return {'success': True, 'message': 'Payment approved and processed successfully'}
                else:
                    return {'success': False, 'message': 'Payment approved but processing failed'}
                    
            else:  # message_lower == 'no'
                # Update request as rejected
                self.supabase.table('payment_requests').update({
                    'client_approved': False,
                    'client_approved_at': datetime.now().isoformat(),
                    'client_whatsapp_response': message,
                    'status': 'rejected'
                }).eq('id', request['id']).execute()
                
                # Notify trainer
                trainer = self.supabase.table('trainers').select('*').eq('id', request['trainer_id']).single().execute()
                
                notification = (
                    f"❌ *Payment Declined*\n\n"
                    f"Client {client.data.get('name', 'Unknown')} has declined the payment request of R{request['amount']}."
                )
                
                self._send_whatsapp_message(trainer.data['whatsapp'], notification)
                
                return {'success': True, 'message': 'Payment declined'}
                
        except Exception as e:
            logger.error(f"Error handling payment response: {str(e)}")
            return {'success': False, 'error': str(e)}
