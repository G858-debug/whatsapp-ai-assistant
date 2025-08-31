"""Subscription plan management for Refiloe"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, supabase_client):
        self.db = supabase_client
        
    def get_active_plan(self, trainer_id: str) -> Dict:
        """Get trainer's active subscription plan"""
        try:
            subscription = self.db.table('trainer_subscriptions').select(
                '*'
            ).eq('trainer_id', trainer_id).eq(
                'status', 'active'
            ).single().execute()
            
            if subscription.data:
                plan = self.db.table('subscription_plans').select(
                    '*'
                ).eq('id', subscription.data['plan_id']).single().execute()
                
                return {
                    'success': True,
                    'plan': plan.data,
                    'subscription': subscription.data
                }
            
            return {'success': False, 'error': 'No active subscription'}
            
        except Exception as e:
            logger.error(f"Error getting active plan: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def change_plan(self, trainer_id: str, new_plan_code: str) -> Dict:
        """Change trainer's subscription plan"""
        try:
            # Get new plan details
            new_plan = self.db.table('subscription_plans').select(
                '*'
            ).eq('plan_code', new_plan_code).single().execute()
            
            if not new_plan.data:
                return {'success': False, 'error': 'Invalid plan code'}
                
            # Update subscription
            self.db.table('trainer_subscriptions').update({
                'plan_id': new_plan.data['id'],
                'status': 'pending_payment',
                'updated_at': datetime.now().isoformat()
            }).eq('trainer_id', trainer_id).execute()
            
            return {'success': True, 'plan': new_plan.data}
            
        except Exception as e:
            logger.error(f"Error changing plan: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def cancel_subscription(self, trainer_id: str) -> Dict:
        """Cancel trainer's subscription"""
        try:
            self.db.table('trainer_subscriptions').update({
                'status': 'cancelled',
                'cancelled_at': datetime.now().isoformat()
            }).eq('trainer_id', trainer_id).execute()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            return {'success': False, 'error': str(e)}