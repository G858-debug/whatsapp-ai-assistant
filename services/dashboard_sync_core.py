"""Core dashboard synchronization functionality"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
import secrets
from utils.logger import log_error, log_info, log_warning

class DashboardSyncCore:
    """Core synchronization between dashboard and WhatsApp"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.dashboard_base_url = config.DASHBOARD_URL if hasattr(config, 'DASHBOARD_URL') else 'https://refiloe.ai/dashboard'
        
        # Cache for user preferences
        self.preference_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def generate_deep_link(self, page: str, user_id: str, user_type: str, 
                          token: str = None, params: Dict = None) -> str:
        """Generate specific dashboard URLs for WhatsApp messages"""
        if not token:
            token = self._generate_dashboard_token(user_id, user_type)
        
        if page == 'challenges':
            url = f"{self.dashboard_base_url}/challenges"
        elif page == 'challenge':
            challenge_id = params.get('challenge_id') if params else None
            url = f"{self.dashboard_base_url}/challenges/{challenge_id}" if challenge_id else f"{self.dashboard_base_url}/challenges"
        elif page == 'leaderboard':
            highlight = params.get('highlight') if params else user_id
            url = f"{self.dashboard_base_url}/leaderboard?highlight={highlight}"
        elif page == 'pre-book':
            challenge_id = params.get('challenge_id') if params else None
            url = f"{self.dashboard_base_url}/pre-book/{challenge_id}" if challenge_id else f"{self.dashboard_base_url}/challenges"
        elif page == 'stats':
            url = f"{self.dashboard_base_url}/stats"
        else:
            url = self.dashboard_base_url
        
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}token={token}"
        
        return url
    
    def _generate_dashboard_token(self, user_id: str, user_type: str) -> str:
        """Generate secure token for dashboard access"""
        try:
            existing = self.db.table('dashboard_tokens').select('*').eq(
                f'{user_type}_id', user_id
            ).eq('is_valid', True).execute()
            
            if existing.data:
                created_at = datetime.fromisoformat(existing.data[0]['created_at'])
                if (datetime.now(pytz.UTC) - created_at).total_seconds() < 86400:
                    return existing.data[0]['token']
            
            token = secrets.token_urlsafe(32)
            
            if user_type == 'trainer':
                token_data = {'trainer_id': user_id}
            else:
                token_data = {'client_id': user_id}
            
            token_data.update({
                'token': token,
                'is_valid': True,
                'created_at': datetime.now(pytz.UTC).isoformat()
            })
            
            self.db.table('dashboard_tokens').insert(token_data).execute()
            
            return token
            
        except Exception as e:
            log_error(f"Error generating dashboard token: {str(e)}")
            return secrets.token_urlsafe(32)
    
    def get_cached_preferences(self, user_id: str, user_type: str) -> Optional[Dict]:
        """Get cached user preferences to reduce database calls"""
        cache_key = f"{user_type}:{user_id}"
        
        if cache_key in self.preference_cache:
            cached = self.preference_cache[cache_key]
            if (datetime.now() - cached['cached_at']).total_seconds() < self.cache_ttl:
                return cached['data']
        
        try:
            profile = self.db.table('gamification_profiles').select('*').eq(
                f'{user_type}_id', user_id
            ).single().execute()
            
            if profile.data:
                self.preference_cache[cache_key] = {
                    'data': profile.data,
                    'cached_at': datetime.now()
                }
                return profile.data
                
        except Exception as e:
            log_error(f"Error loading preferences: {str(e)}")
        
        return None
    
    def get_user_phone(self, user_id: str, user_type: str) -> Optional[str]:
        """Get user's WhatsApp phone number"""
        try:
            if user_type == 'trainer':
                result = self.db.table('trainers').select('whatsapp').eq(
                    'id', user_id
                ).single().execute()
            else:
                result = self.db.table('clients').select('whatsapp').eq(
                    'id', user_id
                ).single().execute()
            
            return result.data.get('whatsapp') if result.data else None
            
        except Exception as e:
            log_error(f"Error getting user phone: {str(e)}")
            return None
    
    def trigger_dashboard_update(self, user_id: str, user_type: str, action: str):
        """Trigger dashboard update"""
        try:
            log_info(f"Dashboard update triggered for {user_type} {user_id}: {action}")
            
            self.db.table('dashboard_updates').insert({
                'user_id': user_id,
                'user_type': user_type,
                'action': action,
                'created_at': datetime.now(self.sa_tz).isoformat()
            }).execute()
            
        except Exception as e:
            log_error(f"Error triggering dashboard update: {str(e)}")
    
    def get_next_digest_time(self, user_id: str, user_type: str) -> datetime:
        """Get next digest time for user"""
        prefs = self.get_cached_preferences(user_id, user_type)
        
        if prefs:
            digest_time = prefs.get('digest_time', '07:00')
        else:
            digest_time = '07:00'
        
        hour, minute = map(int, digest_time.split(':'))
        
        now = datetime.now(self.sa_tz)
        next_digest = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_digest <= now:
            next_digest += timedelta(days=1)
        
        return next_digest