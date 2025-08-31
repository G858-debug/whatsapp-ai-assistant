import hmac
import hashlib
import requests
from typing import Dict, Optional
from datetime import datetime
from config import Config
from utils.logger import log_error, log_info

class PaymentManager:
    """Handles payment processing and verification through PayFast"""
    
    PAYFAST_VERIFY_URL = "https://sandbox.payfast.co.za/eng/query/validate"  # Sandbox
    # PAYFAST_VERIFY_URL = "https://www.payfast.co.za/eng/query/validate"  # Production
    
    def __init__(self, supabase_client):
        """Initialize payment manager"""
        self.db = supabase_client
        self.config = Config
    
    def create_payment_request(self, amount: float, client_id: int, trainer_id: int, description: str = None) -> Dict:
        """Create new payment request"""
        try:
            # Validate inputs
            if amount <= 0:
                return {'success': False, 'error': 'Invalid amount'}
                
            # Create payment request record
            result = self.db.table('payment_requests').insert({
                'amount': amount,
                'client_id': client_id,
                'trainer_id': trainer_id,
                'description': description or 'Training payment',
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }).execute()
            
            if result.data:
                payment_id = result.data[0]['id']
                
                # Generate PayFast payment data
                payment_data = self._generate_payment_data(
                    amount=amount,
                    payment_id=payment_id,
                    description=description
                )
                
                return {
                    'success': True,
                    'payment_id': payment_id,
                    'payment_url': self._get_payment_url(payment_data),
                    'payment_data': payment_data
                }
            else:
                return {'success': False, 'error': 'Failed to create payment request'}
                
        except Exception as e:
            log_error(f"Error creating payment request: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def verify_webhook_signature(self, data: Dict, signature: str) -> bool:
        """Verify PayFast webhook signature"""
        try:
            # Get PayFast signature key from config
            signature_key = self.config.PAYFAST_SIGNATURE_KEY
            
            # Sort data by key
            sorted_data = dict(sorted(data.items()))
            
            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in sorted_data.items()])
            
            # Calculate expected signature
            expected = hmac.new(
                signature_key.encode(),
                query_string.encode(),
                hashlib.md5
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected)
            
        except Exception as e:
            log_error(f"Error verifying signature: {str(e)}")
            return False
    
    def verify_payment_data(self, payment_data: Dict) -> bool:
        """Verify payment data with PayFast"""
        try:
            # Send verification request to PayFast
            response = requests.post(
                self.PAYFAST_VERIFY_URL,
                data=payment_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            return response.text.strip().lower() == 'valid'
            
        except Exception as e:
            log_error(f"Error verifying payment: {str(e)}")
            return False
    
    def update_payment_status(self, payment_id: int, new_status: str, transaction_id: str = None) -> Dict:
        """Update payment request status"""
        try:
            update_data = {
                'status': new_status,
                'updated_at': datetime.now().isoformat()
            }
            
            if transaction_id:
                update_data['transaction_id'] = transaction_id
            
            result = self.db.table('payment_requests').update(
                update_data
            ).eq('id', payment_id).execute()
            
            if result.data:
                log_info(f"Updated payment {payment_id} status to {new_status}")
                return {'success': True}
            else:
                return {'success': False, 'error': 'Payment not found'}
                
        except Exception as e:
            log_error(f"Error updating payment status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_payment_status(self, payment_id: int) -> Dict:
        """Get payment request status"""
        try:
            result = self.db.table('payment_requests').select('*').eq(
                'id', payment_id
            ).single().execute()
            
            if result.data:
                return {
                    'success': True,
                    'status': result.data['status'],
                    'amount': result.data['amount'],
                    'created_at': result.data['created_at'],
                    'updated_at': result.data.get('updated_at')
                }
            else:
                return {'success': False, 'error': 'Payment not found'}
                
        except Exception as e:
            log_error(f"Error getting payment status: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _generate_payment_data(self, amount: float, payment_id: int, description: str = None) -> Dict:
        """Generate PayFast payment data"""
        merchant_id = self.config.PAYFAST_MERCHANT_ID
        merchant_key = self.config.PAYFAST_MERCHANT_KEY
        
        # Required payment data
        payment_data = {
            'merchant_id': merchant_id,
            'merchant_key': merchant_key,
            'return_url': f"{self.config.BASE_URL}/payment/success",
            'cancel_url': f"{self.config.BASE_URL}/payment/cancel",
            'notify_url': f"{self.config.BASE_URL}/webhook/payfast",
            'amount': "{:.2f}".format(amount),
            'm_payment_id': str(payment_id),
            'item_name': description or 'Training payment',
            'item_description': description or 'Personal training services',
            'email_confirmation': '1',
            'confirmation_address': self.config.ADMIN_EMAIL
        }
        
        # Add signature
        payment_data['signature'] = self._generate_signature(payment_data)
        
        return payment_data
    
    def _generate_signature(self, data: Dict) -> str:
        """Generate PayFast signature for payment data"""
        # Sort by key
        sorted_data = dict(sorted(data.items()))
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in sorted_data.items()])
        
        # Calculate MD5 hash
        return hashlib.md5(query_string.encode()).hexdigest()
    
    def _get_payment_url(self, payment_data: Dict) -> str:
        """Get PayFast payment URL"""
        base_url = "https://sandbox.payfast.co.za/eng/process"  # Sandbox
        # base_url = "https://www.payfast.co.za/eng/process"  # Production
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in payment_data.items()])
        
        return f"{base_url}?{query_string}"