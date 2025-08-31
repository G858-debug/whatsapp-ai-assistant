from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from utils.logger import log_error, log_info
import json
import pytz
from collections import defaultdict, Counter
import pandas as pd
import numpy as np
import user_agents

class AnalyticsService:
    """Service for tracking and analyzing user behavior and system performance"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.timezone = pytz.timezone('Africa/Johannesburg')
        
    def track_event(self, event_type: str, user_id: str, user_type: str, 
                   metadata: Dict = None, user_agent_string: str = None) -> bool:
        """Track a user event for analytics"""
        try:
            # Parse user agent if provided
            device_info = {}
            if user_agent_string:
                ua = user_agents.parse(user_agent_string)
                device_info = {
                    'is_mobile': ua.is_mobile,
                    'is_tablet': ua.is_tablet,
                    'is_pc': ua.is_pc,
                    'is_bot': ua.is_bot,
                    'browser': ua.browser.family if ua.browser else None,
                    'os': ua.os.family if ua.os else None,
                    'device': ua.device.family if ua.device else None
                }
            
            event_data = {
                'event_type': event_type,
                'user_id': user_id,
                'user_type': user_type,
                'metadata': metadata or {},
                'device_info': device_info,
                'timestamp': datetime.now(self.timezone).isoformat(),
                'created_at': datetime.now().isoformat()
            }
            
            result = self.db.table('analytics_events').insert(event_data).execute()
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error tracking event: {str(e)}")
            return False
    
    def get_trainer_dashboard_metrics(self, trainer_id: str, 
                                     period_days: int = 30) -> Dict:
        """Get comprehensive dashboard metrics for a trainer"""
        try:
            end_date = datetime.now(self.timezone)
            start_date = end_date - timedelta(days=period_days)
            
            metrics = {
                'overview': self._get_overview_metrics(trainer_id, start_date, end_date),
                'revenue': self._get_revenue_metrics(trainer_id, start_date, end_date),
                'clients': self._get_client_metrics(trainer_id, start_date, end_date),
                'sessions': self._get_session_metrics(trainer_id, start_date, end_date),
                'engagement': self._get_engagement_metrics(trainer_id, start_date, end_date),
                'trends': self._get_trend_data(trainer_id, start_date, end_date)
            }
            
            return metrics
            
        except Exception as e:
            log_error(f"Error getting dashboard metrics: {str(e)}")
            return {}
    
    def _get_overview_metrics(self, trainer_id: str, start_date: datetime, 
                             end_date: datetime) -> Dict:
        """Get overview metrics"""
        try:
            # Total active clients
            active_clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).eq('status', 'active').execute()
            
            # Sessions this period
            sessions = self.db.table('bookings').select('*').eq(
                'trainer_id', trainer_id
            ).gte('session_date', start_date.date().isoformat()).lte(
                'session_date', end_date.date().isoformat()
            ).execute()
            
            completed_sessions = [s for s in sessions.data if s.get('status') == 'completed']
            
            # Revenue this period
            payments = self.db.table('payments').select('amount').eq(
                'trainer_id', trainer_id
            ).eq('status', 'completed').gte(
                'payment_date', start_date.isoformat()
            ).lte('payment_date', end_date.isoformat()).execute()
            
            total_revenue = sum(p['amount'] for p in payments.data) if payments.data else 0
            
            return {
                'active_clients': len(active_clients.data) if active_clients.data else 0,
                'total_sessions': len(sessions.data) if sessions.data else 0,
                'completed_sessions': len(completed_sessions),
                'completion_rate': (len(completed_sessions) / len(sessions.data) * 100) if sessions.data else 0,
                'total_revenue': total_revenue,
                'average_session_value': total_revenue / len(completed_sessions) if completed_sessions else 0
            }
            
        except Exception as e:
            log_error(f"Error getting overview metrics: {str(e)}")
            return {}
    
    def _get_revenue_metrics(self, trainer_id: str, start_date: datetime, 
                            end_date: datetime) -> Dict:
        """Get revenue metrics"""
        try:
            # Get all payments
            payments = self.db.table('payments').select('*').eq(
                'trainer_id', trainer_id
            ).gte('payment_date', start_date.isoformat()).lte(
                'payment_date', end_date.isoformat()
            ).execute()
            
            if not payments.data:
                return {
                    'total': 0,
                    'by_status': {},
                    'by_type': {},
                    'outstanding': 0,
                    'growth_rate': 0
                }
            
            # Group by status
            by_status = defaultdict(float)
            by_type = defaultdict(float)
            
            for payment in payments.data:
                by_status[payment.get('status', 'unknown')] += payment.get('amount', 0)
                by_type[payment.get('payment_type', 'unknown')] += payment.get('amount', 0)
            
            # Calculate growth rate
            mid_date = start_date + (end_date - start_date) / 2
            first_half = sum(p['amount'] for p in payments.data 
                           if datetime.fromisoformat(p['payment_date']) < mid_date)
            second_half = sum(p['amount'] for p in payments.data 
                            if datetime.fromisoformat(p['payment_date']) >= mid_date)
            
            growth_rate = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
            
            return {
                'total': sum(p['amount'] for p in payments.data if p.get('status') == 'completed'),
                'by_status': dict(by_status),
                'by_type': dict(by_type),
                'outstanding': by_status.get('pending', 0) + by_status.get('overdue', 0),
                'growth_rate': round(growth_rate, 2)
            }
            
        except Exception as e:
            log_error(f"Error getting revenue metrics: {str(e)}")
            return {}
    
    def _get_client_metrics(self, trainer_id: str, start_date: datetime, 
                           end_date: datetime) -> Dict:
        """Get client metrics"""
        try:
            # Get all clients
            clients = self.db.table('clients').select('*').eq(
                'trainer_id', trainer_id
            ).execute()
            
            if not clients.data:
                return {
                    'total': 0,
                    'new_this_period': 0,
                    'retention_rate': 0,
                    'by_status': {},
                    'by_package': {}
                }
            
            # New clients this period
            new_clients = [c for c in clients.data 
                          if datetime.fromisoformat(c['created_at']) >= start_date]
            
            # Group by status
            by_status = Counter(c.get('status', 'unknown') for c in clients.data)
            
            # Group by package
            by_package = Counter(c.get('current_package', 'none') for c in clients.data)
            
            # Calculate retention (clients with bookings in both halves of period)
            mid_date = start_date + (end_date - start_date) / 2
            
            bookings = self.db.table('bookings').select('client_id', 'session_date').eq(
                'trainer_id', trainer_id
            ).gte('session_date', start_date.date().isoformat()).lte(
                'session_date', end_date.date().isoformat()
            ).execute()
            
            if bookings.data:
                first_half_clients = set(b['client_id'] for b in bookings.data 
                                        if datetime.fromisoformat(b['session_date']).date() < mid_date.date())
                second_half_clients = set(b['client_id'] for b in bookings.data 
                                         if datetime.fromisoformat(b['session_date']).date() >= mid_date.date())
                
                retained = len(first_half_clients & second_half_clients)
                retention_rate = (retained / len(first_half_clients) * 100) if first_half_clients else 0
            else:
                retention_rate = 0
            
            return {
                'total': len(clients.data),
                'new_this_period': len(new_clients),
                'retention_rate': round(retention_rate, 2),
                'by_status': dict(by_status),
                'by_package': dict(by_package)
            }
            
        except Exception as e:
            log_error(f"Error getting client metrics: {str(e)}")
            return {}
    
    def _get_session_metrics(self, trainer_id: str, start_date: datetime, 
                            end_date: datetime) -> Dict:
        """Get session metrics"""
        try:
            # Get all sessions
            sessions = self.db.table('bookings').select('*').eq(
                'trainer_id', trainer_id
            ).gte('session_date', start_date.date().isoformat()).lte(
                'session_date', end_date.date().isoformat()
            ).execute()
            
            if not sessions.data:
                return {
                    'total': 0,
                    'by_status': {},
                    'by_type': {},
                    'popular_times': [],
                    'cancellation_rate': 0
                }
            
            # Group by status
            by_status = Counter(s.get('status', 'unknown') for s in sessions.data)
            
            # Group by type
            by_type = Counter(s.get('session_type', 'unknown') for s in sessions.data)
            
            # Popular times
            time_counts = Counter()
            for session in sessions.data:
                if 'session_time' in session:
                    hour = datetime.fromisoformat(session['session_time']).hour
                    time_counts[f"{hour:02d}:00"] += 1
            
            popular_times = [{'time': time, 'count': count} 
                           for time, count in time_counts.most_common(5)]
            
            # Cancellation rate
            cancelled = by_status.get('cancelled', 0)
            cancellation_rate = (cancelled / len(sessions.data) * 100) if sessions.data else 0
            
            return {
                'total': len(sessions.data),
                'by_status': dict(by_status),
                'by_type': dict(by_type),
                'popular_times': popular_times,
                'cancellation_rate': round(cancellation_rate, 2)
            }
            
        except Exception as e:
            log_error(f"Error getting session metrics: {str(e)}")
            return {}
    
    def _get_engagement_metrics(self, trainer_id: str, start_date: datetime, 
                               end_date: datetime) -> Dict:
        """Get engagement metrics"""
        try:
            # Get message interactions
            events = self.db.table('analytics_events').select('*').eq(
                'user_type', 'client'
            ).gte('timestamp', start_date.isoformat()).lte(
                'timestamp', end_date.isoformat()
            ).execute()
            
            if not events.data:
                return {
                    'total_interactions': 0,
                    'unique_users': 0,
                    'avg_interactions_per_user': 0,
                    'most_used_features': []
                }
            
            # Filter for this trainer's clients
            clients = self.db.table('clients').select('id').eq(
                'trainer_id', trainer_id
            ).execute()
            
            client_ids = {c['id'] for c in clients.data} if clients.data else set()
            
            trainer_events = [e for e in events.data if e.get('user_id') in client_ids]
            
            if not trainer_events:
                return {
                    'total_interactions': 0,
                    'unique_users': 0,
                    'avg_interactions_per_user': 0,
                    'most_used_features': []
                }
            
            # Calculate metrics
            unique_users = len(set(e['user_id'] for e in trainer_events))
            feature_counts = Counter(e.get('event_type', 'unknown') for e in trainer_events)
            
            return {
                'total_interactions': len(trainer_events),
                'unique_users': unique_users,
                'avg_interactions_per_user': round(len(trainer_events) / unique_users, 2) if unique_users > 0 else 0,
                'most_used_features': [
                    {'feature': feature, 'count': count}
                    for feature, count in feature_counts.most_common(5)
                ]
            }
            
        except Exception as e:
            log_error(f"Error getting engagement metrics: {str(e)}")
            return {}
    
    def _get_trend_data(self, trainer_id: str, start_date: datetime, 
                       end_date: datetime) -> Dict:
        """Get trend data for charts"""
        try:
            # Daily revenue trend
            payments = self.db.table('payments').select('amount', 'payment_date').eq(
                'trainer_id', trainer_id
            ).eq('status', 'completed').gte(
                'payment_date', start_date.isoformat()
            ).lte('payment_date', end_date.isoformat()).execute()
            
            # Daily sessions trend
            sessions = self.db.table('bookings').select('session_date', 'status').eq(
                'trainer_id', trainer_id
            ).gte('session_date', start_date.date().isoformat()).lte(
                'session_date', end_date.date().isoformat()
            ).execute()
            
            # Create daily aggregates
            days = pd.date_range(start=start_date.date(), end=end_date.date(), freq='D')
            
            revenue_by_day = defaultdict(float)
            sessions_by_day = defaultdict(int)
            
            for payment in (payments.data or []):
                day = datetime.fromisoformat(payment['payment_date']).date()
                revenue_by_day[day.isoformat()] += payment['amount']
            
            for session in (sessions.data or []):
                if session.get('status') == 'completed':
                    sessions_by_day[session['session_date']] += 1
            
            # Format for charts
            revenue_trend = [
                {
                    'date': day.isoformat(),
                    'revenue': revenue_by_day.get(day.isoformat(), 0)
                }
                for day in days
            ]
            
            session_trend = [
                {
                    'date': day.isoformat(),
                    'sessions': sessions_by_day.get(day.isoformat(), 0)
                }
                for day in days
            ]
            
            return {
                'revenue': revenue_trend,
                'sessions': session_trend
            }
            
        except Exception as e:
            log_error(f"Error getting trend data: {str(e)}")
            return {'revenue': [], 'sessions': []}
    
    def generate_client_report(self, client_id: str, period_days: int = 30) -> Dict:
        """Generate a progress report for a client"""
        try:
            end_date = datetime.now(self.timezone)
            start_date = end_date - timedelta(days=period_days)
            
            # Get client info
            client = self.db.table('clients').select('*').eq(
                'id', client_id
            ).single().execute()
            
            if not client.data:
                return {'error': 'Client not found'}
            
            # Get sessions
            sessions = self.db.table('bookings').select('*').eq(
                'client_id', client_id
            ).gte('session_date', start_date.date().isoformat()).lte(
                'session_date', end_date.date().isoformat()
            ).execute()
            
            completed_sessions = [s for s in (sessions.data or []) 
                                if s.get('status') == 'completed']
            
            # Get assessments
            assessments = self.db.table('fitness_assessments').select('*').eq(
                'client_id', client_id
            ).gte('created_at', start_date.isoformat()).execute()
            
            # Get habit tracking
            habits = self.db.table('habit_tracking').select('*').eq(
                'client_id', client_id
            ).gte('date', start_date.date().isoformat()).execute()
            
            # Calculate metrics
            total_sessions = len(sessions.data) if sessions.data else 0
            attendance_rate = (len(completed_sessions) / total_sessions * 100) if total_sessions > 0 else 0
            
            # Habit compliance
            if habits.data:
                total_habits = len(habits.data)
                completed_habits = len([h for h in habits.data if h.get('completed')])
                habit_compliance = (completed_habits / total_habits * 100) if total_habits > 0 else 0
            else:
                habit_compliance = 0
            
            return {
                'client': {
                    'name': client.data.get('name'),
                    'joined_date': client.data.get('created_at')
                },
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': period_days
                },
                'sessions': {
                    'total': total_sessions,
                    'completed': len(completed_sessions),
                    'attendance_rate': round(attendance_rate, 2)
                },
                'assessments': {
                    'completed': len(assessments.data) if assessments.data else 0,
                    'latest': assessments.data[0] if assessments.data else None
                },
                'habits': {
                    'compliance_rate': round(habit_compliance, 2),
                    'total_tracked': len(habits.data) if habits.data else 0
                }
            }
            
        except Exception as e:
            log_error(f"Error generating client report: {str(e)}")
            return {'error': str(e)}
    
    def track_message_interaction(self, phone_number: str, message_type: str, 
                                 intent: str = None, response_time_ms: int = None):
        """Track WhatsApp message interactions"""
        try:
            # Identify user
            user_type = None
            user_id = None
            
            # Check if trainer
            trainer = self.db.table('trainers').select('id').eq(
                'phone_number', phone_number
            ).single().execute()
            
            if trainer.data:
                user_type = 'trainer'
                user_id = trainer.data['id']
            else:
                # Check if client
                client = self.db.table('clients').select('id').eq(
                    'phone_number', phone_number
                ).single().execute()
                
                if client.data:
                    user_type = 'client'
                    user_id = client.data['id']
            
            if user_id:
                metadata = {
                    'message_type': message_type,
                    'intent': intent,
                    'response_time_ms': response_time_ms
                }
                
                self.track_event('message_interaction', user_id, user_type, metadata)
                
        except Exception as e:
            log_error(f"Error tracking message interaction: {str(e)}")