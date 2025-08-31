# Extended version of payment_manager.py with complete webhook handling
import os
import hashlib  # This is a built-in module, no pip install needed
import urllib.parse
import requests
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
from utils.logger import log_error, log_info

class PaymentManager:
    def __init__(self, supabase_client):
        """Initialize PaymentManager with Supabase client"""
        self.supabase = supabase_client
        self.merchant_id = os.environ.get('PAYFAST_MERCHANT_ID')
        self.merchant_key = os.environ.get('PAYFAST_MERCHANT_KEY')
        self.passphrase = os.environ.get('PAYFAST_PASSPHRASE', '')
        self.webhook_secret = os.environ.get('PAYFAST_WEBHOOK_SECRET', self.passphrase)
        self.base_url = 'https://www.payfast.co.za/eng/process' if os.environ.get('PAYFAST_MODE') == 'live' else 'https://sandbox.payfast.co.za/eng/process'
        self.api_base_url = 'https://api.payfast.co.za' if os.environ.get('PAYFAST_MODE') == 'live' else 'https://api-sandbox.payfast.co.za'
        
    def verify_webhook_signature(self, payload: Dict, signature: str) -> bool:
        """Verify PayFast webhook signature"""
        try:
            # Sort payload keys
            sorted_payload = dict(sorted(payload.items()))
            
            # Create signature string
            signature_string = urllib.parse.urlencode(sorted_payload)
            
            # Add passphrase if configured
            if self.passphrase:
                signature_string = f"{signature_string}&passphrase={urllib.parse.quote_plus(self.passphrase)}"
            
            # Calculate expected signature
            expected_signature = hashlib.md5(
                signature_string.encode()
            ).hexdigest()
            
            return signature == expected_signature
            
        except Exception as e:
            log_error(f"Signature verification error: {str(e)}")
            return False

    def handle_subscription_webhook(self, payload: Dict) -> Dict:
        """Handle subscription-related webhooks"""
        try:
            payment_status = payload.get('payment_status')
            subscription_id = payload.get('subscription_id')
            
            if not all([payment_status, subscription_id]):
                return {'success': False, 'error': 'Missing required fields'}
                
            # Update subscription status
            self.supabase.table('trainer_subscriptions').update({
                'status': payment_status,
                'last_payment_date': datetime.now().isoformat(),
                'payfast_subscription_id': subscription_id
            }).eq('payfast_subscription_id', subscription_id).execute()
            
            # Handle specific status
            if payment_status == 'COMPLETE':
                # Extend subscription
                self._extend_subscription(subscription_id)
            elif payment_status == 'FAILED':
                # Mark for follow-up
                self._handle_failed_payment(subscription_id)
                
            return {'success': True}
            
        except Exception as e:
            log_error(f"Subscription webhook error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def handle_token_webhook(self, payload: Dict) -> Dict:
        """Handle token-related webhooks"""
        try:
            token_id = payload.get('token')
            setup_code = payload.get('custom_str1')
            
            if not all([token_id, setup_code]):
                return {'success': False, 'error': 'Missing token information'}
                
            # Verify setup request
            setup = self.supabase.table('token_setup_requests').select('*').eq(
                'setup_code', setup_code
            ).single().execute()
            
            if not setup.data:
                return {'success': False, 'error': 'Invalid setup request'}
                
            # Store token
            self.supabase.table('client_payment_tokens').insert({
                'client_id': setup.data['client_id'],
                'trainer_id': setup.data['trainer_id'],
                'payfast_token': token_id,
                'payfast_token_status': 'active',
                'created_at': datetime.now().isoformat()
            }).execute()
            
            return {'success': True}
            
        except Exception as e:
            log_error(f"Token webhook error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def create_payment_request(self, amount: float, description: str, client_phone: str, 
                             payment_type: str = 'once_off') -> Dict:
        """Create a payment request for a client"""
        try:
            # Generate unique payment ID
            payment_id = str(uuid.uuid4())
            
            # Store payment request in database
            payment_data = {
                'payment_id': payment_id,
                'amount': amount,
                'description': description,
                'client_phone': client_phone,
                'payment_type': payment_type,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('payment_requests').insert(payment_data).execute()
            
            if not result.data:
                return {'success': False, 'error': 'Failed to create payment request'}
            
            # Generate PayFast payment URL
            payment_url = self._generate_payment_url(payment_id, amount, description)
            
            return {
                'success': True,
                'payment_id': payment_id,
                'payment_url': payment_url,
                'amount': amount
            }
            
        except Exception as e:
            log_error(f"Payment request creation error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _generate_payment_url(self, payment_id: str, amount: float, description: str) -> str:
        """Generate PayFast payment URL"""
        try:
            # Build payment data
            data = {
                'merchant_id': self.merchant_id,
                'merchant_key': self.merchant_key,
                'amount': f"{amount:.2f}",
                'item_name': description,
                'custom_str1': payment_id,
                'return_url': f"{os.environ.get('APP_BASE_URL', 'https://refiloe.co.za')}/payment/success",
                'cancel_url': f"{os.environ.get('APP_BASE_URL', 'https://refiloe.co.za')}/payment/cancel",
                'notify_url': f"{os.environ.get('APP_BASE_URL', 'https://refiloe.co.za')}/webhook/payfast"
            }
            
            # Generate signature
            signature_string = urllib.parse.urlencode(sorted(data.items()))
            if self.passphrase:
                signature_string = f"{signature_string}&passphrase={urllib.parse.quote_plus(self.passphrase)}"
            
            signature = hashlib.md5(signature_string.encode()).hexdigest()
            data['signature'] = signature
            
            # Build URL
            query_string = urllib.parse.urlencode(data)
            return f"{self.base_url}?{query_string}"
            
        except Exception as e:
            log_error(f"Payment URL generation error: {str(e)}")
            return ""

    def _extend_subscription(self, subscription_id: str):
        """Extend subscription period after successful payment"""
        try:
            # Get current subscription
            result = self.supabase.table('trainer_subscriptions').select('*').eq(
                'payfast_subscription_id', subscription_id
            ).single().execute()
            
            if result.data:
                # Extend by one month
                current_end = datetime.fromisoformat(result.data['subscription_end_date'])
                new_end = current_end + timedelta(days=30)
                
                self.supabase.table('trainer_subscriptions').update({
                    'subscription_end_date': new_end.isoformat(),
                    'status': 'active'
                }).eq('payfast_subscription_id', subscription_id).execute()
                
                log_info(f"Extended subscription {subscription_id} to {new_end}")
                
        except Exception as e:
            log_error(f"Subscription extension error: {str(e)}")

    def _handle_failed_payment(self, subscription_id: str):
        """Handle failed payment for subscription"""
        try:
            # Update subscription status
            self.supabase.table('trainer_subscriptions').update({
                'status': 'payment_failed',
                'last_failed_payment': datetime.now().isoformat()
            }).eq('payfast_subscription_id', subscription_id).execute()
            
            # TODO: Send notification to trainer
            log_info(f"Marked subscription {subscription_id} as payment failed")
            
        except Exception as e:
            log_error(f"Failed payment handling error: {str(e)}")

    def check_payment_status(self, payment_id: str) -> Dict:
        """Check the status of a payment request"""
        try:
            result = self.supabase.table('payment_requests').select('*').eq(
                'payment_id', payment_id
            ).single().execute()
            
            if result.data:
                return {
                    'success': True,
                    'status': result.data['status'],
                    'amount': result.data['amount'],
                    'paid_at': result.data.get('paid_at')
                }
            
            return {'success': False, 'error': 'Payment not found'}
            
        except Exception as e:
            log_error(f"Payment status check error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_webhook(self, payload: Dict, signature: str = None) -> Dict:
        """Main webhook processing method"""
        try:
            # Verify signature if provided
            if signature and not self.verify_webhook_signature(payload, signature):
                return {'success': False, 'error': 'Invalid signature'}
            
            # Determine webhook type
            if 'subscription_id' in payload:
                return self.handle_subscription_webhook(payload)
            elif 'token' in payload:
                return self.handle_token_webhook(payload)
            else:
                # Regular payment webhook
                return self._handle_payment_webhook(payload)
                
        except Exception as e:
            log_error(f"Webhook processing error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _handle_payment_webhook(self, payload: Dict) -> Dict:
        """Handle regular payment webhooks"""
        try:
            payment_id = payload.get('custom_str1')
            payment_status = payload.get('payment_status')
            
            if not all([payment_id, payment_status]):
                return {'success': False, 'error': 'Missing payment information'}
            
            # Update payment status
            update_data = {
                'status': 'paid' if payment_status == 'COMPLETE' else payment_status.lower(),
                'payfast_payment_id': payload.get('pf_payment_id'),
                'paid_at': datetime.now().isoformat() if payment_status == 'COMPLETE' else None
            }
            
            self.supabase.table('payment_requests').update(
                update_data
            ).eq('payment_id', payment_id).execute()
            
            return {'success': True}
            
        except Exception as e:
            log_error(f"Payment webhook error: {str(e)}")
            return {'success': False, 'error': str(e)}