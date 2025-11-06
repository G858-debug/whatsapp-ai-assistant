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
    """Trainee progress dashboard view"""
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
        
        # Get trainee's assigned habits
        assignments_result = dashboard_service.db.table('trainee_habit_assignments').select(
            'habit_id'
        ).eq('client_id', trainee_id).eq('trainer_id', user_id).eq('is_active', True).execute()
        
        habit_ids = [a['habit_id'] for a in assignments_result.data] if assignments_result.data else []
        
        habits = []
        if habit_ids:
            # Get habit details
            from services.habits.habit_service import HabitService
            habit_service = HabitService(dashboard_service.db)
            
            for habit_id in habit_ids:
                success, msg, habit = habit_service.get_habit_by_id(habit_id)
                if success and habit:
                    # Calculate progress data
                    habit_progress = calculate_habit_progress(dashboard_service.db, habit_id, trainee_id)
                    habit.update(habit_progress)
                    habits.append(habit)
        
        return render_template('dashboard/trainee_progress.html',
                             user=user_info,
                             trainee=trainee,
                             habits=habits)
        
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
    
    today = datetime.now().date()
    streak = 0
    current_date = today
    
    # Check backwards from today to find consecutive days with logs
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
        'client_id, clients(name)'
    ).eq('is_active', True).execute()
    
    if not clients_result.data:
        return []
    
    client_stats = {}
    
    # Calculate stats for each client
    for assignment in clients_result.data:
        client_id_iter = assignment['client_id']
        client_name = assignment.get('clients', {}).get('name', 'Unknown') if assignment.get('clients') else 'Unknown'
        
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


def calculate_client_leaderboard(db, client_id):
    """Calculate leaderboard for clients based on habit progress"""
    from datetime import datetime
    
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get all clients with habit assignments
    clients_result = db.table('trainee_habit_assignments').select(
        'client_id, clients(name)'
    ).eq('is_active', True).execute()
    
    if not clients_result.data:
        return []
    
    client_stats = {}
    
    # Calculate stats for each client
    for assignment in clients_result.data:
        client_id_iter = assignment['client_id']
        client_name = assignment.get('clients', {}).get('name', 'Unknown') if assignment.get('clients') else 'Unknown'
        
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
        
        # Get client's assigned habits with trainer info
        assignments_result = dashboard_service.db.table('trainee_habit_assignments').select(
            '*, fitness_habits(*), trainers(name)'
        ).eq('client_id', user_id).eq('is_active', True).execute()
        
        habits = []
        if assignments_result.data:
            for assignment in assignments_result.data:
                habit_data = assignment.get('fitness_habits')
                trainer_data = assignment.get('trainers')
                if habit_data:
                    # Add assignment and trainer info to habit data
                    habit_data['assigned_date'] = assignment.get('assigned_date')
                    habit_data['assignment_id'] = assignment.get('id')
                    habit_data['trainer_id'] = assignment.get('trainer_id')
                    habit_data['trainer_name'] = trainer_data.get('name') if trainer_data else 'Unknown'
                    
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
        
        # Get leaderboard data (for selected month if monthly view)
        if view_type == 'monthly' and selected_month and selected_year:
            leaderboard = calculate_client_leaderboard_for_month(
                dashboard_service.db, user_id, selected_year, selected_month
            )
        else:
            leaderboard = calculate_client_leaderboard(dashboard_service.db, user_id)
        
        return render_template('dashboard/client_habits.html',
                             user=user_info,
                             habits=habits,
                             leaderboard=leaderboard,
                             view_type=view_type,
                             selected_date=selected_date,
                             selected_month=selected_month,
                             selected_year=selected_year)
        
    except Exception as e:
        log_error(f"Client habits dashboard error: {str(e)}")
        return render_template('dashboard/error.html', 
                             error="An error occurred loading the habits dashboard"), 500


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