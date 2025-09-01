# [Previous dashboard.py content remains unchanged until after the existing endpoints]

@dashboard_bp.route('/api/dashboard/calendar/month', methods=['GET'])
@token_required
def get_month_view():
    """Get month view calendar data"""
    try:
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        
        # Get all bookings for month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
            
        bookings = dashboard_service.db.table('bookings').select(
            '*, clients(name)'
        ).eq('trainer_id', request.trainer_id).gte(
            'session_date', start_date.isoformat()
        ).lt('session_date', end_date.isoformat()).execute()
        
        # Format data by date
        calendar_data = {}
        today = datetime.now().date()
        
        for booking in (bookings.data or []):
            date = booking['session_date']
            if date not in calendar_data:
                calendar_data[date] = []
                
            client_name = booking['clients']['name']
            calendar_data[date].append({
                'client_abbrev': f"{client_name.split()[0][0]}{client_name.split()[-1][0]}",
                'time': booking['session_time'],
                'type': booking['session_type'],
                'color': '#4CAF50' if booking['status'] == 'completed' else '#2196F3'
            })
        
        return jsonify({
            'calendar_data': calendar_data,
            'today': today.isoformat(),
            'month_stats': {
                'total_sessions': len(bookings.data or []),
                'completed': sum(1 for b in (bookings.data or []) if b['status'] == 'completed')
            }
        })
        
    except Exception as e:
        log_error(f"Month view error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/calendar/week', methods=['GET'])
@token_required
def get_week_view():
    """Get week view calendar data"""
    try:
        date_str = request.args.get('date')
        if date_str:
            start_date = datetime.fromisoformat(date_str).date()
        else:
            start_date = datetime.now().date()
            
        # Adjust to start of week (Monday)
        while start_date.weekday() != 0:
            start_date -= timedelta(days=1)
            
        end_date = start_date + timedelta(days=7)
        
        bookings = dashboard_service.db.table('bookings').select(
            '*, clients(name, phone_number)'
        ).eq('trainer_id', request.trainer_id).gte(
            'session_date', start_date.isoformat()
        ).lt('session_date', end_date.isoformat()).execute()
        
        # Generate time slots
        time_slots = []
        for hour in range(6, 21):  # 6:00 to 20:00
            time_slots.append(f"{hour:02d}:00")
            time_slots.append(f"{hour:02d}:30")
            
        # Format data
        week_data = {}
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            week_data[current_date.isoformat()] = {
                'date_str': current_date.strftime('%Y-%m-%d'),
                'day_name': current_date.strftime('%A'),
                'slots': {
                    slot: None for slot in time_slots
                }
            }
            
        # Fill in bookings
        for booking in (bookings.data or []):
            date = booking['session_date']
            time = booking['session_time']
            if time in week_data[date]['slots']:
                week_data[date]['slots'][time] = {
                    'client_name': booking['clients']['name'],
                    'phone': booking['clients']['phone_number'],
                    'type': booking['session_type'],
                    'status': booking['status']
                }
                
        return jsonify({
            'week_data': week_data,
            'time_slots': time_slots
        })
        
    except Exception as e:
        log_error(f"Week view error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/calendar/day', methods=['GET'])
@token_required
def get_day_view():
    """Get detailed day view calendar data"""
    try:
        date_str = request.args.get('date', datetime.now().date().isoformat())
        
        bookings = dashboard_service.db.table('bookings').select(
            '*, clients(*)'
        ).eq('trainer_id', request.trainer_id).eq(
            'session_date', date_str
        ).order('session_time').execute()
        
        return jsonify({
            'date': date_str,
            'sessions': [{
                'id': booking['id'],
                'time': booking['session_time'],
                'client': {
                    'name': booking['clients']['name'],
                    'phone': booking['clients']['phone_number'],
                    'email': booking['clients']['email']
                },
                'type': booking['session_type'],
                'status': booking['status'],
                'notes': booking['notes'],
                'quick_actions': [
                    {'label': 'Complete', 'action': 'complete'},
                    {'label': 'Reschedule', 'action': 'reschedule'},
                    {'label': 'Cancel', 'action': 'cancel'}
                ]
            } for booking in (bookings.data or [])]
        })
        
    except Exception as e:
        log_error(f"Day view error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/calendar/preferences', methods=['POST'])
@token_required
def update_calendar_preferences():
    """Update calendar view preferences"""
    try:
        prefs = request.json
        
        result = dashboard_service.db.table('calendar_preferences').upsert({
            'trainer_id': request.trainer_id,
            'default_view': prefs.get('default_view', 'month'),
            'color_scheme': prefs.get('color_scheme', {}),
            'start_time': prefs.get('start_time', '06:00'),
            'end_time': prefs.get('end_time', '20:00'),
            'updated_at': datetime.utcnow().isoformat()
        }).execute()
        
        return jsonify({'success': True, 'message': 'Preferences updated'})
        
    except Exception as e:
        log_error(f"Update preferences error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@dashboard_bp.route('/api/dashboard/calendar/availability', methods=['GET'])
@token_required
def get_availability():
    """Get trainer availability"""
    try:
        date_str = request.args.get('date', datetime.now().date().isoformat())
        
        # Get trainer schedule
        schedule = dashboard_service.db.table('trainer_schedules').select(
            'schedule'
        ).eq('trainer_id', request.trainer_id).single().execute()
        
        # Get existing bookings
        bookings = dashboard_service.db.table('bookings').select(
            'session_time'
        ).eq('trainer_id', request.trainer_id).eq(
            'session_date', date_str
        ).in_('status', ['confirmed', 'rescheduled']).execute()
        
        booked_times = [b['session_time'] for b in (bookings.data or [])]
        
        # Get day's schedule
        day_name = datetime.fromisoformat(date_str).strftime('%A').lower()
        day_schedule = schedule.data['schedule'].get(day_name, []) if schedule.data else []
        
        return jsonify({
            'date': date_str,
            'available_slots': [
                slot for slot in day_schedule
                if slot not in booked_times
            ]
        })
        
    except Exception as e:
        log_error(f"Availability error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500