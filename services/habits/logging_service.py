"""
Logging Service - Habit log management
Handles logging habit completions and calculating progress
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple


def log_error(message: str):
    """Log error message"""
    print(f"[ERROR] {message}")


def log_info(message: str):
    """Log info message"""
    print(f"[INFO] {message}")


class LoggingService:
    """Service for managing habit logs"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    def log_habit(
        self, 
        client_id: str, 
        habit_id: str, 
        value: float, 
        notes: Optional[str] = None,
        log_date: Optional[date] = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Create a habit log entry
        Multiple logs per day are allowed
        
        Args:
            client_id: Client ID
            habit_id: Habit ID
            value: Completed value
            notes: Optional notes
            log_date: Optional date (defaults to today)
            
        Returns:
            Tuple of (success, message, log_data)
        """
        try:
            # Verify habit is assigned to client
            assignment = self.db.table('trainee_habit_assignments')\
                .select('*')\
                .eq('client_id', client_id)\
                .eq('habit_id', habit_id)\
                .eq('is_active', True)\
                .execute()
            
            if not assignment.data:
                return False, "This habit is not assigned to you", None
            
            # Prepare log entry
            log_entry = {
                'habit_id': habit_id,
                'client_id': client_id,
                'log_date': log_date.isoformat() if log_date else date.today().isoformat(),
                'completed_value': float(value),
                'notes': notes
            }
            
            # Insert log
            result = self.db.table('habit_logs').insert(log_entry).execute()
            
            if result.data:
                log_info(f"Habit logged: {habit_id} by {client_id}, value: {value}")
                return True, "Habit logged successfully", result.data[0]
            else:
                return False, "Failed to log habit", None
                
        except Exception as e:
            log_error(f"Error logging habit: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    def get_daily_logs(
        self, 
        client_id: str, 
        log_date: Optional[date] = None
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Get all habit logs for a client on a specific date
        
        Returns:
            Tuple of (success, message, logs_list)
        """
        try:
            target_date = log_date if log_date else date.today()
            
            result = self.db.table('habit_logs')\
                .select('*')\
                .eq('client_id', client_id)\
                .eq('log_date', target_date.isoformat())\
                .order('log_time', desc=True)\
                .execute()
            
            if result.data:
                return True, f"Found {len(result.data)} logs", result.data
            else:
                return True, "No logs found for this date", []
                
        except Exception as e:
            log_error(f"Error getting daily logs: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def get_habit_logs(
        self, 
        client_id: str, 
        habit_id: str, 
        start_date: date, 
        end_date: date
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Get habit logs for a date range
        
        Returns:
            Tuple of (success, message, logs_list)
        """
        try:
            result = self.db.table('habit_logs')\
                .select('*')\
                .eq('client_id', client_id)\
                .eq('habit_id', habit_id)\
                .gte('log_date', start_date.isoformat())\
                .lte('log_date', end_date.isoformat())\
                .order('log_date', desc=True)\
                .order('log_time', desc=True)\
                .execute()
            
            if result.data:
                return True, f"Found {len(result.data)} logs", result.data
            else:
                return True, "No logs found for this period", []
                
        except Exception as e:
            log_error(f"Error getting habit logs: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def calculate_daily_progress(
        self, 
        client_id: str, 
        log_date: Optional[date] = None
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Calculate progress for all habits on a specific date
        
        Returns:
            Tuple of (success, message, progress_list)
            Each progress item contains: habit_id, habit_name, target, completed, due, percentage
        """
        try:
            target_date = log_date if log_date else date.today()
            
            # Get all assigned habits
            assignments = self.db.table('trainee_habit_assignments')\
                .select('*, fitness_habits(*)')\
                .eq('client_id', client_id)\
                .eq('is_active', True)\
                .execute()
            
            if not assignments.data:
                return True, "No habits assigned", []
            
            progress_list = []
            
            for assignment in assignments.data:
                habit = assignment.get('fitness_habits')
                if not habit:
                    continue
                
                habit_id = habit.get('habit_id')
                
                # Get all logs for this habit on this date
                logs = self.db.table('habit_logs')\
                    .select('completed_value')\
                    .eq('client_id', client_id)\
                    .eq('habit_id', habit_id)\
                    .eq('log_date', target_date.isoformat())\
                    .execute()
                
                # Calculate totals
                total_completed = sum(log.get('completed_value', 0) for log in logs.data) if logs.data else 0
                target = float(habit.get('target_value', 0))
                due = max(0, target - total_completed)
                percentage = (total_completed / target * 100) if target > 0 else 0
                
                progress_list.append({
                    'habit_id': habit_id,
                    'habit_name': habit.get('habit_name'),
                    'target': target,
                    'unit': habit.get('unit'),
                    'completed': total_completed,
                    'due': due,
                    'percentage': round(percentage, 1),
                    'log_count': len(logs.data) if logs.data else 0
                })
            
            return True, f"Progress calculated for {len(progress_list)} habits", progress_list
            
        except Exception as e:
            log_error(f"Error calculating daily progress: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def calculate_habit_progress(
        self, 
        client_id: str, 
        habit_id: str, 
        log_date: Optional[date] = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Calculate progress for a specific habit on a specific date
        
        Returns:
            Tuple of (success, message, progress_dict)
        """
        try:
            target_date = log_date if log_date else date.today()
            
            # Get habit details (case-insensitive)
            habit_result = self.db.table('fitness_habits')\
                .select('*')\
                .ilike('habit_id', habit_id)\
                .execute()
            
            if not habit_result.data:
                return False, "Habit not found", None
            
            habit = habit_result.data[0]
            
            # Get all logs for this date
            logs = self.db.table('habit_logs')\
                .select('completed_value')\
                .eq('client_id', client_id)\
                .eq('habit_id', habit_id)\
                .eq('log_date', target_date.isoformat())\
                .execute()
            
            # Calculate totals
            total_completed = sum(log.get('completed_value', 0) for log in logs.data) if logs.data else 0
            target = float(habit.get('target_value', 0))
            due = max(0, target - total_completed)
            percentage = (total_completed / target * 100) if target > 0 else 0
            
            progress = {
                'habit_id': habit_id,
                'habit_name': habit.get('habit_name'),
                'target': target,
                'unit': habit.get('unit'),
                'completed': total_completed,
                'due': due,
                'percentage': round(percentage, 1),
                'log_count': len(logs.data) if logs.data else 0,
                'date': target_date.isoformat()
            }
            
            return True, "Progress calculated", progress
            
        except Exception as e:
            log_error(f"Error calculating habit progress: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    def get_weekly_summary(
        self, 
        client_id: str, 
        week_start: date
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Get weekly summary for all habits
        
        Returns:
            Tuple of (success, message, summary_list)
        """
        try:
            week_end = week_start + timedelta(days=6)
            
            # Get all assigned habits
            assignments = self.db.table('trainee_habit_assignments')\
                .select('*, fitness_habits(*)')\
                .eq('client_id', client_id)\
                .eq('is_active', True)\
                .execute()
            
            if not assignments.data:
                return True, "No habits assigned", []
            
            summary_list = []
            
            for assignment in assignments.data:
                habit = assignment.get('fitness_habits')
                if not habit:
                    continue
                
                habit_id = habit.get('habit_id')
                
                # Get all logs for this week
                logs = self.db.table('habit_logs')\
                    .select('log_date, completed_value')\
                    .eq('client_id', client_id)\
                    .eq('habit_id', habit_id)\
                    .gte('log_date', week_start.isoformat())\
                    .lte('log_date', week_end.isoformat())\
                    .execute()
                
                # Calculate daily totals
                daily_totals = {}
                for log in (logs.data if logs.data else []):
                    log_date = log.get('log_date')
                    value = log.get('completed_value', 0)
                    daily_totals[log_date] = daily_totals.get(log_date, 0) + value
                
                target = float(habit.get('target_value', 0))
                days_logged = len(daily_totals)
                total_completed = sum(daily_totals.values())
                total_target = target * 7
                avg_completion = (total_completed / total_target * 100) if total_target > 0 else 0
                
                summary_list.append({
                    'habit_id': habit_id,
                    'habit_name': habit.get('habit_name'),
                    'target_per_day': target,
                    'unit': habit.get('unit'),
                    'days_logged': days_logged,
                    'total_completed': total_completed,
                    'total_target': total_target,
                    'avg_completion': round(avg_completion, 1),
                    'daily_totals': daily_totals
                })
            
            return True, f"Weekly summary for {len(summary_list)} habits", summary_list
            
        except Exception as e:
            log_error(f"Error getting weekly summary: {str(e)}")
            return False, f"Error: {str(e)}", []
