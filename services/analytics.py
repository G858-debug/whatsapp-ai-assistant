# services/analytics.py
# Analytics service for tracking dashboard usage

import json
import uuid
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, List
import user_agents
from utils.logger import log_info, log_error

class AnalyticsService:
    """Track and analyze dashboard usage"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
    
    def track_event(self, trainer_id: str, event_data: Dict) -> bool:
        """Track a single analytics event"""
        try:
            # Parse user agent if provided
            device_info = self._parse_device_info(event_data.get('user_agent', ''))
            
            # Create analytics record
            record = {
                'trainer_id': trainer_id,
                'session_id': event_data.get('session_id', str(uuid.uuid4())),
                'event_type': event_data.get('event_type', 'page_view'),
                'event_name': event_data.get('event_name'),
                'event_data': json.dumps(event_data.get('data', {})),
                'page_section': event_data.get('section'),
                'time_on_page': event_data.get('time_on_page'),
                'device_type': device_info['device_type'],
                'browser': device_info['browser'],
                'os': device_info['os'],
                'screen_size': event_data.get('screen_size'),
                'is_pwa': event_data.get('is_pwa', False),
                'load_time_ms': event_data.get('load_time'),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Insert analytics event
            self.db.table('dashboard_analytics').insert(record).execute()
            
            # Update engagement metrics
            self._update_engagement_metrics(trainer_id, event_data)
            
            # Update feature usage if applicable
            if event_data.get('feature'):
                self._update_feature_usage(trainer_id, event_data['feature'])
            
            return True
            
        except Exception as e:
            log_error(f"Error tracking analytics: {str(e)}")
            return False
    
    def track_page_view(self, trainer_id: str, section: str, request_data: Dict) -> bool:
        """Simplified method for tracking page views"""
        return self.track_event(trainer_id, {
            'event_type': 'page_view',
            'event_name': f'view_{section}',
            'section': section,
            'user_agent': request_data.get('user_agent'),
            'screen_size': request_data.get('screen_size'),
            'is_pwa': request_data.get('is_pwa', False),
            'session_id': request_data.get('session_id')
        })
    
    def track_feature_use(self, trainer_id: str, feature: str, details: Dict = None) -> bool:
        """Track when a specific feature is used"""
        return self.track_event(trainer_id, {
            'event_type': 'feature_use',
            'event_name': feature,
            'feature': feature,
            'data': details or {}
        })
    
    def get_trainer_analytics(self, trainer_id: str, days: int = 30) -> Dict:
        """Get analytics summary for a trainer"""
        try:
            cutoff = (datetime.now(self.sa_tz) - timedelta(days=days)).isoformat()
            
            # Get engagement metrics
            engagement = self.db.table('engagement_metrics').select('*').eq(
                'trainer_id', trainer_id
            ).execute()
            
            # Get recent events
            events = self.db.table('dashboard_analytics').select('*').eq(
                'trainer_id', trainer_id
            ).gte('created_at', cutoff).order('created_at', desc=True).execute()
            
            # Get feature usage
            features = self.db.table('feature_usage').select('*').eq(
                'trainer_id', trainer_id
            ).order('usage_count', desc=True).execute()
            
            # Calculate insights
            insights = self._calculate_insights(events.data if events.data else [])
            
            return {
                'engagement': engagement.data[0] if engagement.data else {},
                'recent_activity': self._format_recent_activity(events.data[:10] if events.data else []),
                'feature_usage': features.data if features.data else [],
                'insights': insights,
                'period_days': days
            }
            
        except Exception as e:
            log_error(f"Error getting analytics: {str(e)}")
            return {}
    
    def get_global_analytics(self) -> Dict:
        """Get system-wide analytics (admin view)"""
        try:
            # Daily active users
            dau = self.db.from_('daily_active_users').select('*').limit(30).execute()
            
            # Feature popularity
            features = self.db.from_('feature_popularity').select('*').execute()
            
            # Engagement summary
            engagement = self.db.from_('trainer_engagement_summary').select('*').limit(100).execute()
            
            return {
                'daily_active_users': dau.data if dau.data else [],
                'feature_popularity': features.data if features.data else [],
                'trainer_engagement': engagement.data if engagement.data else [],
                'summary': self._calculate_global_summary()
            }
            
        except Exception as e:
            log_error(f"Error getting global analytics: {str(e)}")
            return {}
    
    def _parse_device_info(self, user_agent_string: str) -> Dict:
        """Parse user agent to get device info"""
        try:
            ua = user_agents.parse(user_agent_string)
            
            if ua.is_mobile:
                device_type = 'mobile'
            elif ua.is_tablet:
                device_type = 'tablet'
            else:
                device_type = 'desktop'
            
            return {
                'device_type': device_type,
                'browser': ua.browser.family,
                'os': ua.os.family,
                'is_mobile': ua.is_mobile
            }
        except:
            return {
                'device_type': 'unknown',
                'browser': 'unknown',
                'os': 'unknown',
                'is_mobile': False
            }
    
    def _update_engagement_metrics(self, trainer_id: str, event_data: Dict):
        """Update or create engagement metrics"""
        try:
            # Check if metrics exist
            existing = self.db.table('engagement_metrics').select('*').eq(
                'trainer_id', trainer_id
            ).execute()
            
            now = datetime.now(self.sa_tz)
            hour = now.hour
            
            if hour < 6:
                time_period = 'night'
            elif hour < 12:
                time_period = 'morning'
            elif hour < 18:
                time_period = 'afternoon'
            else:
                time_period = 'evening'
            
            if existing.data:
                # Update existing
                metrics = existing.data[0]
                
                # Calculate consecutive days
                last_visit = datetime.fromisoformat(metrics['last_visit'].replace('Z', '+00:00'))
                last_visit = last_visit.astimezone(self.sa_tz)
                days_diff = (now.date() - last_visit.date()).days
                
                if days_diff == 1:
                    consecutive = metrics.get('consecutive_days', 0) + 1
                elif days_diff == 0:
                    consecutive = metrics.get('consecutive_days', 1)
                else:
                    consecutive = 1
                
                updates = {
                    'total_sessions': metrics['total_sessions'] + 1,
                    'total_page_views': metrics['total_page_views'] + 1,
                    'last_visit': now.date().isoformat(),
                    'consecutive_days': consecutive,
                    'preferred_time': time_period,
                    'updated_at': now.isoformat()
                }
                
                if event_data.get('is_pwa'):
                    updates['opens_from_pwa'] = metrics.get('opens_from_pwa', 0) + 1
                
                self.db.table('engagement_metrics').update(updates).eq(
                    'trainer_id', trainer_id
                ).execute()
                
            else:
                # Create new
                self.db.table('engagement_metrics').insert({
                    'trainer_id': trainer_id,
                    'total_sessions': 1,
                    'total_page_views': 1,
                    'first_visit': now.date().isoformat(),
                    'last_visit': now.date().isoformat(),
                    'days_active': 1,
                    'consecutive_days': 1,
                    'preferred_time': time_period,
                    'preferred_device': event_data.get('device_type', 'unknown'),
                    'installed_pwa': event_data.get('is_pwa', False)
                }).execute()
                
        except Exception as e:
            log_error(f"Error updating engagement: {str(e)}")
    
    def _update_feature_usage(self, trainer_id: str, feature_name: str):
        """Update feature usage statistics"""
        try:
            # Check if exists
            existing = self.db.table('feature_usage').select('*').eq(
                'trainer_id', trainer_id
            ).eq('feature_name', feature_name).execute()
            
            if existing.data:
                # Update
                current = existing.data[0]
                self.db.table('feature_usage').update({
                    'usage_count': current['usage_count'] + 1,
                    'last_used': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }).eq('id', current['id']).execute()
            else:
                # Create
                self.db.table('feature_usage').insert({
                    'trainer_id': trainer_id,
                    'feature_name': feature_name,
                    'usage_count': 1,
                    'last_used': datetime.now(self.sa_tz).isoformat()
                }).execute()
                
        except Exception as e:
            log_error(f"Error updating feature usage: {str(e)}")
    
    def _calculate_insights(self, events: List[Dict]) -> Dict:
        """Calculate actionable insights from events"""
        if not events:
            return {'status': 'No data yet'}
        
        insights = {}
        
        # Most active time
        hours = [datetime.fromisoformat(e['created_at'].replace('Z', '+00:00')).hour 
                for e in events]
        if hours:
            most_common_hour = max(set(hours), key=hours.count)
            if most_common_hour < 12:
                insights['best_time'] = f"You're most active in the morning (around {most_common_hour}:00)"
            elif most_common_hour < 18:
                insights['best_time'] = f"You're most active in the afternoon (around {most_common_hour}:00)"
            else:
                insights['best_time'] = f"You're most active in the evening (around {most_common_hour}:00)"
        
        # Most viewed section
        sections = [e.get('page_section') for e in events if e.get('page_section')]
        if sections:
            top_section = max(set(sections), key=sections.count)
            insights['focus_area'] = f"You spend most time viewing {top_section}"
        
        # Device preference
        devices = [e.get('device_type') for e in events if e.get('device_type')]
        if devices:
            main_device = max(set(devices), key=devices.count)
            insights['device'] = f"You primarily use {main_device} to access your dashboard"
        
        return insights
    
    def _format_recent_activity(self, events: List[Dict]) -> List[Dict]:
        """Format recent activity for display"""
        formatted = []
        for event in events:
            timestamp = datetime.fromisoformat(event['created_at'].replace('Z', '+00:00'))
            formatted.append({
                'time': timestamp.strftime('%d %b %H:%M'),
                'type': event['event_type'],
                'name': event['event_name'],
                'section': event.get('page_section', 'dashboard')
            })
        return formatted
    
    def _calculate_global_summary(self) -> Dict:
        """Calculate system-wide summary stats"""
        try:
            # Total trainers using dashboard
            total_users = self.db.table('engagement_metrics').select(
                'count', count='exact'
            ).execute()
            
            # Active in last 7 days
            week_ago = (datetime.now(self.sa_tz) - timedelta(days=7)).isoformat()
            active_users = self.db.table('engagement_metrics').select(
                'count', count='exact'
            ).gte('last_visit', week_ago).execute()
            
            # PWA installs
            pwa_users = self.db.table('engagement_metrics').select(
                'count', count='exact'
            ).eq('installed_pwa', True).execute()
            
            return {
                'total_users': total_users.count if total_users else 0,
                'active_users_7d': active_users.count if active_users else 0,
                'pwa_installs': pwa_users.count if pwa_users else 0,
                'adoption_rate': f"{(pwa_users.count / total_users.count * 100):.1f}%" 
                                if total_users and total_users.count > 0 else "0%"
            }
            
        except Exception as e:
            log_error(f"Error calculating summary: {str(e)}")
            return {}
