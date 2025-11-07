"""
Dashboard Routes
Web dashboard for relationship management
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from services.dashboard import DashboardService, DashboardTokenManager
from utils.logger import log_info, log_error
import os

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Initialize services (will be set by app)
dashboard_service = None
token_manager = None

def init_dashboard_services(supabase_client):
    """Initialize dashboard services"""
    global dashboard_service, token_manager
    dashboard_service = DashboardService(supabase_client)
    token_manager = DashboardTokenManager(supabase_client)

@dashboard_bp.route('/<user_id>/<token>')
def dashboard_view(user_id, token):
    """Main dashboard view"""
    try:
        # Validate token
        token_data = token_manager.validate_token(token, user_id)
        if not token_data:
            return render_template('dashboard/error.html', 
                                 error="Invalid or expired access token"), 403
        
        # Get user info
        user_info = dashboard_service.get_user_info(user_id, token_data['role'])
        if not user_info:
            return render_template('dashboard/error.html', 
                                 error="User not found"), 404
        
        # Check if this is a special purpose dashboard
        purpose = token_data.get('purpose', 'relationships')
        
        if purpose == 'browse_trainers' and token_data['role'] == 'client':
            # Special dashboard for browsing ALL trainers on the platform
            relationships = dashboard_service.get_all_trainers(user_id)
            stats = {
                'active_count': len([t for t in relationships if not t['is_connected']]),
                'pending_count': len([t for t in relationships if t['is_connected']]),
                'total_count': len(relationships)
            }
            relationship_type = 'available_trainers'
        else:
            # Regular dashboard showing user's relationships
            relationships = dashboard_service.get_relationships(user_id, token_data['role'])
            stats = dashboard_service.get_dashboard_stats(user_id, token_data['role'])
            relationship_type = 'clients' if token_data['role'] == 'trainer' else 'trainers'
        
        return render_template('dashboard/main.html',
                             user=user_info,
                             relationships=relationships,
                             stats=stats,
                             relationship_type=relationship_type,
                             role=token_data['role'],
                             purpose=purpose)
        
    except Exception as e:
        log_error(f"Dashboard error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the dashboard"), 500

@dashboard_bp.route('/api/<user_id>/<token>/relationships')
def api_get_relationships(user_id, token):
    """API endpoint to get relationships (for AJAX)"""
    try:
        # Validate token (but don't mark as used for API calls)
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check if token exists and is valid (but don't consume it)
        from datetime import datetime
        result = dashboard_service.db.table('dashboard_tokens').select('*').eq(
            'token_hash', token_hash
        ).eq('user_id', user_id).gt(
            'expires_at', datetime.now().isoformat()
        ).execute()
        
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 403
        
        token_data = result.data[0]
        
        # Get relationships
        status = request.args.get('status', 'active')
        relationships = dashboard_service.get_relationships(user_id, token_data['role'], status)
        
        return jsonify({'relationships': relationships})
        
    except Exception as e:
        log_error(f"API error: {str(e)}")
        return jsonify({'error': str(e)}), 500



@dashboard_bp.route('/habits/<user_id>/<token>')
def trainer_habits_view(user_id, token):
    """Trainer habits dashboard view"""
    try:
        # Validate token
        token_data = token_manager.validate_token(token, user_id)
        if not token_data or token_data['role'] != 'trainer':
            return render_template('dashboard/error.html', 
                                 error="Invalid or expired access token"), 403
        
        # Get user info
        user_info = dashboard_service.get_user_info(user_id, 'trainer')
        if not user_info:
            return render_template('dashboard/error.html', 
                                 error="User not found"), 404
        
        # Get trainer habits
        from services.habits.habit_service import HabitService
        habit_service = HabitService(dashboard_service.db)
        
        success, msg, habits = habit_service.get_trainer_habits(user_id, active_only=True)
        
        if not success:
            habits = []
        
        # Add assignment counts to habits
        for habit in habits:
            habit['assignment_count'] = habit_service.get_habit_assignment_count(habit['habit_id'])
        
        # Calculate stats
        stats = {
            'total_habits': len(habits),
            'active_habits': len([h for h in habits if h.get('is_active', True)]),
            'assigned_habits': len([h for h in habits if habit_service.get_habit_assignment_count(h['habit_id']) > 0]),
            'total_assignments': sum(habit_service.get_habit_assignment_count(h['habit_id']) for h in habits)
        }
        
        return render_template('dashboard/trainer_habits.html',
                             user=user_info,
                             habits=habits,
                             stats=stats)
        
    except Exception as e:
        log_error(f"Trainer habits dashboard error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the habits dashboard"), 500


@dashboard_bp.route('/progress/<user_id>/<token>/<trainee_id>')
def trainee_progress_view(user_id, token, trainee_id):
    """Trainee progress dashboard view - enhanced version matching client dashboard"""
    try:
        # Validate token
        token_data = token_manager.validate_token(token, user_id)
        if not token_data or token_data['role'] != 'trainer':
            return render_template('dashboard/error.html', 
                                 error="Invalid or expired access token"), 403
        
        # Get trainer info from trainers table
        trainer_result = dashboard_service.db.table('trainers').select('*').eq('trainer_id', user_id).execute()
        if not trainer_result.data:
            return render_template('dashboard/error.html', 
                                 error="Trainer not found"), 404
        trainer_info = trainer_result.data[0]
        
        # Get trainee info
        trainee_result = dashboard_service.db.table('clients').select('*').eq('client_id', trainee_id).execute()
        if not trainee_result.data:
            return render_template('dashboard/error.html', 
                                 error="Trainee not found"), 404
        
        trainee_info = trainee_result.data[0]
        
        # Get date parameters from query string
        view_type = request.args.get('view', 'daily')  # daily or monthly
        selected_date = request.args.get('date')  # YYYY-MM-DD format
        selected_month = request.args.get('month')  # MM format
        selected_year = request.args.get('year')  # YYYY format
        
        # Get trainee's assigned habits by this trainer
        assignments_result = dashboard_service.db.table('trainee_habit_assignments').select(
            '*, fitness_habits(*)'
        ).eq('client_id', trainee_id).eq('trainer_id', user_id).eq('is_active', True).execute()
        
        habits = []
        if assignments_result.data:
            for assignment in assignments_result.data:
                habit_data = assignment.get('fitness_habits')
                if habit_data:
                    # Add assignment info to habit data
                    habit_data['assigned_date'] = assignment.get('assigned_date')
                    habit_data['assignment_id'] = assignment.get('id')
                    habit_data['trainer_id'] = assignment.get('trainer_id')
                    habit_data['trainer_name'] = trainer_info.get('name', 'Unknown')
                    
                    # Calculate progress data based on selected date/month
                    if view_type == 'monthly' and selected_month and selected_year:
                        habit_progress = calculate_habit_progress_for_month(
                            dashboard_service.db, habit_data['habit_id'], trainee_id, 
                            selected_year, selected_month
                        )
                    elif view_type == 'daily' and selected_date:
                        habit_progress = calculate_habit_progress_for_date(
                            dashboard_service.db, habit_data['habit_id'], trainee_id, 
                            selected_date
                        )
                    else:
                        # Default to current day/month
                        habit_progress = calculate_habit_progress(dashboard_service.db, habit_data['habit_id'], trainee_id)
                    
                    habit_data.update(habit_progress)
                    
                    # Calculate streak
                    streak = calculate_habit_streak(dashboard_service.db, habit_data['habit_id'], trainee_id)
                    habit_data['streak_days'] = streak
                    
                    habits.append(habit_data)
        
        # Calculate statistics for the selected period
        stats = calculate_habit_statistics(habits, view_type, selected_date, selected_month, selected_year)
        
        # Calculate leaderboard with this trainee's position among all clients
        leaderboard = calculate_proper_leaderboard(dashboard_service.db, trainee_id, view_type, selected_date, selected_month, selected_year)
        
        return render_template('dashboard/trainee_progress.html',
                             trainer=trainer_info,
                             trainee=trainee_info,
                             habits=habits,
                             stats=stats,
                             leaderboard=leaderboard,
                             view_type=view_type,
                             selected_date=selected_date,
                             selected_month=selected_month,
                             selected_year=selected_year)
        
    except Exception as e:
        log_error(f"Trainee progress dashboard error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the progress dashboard"), 500


@dashboard_bp.route('/trainee-habits/<user_id>/<token>/<trainee_id>')
def trainee_habits_view(user_id, token, trainee_id):
    """Trainee habits dashboard view - shows only habits assigned by this trainer"""
    try:
        # Validate token
        token_data = token_manager.validate_token(token, user_id)
        if not token_data or token_data['role'] != 'trainer':
            return render_template('dashboard/error.html', 
                                 error="Invalid or expired access token"), 403
        
        # Get user info
        user_info = dashboard_service.get_user_info(user_id, 'trainer')
        if not user_info:
            return render_template('dashboard/error.html', 
                                 error="User not found"), 404
        
        # Get trainee info
        trainee_result = dashboard_service.db.table('clients').select('*').eq('client_id', trainee_id).execute()
        if not trainee_result.data:
            return render_template('dashboard/error.html', 
                                 error="Trainee not found"), 404
        
        trainee = trainee_result.data[0]
        
        # Get habits assigned by THIS TRAINER ONLY to this trainee
        from services.habits.assignment_service import AssignmentService
        assignment_service = AssignmentService(dashboard_service.db)
        
        # Get assignments with habit details - only for this trainer
        assignments_result = dashboard_service.db.table('trainee_habit_assignments').select(
            '*, fitness_habits(*)'
        ).eq('client_id', trainee_id).eq('trainer_id', user_id).eq('is_active', True).execute()
        
        habits = []
        if assignments_result.data:
            for assignment in assignments_result.data:
                habit_data = assignment.get('fitness_habits')
                if habit_data:
                    # Add assignment info to habit data
                    habit_data['assigned_date'] = assignment.get('assigned_date')
                    habit_data['assignment_id'] = assignment.get('id')
                    habits.append(habit_data)
        
        # Add connected date to trainee info
        relationship_result = dashboard_service.db.table('trainer_client_list').select(
            'approved_at'
        ).eq('trainer_id', user_id).eq('client_id', trainee_id).execute()
        
        connected_date = 'Unknown'
        if relationship_result.data and relationship_result.data[0].get('approved_at'):
            connected_date = relationship_result.data[0]['approved_at'][:10]
        
        trainee['connected_date'] = connected_date
        
        return render_template('dashboard/trainee_habits.html',
                             user=user_info,
                             trainee=trainee,
                             habits=habits)
        
    except Exception as e:
        log_error(f"Trainee habits dashboard error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the habits dashboard"), 500


def calculate_habit_progress(db, habit_id, client_id):
    """Calculate habit progress for daily and monthly views"""
    from datetime import datetime, timedelta
    import calendar
    
    today = datetime.now().date()
    current_month_start = today.replace(day=1)
    
    # Get today's logs
    daily_logs = db.table('habit_logs').select('completed_value').eq(
        'habit_id', habit_id
    ).eq('client_id', client_id).eq('log_date', today.isoformat()).execute()
    
    daily_completed = sum(float(log['completed_value']) for log in daily_logs.data) if daily_logs.data else 0
    
    # Get this month's logs
    monthly_logs = db.table('habit_logs').select('completed_value').eq(
        'habit_id', habit_id
    ).eq('client_id', client_id).gte('log_date', current_month_start.isoformat()).execute()
    
    monthly_completed = sum(float(log['completed_value']) for log in monthly_logs.data) if monthly_logs.data else 0
    
    # Get habit target
    habit_result = db.table('fitness_habits').select('target_value, frequency').eq('habit_id', habit_id).execute()
    if not habit_result.data:
        return {}
    
    habit_data = habit_result.data[0]
    daily_target = float(habit_data['target_value'])
    
    # Calculate monthly target (days in current month * daily target)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    monthly_target = daily_target * days_in_month
    
    # Calculate remaining/exceeded
    daily_remaining = max(0, daily_target - daily_completed)
    daily_exceeded = max(0, daily_completed - daily_target)
    monthly_remaining = max(0, monthly_target - monthly_completed)
    monthly_exceeded = max(0, monthly_completed - monthly_target)
    
    # Calculate progress percentages
    daily_progress_percent = min(100, (daily_completed / daily_target * 100)) if daily_target > 0 else 0
    monthly_progress_percent = min(100, (monthly_completed / monthly_target * 100)) if monthly_target > 0 else 0
    
    # Calculate completion rates
    daily_completion_rate = min(100, daily_progress_percent)
    monthly_completion_rate = min(100, monthly_progress_percent)
    
    # Count logs
    daily_logs_count = len(daily_logs.data) if daily_logs.data else 0
    monthly_logs_count = len(monthly_logs.data) if monthly_logs.data else 0
    
    return {
        'daily_completed': daily_completed,
        'monthly_completed': monthly_completed,
        'daily_target': daily_target,
        'monthly_target': monthly_target,
        'daily_remaining': daily_remaining,
        'daily_exceeded': daily_exceeded,
        'monthly_remaining': monthly_remaining,
        'monthly_exceeded': monthly_exceeded,
        'daily_progress_percent': daily_progress_percent,
        'monthly_progress_percent': monthly_progress_percent,
        'daily_completion_rate': daily_completion_rate,
        'monthly_completion_rate': monthly_completion_rate,
        'daily_logs_count': daily_logs_count,
        'monthly_logs_count': monthly_logs_count
    }


def calculate_habit_streak(db, habit_id, client_id):
    """Calculate current habit streak (consecutive days with logs)"""
    from datetime import datetime, timedelta
    
    # Get the most recent log date for this habit and client
    recent_log = db.table('habit_logs').select('log_date').eq(
        'habit_id', habit_id
    ).eq('client_id', client_id).order('log_date', desc=True).limit(1).execute()
    
    if not recent_log.data:
        return 0
    
    # Start from the most recent log date
    most_recent_date = datetime.strptime(recent_log.data[0]['log_date'], '%Y-%m-%d').date()
    streak = 0
    current_date = most_recent_date
    
    # Check backwards from most recent log date to find consecutive days with logs
    for i in range(365):  # Check up to 1 year back
        logs = db.table('habit_logs').select('id').eq(
            'habit_id', habit_id
        ).eq('client_id', client_id).eq('log_date', current_date.isoformat()).execute()
        
        if logs.data:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak


def calculate_habit_progress_for_date(db, habit_id, client_id, target_date):
    """Calculate habit progress for a specific date"""
    from datetime import datetime
    
    # Get logs for the specific date
    daily_logs = db.table('habit_logs').select('completed_value').eq(
        'habit_id', habit_id
    ).eq('client_id', client_id).eq('log_date', target_date).execute()
    
    daily_completed = sum(float(log['completed_value']) for log in daily_logs.data) if daily_logs.data else 0
    
    # Get habit target
    habit_result = db.table('fitness_habits').select('target_value, frequency').eq('habit_id', habit_id).execute()
    if not habit_result.data:
        return {}
    
    habit_data = habit_result.data[0]
    daily_target = float(habit_data['target_value'])
    
    # Calculate progress
    daily_progress_percent = min(100, (daily_completed / daily_target * 100)) if daily_target > 0 else 0
    daily_remaining = max(0, daily_target - daily_completed)
    daily_exceeded = max(0, daily_completed - daily_target)
    
    return {
        'daily_completed': daily_completed,
        'daily_target': daily_target,
        'daily_remaining': daily_remaining,
        'daily_exceeded': daily_exceeded,
        'daily_progress_percent': daily_progress_percent,
        'daily_completion_rate': min(100, daily_progress_percent),
        'daily_logs_count': len(daily_logs.data) if daily_logs.data else 0,
        'monthly_completed': 0,  # Not applicable for daily view
        'monthly_target': 0,
        'monthly_progress_percent': 0,
        'monthly_completion_rate': 0,
        'monthly_logs_count': 0
    }


def calculate_habit_progress_for_month(db, habit_id, client_id, year, month):
    """Calculate habit progress for a specific month"""
    from datetime import datetime
    import calendar
    
    # Create date range for the month
    year_int = int(year)
    month_int = int(month)
    month_start = f"{year}-{month.zfill(2)}-01"
    days_in_month = calendar.monthrange(year_int, month_int)[1]
    month_end = f"{year}-{month.zfill(2)}-{days_in_month:02d}"
    
    # Get logs for the specific month
    monthly_logs = db.table('habit_logs').select('completed_value').eq(
        'habit_id', habit_id
    ).eq('client_id', client_id).gte('log_date', month_start).lte('log_date', month_end).execute()
    
    monthly_completed = sum(float(log['completed_value']) for log in monthly_logs.data) if monthly_logs.data else 0
    
    # Get habit target
    habit_result = db.table('fitness_habits').select('target_value, frequency').eq('habit_id', habit_id).execute()
    if not habit_result.data:
        return {}
    
    habit_data = habit_result.data[0]
    daily_target = float(habit_data['target_value'])
    monthly_target = daily_target * days_in_month
    
    # Calculate progress
    monthly_progress_percent = min(100, (monthly_completed / monthly_target * 100)) if monthly_target > 0 else 0
    monthly_remaining = max(0, monthly_target - monthly_completed)
    monthly_exceeded = max(0, monthly_completed - monthly_target)
    
    return {
        'monthly_completed': monthly_completed,
        'monthly_target': monthly_target,
        'monthly_remaining': monthly_remaining,
        'monthly_exceeded': monthly_exceeded,
        'monthly_progress_percent': monthly_progress_percent,
        'monthly_completion_rate': min(100, monthly_progress_percent),
        'monthly_logs_count': len(monthly_logs.data) if monthly_logs.data else 0,
        'daily_completed': 0,  # Not applicable for monthly view
        'daily_target': daily_target,  # Keep for reference
        'daily_progress_percent': 0,
        'daily_completion_rate': 0,
        'daily_logs_count': 0
    }


def calculate_client_leaderboard_for_month(db, client_id, year, month):
    """Calculate leaderboard for clients based on habit progress for a specific month"""
    from datetime import datetime
    import calendar
    
    # Create date range for the month
    year_int = int(year)
    month_int = int(month)
    month_start = f"{year}-{month.zfill(2)}-01"
    days_in_month = calendar.monthrange(year_int, month_int)[1]
    month_end = f"{year}-{month.zfill(2)}-{days_in_month:02d}"
    
    # Get all clients with habit assignments
    clients_result = db.table('trainee_habit_assignments').select(
        'client_id'
    ).eq('is_active', True).execute()
    
    if not clients_result.data:
        return []
    
    # Get unique client IDs
    client_ids = list(set(assignment['client_id'] for assignment in clients_result.data))
    
    # Get client names separately
    clients_info = {}
    if client_ids:
        clients_names_result = db.table('clients').select('client_id, name').in_('client_id', client_ids).execute()
        if clients_names_result.data:
            clients_info = {client['client_id']: client['name'] for client in clients_names_result.data}
    
    client_stats = {}
    
    # Calculate stats for each client
    for assignment in clients_result.data:
        client_id_iter = assignment['client_id']
        client_name = clients_info.get(client_id_iter, 'Unknown')
        
        if client_id_iter not in client_stats:
            client_stats[client_id_iter] = {
                'client_id': client_id_iter,
                'name': client_name,
                'total_progress': 0,
                'habit_count': 0,
                'total_streak': 0,
                'trainer_ids': set()
            }
        
        # Get habit assignments for this client
        habit_assignments = db.table('trainee_habit_assignments').select(
            'habit_id, trainer_id'
        ).eq('client_id', client_id_iter).eq('is_active', True).execute()
        
        for habit_assignment in habit_assignments.data:
            habit_id = habit_assignment['habit_id']
            trainer_id = habit_assignment['trainer_id']
            
            client_stats[client_id_iter]['trainer_ids'].add(trainer_id)
            client_stats[client_id_iter]['habit_count'] += 1
            
            # Calculate progress for this habit for the specific month
            progress = calculate_habit_progress_for_month(db, habit_id, client_id_iter, year, month)
            client_stats[client_id_iter]['total_progress'] += progress.get('monthly_progress_percent', 0)
            
            # Calculate streak for this habit
            streak = calculate_habit_streak(db, habit_id, client_id_iter)
            client_stats[client_id_iter]['total_streak'] += streak
    
    # Calculate average progress and prepare leaderboard
    leaderboard = []
    for client_data in client_stats.values():
        if client_data['habit_count'] > 0:
            avg_progress = client_data['total_progress'] / client_data['habit_count']
            trainer_ids = list(client_data['trainer_ids'])
            
            leaderboard.append({
                'client_id': client_data['client_id'],
                'name': client_data['name'],
                'progress': round(avg_progress, 1),
                'habit_count': client_data['habit_count'],
                'total_streak': client_data['total_streak'],
                'trainer_ids': trainer_ids,
                'is_current_user': client_data['client_id'] == client_id
            })
    
    # Sort by progress (descending)
    leaderboard.sort(key=lambda x: x['progress'], reverse=True)
    
    # Add ranking
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1
    
    # Ensure current user is in top 10 or add them
    current_user_entry = next((entry for entry in leaderboard if entry['is_current_user']), None)
    top_10 = leaderboard[:10]
    
    if current_user_entry and current_user_entry not in top_10:
        top_10.append(current_user_entry)
    
    return top_10


def get_client_last_activity(db, client_id):
    """Get the most recent activity date for a client"""
    from datetime import datetime
    
    # Get the most recent habit log for this client
    recent_log = db.table('habit_logs').select('log_date').eq(
        'client_id', client_id
    ).order('log_date', desc=True).limit(1).execute()
    
    if recent_log.data:
        log_date = recent_log.data[0]['log_date']
        # Convert to readable format
        try:
            date_obj = datetime.strptime(log_date, '%Y-%m-%d')
            return date_obj.strftime('%b %d')  # e.g., "Nov 06"
        except:
            return log_date
    
    return "No activity"


def get_trainer_trainees_with_progress(db, trainer_id):
    """Get trainer's trainees with their progress data"""
    from datetime import datetime
    
    # Get trainer's trainees
    trainees_result = db.table('trainer_client_list').select(
        'client_id'
    ).eq('trainer_id', trainer_id).eq('connection_status', 'active').execute()
    
    if not trainees_result.data:
        return []
    
    trainees = []
    for trainee_data in trainees_result.data:
        client_id = trainee_data['client_id']
        
        # Get client info separately
        client_result = db.table('clients').select('name, whatsapp, email').eq('client_id', client_id).execute()
        client_info = client_result.data[0] if client_result.data else {}
        
        if client_info:
            # Get habit assignments count
            assignments_result = db.table('trainee_habit_assignments').select(
                'habit_id'
            ).eq('client_id', client_id).eq('trainer_id', trainer_id).eq('is_active', True).execute()
            
            habit_count = len(assignments_result.data) if assignments_result.data else 0
            
            # Calculate overall progress
            total_progress = 0
            total_streak = 0
            
            if assignments_result.data:
                for assignment in assignments_result.data:
                    habit_id = assignment['habit_id']
                    
                    # Calculate progress
                    progress = calculate_habit_progress(db, habit_id, client_id)
                    total_progress += progress.get('monthly_progress_percent', 0)
                    
                    # Calculate streak
                    streak = calculate_habit_streak(db, habit_id, client_id)
                    total_streak += streak
            
            avg_progress = total_progress / habit_count if habit_count > 0 else 0
            
            trainees.append({
                'client_id': client_id,
                'name': client_info.get('name', 'Unknown'),
                'phone': client_info.get('whatsapp', ''),
                'whatsapp': client_info.get('whatsapp', ''),
                'email': client_info.get('email', ''),
                'habit_count': habit_count,
                'avg_progress': round(avg_progress, 1),
                'total_streak': total_streak,
                'last_activity': get_client_last_activity(db, client_id)
            })
    
    return trainees

def calculate_trainer_stats(db, trainer_id, trainees):
    """Calculate comprehensive trainer statistics"""
    from datetime import datetime, timedelta
    
    # Client Statistics
    total_clients = len(trainees)
    active_clients = len([t for t in trainees if t.get('avg_progress', 0) > 0])
    inactive_clients = total_clients - active_clients
    
    # Get all trainer's fitness habits
    trainer_habits_result = db.table('fitness_habits').select('*').eq('trainer_id', trainer_id).execute()
    total_habits_created = len(trainer_habits_result.data) if trainer_habits_result.data else 0
    
    # Get habit assignments
    assignments_result = db.table('trainee_habit_assignments').select('*').eq('trainer_id', trainer_id).execute()
    total_assignments = len(assignments_result.data) if assignments_result.data else 0
    active_assignments = len([a for a in assignments_result.data if a.get('is_active', False)]) if assignments_result.data else 0
    
    # Calculate unassigned habits
    unassigned_habits = total_habits_created - active_assignments
    
    # Get habit logs for today and this month
    today = datetime.now().date()
    month_start = today.replace(day=1)
    
    # Get habit IDs for this trainer's assignments
    trainer_habit_ids = [a.get('habit_id') for a in (assignments_result.data or []) if a.get('is_active', False)]
    
    # Daily habit log statistics (only for trainer's assigned habits)
    daily_logs = []
    if trainer_habit_ids:
        daily_logs_result = db.table('habit_logs').select('*').eq('log_date', str(today)).in_('habit_id', trainer_habit_ids).execute()
        daily_logs = daily_logs_result.data if daily_logs_result.data else []
    
    # Monthly habit log statistics (only for trainer's assigned habits)
    monthly_logs = []
    if trainer_habit_ids:
        monthly_logs_result = db.table('habit_logs').select('*').gte('log_date', str(month_start)).lte('log_date', str(today)).in_('habit_id', trainer_habit_ids).execute()
        monthly_logs = monthly_logs_result.data if monthly_logs_result.data else []
    
    # Calculate per-trainee progress statistics
    trainee_daily_progress = []
    trainee_monthly_progress = []
    
    for trainee in trainees:
        client_id = trainee.get('client_id')
        # Get assignments for this specific client (same as in get_trainer_trainees_with_progress)
        client_assignments_result = db.table('trainee_habit_assignments').select('*').eq('client_id', client_id).eq('is_active', True).execute()
        client_assignments = client_assignments_result.data if client_assignments_result.data else []
        
        # Daily progress for this trainee
        client_daily_logs = [log for log in daily_logs if log.get('client_id') == client_id]
        daily_stats = calculate_completion_stats(client_daily_logs, client_assignments, db)
        
        trainee_daily_progress.append({
            'name': trainee.get('name', 'Unknown'),
            'progress': trainee.get('avg_progress', 0),
            'total_habits': len(client_assignments),
            'target_met': daily_stats['target_met'],
            'completed': daily_stats['completed'],
            'partial': daily_stats['partial'],
            'not_started': daily_stats['not_started']
        })
        
        # Monthly progress for this trainee
        client_monthly_logs = [log for log in monthly_logs if log.get('client_id') == client_id]
        monthly_stats = calculate_completion_stats(client_monthly_logs, client_assignments, db)
        
        trainee_monthly_progress.append({
            'name': trainee.get('name', 'Unknown'),
            'progress': trainee.get('avg_progress', 0),
            'total_habits': len(client_assignments),
            'target_met': monthly_stats['target_met'],
            'completed': monthly_stats['completed'],
            'partial': monthly_stats['partial'],
            'not_started': monthly_stats['not_started']
        })
    
    # Client-by-client habit assignments
    client_habit_breakdown = {}
    for trainee in trainees:
        client_id = trainee.get('client_id')
        # Get assignments for this specific client
        client_assignments_result = db.table('trainee_habit_assignments').select('*').eq('client_id', client_id).eq('is_active', True).execute()
        client_assignments = client_assignments_result.data if client_assignments_result.data else []
        client_habit_breakdown[client_id] = {
            'name': trainee.get('name', 'Unknown'),
            'assigned_habits': len(client_assignments),
            'progress': trainee.get('avg_progress', 0),
            'streak': trainee.get('total_streak', 0)
        }
    
    # Global leaderboard ranking (simplified - can be enhanced)
    leaderboard_data = []
    for trainee in trainees:
        leaderboard_data.append({
            'client_id': trainee.get('client_id'),
            'name': trainee.get('name', 'Unknown'),
            'progress': trainee.get('avg_progress', 0),
            'streak': trainee.get('total_streak', 0),
            'habit_count': trainee.get('habit_count', 0)
        })
    
    # Sort by progress and streak
    leaderboard_data.sort(key=lambda x: (x['progress'], x['streak']), reverse=True)
    
    # Add rankings
    for i, client in enumerate(leaderboard_data):
        client['rank'] = i + 1
    
    # Calculate average streak for active clients
    active_streaks = [t.get('total_streak', 0) for t in trainees if t.get('avg_progress', 0) > 0]
    avg_streak = sum(active_streaks) / len(active_streaks) if active_streaks else 0
    
    return {
        # Client Statistics
        'total_clients': total_clients,
        'active_clients': active_clients,
        'inactive_clients': inactive_clients,
        
        # Habit Statistics
        'total_habits_created': total_habits_created,
        'total_assignments': total_assignments,
        'active_assignments': active_assignments,
        'unassigned_habits': max(0, unassigned_habits),
        
        # Per-Trainee Progress
        'trainee_daily_progress': trainee_daily_progress,
        'trainee_monthly_progress': trainee_monthly_progress,
        
        # Client Breakdown
        'client_habit_breakdown': client_habit_breakdown,
        
        # Leaderboard
        'leaderboard': leaderboard_data[:10],  # Top 10
        
        # Overall Metrics
        'avg_progress': sum(t.get('avg_progress', 0) for t in trainees) / total_clients if total_clients > 0 else 0,
        'total_streaks': sum(t.get('total_streak', 0) for t in trainees),
        'avg_streak': avg_streak
    }


def calculate_completion_stats(logs, assignments, db):
    """Calculate habit completion statistics based on actual target values"""
    if not assignments:
        return {'completed': 0, 'partial': 0, 'not_started': 0, 'target_met': 0}
    
    # Get habit IDs from assignments
    habit_ids = [a.get('habit_id') for a in assignments if a.get('is_active', False)]
    
    completed = 0
    partial = 0
    not_started = 0
    target_met = 0
    
    for habit_id in habit_ids:
        habit_logs = [log for log in logs if log.get('habit_id') == habit_id]
        
        if not habit_logs:
            not_started += 1
        else:
            # Get the habit's target value from fitness_habits table
            habit_result = db.table('fitness_habits').select('target_value, unit').eq('habit_id', habit_id).execute()
            
            if habit_result.data:
                target_value = float(habit_result.data[0].get('target_value', 0))
                max_completed = max((float(log.get('completed_value', 0)) for log in habit_logs), default=0)
                
                if max_completed == 0:
                    not_started += 1
                elif max_completed >= target_value:
                    # Target met or exceeded
                    completed += 1
                    target_met += 1
                else:
                    # Some progress but target not met
                    partial += 1
            else:
                # Habit not found, treat as not started
                not_started += 1
    
    return {
        'completed': completed,
        'partial': partial, 
        'not_started': not_started,
        'target_met': target_met
    }


def get_trainee_habits_with_progress(db, trainer_id, trainee_id):
    """Get trainee's habits with detailed progress"""
    # Get habits assigned by this trainer to this trainee
    assignments_result = db.table('trainee_habit_assignments').select(
        '*, fitness_habits(*)'
    ).eq('client_id', trainee_id).eq('trainer_id', trainer_id).eq('is_active', True).execute()
    
    habits = []
    if assignments_result.data:
        for assignment in assignments_result.data:
            habit_data = assignment.get('fitness_habits')
            if habit_data:
                # Add assignment info
                habit_data['assigned_date'] = assignment.get('assigned_date')
                habit_data['assignment_id'] = assignment.get('id')
                
                # Calculate progress
                habit_progress = calculate_habit_progress(db, habit_data['habit_id'], trainee_id)
                habit_data.update(habit_progress)
                
                # Calculate streak
                streak = calculate_habit_streak(db, habit_data['habit_id'], trainee_id)
                habit_data['streak_days'] = streak
                
                habits.append(habit_data)
    
    return habits


def calculate_trainer_leaderboard(db, trainer_id, current_trainee_id):
    """Calculate leaderboard for trainer's trainees"""
    # Get all trainees of this trainer
    trainees_result = db.table('trainer_client_list').select(
        'client_id, clients(name)'
    ).eq('trainer_id', trainer_id).eq('is_active', True).execute()
    
    if not trainees_result.data:
        return []
    
    leaderboard = []
    
    for trainee_data in trainees_result.data:
        client_id = trainee_data['client_id']
        client_name = trainee_data.get('clients', {}).get('name', 'Unknown') if trainee_data.get('clients') else 'Unknown'
        
        # Get habit assignments for this trainee from this trainer
        assignments_result = db.table('trainee_habit_assignments').select(
            'habit_id'
        ).eq('client_id', client_id).eq('trainer_id', trainer_id).eq('is_active', True).execute()
        
        habit_count = len(assignments_result.data) if assignments_result.data else 0
        total_progress = 0
        total_streak = 0
        
        if assignments_result.data:
            for assignment in assignments_result.data:
                habit_id = assignment['habit_id']
                
                # Calculate progress
                progress = calculate_habit_progress(db, habit_id, client_id)
                total_progress += progress.get('monthly_progress_percent', 0)
                
                # Calculate streak
                streak = calculate_habit_streak(db, habit_id, client_id)
                total_streak += streak
        
        avg_progress = total_progress / habit_count if habit_count > 0 else 0
        
        leaderboard.append({
            'client_id': client_id,
            'name': client_name,
            'progress': round(avg_progress, 1),
            'habit_count': habit_count,
            'total_streak': total_streak,
            'is_current_trainee': client_id == current_trainee_id
        })
    
    # Sort by progress (descending)
    leaderboard.sort(key=lambda x: x['progress'], reverse=True)
    
    # Add ranking
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1
    
    return leaderboard


def calculate_trainee_detailed_stats(db, trainer_id, trainee_id):
    """Calculate detailed statistics for a specific trainee"""
    from datetime import datetime, timedelta
    
    # Get habit assignments
    assignments_result = db.table('trainee_habit_assignments').select(
        'habit_id, assigned_date'
    ).eq('client_id', trainee_id).eq('trainer_id', trainer_id).eq('is_active', True).execute()
    
    if not assignments_result.data:
        return {
            'total_habits': 0,
            'completed_today': 0,
            'completion_rate': 0,
            'longest_streak': 0,
            'days_active': 0
        }
    
    total_habits = len(assignments_result.data)
    completed_today = 0
    total_progress = 0
    longest_streak = 0
    
    today = datetime.now().date()
    
    for assignment in assignments_result.data:
        habit_id = assignment['habit_id']
        
        # Check if completed today
        today_logs = db.table('habit_logs').select('completed_value').eq(
            'habit_id', habit_id
        ).eq('client_id', trainee_id).eq('log_date', today.isoformat()).execute()
        
        if today_logs.data and any(float(log['completed_value']) > 0 for log in today_logs.data):
            completed_today += 1
        
        # Calculate progress
        progress = calculate_habit_progress(db, habit_id, trainee_id)
        total_progress += progress.get('monthly_progress_percent', 0)
        
        # Calculate streak
        streak = calculate_habit_streak(db, habit_id, trainee_id)
        longest_streak = max(longest_streak, streak)
    
    completion_rate = (total_progress / total_habits) if total_habits > 0 else 0
    
    # Calculate days active (days with any habit logs)
    logs_result = db.table('habit_logs').select('log_date').eq('client_id', trainee_id).execute()
    unique_dates = set(log['log_date'] for log in logs_result.data) if logs_result.data else set()
    days_active = len(unique_dates)
    
    return {
        'total_habits': total_habits,
        'completed_today': completed_today,
        'completion_rate': round(completion_rate, 1),
        'longest_streak': longest_streak,
        'days_active': days_active
    }


def calculate_client_leaderboard(db, client_id):
    """Calculate leaderboard for clients based on habit progress"""
    from datetime import datetime
    
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get all clients with habit assignments
    clients_result = db.table('trainee_habit_assignments').select(
        'client_id'
    ).eq('is_active', True).execute()
    
    if not clients_result.data:
        return []
    
    # Get unique client IDs
    client_ids = list(set(assignment['client_id'] for assignment in clients_result.data))
    
    # Get client names separately
    clients_info = {}
    if client_ids:
        clients_names_result = db.table('clients').select('client_id, name').in_('client_id', client_ids).execute()
        if clients_names_result.data:
            clients_info = {client['client_id']: client['name'] for client in clients_names_result.data}
    
    client_stats = {}
    
    # Calculate stats for each client
    for assignment in clients_result.data:
        client_id_iter = assignment['client_id']
        client_name = clients_info.get(client_id_iter, 'Unknown')
        
        if client_id_iter not in client_stats:
            client_stats[client_id_iter] = {
                'client_id': client_id_iter,
                'name': client_name,
                'total_progress': 0,
                'habit_count': 0,
                'total_streak': 0,
                'trainer_ids': set()
            }
        
        # Get habit assignments for this client
        habit_assignments = db.table('trainee_habit_assignments').select(
            'habit_id, trainer_id'
        ).eq('client_id', client_id_iter).eq('is_active', True).execute()
        
        for habit_assignment in habit_assignments.data:
            habit_id = habit_assignment['habit_id']
            trainer_id = habit_assignment['trainer_id']
            
            client_stats[client_id_iter]['trainer_ids'].add(trainer_id)
            client_stats[client_id_iter]['habit_count'] += 1
            
            # Calculate progress for this habit this month
            progress = calculate_habit_progress(db, habit_id, client_id_iter)
            client_stats[client_id_iter]['total_progress'] += progress.get('monthly_progress_percent', 0)
            
            # Calculate streak for this habit
            streak = calculate_habit_streak(db, habit_id, client_id_iter)
            client_stats[client_id_iter]['total_streak'] += streak
    
    # Calculate average progress and prepare leaderboard
    leaderboard = []
    for client_data in client_stats.values():
        if client_data['habit_count'] > 0:
            avg_progress = client_data['total_progress'] / client_data['habit_count']
            trainer_ids = list(client_data['trainer_ids'])
            
            leaderboard.append({
                'client_id': client_data['client_id'],
                'name': client_data['name'],
                'progress': round(avg_progress, 1),
                'habit_count': client_data['habit_count'],
                'total_streak': client_data['total_streak'],
                'trainer_ids': trainer_ids,
                'is_current_user': client_data['client_id'] == client_id
            })
    
    # Sort by progress (descending)
    leaderboard.sort(key=lambda x: x['progress'], reverse=True)
    
    # Add ranking
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1
    
    # Ensure current user is in top 10 or add them
    current_user_entry = next((entry for entry in leaderboard if entry['is_current_user']), None)
    top_10 = leaderboard[:10]
    
    if current_user_entry and current_user_entry not in top_10:
        top_10.append(current_user_entry)
    
    return top_10


@dashboard_bp.route('/client-habits/<user_id>/<token>')
def client_habits_view(user_id, token):
    """Client habits dashboard view with progress tracking and leaderboard"""
    try:
        # Validate token
        token_data = token_manager.validate_token(token, user_id)
        if not token_data or token_data['role'] != 'client':
            return render_template('dashboard/error.html', 
                                 error="Invalid or expired access token"), 403
        
        # Get user info
        user_info = dashboard_service.get_user_info(user_id, 'client')
        if not user_info:
            return render_template('dashboard/error.html', 
                                 error="User not found"), 404
        
        # Get date parameters from query string
        view_type = request.args.get('view', 'daily')  # daily or monthly
        selected_date = request.args.get('date')  # YYYY-MM-DD format
        selected_month = request.args.get('month')  # MM format
        selected_year = request.args.get('year')  # YYYY format
        
        # Get client's assigned habits
        assignments_result = dashboard_service.db.table('trainee_habit_assignments').select(
            '*, fitness_habits(*)'
        ).eq('client_id', user_id).eq('is_active', True).execute()
        
        habits = []
        if assignments_result.data:
            # Get unique trainer IDs to fetch trainer info
            trainer_ids = list(set(assignment.get('trainer_id') for assignment in assignments_result.data if assignment.get('trainer_id')))
            
            # Fetch trainer info
            trainers_info = {}
            if trainer_ids:
                trainers_result = dashboard_service.db.table('trainers').select('trainer_id, name').in_('trainer_id', trainer_ids).execute()
                if trainers_result.data:
                    trainers_info = {trainer['trainer_id']: trainer['name'] for trainer in trainers_result.data}
            
            for assignment in assignments_result.data:
                habit_data = assignment.get('fitness_habits')
                if habit_data:
                    # Add assignment and trainer info to habit data
                    habit_data['assigned_date'] = assignment.get('assigned_date')
                    habit_data['assignment_id'] = assignment.get('id')
                    trainer_id = assignment.get('trainer_id')
                    habit_data['trainer_id'] = trainer_id
                    habit_data['trainer_name'] = trainers_info.get(trainer_id, 'Unknown')
                    
                    # Calculate progress data based on selected date/month
                    if view_type == 'monthly' and selected_month and selected_year:
                        habit_progress = calculate_habit_progress_for_month(
                            dashboard_service.db, habit_data['habit_id'], user_id, 
                            selected_year, selected_month
                        )
                    elif view_type == 'daily' and selected_date:
                        habit_progress = calculate_habit_progress_for_date(
                            dashboard_service.db, habit_data['habit_id'], user_id, 
                            selected_date
                        )
                    else:
                        # Default to current day/month
                        habit_progress = calculate_habit_progress(dashboard_service.db, habit_data['habit_id'], user_id)
                    
                    habit_data.update(habit_progress)
                    
                    # Calculate streak
                    streak = calculate_habit_streak(dashboard_service.db, habit_data['habit_id'], user_id)
                    habit_data['streak_days'] = streak
                    
                    habits.append(habit_data)
        
        # Calculate statistics for the selected period
        stats = calculate_habit_statistics(habits, view_type, selected_date, selected_month, selected_year)
        
        # Calculate proper leaderboard with all users
        leaderboard = calculate_proper_leaderboard(dashboard_service.db, user_id, view_type, selected_date, selected_month, selected_year)
        
        return render_template('dashboard/client_habits.html',
                             user=user_info,
                             habits=habits,
                             stats=stats,
                             leaderboard=leaderboard,
                             view_type=view_type,
                             selected_date=selected_date,
                             selected_month=selected_month,
                             selected_year=selected_year)
        
    except Exception as e:
        log_error(f"Client habits dashboard error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the habits dashboard"), 500


@dashboard_bp.route('/trainer/<user_id>/<token>')
def trainer_main_dashboard(user_id, token):
    """Main trainer dashboard with trainee list and management"""
    try:
        # Validate token
        token_data = token_manager.validate_token(token, user_id)
        if not token_data or token_data['role'] != 'trainer':
            return render_template('dashboard/error.html', 
                                 error="Invalid or expired access token"), 403
        
        # Get user info
        user_info = dashboard_service.get_user_info(user_id, 'trainer')
        if not user_info:
            return render_template('dashboard/error.html', 
                                 error="User not found"), 404
        
        # Get trainer's trainees with progress data
        trainees = get_trainer_trainees_with_progress(dashboard_service.db, user_id)
        
        # Calculate trainer stats
        trainer_stats = calculate_trainer_stats(dashboard_service.db, user_id, trainees)
        
        return render_template('dashboard/trainer_main.html',
                             user=user_info,
                             trainees=trainees,
                             stats=trainer_stats)
        
    except Exception as e:
        log_error(f"Trainer main dashboard error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the trainer dashboard"), 500


@dashboard_bp.route('/trainer/<user_id>/<token>/trainee/<trainee_id>')
def trainer_trainee_detail(user_id, token, trainee_id):
    """Detailed view of specific trainee's progress"""
    try:
        # Validate token
        token_data = token_manager.validate_token(token, user_id)
        if not token_data or token_data['role'] != 'trainer':
            return render_template('dashboard/error.html', 
                                 error="Invalid or expired access token"), 403
        
        # Get user info
        user_info = dashboard_service.get_user_info(user_id, 'trainer')
        if not user_info:
            return render_template('dashboard/error.html', 
                                 error="User not found"), 404
        
        # Get trainee info
        trainee_result = dashboard_service.db.table('clients').select('*').eq('client_id', trainee_id).execute()
        if not trainee_result.data:
            return render_template('dashboard/error.html', 
                                 error="Trainee not found"), 404
        
        trainee = trainee_result.data[0]
        
        # Get trainee's habits assigned by this trainer
        trainee_habits = get_trainee_habits_with_progress(dashboard_service.db, user_id, trainee_id)
        
        # Get leaderboard for this trainer's trainees
        leaderboard = calculate_trainer_leaderboard(dashboard_service.db, user_id, trainee_id)
        
        # Calculate trainee detailed stats
        trainee_stats = calculate_trainee_detailed_stats(dashboard_service.db, user_id, trainee_id)
        
        return render_template('dashboard/trainer_trainee_detail.html',
                             user=user_info,
                             trainee=trainee,
                             habits=trainee_habits,
                             leaderboard=leaderboard,
                             stats=trainee_stats)
        
    except Exception as e:
        log_error(f"Trainer trainee detail error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the trainee details"), 500


@dashboard_bp.route('/api/<user_id>/<token>/export')
def api_export_csv(user_id, token):
    """API endpoint to export relationships as CSV"""
    try:
        # Validate token
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        from datetime import datetime
        result = dashboard_service.db.table('dashboard_tokens').select('*').eq(
            'token_hash', token_hash
        ).eq('user_id', user_id).gt(
            'expires_at', datetime.now().isoformat()
        ).execute()
        
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 403
        
        token_data = result.data[0]
        
        # Get relationships
        relationships = dashboard_service.get_relationships(user_id, token_data['role'])
        
        # Generate CSV
        import csv
        import io
        from flask import make_response
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        if token_data['role'] == 'trainer':
            writer.writerow(['Name', 'Client ID', 'Phone', 'Email', 'Goals', 'Experience', 'Connected Date'])
        else:
            writer.writerow(['Name', 'Trainer ID', 'Phone', 'Email', 'Specialization', 'Experience', 'City', 'Connected Date'])
        
        # Write data
        for rel in relationships:
            if token_data['role'] == 'trainer':
                writer.writerow([
                    rel['name'], rel['id'], rel['phone'], rel['email'],
                    rel['additional_info'].get('goals', ''),
                    rel['additional_info'].get('experience', ''),
                    rel['connected_date']
                ])
            else:
                writer.writerow([
                    rel['name'], rel['id'], rel['phone'], rel['email'],
                    rel['additional_info'].get('specialization', ''),
                    rel['additional_info'].get('experience', ''),
                    rel['additional_info'].get('city', ''),
                    rel['connected_date']
                ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename={token_data["role"]}_{user_id}_relationships.csv'
        
        return response
        
    except Exception as e:
        log_error(f"Export CSV error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def calculate_habit_statistics(habits, view_type, selected_date=None, selected_month=None, selected_year=None):
    """Calculate habit statistics for the selected period"""
    try:
        stats = {
            'active_habits': 0,
            'fully_completed': 0,
            'working_habits': 0,
            'not_started': 0,
            'trainers': set()
        }
        
        for habit in habits:
            # Count active habits
            stats['active_habits'] += 1
            
            # Count unique trainers
            if habit.get('trainer_id'):
                stats['trainers'].add(habit.get('trainer_id'))
            
            # Determine progress status based on view type
            if view_type == 'daily':
                progress_percent = habit.get('daily_progress_percent', 0)
            else:  # monthly
                progress_percent = habit.get('monthly_progress_percent', 0)
            
            # Categorize habits based on progress
            if progress_percent >= 100:
                stats['fully_completed'] += 1
            elif progress_percent > 0:
                stats['working_habits'] += 1
            else:
                stats['not_started'] += 1
        
        # Convert trainers set to count
        stats['trainers'] = len(stats['trainers'])
        
        return stats
        
    except Exception as e:
        log_error(f"Error calculating habit statistics: {str(e)}")
        return {
            'active_habits': 0,
            'fully_completed': 0,
            'working_habits': 0,
            'not_started': 0,
            'trainers': 0
        }


def calculate_proper_leaderboard(db, current_user_id, view_type='daily', selected_date=None, selected_month=None, selected_year=None):
    """Calculate proper leaderboard based on actual habit logs and assignments"""
    try:
        from datetime import datetime, date
        import calendar
        
        # Determine date range based on view type
        if view_type == 'daily':
            if selected_date:
                target_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            date_filter = target_date
            date_range = (target_date, target_date)
        else:  # monthly
            if selected_month and selected_year:
                year_int = int(selected_year)
                month_int = int(selected_month)
            else:
                now = datetime.now()
                year_int = now.year
                month_int = now.month
            
            # Get first and last day of month
            first_day = date(year_int, month_int, 1)
            last_day = date(year_int, month_int, calendar.monthrange(year_int, month_int)[1])
            date_range = (first_day, last_day)
        
        # Get all active habit assignments with client and habit info
        assignments_query = db.table('trainee_habit_assignments').select(
            'client_id, habit_id, fitness_habits(habit_name, target_value, unit, frequency)'
        ).eq('is_active', True).execute()
        
        if not assignments_query.data:
            return []
        
        # Get all client names
        client_ids = list(set(assignment['client_id'] for assignment in assignments_query.data))
        clients_query = db.table('clients').select('client_id, name').in_('client_id', client_ids).execute()
        clients_info = {client['client_id']: client['name'] for client in clients_query.data} if clients_query.data else {}
        
        # Get habit logs for the date range
        if view_type == 'daily':
            logs_query = db.table('habit_logs').select(
                'client_id, habit_id, completed_value, log_date'
            ).eq('log_date', date_range[0].isoformat()).execute()
        else:  # monthly
            logs_query = db.table('habit_logs').select(
                'client_id, habit_id, completed_value, log_date'
            ).gte('log_date', date_range[0].isoformat()).lte('log_date', date_range[1].isoformat()).execute()
        
        # Process logs to get latest entry per habit per day (in case of multiple entries)
        processed_logs = {}
        for log in logs_query.data if logs_query.data else []:
            key = f"{log['client_id']}_{log['habit_id']}_{log['log_date']}"
            if key not in processed_logs:
                processed_logs[key] = log
            # Keep the one with higher completed_value if multiple entries same day
            elif float(log['completed_value']) > float(processed_logs[key]['completed_value']):
                processed_logs[key] = log
        
        # Calculate stats for each client
        client_stats = {}
        
        for assignment in assignments_query.data:
            client_id = assignment['client_id']
            habit_id = assignment['habit_id']
            habit_info = assignment.get('fitness_habits', {})
            
            if not habit_info:
                continue
                
            if client_id not in client_stats:
                client_stats[client_id] = {
                    'client_id': client_id,
                    'name': clients_info.get(client_id, 'Unknown'),
                    'total_progress': 0,
                    'habit_count': 0,
                    'total_streak': 0,
                    'habits_data': []
                }
            
            client_stats[client_id]['habit_count'] += 1
            
            # Calculate progress for this habit
            target_value = float(habit_info.get('target_value', 1))
            
            if view_type == 'daily':
                # For daily view, check if there's a log for the target date
                log_key = f"{client_id}_{habit_id}_{date_range[0].isoformat()}"
                if log_key in processed_logs:
                    completed_value = float(processed_logs[log_key]['completed_value'])
                    progress_percent = min(100, (completed_value / target_value) * 100)
                else:
                    progress_percent = 0
                    
                client_stats[client_id]['total_progress'] += progress_percent
                
            else:  # monthly
                # For monthly view, sum all logs in the month
                total_completed = 0
                days_in_month = calendar.monthrange(year_int, month_int)[1]
                
                for day in range(1, days_in_month + 1):
                    day_date = date(year_int, month_int, day)
                    log_key = f"{client_id}_{habit_id}_{day_date.isoformat()}"
                    if log_key in processed_logs:
                        total_completed += float(processed_logs[log_key]['completed_value'])
                
                # Calculate monthly progress (target * days in month)
                monthly_target = target_value * days_in_month
                progress_percent = min(100, (total_completed / monthly_target) * 100) if monthly_target > 0 else 0
                client_stats[client_id]['total_progress'] += progress_percent
            
            # Calculate streak for this habit (simplified - count consecutive days with logs)
            streak = calculate_habit_streak(db, habit_id, client_id)
            client_stats[client_id]['total_streak'] += streak
        
        # Create leaderboard entries
        leaderboard = []
        for client_data in client_stats.values():
            if client_data['habit_count'] > 0:
                avg_progress = client_data['total_progress'] / client_data['habit_count']
                leaderboard.append({
                    'client_id': client_data['client_id'],
                    'name': client_data['name'],
                    'progress': round(avg_progress, 1),
                    'habit_count': client_data['habit_count'],
                    'total_streak': client_data['total_streak'],
                    'is_current_user': client_data['client_id'] == current_user_id
                })
        
        # Sort by progress (descending), then by total_streak (descending)
        leaderboard.sort(key=lambda x: (x['progress'], x['total_streak']), reverse=True)
        
        # Add ranks and limit to top 10 + current user
        for i, entry in enumerate(leaderboard):
            entry['rank'] = i + 1
        
        # Ensure current user is included even if not in top 10
        top_10 = leaderboard[:10]
        current_user_entry = next((entry for entry in leaderboard if entry['is_current_user']), None)
        
        if current_user_entry and current_user_entry not in top_10:
            top_10.append(current_user_entry)
        
        return top_10
        
    except Exception as e:
        log_error(f"Error calculating proper leaderboard: {str(e)}")
        return []