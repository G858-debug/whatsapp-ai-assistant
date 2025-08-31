# Extended version of payment_manager.py with complete webhook handling
import os
import hashlib
import urllib.parse
import requests
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

class PaymentManager:
    def __init__(self):
        # [Previous init code remains the same]
        self.webhook_secret = os.environ.get('PAYFAST_WEBHOOK_SECRET')
        
    def verify_webhook_signature(self, payload: Dict, signature: str) -> bool:
        """Verify PayFast webhook signature"""
        try:
            # Sort payload keys
            sorted_payload = dict(sorted(payload.items()))
            
            # Create signature string
            signature_string = urllib.parse.urlencode(sorted_payload)
            
            # Calculate expected signature
            expected_signature = hashlib.md5(
                (signature_string + self.webhook_secret).encode()
            ).hexdigest()
            
            return signature == expected_signature
            
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
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
            logger.error(f"Subscription webhook error: {str(e)}")
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
            logger.error(f"Token webhook error: {str(e)}")
            return {'success': False, 'error': str(e)}

    # [Previous payment methods remain the same]