"""Subscription management service"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
from utils.logger import log_info, log_error

class SubscriptionManager:
    """Manages trainer subscriptions"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Subscription plans
        self.plans = {
            'free': {
                'name': 'Free',
                'price': 0,
                'client_limit': 3,
                'features': ['Basic features']
            },
            'professional': {
                'name': 'Professional',
                'price': 49,
                'client_limit': None,
                'features': ['Unlimited clients', 'All features']
            }
        }
    
    def check_subscription(self, trainer_id: str) -> Dict:
        """Check trainer's subscription status"""
        try:
            result = self.db.table('trainers').select(
                'subscription_status, subscription_expires_at'
            ).eq('id', trainer_id).single().execute()
            
            if not result.data:
                return {'status': 'free', 'valid': True}
            
            status = result.data.get('subscription_status', 'free')
            expires_at = result.data.get('subscription_expires_at')
            
            if status == 'professional' and expires_at:
                expires = datetime.fromisoformat(expires_at)
                if expires < datetime.now(self.sa_tz):
                    # Expired
                    self.db.table('trainers').update({
                        'subscription_status': 'free'
                    }).eq('id', trainer_id).execute()
                    
                    return {'status': 'free', 'valid': True, 'expired': True}
            
            return {'status': status, 'valid': True}
            
        except Exception as e:
            log_error(f"Error checking subscription: {str(e)}")
            return {'status': 'free', 'valid': False}
    
    def can_add_client(self, trainer_id: str) -> bool:
        """Check if trainer can add more clients"""
        try:
            sub = self.check_subscription(trainer_id)
            
            if sub['status'] == 'professional':
                return True
            
            # Check client count for free plan
            count = self.db.table('clients').select(
                'id', count='exact'
            ).eq('trainer_id', trainer_id).eq(
                'status', 'active'
            ).execute()
            
            return (count.count or 0) < self.plans['free']['client_limit']
            
        except Exception as e:
            log_error(f"Error checking client limit: {str(e)}")
            return False