# payfast_webhook.py
"""
PayFast Webhook Handler for Refiloe
Processes PayFast notifications for payments and subscriptions
"""

import os
import hashlib
import urllib.parse
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from supabase import create_client, Client
import logging
import requests
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
payfast_webhook_bp = Blueprint('payfast_webhook', __name__)

class PayFastWebhookHandler:
    """Handles PayFast webhook notifications"""
    
    def __init__(self):
        """Initialize webhook handler"""
        # Supabase setup
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # PayFast configuration
        self.payfast_config = {
            'merchant_id': os.environ.get('PAYFAST_MERCHANT_ID', '10000100'),
            'merchant_key': os.environ.get('PAYFAST_MERCHANT_KEY', '46f0cd694581a'),
            'passphrase': os.environ.get('PAYFAST_PASSPHRASE', ''),
            'test_mode': os.environ.get('PAYFAST_TEST_MODE', 'true').lower() == 'true'
        }
        
        # Valid PayFast IP addresses
        self.valid_ips = [
            '41.74.179.194', '41.74.179.195', '41.74.179.196',
            '41.74.179.197', '41.74.179.200', '41.74.179.201',
            '41.74.179.203', '41.74.179.204', '41.74.179.210',
            '41.74.179.211', '41.74.179.212', '41.74.179.217',
            '41.74.179.218', '197.97.145.144', '197.97.145.145',
            '197.97.145.149', '197.97.145.150', '197.97.145.154',
            '197.97.145.155', '197.97.145.156', '197.97.145.157',
            '197.97.145.158', '197.97.145.159', '197.97.145.160',
            '197.97.145.161', '197.97.145.162', '197.97.145.163',
            '197.97.145.164', '197.97.145.165'
        ]

    def validate_signature(self, data: Dict) -> bool:
        """
        Validate PayFast signature
        """
        try:
            # Get received signature
            received_signature = data.get('signature', '')
            
            # Create copy without signature
            data_copy = {k: v for k, v in data.items() if k != 'signature'}
            
            # Sort and encode parameters
            param_string = urllib.parse.urlencode(sorted(data_copy.items()))
            
            # Add passphrase if configured
            if self.payfast_config['passphrase']:
                param_string += f"&passphrase={urllib.parse.quote_plus(self.payfast_config['passphrase'])}"
            
            # Generate MD5 hash
            calculated_signature = hashlib.md5(param_string.encode()).hexdigest()
            
            return calculated_signature == received_signature
            
        except Exception as e:
            logger.error(f"Error validating signature: {str(e)}")
            return False

    def validate_ip(self, ip_address: str) -> bool:
        """
        Validate that request comes from PayFast IP
        """
        if self.payfast_config['test_mode']:
            return True  # Skip IP validation in test mode
        return ip_address in self.valid_ips

    def validate_payment_data(self, data: Dict) -> bool:
        """
        Validate payment data against expected values
        """
        try:
            # Check merchant ID
            if data.get('merchant_id') != self.payfast_config['merchant_id']:
                logger.error(f"Invalid merchant_id: {data.get('merchant_id')}")
                return False
            
            # Verify payment status
            if data.get('payment_status') != 'COMPLETE':
                logger.info(f"Payment status not complete: {data.get('payment_status')}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating payment data: {str(e)}")
            return False

    def process_payment_notification(self, data: Dict) -> Dict:
        """
        Process a payment notification from PayFast
        """
        try:
            # Log the webhook for debugging
            self.supabase.table('payfast_webhooks').insert({
                'webhook_type': 'payment',
                'event_type': data.get('payment_status'),
                'payfast_payment_id': data.get('pf_payment_id'),
                'payload': json.dumps(data),
                'signature': data.get('signature'),
                'signature_valid': self.validate_signature(data),
                'created_at': datetime.now().isoformat()
            }).execute()
            
            # Get payment ID from custom fields
            m_payment_id = data.get('m_payment_id', '')
            
            if m_payment_id.startswith('SUB_'):
                # This is a subscription payment
                return self.process_subscription_payment(data)
            elif m_payment_id.startswith('TOKEN_'):
                # This is a tokenization payment
                return self.process_tokenization_payment(data)
            elif m_payment_id.startswith('PAY_'):
                # This is a regular payment
                return self.process_regular_payment(data)
            else:
                logger.warning(f"Unknown payment type: {m_payment_id}")
                return {'success': False, 'message': 'Unknown payment type'}
                
        except Exception as e:
            logger.error(f"Error processing payment notification: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_subscription_payment(self, data: Dict) -> Dict:
        """
        Process subscription payment for trainer
        """
        try:
            trainer_id = data.get('m_payment_id', '').replace('SUB_', '')
            
            # Find trainer subscription
            subscription = self.supabase.table('trainer_subscriptions').select('*').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').single().execute()
            
            if not subscription.data:
                # Create new subscription
                plan = self.supabase.table('subscription_plans').select('*').eq(
                    'plan_code', 'professional'
                ).single().execute()
                
                subscription = self.supabase.table('trainer_subscriptions').insert({
                    'trainer_id': trainer_id,
                    'plan_id': plan.data['id'],
                    'status': 'active',
                    'billing_cycle': 'monthly',
                    'payfast_token': data.get('token'),
                    'payfast_subscription_id': data.get('pf_payment_id'),
                    'current_period_start': datetime.now().isoformat(),
                    'current_period_end': (datetime.now() + timedelta(days=30)).isoformat()
                }).execute()
            
            # Record payment
            self.supabase.table('subscription_payment_history').insert({
                'trainer_id': trainer_id,
                'subscription_id': subscription.data[0]['id'] if isinstance(subscription.data, list) else subscription.data['id'],
                'amount': float(data.get('amount_gross', 0)),
                'fee_amount': float(data.get('amount_fee', 0)),
                'net_amount': float(data.get('amount_net', 0)),
                'payment_status': 'complete',
                'payfast_payment_id': data.get('pf_payment_id'),
                'payfast_payment_status': data.get('payment_status'),
                'webhook_data': json.dumps(data)
            }).execute()
            
            # Update trainer status
            self.supabase.table('trainers').update({
                'subscription_status': 'active',
                'subscription_expires_at': (datetime.now() + timedelta(days=30)).isoformat()
            }).eq('id', trainer_id).execute()
            
            return {'success': True, 'message': 'Subscription payment processed'}
            
        except Exception as e:
            logger.error(f"Error processing subscription payment: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_tokenization_payment(self, data: Dict) -> Dict:
        """
        Process tokenization (save card) payment
        """
        try:
            # Extract client and trainer IDs
            parts = data.get('m_payment_id', '').replace('TOKEN_', '').split('_')
            if len(parts) != 2:
                return {'success': False, 'message': 'Invalid token payment ID'}
            
            client_id, trainer_id = parts
            setup_code = data.get('custom_str1', '')
            
            # Find setup request
            setup_request = self.supabase.table('token_setup_requests').select('*').eq(
                'setup_code', setup_code
            ).eq('status', 'pending').single().execute()
            
            if not setup_request.data:
                return {'success': False, 'message': 'Setup request not found'}
            
            # Create payment token record
            token = self.supabase.table('client_payment_tokens').insert({
                'client_id': client_id,
                'trainer_id': trainer_id,
                'payfast_token': data.get('token'),
                'payfast_token_status': 'active',
                'card_last_four': data.get('card_last4', ''),
                'card_brand': self._determine_card_brand(data.get('card_number', '')),
                'consent_given': True,
                'consent_date': datetime.now().isoformat(),
                'consent_message': f"Token created via PayFast on {datetime.now().strftime('%Y-%m-%d')}"
            }).execute()
            
            # Update setup request
            self.supabase.table('token_setup_requests').update({
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'token_id': token.data[0]['id']
            }).eq('id', setup_request.data['id']).execute()
            
            # Send confirmation to client
            client = self.supabase.table('clients').select('*').eq('id', client_id).single().execute()
            trainer = self.supabase.table('trainers').select('*').eq('id', trainer_id).single().execute()
            
            self._send_whatsapp_confirmation(
                client.data['whatsapp'],
                f"✅ Payment method saved successfully!\n\n"
                f"Card: {token.data[0]['card_brand']} ****{token.data[0]['card_last_four']}\n"
                f"For: {trainer.data['business_name'] or trainer.data['name']}\n\n"
                f"You can now make quick payments via WhatsApp."
            )
            
            # Refund the R5 verification
            # This would need PayFast refund API implementation
            
            return {'success': True, 'message': 'Token created successfully'}
            
        except Exception as e:
            logger.error(f"Error processing tokenization: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_regular_payment(self, data: Dict) -> Dict:
        """
        Process regular client payment
        """
        try:
            payment_request_id = data.get('custom_str1', '')
            
            # Find payment request
            payment_request = self.supabase.table('payment_requests').select('*').eq(
                'id', payment_request_id
            ).single().execute()
            
            if not payment_request.data:
                return {'success': False, 'message': 'Payment request not found'}
            
            # Create payment record
            payment = self.supabase.table('payments').insert({
                'trainer_id': payment_request.data['trainer_id'],
                'client_id': payment_request.data['client_id'],
                'payment_request_id': payment_request_id,
                'amount': float(data.get('amount_gross', 0)),
                'processor_fee': float(data.get('amount_fee', 0)),
                'net_amount': float(data.get('amount_net', 0)),
                'payment_method': 'payfast',
                'status': 'paid',
                'paid_date': datetime.now().isoformat(),
                'payfast_payment_id': data.get('pf_payment_id'),
                'payfast_payment_status': data.get('payment_status'),
                'webhook_data': json.dumps(data)
            }).execute()
            
            # Update payment request
            self.supabase.table('payment_requests').update({
                'status': 'paid',
                'payment_completed_at': datetime.now().isoformat(),
                'payment_id': payment.data[0]['id'],
                'payfast_payment_id': data.get('pf_payment_id')
            }).eq('id', payment_request_id).execute()
            
            # Send confirmations
            self._send_payment_confirmations(payment.data[0]['id'])
            
            return {'success': True, 'message': 'Payment processed successfully'}
            
        except Exception as e:
            logger.error(f"Error processing regular payment: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _determine_card_brand(self, card_number: str) -> str:
        """
        Determine card brand from partial card number
        """
        if card_number.startswith('4'):
            return 'Visa'
        elif card_number.startswith('5'):
            return 'Mastercard'
        elif card_number.startswith('3'):
            return 'Amex'
        else:
            return 'Card'

    def _send_whatsapp_confirmation(self, phone: str, message: str) -> None:
        """
        Send WhatsApp confirmation message
        """
        try:
            whatsapp_token = os.environ.get("ACCESS_TOKEN")
            phone_number_id = os.environ.get("PHONE_NUMBER_ID")
            
            # Format phone number
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('27'):
                phone = '27' + phone.lstrip('0')
            
            headers = {
                "Authorization": f"Bearer {whatsapp_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }
            
            url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
            requests.post(url, headers=headers, json=data)
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp: {str(e)}")

    def _send_payment_confirmations(self, payment_id: str) -> None:
        """
        Send payment confirmations to trainer and client
        """
        try:
            payment = self.supabase.table('payments').select(
                '*, clients(*), trainers(*)'
            ).eq('id', payment_id).single().execute()
            
            client = payment.data['clients']
            trainer = payment.data['trainers']
            
            # Client confirmation
            client_msg = (
                f"✅ *Payment Successful*\n\n"
                f"Amount: R{payment.data['amount']}\n"
                f"To: {trainer['business_name'] or trainer['name']}\n"
                f"Reference: {payment.data['id'][:8].upper()}\n\n"
                f"Thank you! 💪"
            )
            
            # Trainer confirmation  
            trainer_msg = (
                f"💰 *Payment Received*\n\n"
                f"From: {client['name']}\n"
                f"Amount: R{payment.data['amount']}\n"
                f"Net: R{payment.data['net_amount']}\n"
                f"Reference: {payment.data['id'][:8].upper()}"
            )
            
            self._send_whatsapp_confirmation(client['whatsapp'], client_msg)
            self._send_whatsapp_confirmation(trainer['whatsapp'], trainer_msg)
            
        except Exception as e:
            logger.error(f"Error sending confirmations: {str(e)}")


# Initialize handler
webhook_handler = PayFastWebhookHandler()

@payfast_webhook_bp.route('/webhooks/payfast', methods=['POST'])
def handle_payfast_webhook():
    """
    Main webhook endpoint for PayFast notifications
    """
    try:
        # Get request data
        data = dict(request.form)
        
        # Validate IP address
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if not webhook_handler.validate_ip(client_ip):
            logger.warning(f"Invalid IP address: {client_ip}")
            return 'INVALID', 401
        
        # Validate signature
        if not webhook_handler.validate_signature(data):
            logger.warning("Invalid signature")
            return 'INVALID', 401
        
        # Validate payment data
        if not webhook_handler.validate_payment_data(data):
            logger.warning("Invalid payment data")
            return 'INVALID', 400
        
        # Process the notification
        result = webhook_handler.process_payment_notification(data)
        
        if result['success']:
            return 'OK', 200
        else:
            return 'ERROR', 500
            
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return 'ERROR', 500

@payfast_webhook_bp.route('/webhooks/payfast/test', methods=['GET'])
def test_webhook():
    """
    Test endpoint to verify webhook is accessible
    """
    return jsonify({
        'status': 'ok',
        'message': 'PayFast webhook endpoint is active',
        'test_mode': webhook_handler.payfast_config['test_mode']
    }), 200
