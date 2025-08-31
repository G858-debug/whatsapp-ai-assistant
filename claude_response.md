## ANALYSIS
Based on the provided files and requirements, I'll address the key fixes needed for payment integration, assessment module, dashboard features, and error handling. I'll prioritize critical functionality while maintaining security and data integrity.

## FILES TO CHANGE

### FILE: payment_manager.py
```python
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
```

### NEW FILE: services/subscription_manager.py
```python
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
```

## MIGRATION: 20240325_subscription_enhancements.sql
```sql
-- Add subscription management tables

-- Subscription plans
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_monthly DECIMAL(10,2) NOT NULL,
    price_annual DECIMAL(10,2),
    features JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trainer subscriptions
CREATE TABLE trainer_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainer_id UUID REFERENCES trainers(id),
    plan_id UUID REFERENCES subscription_plans(id),
    status VARCHAR(50) NOT NULL,
    payfast_subscription_id VARCHAR(100),
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_trainer_subs_trainer_id ON trainer_subscriptions(trainer_id);
CREATE INDEX idx_trainer_subs_status ON trainer_subscriptions(status);
```

## SUMMARY
Key changes made:
1. Enhanced PaymentManager with complete webhook handling for subscriptions and tokens
2. Added new SubscriptionManager service for plan management
3. Added database migration for subscription-related tables
4. Improved error handling and logging throughout
5. Added signature verification for webhooks
6. Implemented proper token management for saved payment methods

Next steps:
1. Implement assessment module fixes
2. Complete dashboard features
3. Enhance error handling & validation

Let me know if you'd like me to continue with the remaining components.