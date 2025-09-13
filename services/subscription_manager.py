"""Subscription management service"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error

class SubscriptionManager:
    """Manage trainer subscriptions"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Subscription plans
        self.PLANS = {
            'free': {
                'name': 'Free',
                'price': 0,
                'max_clients': 3,
                'features': ['basic_scheduling', 'whatsapp_bot']
            },
            'professional': {
                'name': 'Professional',
                'price': 49,
                'max_clients': None,  # Unlimited
                'features': ['all_features', 'priority_support', 'analytics']
            }
        }
    
    def get_trainer_subscription(self, trainer_id: str) -> Dict:
        """Get trainer's current subscription"""
        try:
            result = self.db.table('trainer_subscriptions').select('*').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').single().execute()
            
            if result.data:
                return result.data
            
            # Return free plan by default
            return {
                'plan': 'free',
                'status': 'active',
                'max_clients': self.PLANS['free']['max_clients']
            }
            
        except Exception as e:
            log_error(f"Error getting subscription: {str(e)}")
            return {
                'plan': 'free',
                'status': 'active',
                'max_clients': 3
            }
    
    def can_add_client(self, trainer_id: str) -> bool:
        """Check if trainer can add more clients"""
        try:
            subscription = self.get_trainer_subscription(trainer_id)
            
            # Unlimited for professional
            if subscription['plan'] == 'professional':
                return True
            
            # Check current client count
            clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            current_count = len(clients.data) if clients.data else 0
            max_clients = subscription.get('max_clients', 3)
            
            return current_count < max_clients
            
        except Exception as e:
            log_error(f"Error checking client limit: {str(e)}")
            return False
    
    def upgrade_subscription(self, trainer_id: str, plan: str) -> Dict:
        """Upgrade trainer subscription"""
        try:
            if plan not in self.PLANS:
                return {'success': False, 'error': 'Invalid plan'}
            
            # Deactivate current subscription
            self.db.table('trainer_subscriptions').update({
                'status': 'inactive',
                'ended_at': datetime.now(self.sa_tz).isoformat()
            }).eq('trainer_id', trainer_id).eq('status', 'active').execute()
            
            # Create new subscription
            subscription_data = {
                'trainer_id': trainer_id,
                'plan': plan,
                'status': 'active',
                'price': self.PLANS[plan]['price'],
                'start_date': datetime.now(self.sa_tz).isoformat(),
                'end_date': (datetime.now(self.sa_tz) + timedelta(days=30)).isoformat(),
                'auto_renew': True
            }
            
            result = self.db.table('trainer_subscriptions').insert(
                subscription_data
            ).execute()
            
            if result.data:
                log_info(f"Trainer {trainer_id} upgraded to {plan}")
                return {'success': True, 'subscription': result.data[0]}
            
            return {'success': False, 'error': 'Failed to create subscription'}
            
        except Exception as e:
            log_error(f"Error upgrading subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def cancel_subscription(self, trainer_id: str) -> Dict:
        """Cancel trainer subscription"""
        try:
            result = self.db.table('trainer_subscriptions').update({
                'auto_renew': False,
                'cancelled_at': datetime.now(self.sa_tz).isoformat()
            }).eq('trainer_id', trainer_id).eq('status', 'active').execute()
            
            if result.data:
                return {'success': True, 'message': 'Subscription will end at the end of the billing period'}
            
            return {'success': False, 'error': 'No active subscription found'}
            
        except Exception as e:
            log_error(f"Error cancelling subscription: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def check_subscription_limits(self, trainer_id: str) -> Dict:
        """Check current usage against subscription limits"""
        try:
            subscription = self.get_trainer_subscription(trainer_id)
            
            # Get current usage
            clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            current_clients = len(clients.data) if clients.data else 0
            max_clients = subscription.get('max_clients')
            
            return {
                'plan': subscription['plan'],
                'current_clients': current_clients,
                'max_clients': max_clients,
                'can_add_clients': max_clients is None or current_clients < max_clients,
                'usage_percentage': (current_clients / max_clients * 100) if max_clients else 0
            }
            
        except Exception as e:
            log_error(f"Error checking limits: {str(e)}")
            return {
                'plan': 'free',
                'current_clients': 0,
                'max_clients': 3,
                'can_add_clients': True
            }