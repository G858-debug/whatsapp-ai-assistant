from flask import Blueprint, render_template, jsonify, request, send_file
import secrets
import hashlib
from datetime import datetime, timedelta
import pytz
import json
from typing import Dict, Optional
import io
import csv

from models.trainer import TrainerModel
from models.client import ClientModel  
from models.booking import BookingModel
from utils.logger import log_info, log_error

# Create Blueprint
dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates')

class DashboardService:
    """Handle keep-alive dashboard links"""
    
    def __init__(self, config, supabase_client):
        self.config = config
        self.db = supabase_client
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        self.trainer_model = TrainerModel(supabase_client, config)
        self.client_model = ClientModel(supabase_client, config)
        self.booking_model = BookingModel(supabase_client, config)
        
        # Keep-alive configuration
        self.INACTIVE_DAYS = 30  # Links expire after 30 days of no use
        self.EXTEND_DAYS = 30    # Each click extends by 30 days
    
    def generate_dashboard_link(self, trainer_id: str) -> Dict:
        """Generate or retrieve permanent dashboard link"""
        try:
            # Check for existing link
            result = self.db.table('dashboard_links').select('*').eq(
                'trainer_id', trainer_id
            ).eq('is_active', True).execute()
            
            if result.data:
                # Return existing link
                link_data = result.data[0]
                dashboard_url = self._build_url(link_data['short_code'])
                
                # Check how long since last access
                last_accessed = datetime.fromisoformat(link_data['last_accessed'].replace('Z', '+00:00'))
                last_accessed = last_accessed.astimezone(self.sa_tz)
                days_ago = (datetime.now(self.sa_tz) - last_accessed).days
                
                # Personalize message based on usage
                access_count = link_data.get('access_count', 0)
                
                if days_ago == 0:
                    message = f"📊 Your dashboard: {dashboard_url}"
                elif days_ago < 7:
                    message = f"📊 Welcome back! Your dashboard:\n\n{dashboard_url}"
                else:
                    message = f"📊 Your dashboard is ready:\n\n{dashboard_url}"
                
                # Add helpful tip for new users
                if access_count < 3:
                    message += "\n\n💡 Tip: Save this link - it's yours to keep!"
                elif access_count < 10:
                    message += "\n\n📌 This is your permanent dashboard link"
                
                log_info(f"Returned existing link for trainer {trainer_id}")
                
                return {
                    'success': True,
                    'url': dashboard_url,
                    'message': message
                }
            
            else:
                # Create new permanent link
                short_code = self._generate_short_code()
                
                # Store in database
                self.db.table('dashboard_links').insert({
                    'trainer_id': trainer_id,
                    'short_code': short_code,
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'last_accessed': datetime.now(self.sa_tz).isoformat(),
                    'expires_at': (datetime.now(self.sa_tz) + timedelta(days=self.EXTEND_DAYS)).isoformat(),
                    'access_count': 0,
                    'is_active': True
                }).execute()
                
                dashboard_url = self._build_url(short_code)
                
                log_info(f"Created new permanent link for trainer {trainer_id}")
                
                return {
                    'success': True,
                    'url': dashboard_url,
                    'message': f"""📊 Your permanent dashboard is ready!

{dashboard_url}

✨ This is YOUR link"""
                }
                
        except Exception as e:
            log_error(f"Error generating dashboard link: {str(e)}")
            # Fallback to simple temporary link
            return self._generate_fallback_link(trainer_id)
    
    def validate_token(self, token: str) -> Optional[str]:
        """Validate link and refresh expiry (keep-alive mechanism)"""
        try:
            # Try to find by short_code (new system)
            result = self.db.table('dashboard_links').select('*').eq(
                'short_code', token
            ).eq('is_active', True).execute()
            
            if not result.data:
                # Maybe it's an old-style token, check dashboard_tokens table if it exists
                return self._check_old_token(token)
            
            link_data = result.data[0]
            expires_at = datetime.fromisoformat(link_data['expires_at'].replace('Z', '+00:00'))
            expires_at = expires_at.astimezone(self.sa_tz)
            
            # Check if expired (only after 30 days of no use)
            if datetime.now(self.sa_tz) > expires_at:
                # Mark as inactive
                self.db.table('dashboard_links').update({
                    'is_active': False
                }).eq('id', link_data['id']).execute()
                
                log_info(f"Link expired for trainer {link_data['trainer_id']} - not used for 30 days")
                return None
            
            # KEEP-ALIVE: Extend expiry by 30 days from NOW
            new_expiry = datetime.now(self.sa_tz) + timedelta(days=self.EXTEND_DAYS)
            
            # Update last accessed and extend expiry
            self.db.table('dashboard_links').update({
                'last_accessed': datetime.now(self.sa_tz).isoformat(),
                'expires_at': new_expiry.isoformat(),
                'access_count': link_data.get('access_count', 0) + 1
            }).eq('id', link_data['id']).execute()
            
            log_info(f"Link accessed and extended for trainer {link_data['trainer_id']}")
            
            return link_data['trainer_id']
            
        except Exception as e:
            log_error(f"Error validating token: {str(e)}")
            return None
    
    def _generate_short_code(self) -> str:
        """Generate a short, memorable code"""
        # Generate 6-character code (enough for millions of trainers)
        code = secrets.token_urlsafe(6)[:6]
        
        # Make sure it's unique
        result = self.db.table('dashboard_links').select('id').eq(
            'short_code', code
        ).execute()
        
        if result.data:
            # Collision (very rare), try again
            return self._generate_short_code()
        
        return code
    
    def _build_url(self, short_code: str) -> str:
        """Build the dashboard URL"""
        base_url = self.config.DASHBOARD_BASE_URL if hasattr(self.config, 'DASHBOARD_BASE_URL') else 'https://web-production-26de5.up.railway.app'
        return f"{base_url}/d/{short_code}"
    
    def _generate_fallback_link(self, trainer_id: str) -> Dict:
        """Fallback for when database fails"""
        code = secrets.token_urlsafe(6)[:6]
        url = self._build_url(code)
        
        return {
            'success': True,
            'url': url,
            'message': f"""📊 Dashboard ready!

{url}

(Temporary link - expires in 24 hours)"""
        }
    
    def _check_old_token(self, token: str) -> Optional[str]:
        """Check if this is an old-style token from the previous system"""
        try:
            # Check if dashboard_tokens table exists (old system)
            result = self.db.table('dashboard_tokens').select('*').eq(
                'token', token
            ).execute()
            
            if result.data:
                token_data = result.data[0]
                expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
                expires_at = expires_at.astimezone(self.sa_tz)
                
                if datetime.now(self.sa_tz) < expires_at:
                    return token_data['trainer_id']
        except:
            # Table doesn't exist or other error - that's fine
            pass
        
        return None
    
    def get_dashboard_data(self, trainer_id: str) -> Dict:
        """Get all data needed for dashboard"""
        try:
            now = datetime.now(self.sa_tz)
            
            # Get trainer info
            trainer = self.trainer_model.get_by_id(trainer_id)
            if not trainer:
                return None
            
            # Get stats
            stats = self.get_trainer_stats(trainer_id)
            
            # Get today's sessions
            today_start = now.replace(hour=0, minute=0, second=0)
            today_end = today_start + timedelta(days=1)
            today_sessions = self.booking_model.get_trainer_schedule(
                trainer_id, today_start, today_end
            )
            
            # Get week sessions
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=7)
            week_sessions = self.booking_model.get_trainer_schedule(
                trainer_id, week_start, week_end
            )
            
            # Get clients
            clients = self.client_model.get_trainer_clients(trainer_id)
            
            # Process clients for display
            for client in clients:
                if client.get('last_session_date'):
                    last_date = datetime.fromisoformat(client['last_session_date'])
                    days_ago = (now - last_date).days
                    if days_ago == 0:
                        client['last_session_display'] = 'Today'
                    elif days_ago == 1:
                        client['last_session_display'] = 'Yesterday'
                    else:
                        client['last_session_display'] = f'{days_ago} days ago'
                else:
                    client['last_session_display'] = 'Never'
            
            # Get availability
            settings = trainer.get('settings', {})
            if isinstance(settings, str):
                settings = json.loads(settings)
            availability = settings.get('availability', self.config.get_booking_slots())
            
            # Calculate revenue
            revenue = self.calculate_revenue(trainer_id)
            
            # Format week calendar
            week_days = []
            for i in range(7):
                day_date = week_start + timedelta(days=i)
                day_sessions = [s for s in week_sessions 
                               if datetime.fromisoformat(s['session_datetime']).date() == day_date.date()]
                
                week_days.append({
                    'date': day_date.day,
                    'is_today': day_date.date() == now.date(),
                    'has_sessions': len(day_sessions) > 0,
                    'session_count': len(day_sessions)
                })
            
            # Format sessions for display
            formatted_today_sessions = []
            for session in today_sessions:
                session_time = datetime.fromisoformat(session['session_datetime'])
                formatted_today_sessions.append({
                    'client_name': session.get('clients', {}).get('name', 'Unknown'),
                    'time': session_time.strftime('%I:%M %p'),
                    'duration': session.get('duration_minutes', 60),
                    'price': session.get('price', 0),
                    'status': 'confirmed' if session.get('status') == 'scheduled' else session.get('status', 'pending')
                })
            
            formatted_week_sessions = []
            for session in week_sessions:
                session_time = datetime.fromisoformat(session['session_datetime'])
                formatted_week_sessions.append({
                    'day': session_time.strftime('%a'),
                    'client_name': session.get('clients', {}).get('name', 'Unknown'),
                    'time': session_time.strftime('%I:%M %p'),
                    'duration': session.get('duration_minutes', 60)
                })
            
            return {
                'trainer': trainer,
                'stats': stats,
                'today_sessions': formatted_today_sessions,
                'week_sessions': formatted_week_sessions,
                'week_days': week_days,
                'clients': clients,
                'revenue': revenue,
                'availability': availability,
                'settings': {
                    'session_duration': trainer.get('default_session_duration', 60),
                    'price_per_session': trainer.get('pricing_per_session', 300)
                },
                'current_date': now.strftime('%A, %d %B %Y'),
                'recent_payments': []  # TODO: Implement when payment tracking is added
            }
            
        except Exception as e:
            log_error(f"Error getting dashboard data: {str(e)}")
            return None
    
    def get_trainer_stats(self, trainer_id: str) -> Dict:
        """Calculate trainer statistics"""
        try:
            now = datetime.now(self.sa_tz)
            
            # Today's sessions
            today_start = now.replace(hour=0, minute=0, second=0)
            today_end = today_start + timedelta(days=1)
            today_sessions = self.booking_model.get_trainer_schedule(
                trainer_id, today_start, today_end
            )
            
            # This week's sessions
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=7)
            week_sessions = self.booking_model.get_trainer_schedule(
                trainer_id, week_start, week_end
            )
            
            # This month's revenue
            month_start = now.replace(day=1, hour=0, minute=0, second=0)
            month_sessions = self.booking_model.get_trainer_schedule(
                trainer_id, month_start, now
            )
            monthly_revenue = sum(s.get('price', 0) for s in month_sessions)
            
            # Active clients
            clients = self.client_model.get_trainer_clients(trainer_id)
            
            return {
                'today_sessions': len(today_sessions),
                'weekly_sessions': len(week_sessions),
                'monthly_revenue': f"{monthly_revenue:.0f}",
                'active_clients': len(clients)
            }
            
        except Exception as e:
            log_error(f"Error calculating stats: {str(e)}")
            return {
                'today_sessions': 0,
                'weekly_sessions': 0,
                'monthly_revenue': "0",
                'active_clients': 0
            }
    
    def calculate_revenue(self, trainer_id: str) -> Dict:
        """Calculate revenue information"""
        try:
            now = datetime.now(self.sa_tz)
            
            # This month
            month_start = now.replace(day=1, hour=0, minute=0, second=0)
            month_sessions = self.booking_model.get_trainer_schedule(
                trainer_id, month_start, now
            )
            this_month = sum(s.get('price', 0) for s in month_sessions)
            
            # Last month
            last_month_end = month_start - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            last_month_sessions = self.booking_model.get_trainer_schedule(
                trainer_id, last_month_start, last_month_end
            )
            last_month = sum(s.get('price', 0) for s in last_month_sessions)
            
            # Calculate progress (assuming goal of R20000/month)
            monthly_goal = 20000
            progress = min(100, (this_month / monthly_goal) * 100) if monthly_goal > 0 else 0
            
            return {
                'this_month': f"{this_month:.0f}",
                'last_month': f"{last_month:.0f}",
                'outstanding': "0",  # TODO: Implement when payment tracking is added
                'month_progress': f"{progress:.0f}"
            }
            
        except Exception as e:
            log_error(f"Error calculating revenue: {str(e)}")
            return {
                'this_month': "0",
                'last_month': "0",
                'outstanding': "0",
                'month_progress': "0"
            }
    
    def export_trainer_data(self, trainer_id: str, format: str = 'csv') -> Optional[bytes]:
        """Export trainer data in specified format"""
        try:
            # Get all data
            data = self.get_dashboard_data(trainer_id)
            if not data:
                return None
            
            if format == 'csv':
                # Create CSV
                output = io.StringIO()
                
                # Write clients
                writer = csv.writer(output)
                writer.writerow(['CLIENTS REPORT'])
                writer.writerow(['Name', 'Package', 'Sessions Remaining', 'Last Session'])
                
                for client in data['clients']:
                    writer.writerow([
                        client['name'],
                        client.get('package_type', 'Unknown'),
                        client.get('sessions_remaining', 0),
                        client.get('last_session_display', 'Never')
                    ])
                
                writer.writerow([])  # Empty row
                
                # Write this week's sessions
                writer.writerow(['THIS WEEK SESSIONS'])
                writer.writerow(['Day', 'Client', 'Time', 'Duration'])
                
                for session in data['week_sessions']:
                    writer.writerow([
                        session['day'],
                        session['client_name'],
                        session['time'],
                        f"{session['duration']} min"
                    ])
                
                # Get the string value and convert to bytes
                csv_string = output.getvalue()
                return csv_string.encode('utf-8')
            
            return None
            
        except Exception as e:
            log_error(f"Error exporting data: {str(e)}")
            return None
    
    def get_client_assessment_dashboard_data(self, client_id: str) -> Dict:
        """Get comprehensive assessment data for client dashboard"""
        try:
            # Get all assessments for progress tracking
            assessments = self.db.table('fitness_assessments').select(
                '''*, 
                physical_measurements(*),
                fitness_goals(*),
                fitness_test_results(*),
                assessment_photos(*)'''
            ).eq('client_id', client_id).eq('status', 'completed').order(
                'assessment_date', desc=True
            ).execute()
            
            if not assessments.data:
                return None
            
            latest = assessments.data[0]
            
            # Prepare chart data for weight progress
            weight_history = []
            bmi_history = []
            fitness_history = []
            
            for assess in assessments.data:
                date = datetime.fromisoformat(assess['assessment_date']).strftime('%d %b')
                
                if assess.get('physical_measurements'):
                    m = assess['physical_measurements'][0]
                    if m.get('weight_kg'):
                        weight_history.append({
                            'date': date,
                            'value': m['weight_kg']
                        })
                    if m.get('bmi'):
                        bmi_history.append({
                            'date': date,
                            'value': m['bmi']
                        })
                
                if assess.get('fitness_test_results'):
                    t = assess['fitness_test_results'][0]
                    if t.get('push_ups_count') is not None:
                        fitness_history.append({
                            'date': date,
                            'pushups': t['push_ups_count'],
                            'plank': t.get('plank_hold_seconds', 0)
                        })
            
            # Get photos for before/after
            photos = {
                'front': [],
                'side': [],
                'back': []
            }
            
            for assess in assessments.data[:2]:  # Get last 2 assessments for comparison
                if assess.get('assessment_photos'):
                    for photo in assess['assessment_photos']:
                        if not photo.get('is_deleted'):
                            photo_type = photo.get('photo_type', 'other')
                            if photo_type in photos:
                                photos[photo_type].append({
                                    'url': photo['photo_url'],
                                    'date': datetime.fromisoformat(assess['assessment_date']).strftime('%d %b %Y')
                                })
            
            return {
                'latest_assessment': latest,
                'total_assessments': len(assessments.data),
                'weight_history': list(reversed(weight_history)),
                'bmi_history': list(reversed(bmi_history)),
                'fitness_history': list(reversed(fitness_history)),
                'photos': photos,
                'has_progress': len(assessments.data) > 1
            }
            
        except Exception as e:
            log_error(f"Error getting client dashboard data: {str(e)}")
            return None

# Initialize service (will be done in main app)
dashboard_service = None

@dashboard_bp.route('/dashboard/<token>')
def view_dashboard(token):
    """View dashboard with secure token"""
    try:
        # Validate token
        trainer_id = dashboard_service.validate_token(token)
        
        if not trainer_id:
            return render_template('error.html', 
                                 message="This link has expired or is invalid. Please request a new link via WhatsApp."), 403
        
        # Get dashboard data
        data = dashboard_service.get_dashboard_data(trainer_id)
        
        if not data:
            return render_template('error.html', 
                                 message="Could not load dashboard data."), 500
        
        # Render dashboard
        return render_template('dashboard.html', **data)
        
    except Exception as e:
        log_error(f"Error loading dashboard: {str(e)}")
        return render_template('error.html', 
                             message="An error occurred loading your dashboard."), 500

@dashboard_bp.route('/export/<token>')
def export_data(token):
    """Export trainer data as CSV"""
    try:
        # Validate token
        trainer_id = dashboard_service.validate_token(token)
        
        if not trainer_id:
            return jsonify({'error': 'Invalid or expired token'}), 403
        
        # Export data
        csv_data = dashboard_service.export_trainer_data(trainer_id, 'csv')
        
        if csv_data:
            # Create response
            output = io.BytesIO()
            output.write(csv_data)
            output.seek(0)
            
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'trainer_data_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        else:
            return jsonify({'error': 'Could not export data'}), 500
            
    except Exception as e:
        log_error(f"Error exporting data: {str(e)}")
        return jsonify({'error': 'Export failed'}), 500

@dashboard_bp.route('/api/dashboard/<token>/refresh')
def refresh_dashboard_data(token):
    """API endpoint to refresh dashboard data"""
    try:
        # Validate token
        trainer_id = dashboard_service.validate_token(token)
        
        if not trainer_id:
            return jsonify({'error': 'Invalid or expired token'}), 403
        
        # Get fresh data
        data = dashboard_service.get_dashboard_data(trainer_id)
        
        if data:
            # Return only the stats for now
            return jsonify({
                'success': True,
                'stats': data['stats'],
                'updated_at': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
            })
        else:
            return jsonify({'error': 'Could not refresh data'}), 500
            
    except Exception as e:
        log_error(f"Error refreshing dashboard: {str(e)}")
        return jsonify({'error': 'Refresh failed'}), 500

@dashboard_bp.route('/dashboard/<token>/assessment-settings')
def assessment_settings(token):
    """Assessment customization page"""
    try:
        # Validate token
        trainer_id = dashboard_service.validate_token(token)
        
        if not trainer_id:
            return render_template('error.html', 
                                 message="This link has expired or is invalid. Please request a new link via WhatsApp."), 403
        
        # Get trainer data
        trainer = dashboard_service.trainer_model.get_by_id(trainer_id)
        if not trainer:
            return render_template('error.html', 
                                 message="Could not load trainer data."), 404
        
        # Get existing template if any
        template_result = dashboard_service.db.table('assessment_templates').select('*').eq(
            'trainer_id', trainer_id
        ).eq('is_active', True).execute()
        
        template_settings = {}
        if template_result.data:
            template_settings = template_result.data[0]
        else:
            # Default settings
            template_settings = {
                'completed_by': 'client',
                'frequency': 'quarterly',
                'include_photos': True,
                'include_health': True,
                'include_lifestyle': True,
                'include_goals': True,
                'include_measurements': True,
                'include_tests': True
            }
        
        # Render the assessment settings page
        return render_template('dashboard_assessment.html', 
                             trainer=trainer,
                             template_settings=json.dumps(template_settings))
        
    except Exception as e:
        log_error(f"Error loading assessment settings: {str(e)}")
        return render_template('error.html', 
                             message="An error occurred loading settings."), 500

@dashboard_bp.route('/api/assessment-template/save', methods=['POST'])
def save_assessment_template():
    """Save assessment template settings"""
    try:
        data = request.get_json()
        
        # Get token from header or data
        token = request.headers.get('X-Dashboard-Token') or data.get('token')
        
        # For now, we'll use the referrer to extract token
        referrer = request.referrer
        if referrer and '/dashboard/' in referrer:
            # Extract token from URL
            parts = referrer.split('/dashboard/')
            if len(parts) > 1:
                token = parts[1].split('/')[0]
        
        if not token:
            return jsonify({'success': False, 'error': 'Invalid session'}), 401
        
        # Validate token and get trainer_id
        trainer_id = dashboard_service.validate_token(token)
        if not trainer_id:
            return jsonify({'success': False, 'error': 'Session expired'}), 401
        
        # Prepare template data
        template_data = {
            'trainer_id': trainer_id,
            'template_name': 'Custom Template',
            'is_active': True,
            'completed_by': data['settings']['completed_by'],
            'frequency': data['settings']['frequency'],
            'include_photos': data['settings']['include_photos'],
            'include_health': 'health' in data.get('sections', {}),
            'include_lifestyle': 'lifestyle' in data.get('sections', {}),
            'include_goals': 'goals' in data.get('sections', {}),
            'include_measurements': 'measurements' in data.get('sections', {}),
            'include_tests': 'tests' in data.get('sections', {}),
            'health_questions': json.dumps(data.get('sections', {}).get('health', [])),
            'lifestyle_questions': json.dumps(data.get('sections', {}).get('lifestyle', [])),
            'goals_questions': json.dumps(data.get('sections', {}).get('goals', [])),
            'measurement_fields': json.dumps(data.get('sections', {}).get('measurements', [])),
            'test_fields': json.dumps(data.get('sections', {}).get('tests', [])),
            'updated_at': datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
        }
        
        # Check if template exists
        existing = dashboard_service.db.table('assessment_templates').select('id').eq(
            'trainer_id', trainer_id
        ).eq('is_active', True).execute()
        
        if existing.data:
            # Update existing template
            result = dashboard_service.db.table('assessment_templates').update(
                template_data
            ).eq('id', existing.data[0]['id']).execute()
        else:
            # Create new template
            template_data['created_at'] = datetime.now(pytz.timezone('Africa/Johannesburg')).isoformat()
            result = dashboard_service.db.table('assessment_templates').insert(
                template_data
            ).execute()
        
        if result.data:
            return jsonify({'success': True, 'message': 'Template saved successfully!'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save template'}), 500
            
    except Exception as e:
        log_error(f"Error saving template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/assessment/client/<token>')
def view_client_assessment(token):
    """Client view of their assessment with charts and progress"""
    try:
        # Validate token (could be a special client token)
        result = dashboard_service.db.table('assessment_access_tokens').select(
            'client_id, expires_at'
        ).eq('token', token).execute()
        
        if not result.data:
            return render_template('error.html', 
                                 message="Invalid or expired link. Please request a new one."), 403
        
        token_data = result.data[0]
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        
        if datetime.now(pytz.timezone('Africa/Johannesburg')) > expires_at:
            return render_template('error.html', 
                                 message="This link has expired. Please request a new one."), 403
        
        client_id = token_data['client_id']
        
        # Get client and assessment data
        client = dashboard_service.client_model.get_by_id(client_id)
        assessment_data = dashboard_service.get_client_assessment_dashboard_data(client_id)
        
        if not assessment_data:
            return render_template('error.html', 
                                 message="No assessment data found."), 404
        
        return render_template('client_assessment.html', 
                             client=client,
                             **assessment_data)
        
    except Exception as e:
        log_error(f"Error viewing client assessment: {str(e)}")
        return render_template('error.html', 
                             message="An error occurred loading your assessment."), 500
