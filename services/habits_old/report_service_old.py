"""
Report Service - Generate habit progress reports
Handles CSV generation and report statistics
"""

import csv
import io
from datetime import date, timedelta
from calendar import monthrange
from typing import Dict, List, Optional, Tuple


def log_error(message: str):
    """Log error message"""
    print(f"[ERROR] {message}")


def log_info(message: str):
    """Log info message"""
    print(f"[INFO] {message}")


class ReportService:
    """Service for generating habit reports"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    def generate_weekly_report(
        self, 
        client_id: str, 
        week_start: date
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate weekly progress report as CSV
        
        Returns:
            Tuple of (success, message, csv_content)
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
                return False, "No habits assigned", None
            
            # Prepare CSV data
            csv_data = []
            summary_stats = {
                'total_habits': len(assignments.data),
                'total_days': 7,
                'total_logs': 0,
                'avg_completion': 0
            }
            
            # Process each habit
            for assignment in assignments.data:
                habit = assignment.get('fitness_habits')
                if not habit:
                    continue
                
                habit_id = habit.get('habit_id')
                habit_name = habit.get('habit_name')
                target = float(habit.get('target_value', 0))
                unit = habit.get('unit')
                
                # Get logs for the week
                logs = self.db.table('habit_logs')\
                    .select('log_date, completed_value')\
                    .eq('client_id', client_id)\
                    .eq('habit_id', habit_id)\
                    .gte('log_date', week_start.isoformat())\
                    .lte('log_date', week_end.isoformat())\
                    .order('log_date')\
                    .execute()
                
                # Calculate daily totals
                daily_totals = {}
                for log in (logs.data if logs.data else []):
                    log_date = log.get('log_date')
                    value = log.get('completed_value', 0)
                    daily_totals[log_date] = daily_totals.get(log_date, 0) + value
                
                # Create row for each day
                current_date = week_start
                for day in range(7):
                    date_str = current_date.isoformat()
                    completed = daily_totals.get(date_str, 0)
                    due = max(0, target - completed)
                    percentage = (completed / target * 100) if target > 0 else 0
                    
                    csv_data.append({
                        'Date': date_str,
                        'Day': current_date.strftime('%A'),
                        'Habit': habit_name,
                        'Target': target,
                        'Unit': unit,
                        'Completed': completed,
                        'Due': due,
                        'Completion %': round(percentage, 1)
                    })
                    
                    if completed > 0:
                        summary_stats['total_logs'] += 1
                    
                    current_date += timedelta(days=1)
            
            # Calculate average completion
            if csv_data:
                total_percentage = sum(row['Completion %'] for row in csv_data)
                summary_stats['avg_completion'] = round(total_percentage / len(csv_data), 1)
            
            # Generate CSV
            csv_content = self._generate_csv(csv_data, summary_stats, 'Weekly Report', week_start, week_end)
            
            log_info(f"Weekly report generated for client {client_id}")
            return True, "Weekly report generated", csv_content
            
        except Exception as e:
            log_error(f"Error generating weekly report: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    def generate_monthly_report(
        self, 
        client_id: str, 
        month: int, 
        year: int
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate monthly progress report as CSV
        
        Returns:
            Tuple of (success, message, csv_content)
        """
        try:
            # Get first and last day of month
            month_start = date(year, month, 1)
            last_day = monthrange(year, month)[1]
            month_end = date(year, month, last_day)
            
            # Get all assigned habits
            assignments = self.db.table('trainee_habit_assignments')\
                .select('*, fitness_habits(*)')\
                .eq('client_id', client_id)\
                .eq('is_active', True)\
                .execute()
            
            if not assignments.data:
                return False, "No habits assigned", None
            
            # Prepare CSV data
            csv_data = []
            summary_stats = {
                'total_habits': len(assignments.data),
                'total_days': last_day,
                'total_logs': 0,
                'avg_completion': 0
            }
            
            # Process each habit
            for assignment in assignments.data:
                habit = assignment.get('fitness_habits')
                if not habit:
                    continue
                
                habit_id = habit.get('habit_id')
                habit_name = habit.get('habit_name')
                target = float(habit.get('target_value', 0))
                unit = habit.get('unit')
                
                # Get logs for the month
                logs = self.db.table('habit_logs')\
                    .select('log_date, completed_value')\
                    .eq('client_id', client_id)\
                    .eq('habit_id', habit_id)\
                    .gte('log_date', month_start.isoformat())\
                    .lte('log_date', month_end.isoformat())\
                    .order('log_date')\
                    .execute()
                
                # Calculate daily totals
                daily_totals = {}
                for log in (logs.data if logs.data else []):
                    log_date = log.get('log_date')
                    value = log.get('completed_value', 0)
                    daily_totals[log_date] = daily_totals.get(log_date, 0) + value
                
                # Create row for each day
                current_date = month_start
                for day in range(last_day):
                    date_str = current_date.isoformat()
                    completed = daily_totals.get(date_str, 0)
                    due = max(0, target - completed)
                    percentage = (completed / target * 100) if target > 0 else 0
                    
                    csv_data.append({
                        'Date': date_str,
                        'Day': current_date.strftime('%A'),
                        'Habit': habit_name,
                        'Target': target,
                        'Unit': unit,
                        'Completed': completed,
                        'Due': due,
                        'Completion %': round(percentage, 1)
                    })
                    
                    if completed > 0:
                        summary_stats['total_logs'] += 1
                    
                    current_date += timedelta(days=1)
            
            # Calculate average completion
            if csv_data:
                total_percentage = sum(row['Completion %'] for row in csv_data)
                summary_stats['avg_completion'] = round(total_percentage / len(csv_data), 1)
            
            # Generate CSV
            csv_content = self._generate_csv(csv_data, summary_stats, 'Monthly Report', month_start, month_end)
            
            log_info(f"Monthly report generated for client {client_id}")
            return True, "Monthly report generated", csv_content
            
        except Exception as e:
            log_error(f"Error generating monthly report: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    def generate_trainer_report(
        self, 
        trainer_id: str, 
        client_id: str, 
        start_date: date, 
        end_date: date
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate trainer view of client progress
        
        Returns:
            Tuple of (success, message, csv_content)
        """
        try:
            # Verify client is in trainer's list using relationship service
            from services.relationships.relationship_service import RelationshipService
            relationship_service = RelationshipService(self.db)
            
            if not relationship_service.check_relationship_exists(trainer_id, client_id):
                return False, "Client not found in your list", None
            
            # Get habits assigned by this trainer to this client
            assignments = self.db.table('trainee_habit_assignments')\
                .select('*, fitness_habits(*)')\
                .eq('client_id', client_id)\
                .eq('trainer_id', trainer_id)\
                .eq('is_active', True)\
                .execute()
            
            if not assignments.data:
                return False, "No habits assigned to this client", None
            
            # Prepare CSV data
            csv_data = []
            summary_stats = {
                'total_habits': len(assignments.data),
                'total_days': (end_date - start_date).days + 1,
                'total_logs': 0,
                'avg_completion': 0
            }
            
            # Process each habit
            for assignment in assignments.data:
                habit = assignment.get('fitness_habits')
                if not habit:
                    continue
                
                habit_id = habit.get('habit_id')
                habit_name = habit.get('habit_name')
                target = float(habit.get('target_value', 0))
                unit = habit.get('unit')
                
                # Get logs for the period
                logs = self.db.table('habit_logs')\
                    .select('log_date, completed_value')\
                    .eq('client_id', client_id)\
                    .eq('habit_id', habit_id)\
                    .gte('log_date', start_date.isoformat())\
                    .lte('log_date', end_date.isoformat())\
                    .order('log_date')\
                    .execute()
                
                # Calculate daily totals
                daily_totals = {}
                for log in (logs.data if logs.data else []):
                    log_date = log.get('log_date')
                    value = log.get('completed_value', 0)
                    daily_totals[log_date] = daily_totals.get(log_date, 0) + value
                
                # Create row for each day
                current_date = start_date
                while current_date <= end_date:
                    date_str = current_date.isoformat()
                    completed = daily_totals.get(date_str, 0)
                    due = max(0, target - completed)
                    percentage = (completed / target * 100) if target > 0 else 0
                    
                    csv_data.append({
                        'Date': date_str,
                        'Day': current_date.strftime('%A'),
                        'Habit': habit_name,
                        'Target': target,
                        'Unit': unit,
                        'Completed': completed,
                        'Due': due,
                        'Completion %': round(percentage, 1)
                    })
                    
                    if completed > 0:
                        summary_stats['total_logs'] += 1
                    
                    current_date += timedelta(days=1)
            
            # Calculate average completion
            if csv_data:
                total_percentage = sum(row['Completion %'] for row in csv_data)
                summary_stats['avg_completion'] = round(total_percentage / len(csv_data), 1)
            
            # Generate CSV
            csv_content = self._generate_csv(csv_data, summary_stats, 'Trainer Report', start_date, end_date)
            
            log_info(f"Trainer report generated for client {client_id}")
            return True, "Trainer report generated", csv_content
            
        except Exception as e:
            log_error(f"Error generating trainer report: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    def _generate_csv(
        self, 
        data: List[Dict], 
        summary: Dict, 
        report_type: str, 
        start_date: date, 
        end_date: date
    ) -> str:
        """
        Generate CSV content from data
        
        Returns:
            CSV content as string
        """
        output = io.StringIO()
        
        # Write header
        output.write(f"{report_type}\n")
        output.write(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
        output.write(f"Generated: {date.today().strftime('%Y-%m-%d')}\n")
        output.write("\n")
        
        # Write data
        if data:
            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        # Write summary
        output.write("\n")
        output.write("SUMMARY STATISTICS\n")
        output.write(f"Total Habits,{summary.get('total_habits', 0)}\n")
        output.write(f"Total Days,{summary.get('total_days', 0)}\n")
        output.write(f"Days with Logs,{summary.get('total_logs', 0)}\n")
        output.write(f"Average Completion %,{summary.get('avg_completion', 0)}\n")
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
