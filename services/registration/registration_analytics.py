#!/usr/bin/env python3
"""
Registration Analytics Service
Provides comprehensive analytics and insights for registration optimization
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error, log_warning

class RegistrationAnalytics:
    """Advanced registration analytics and reporting"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def get_comprehensive_analytics(self, days: int = 30) -> Dict:
        """Get comprehensive registration analytics for the specified period"""
        try:
            # Calculate date range
            end_date = datetime.now(self.sa_tz)
            start_date = end_date - timedelta(days=days)
            
            # Get all analytics data for the period
            result = self.db.table('registration_analytics').select('*').gte(
                'timestamp', start_date.isoformat()
            ).lte('timestamp', end_date.isoformat()).execute()
            
            analytics_data = result.data if result.data else []
            
            # Process comprehensive analytics
            analytics = {
                'period': {
                    'days': days,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'total_events': len(analytics_data)
                },
                'overview': self._calculate_overview_metrics(analytics_data),
                'funnel_analysis': self._analyze_registration_funnel(analytics_data),
                'error_analysis': self._analyze_errors(analytics_data),
                'performance_trends': self._analyze_performance_trends(analytics_data, days),
                'user_behavior': self._analyze_user_behavior(analytics_data),
                'recommendations': []
            }
            
            # Generate optimization recommendations
            analytics['recommendations'] = self._generate_recommendations(analytics)
            
            log_info(f"Generated comprehensive analytics for {days} days: {analytics['overview']['completion_rate']}% completion rate")
            
            return analytics
            
        except Exception as e:
            log_error(f"Error generating comprehensive analytics: {str(e)}")
            return {
                'error': str(e),
                'period': {'days': days, 'total_events': 0}
            }
    
    def _calculate_overview_metrics(self, analytics_data: List[Dict]) -> Dict:
        """Calculate high-level overview metrics"""
        
        overview = {
            'registrations_started': 0,
            'registrations_completed': 0,
            'registrations_abandoned': 0,
            'already_registered_attempts': 0,
            'total_validation_errors': 0,
            'total_system_errors': 0,
            'completion_rate': 0,
            'abandonment_rate': 0,
            'error_rate': 0,
            'unique_users': 0
        }
        
        unique_phones = set()
        started_phones = set()
        completed_phones = set()
        
        for event in analytics_data:
            event_type = event.get('event_type')
            phone = event.get('phone_number')
            
            if phone:
                unique_phones.add(phone)
            
            if event_type == 'started':
                overview['registrations_started'] += 1
                started_phones.add(phone)
            elif event_type == 'completed':
                overview['registrations_completed'] += 1
                completed_phones.add(phone)
            elif event_type == 'abandoned':
                overview['registrations_abandoned'] += 1
            elif event_type == 'already_registered':
                overview['already_registered_attempts'] += 1
            elif event_type == 'validation_error':
                overview['total_validation_errors'] += 1
            elif event_type in ['system_error', 'completion_error']:
                overview['total_system_errors'] += 1
        
        # Calculate rates
        unique_started = len(started_phones)
        unique_completed = len(completed_phones)
        
        if unique_started > 0:
            overview['completion_rate'] = round((unique_completed / unique_started) * 100, 2)
            overview['abandonment_rate'] = round(((unique_started - unique_completed) / unique_started) * 100, 2)
        
        total_events = len(analytics_data)
        if total_events > 0:
            overview['error_rate'] = round(((overview['total_validation_errors'] + overview['total_system_errors']) / total_events) * 100, 2)
        
        overview['unique_users'] = len(unique_phones)
        overview['unique_started'] = unique_started
        overview['unique_completed'] = unique_completed
        
        return overview
    
    def _analyze_registration_funnel(self, analytics_data: List[Dict]) -> Dict:
        """Analyze the registration funnel step by step"""
        
        funnel = {
            'step_completion': {},
            'step_drop_off': {},
            'step_error_rates': {},
            'average_time_per_step': {},
            'bottleneck_steps': []
        }
        
        # Track step completions and errors
        step_events = {}
        step_errors = {}
        
        for event in analytics_data:
            event_type = event.get('event_type')
            step = event.get('step_number')
            
            if step is not None:
                if step not in step_events:
                    step_events[step] = {'completed': 0, 'errors': 0, 'total': 0}
                
                step_events[step]['total'] += 1
                
                if event_type == 'step_completed':
                    step_events[step]['completed'] += 1
                elif event_type == 'validation_error':
                    step_events[step]['errors'] += 1
        
        # Calculate funnel metrics
        total_steps = 7  # Trainer registration has 7 steps
        
        for step in range(total_steps):
            if step in step_events:
                events = step_events[step]
                funnel['step_completion'][step] = events['completed']
                funnel['step_error_rates'][step] = round((events['errors'] / events['total']) * 100, 2) if events['total'] > 0 else 0
            else:
                funnel['step_completion'][step] = 0
                funnel['step_error_rates'][step] = 0
        
        # Calculate drop-off rates
        for step in range(total_steps - 1):
            current_completions = funnel['step_completion'].get(step, 0)
            next_completions = funnel['step_completion'].get(step + 1, 0)
            
            if current_completions > 0:
                drop_off_rate = round(((current_completions - next_completions) / current_completions) * 100, 2)
                funnel['step_drop_off'][step] = drop_off_rate
            else:
                funnel['step_drop_off'][step] = 0
        
        # Identify bottleneck steps (high drop-off or error rates)
        for step in range(total_steps):
            drop_off = funnel['step_drop_off'].get(step, 0)
            error_rate = funnel['step_error_rates'].get(step, 0)
            
            if drop_off > 20 or error_rate > 15:  # Thresholds for bottlenecks
                funnel['bottleneck_steps'].append({
                    'step': step,
                    'drop_off_rate': drop_off,
                    'error_rate': error_rate,
                    'issue_type': 'high_drop_off' if drop_off > 20 else 'high_errors'
                })
        
        return funnel
    
    def _analyze_errors(self, analytics_data: List[Dict]) -> Dict:
        """Analyze validation and system errors"""
        
        error_analysis = {
            'validation_errors': {
                'by_field': {},
                'by_message': {},
                'total_count': 0
            },
            'system_errors': {
                'by_type': {},
                'by_message': {},
                'total_count': 0
            },
            'error_trends': {},
            'most_problematic_fields': []
        }
        
        for event in analytics_data:
            event_type = event.get('event_type')
            error_field = event.get('error_field')
            error_message = event.get('error_message', '')
            
            if event_type == 'validation_error':
                error_analysis['validation_errors']['total_count'] += 1
                
                if error_field:
                    field_count = error_analysis['validation_errors']['by_field'].get(error_field, 0)
                    error_analysis['validation_errors']['by_field'][error_field] = field_count + 1
                
                if error_message:
                    msg_count = error_analysis['validation_errors']['by_message'].get(error_message, 0)
                    error_analysis['validation_errors']['by_message'][error_message] = msg_count + 1
            
            elif event_type in ['system_error', 'completion_error']:
                error_analysis['system_errors']['total_count'] += 1
                
                if error_message:
                    msg_count = error_analysis['system_errors']['by_message'].get(error_message, 0)
                    error_analysis['system_errors']['by_message'][error_message] = msg_count + 1
        
        # Identify most problematic fields
        field_errors = error_analysis['validation_errors']['by_field']
        sorted_fields = sorted(field_errors.items(), key=lambda x: x[1], reverse=True)
        
        for field, count in sorted_fields[:5]:  # Top 5 problematic fields
            error_analysis['most_problematic_fields'].append({
                'field': field,
                'error_count': count,
                'percentage': round((count / error_analysis['validation_errors']['total_count']) * 100, 2) if error_analysis['validation_errors']['total_count'] > 0 else 0
            })
        
        return error_analysis
    
    def _analyze_performance_trends(self, analytics_data: List[Dict], days: int) -> Dict:
        """Analyze performance trends over time"""
        
        trends = {
            'daily_registrations': {},
            'daily_completion_rates': {},
            'daily_error_rates': {},
            'trend_direction': 'stable',
            'performance_summary': {}
        }
        
        # Group events by date
        daily_data = {}
        
        for event in analytics_data:
            timestamp = event.get('timestamp')
            if timestamp:
                try:
                    event_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    date_str = event_date.isoformat()
                    
                    if date_str not in daily_data:
                        daily_data[date_str] = {
                            'started': set(),
                            'completed': set(),
                            'errors': 0,
                            'total_events': 0
                        }
                    
                    daily_data[date_str]['total_events'] += 1
                    
                    event_type = event.get('event_type')
                    phone = event.get('phone_number')
                    
                    if event_type == 'started' and phone:
                        daily_data[date_str]['started'].add(phone)
                    elif event_type == 'completed' and phone:
                        daily_data[date_str]['completed'].add(phone)
                    elif event_type in ['validation_error', 'system_error']:
                        daily_data[date_str]['errors'] += 1
                        
                except Exception as e:
                    log_warning(f"Error parsing timestamp {timestamp}: {str(e)}")
        
        # Calculate daily metrics
        completion_rates = []
        
        for date_str, data in daily_data.items():
            started_count = len(data['started'])
            completed_count = len(data['completed'])
            
            trends['daily_registrations'][date_str] = {
                'started': started_count,
                'completed': completed_count
            }
            
            if started_count > 0:
                completion_rate = (completed_count / started_count) * 100
                trends['daily_completion_rates'][date_str] = round(completion_rate, 2)
                completion_rates.append(completion_rate)
            else:
                trends['daily_completion_rates'][date_str] = 0
            
            if data['total_events'] > 0:
                error_rate = (data['errors'] / data['total_events']) * 100
                trends['daily_error_rates'][date_str] = round(error_rate, 2)
            else:
                trends['daily_error_rates'][date_str] = 0
        
        # Determine trend direction
        if len(completion_rates) >= 3:
            recent_avg = sum(completion_rates[-3:]) / 3
            earlier_avg = sum(completion_rates[:-3]) / len(completion_rates[:-3]) if len(completion_rates) > 3 else recent_avg
            
            if recent_avg > earlier_avg + 5:
                trends['trend_direction'] = 'improving'
            elif recent_avg < earlier_avg - 5:
                trends['trend_direction'] = 'declining'
            else:
                trends['trend_direction'] = 'stable'
        
        return trends
    
    def _analyze_user_behavior(self, analytics_data: List[Dict]) -> Dict:
        """Analyze user behavior patterns"""
        
        behavior = {
            'retry_patterns': {},
            'completion_times': {},
            'peak_registration_hours': {},
            'user_segments': {}
        }
        
        # Analyze retry patterns
        user_attempts = {}
        
        for event in analytics_data:
            phone = event.get('phone_number')
            event_type = event.get('event_type')
            
            if phone and event_type in ['started', 'validation_error', 'completed']:
                if phone not in user_attempts:
                    user_attempts[phone] = {'attempts': 0, 'errors': 0, 'completed': False}
                
                if event_type == 'started':
                    user_attempts[phone]['attempts'] += 1
                elif event_type == 'validation_error':
                    user_attempts[phone]['errors'] += 1
                elif event_type == 'completed':
                    user_attempts[phone]['completed'] = True
        
        # Categorize users by behavior
        single_attempt_success = 0
        multiple_attempt_success = 0
        high_error_users = 0
        
        for phone, data in user_attempts.items():
            if data['completed']:
                if data['attempts'] == 1 and data['errors'] == 0:
                    single_attempt_success += 1
                else:
                    multiple_attempt_success += 1
            
            if data['errors'] > 3:
                high_error_users += 1
        
        behavior['user_segments'] = {
            'single_attempt_success': single_attempt_success,
            'multiple_attempt_success': multiple_attempt_success,
            'high_error_users': high_error_users,
            'total_users': len(user_attempts)
        }
        
        return behavior
    
    def _generate_recommendations(self, analytics: Dict) -> List[Dict]:
        """Generate optimization recommendations based on analytics"""
        
        recommendations = []
        
        overview = analytics.get('overview', {})
        funnel = analytics.get('funnel_analysis', {})
        errors = analytics.get('error_analysis', {})
        
        # Completion rate recommendations
        completion_rate = overview.get('completion_rate', 0)
        
        if completion_rate < 70:
            recommendations.append({
                'type': 'critical',
                'category': 'completion_rate',
                'title': 'Low Completion Rate',
                'description': f'Registration completion rate is {completion_rate}%, which is below the target of 70%.',
                'action': 'Review registration flow for user experience issues and simplify complex steps.',
                'priority': 'high'
            })
        elif completion_rate < 85:
            recommendations.append({
                'type': 'improvement',
                'category': 'completion_rate',
                'title': 'Moderate Completion Rate',
                'description': f'Registration completion rate is {completion_rate}%. There\'s room for improvement.',
                'action': 'Optimize form fields and validation messages for better user experience.',
                'priority': 'medium'
            })
        
        # Error rate recommendations
        error_rate = overview.get('error_rate', 0)
        
        if error_rate > 15:
            recommendations.append({
                'type': 'critical',
                'category': 'error_rate',
                'title': 'High Error Rate',
                'description': f'Error rate is {error_rate}%, indicating significant user friction.',
                'action': 'Review validation logic and improve error messages for clarity.',
                'priority': 'high'
            })
        
        # Bottleneck step recommendations
        bottlenecks = funnel.get('bottleneck_steps', [])
        
        for bottleneck in bottlenecks:
            step = bottleneck['step']
            step_names = ['Name', 'Business', 'Email', 'Specialization', 'Experience', 'Location', 'Pricing']
            step_name = step_names[step] if step < len(step_names) else f'Step {step + 1}'
            
            recommendations.append({
                'type': 'optimization',
                'category': 'funnel_bottleneck',
                'title': f'Bottleneck at {step_name} Step',
                'description': f'{step_name} step has {bottleneck["drop_off_rate"]}% drop-off and {bottleneck["error_rate"]}% error rate.',
                'action': f'Simplify {step_name} field validation and improve user guidance.',
                'priority': 'medium'
            })
        
        # Field-specific recommendations
        problematic_fields = errors.get('most_problematic_fields', [])
        
        for field_data in problematic_fields[:3]:  # Top 3 problematic fields
            field = field_data['field']
            count = field_data['error_count']
            
            recommendations.append({
                'type': 'field_optimization',
                'category': 'validation_errors',
                'title': f'High Error Rate in {field.title()} Field',
                'description': f'{field.title()} field has {count} validation errors ({field_data["percentage"]}% of all validation errors).',
                'action': f'Review {field} field validation rules and improve error messages.',
                'priority': 'medium'
            })
        
        return recommendations
    
    def get_real_time_metrics(self) -> Dict:
        """Get real-time registration metrics for monitoring"""
        try:
            # Get metrics for the last 24 hours
            end_date = datetime.now(self.sa_tz)
            start_date = end_date - timedelta(hours=24)
            
            result = self.db.table('registration_analytics').select('*').gte(
                'timestamp', start_date.isoformat()
            ).execute()
            
            recent_data = result.data if result.data else []
            
            metrics = {
                'last_24_hours': {
                    'total_events': len(recent_data),
                    'registrations_started': 0,
                    'registrations_completed': 0,
                    'validation_errors': 0,
                    'system_errors': 0
                },
                'current_status': 'healthy',
                'alerts': []
            }
            
            # Process recent events
            for event in recent_data:
                event_type = event.get('event_type')
                
                if event_type == 'started':
                    metrics['last_24_hours']['registrations_started'] += 1
                elif event_type == 'completed':
                    metrics['last_24_hours']['registrations_completed'] += 1
                elif event_type == 'validation_error':
                    metrics['last_24_hours']['validation_errors'] += 1
                elif event_type in ['system_error', 'completion_error']:
                    metrics['last_24_hours']['system_errors'] += 1
            
            # Determine system status and generate alerts
            started = metrics['last_24_hours']['registrations_started']
            completed = metrics['last_24_hours']['registrations_completed']
            errors = metrics['last_24_hours']['validation_errors'] + metrics['last_24_hours']['system_errors']
            
            if started > 0:
                completion_rate = (completed / started) * 100
                error_rate = (errors / len(recent_data)) * 100 if recent_data else 0
                
                if completion_rate < 50:
                    metrics['current_status'] = 'critical'
                    metrics['alerts'].append({
                        'type': 'critical',
                        'message': f'Low completion rate: {completion_rate:.1f}% in last 24 hours'
                    })
                elif error_rate > 25:
                    metrics['current_status'] = 'warning'
                    metrics['alerts'].append({
                        'type': 'warning',
                        'message': f'High error rate: {error_rate:.1f}% in last 24 hours'
                    })
            
            return metrics
            
        except Exception as e:
            log_error(f"Error getting real-time metrics: {str(e)}")
            return {
                'error': str(e),
                'current_status': 'unknown',
                'last_24_hours': {}
            }
    
    def generate_analytics_report(self, days: int = 7, format: str = 'summary') -> str:
        """Generate a formatted analytics report"""
        try:
            analytics = self.get_comprehensive_analytics(days)
            
            if format == 'summary':
                return self._generate_summary_report(analytics)
            elif format == 'detailed':
                return self._generate_detailed_report(analytics)
            else:
                return self._generate_summary_report(analytics)
                
        except Exception as e:
            log_error(f"Error generating analytics report: {str(e)}")
            return f"Error generating report: {str(e)}"
    
    def _generate_summary_report(self, analytics: Dict) -> str:
        """Generate a summary analytics report"""
        
        overview = analytics.get('overview', {})
        recommendations = analytics.get('recommendations', [])
        
        report = f"""
📊 **Registration Analytics Summary**
Period: {analytics.get('period', {}).get('days', 0)} days

**Key Metrics:**
• Completion Rate: {overview.get('completion_rate', 0)}%
• Total Started: {overview.get('unique_started', 0)}
• Total Completed: {overview.get('unique_completed', 0)}
• Error Rate: {overview.get('error_rate', 0)}%

**Status:** {'🟢 Healthy' if overview.get('completion_rate', 0) > 80 else '🟡 Needs Attention' if overview.get('completion_rate', 0) > 60 else '🔴 Critical'}

**Top Recommendations:**
"""
        
        for i, rec in enumerate(recommendations[:3], 1):
            priority_emoji = '🔴' if rec['priority'] == 'high' else '🟡' if rec['priority'] == 'medium' else '🟢'
            report += f"{i}. {priority_emoji} {rec['title']}\n   {rec['action']}\n\n"
        
        return report.strip()
    
    def _generate_detailed_report(self, analytics: Dict) -> str:
        """Generate a detailed analytics report"""
        
        # This would be a comprehensive report with all metrics
        # For now, return the summary format
        return self._generate_summary_report(analytics)