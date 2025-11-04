"""
Assignment Service - Habit assignment management
Handles assigning habits to clients and managing assignments
"""

from typing import Dict, List, Optional, Tuple


def log_error(message: str):
    """Log error message"""
    print(f"[ERROR] {message}")


def log_info(message: str):
    """Log info message"""
    print(f"[INFO] {message}")


class AssignmentService:
    """Service for managing habit assignments"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    def assign_habit(
        self, 
        habit_id: str, 
        client_ids: List[str], 
        trainer_id: str
    ) -> Tuple[bool, str, Dict]:
        """
        Assign a habit to one or more clients
        
        Args:
            habit_id: Habit ID to assign
            client_ids: List of client IDs
            trainer_id: Trainer ID (for verification)
            
        Returns:
            Tuple of (success, message, results_dict)
            results_dict contains: {'assigned': [], 'already_assigned': [], 'failed': []}
        """
        try:
            results = {
                'assigned': [],
                'already_assigned': [],
                'failed': []
            }
            
            # Verify habit exists and belongs to trainer (case-insensitive)
            habit_result = self.db.table('fitness_habits')\
                .select('*')\
                .ilike('habit_id', habit_id)\
                .eq('trainer_id', trainer_id)\
                .eq('is_active', True)\
                .execute()
            
            if not habit_result.data:
                return False, "Habit not found or doesn't belong to you", results
            
            # Get the actual habit_id from database
            actual_habit_id = habit_result.data[0].get('habit_id')
            
            # Process each client
            for client_id in client_ids:
                # Check if already assigned
                existing = self.db.table('trainee_habit_assignments')\
                    .select('*')\
                    .eq('habit_id', actual_habit_id)\
                    .eq('client_id', client_id)\
                    .execute()
                
                if existing.data:
                    # Check if active
                    if existing.data[0].get('is_active'):
                        results['already_assigned'].append(client_id)
                    else:
                        # Reactivate assignment
                        update_result = self.db.table('trainee_habit_assignments')\
                            .update({'is_active': True})\
                            .eq('habit_id', actual_habit_id)\
                            .eq('client_id', client_id)\
                            .execute()
                        
                        if update_result.data:
                            results['assigned'].append(client_id)
                        else:
                            results['failed'].append(client_id)
                else:
                    # Create new assignment
                    assignment_data = {
                        'habit_id': actual_habit_id,
                        'client_id': client_id,
                        'trainer_id': trainer_id,
                        'is_active': True
                    }
                    
                    insert_result = self.db.table('trainee_habit_assignments')\
                        .insert(assignment_data)\
                        .execute()
                    
                    if insert_result.data:
                        results['assigned'].append(client_id)
                        log_info(f"Habit {habit_id} assigned to client {client_id}")
                    else:
                        results['failed'].append(client_id)
            
            # Build message
            msg_parts = []
            if results['assigned']:
                msg_parts.append(f"✅ Assigned to {len(results['assigned'])} client(s)")
            if results['already_assigned']:
                msg_parts.append(f"ℹ️ {len(results['already_assigned'])} already assigned")
            if results['failed']:
                msg_parts.append(f"❌ {len(results['failed'])} failed")
            
            message = "\n".join(msg_parts) if msg_parts else "No assignments made"
            success = len(results['assigned']) > 0
            
            return success, message, results
            
        except Exception as e:
            log_error(f"Error assigning habit: {str(e)}")
            return False, f"Error: {str(e)}", {'assigned': [], 'already_assigned': [], 'failed': []}
    
    def get_client_habits(
        self, 
        client_id: str, 
        active_only: bool = True
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Get all habits assigned to a client with habit details
        
        Returns:
            Tuple of (success, message, habits_list)
        """
        try:
            # Get assignments
            query = self.db.table('trainee_habit_assignments')\
                .select('*, fitness_habits(*)')\
                .eq('client_id', client_id)
            
            if active_only:
                query = query.eq('is_active', True)
            
            result = query.order('assigned_date', desc=True).execute()
            
            if result.data:
                # Flatten the data structure
                habits = []
                for assignment in result.data:
                    if assignment.get('fitness_habits'):
                        habit_data = assignment['fitness_habits']
                        habit_data['assigned_date'] = assignment.get('assigned_date')
                        habit_data['assignment_id'] = assignment.get('id')
                        habits.append(habit_data)
                
                return True, f"Found {len(habits)} habits", habits
            else:
                return True, "No habits assigned", []
                
        except Exception as e:
            log_error(f"Error getting client habits: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def get_client_habits_by_trainer(
        self, 
        client_id: str, 
        trainer_id: str,
        active_only: bool = True
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Get habits assigned to a client by a specific trainer only
        
        Returns:
            Tuple of (success, message, habits_list)
        """
        try:
            # Get assignments by specific trainer only
            query = self.db.table('trainee_habit_assignments')\
                .select('*, fitness_habits(*)')\
                .eq('client_id', client_id)\
                .eq('trainer_id', trainer_id)
            
            if active_only:
                query = query.eq('is_active', True)
            
            result = query.order('assigned_date', desc=True).execute()
            
            if result.data:
                # Flatten the data structure
                habits = []
                for assignment in result.data:
                    if assignment.get('fitness_habits'):
                        habit_data = assignment['fitness_habits']
                        habit_data['assigned_date'] = assignment.get('assigned_date')
                        habit_data['assignment_id'] = assignment.get('id')
                        habits.append(habit_data)
                
                return True, f"Found {len(habits)} habits assigned by this trainer", habits
            else:
                return True, "No habits assigned by this trainer", []
                
        except Exception as e:
            log_error(f"Error getting client habits by trainer: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def get_habit_assignments(
        self, 
        habit_id: str, 
        active_only: bool = True
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Get all clients assigned to a habit
        
        Returns:
            Tuple of (success, message, assignments_list)
        """
        try:
            query = self.db.table('trainee_habit_assignments')\
                .select('*')\
                .eq('habit_id', habit_id)
            
            if active_only:
                query = query.eq('is_active', True)
            
            result = query.order('assigned_date', desc=True).execute()
            
            if result.data:
                return True, f"Found {len(result.data)} assignments", result.data
            else:
                return True, "No assignments found", []
                
        except Exception as e:
            log_error(f"Error getting habit assignments: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def unassign_habit(
        self, 
        habit_id: str, 
        client_id: str, 
        trainer_id: str
    ) -> Tuple[bool, str]:
        """
        Unassign a habit from a client (soft delete)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify assignment exists and belongs to trainer
            result = self.db.table('trainee_habit_assignments')\
                .select('*')\
                .eq('habit_id', habit_id)\
                .eq('client_id', client_id)\
                .eq('trainer_id', trainer_id)\
                .execute()
            
            if not result.data:
                return False, "Assignment not found"
            
            # Soft delete
            update_result = self.db.table('trainee_habit_assignments')\
                .update({'is_active': False})\
                .eq('habit_id', habit_id)\
                .eq('client_id', client_id)\
                .execute()
            
            if update_result.data:
                log_info(f"Habit {habit_id} unassigned from client {client_id}")
                return True, "Habit unassigned successfully"
            else:
                return False, "Failed to unassign habit"
                
        except Exception as e:
            log_error(f"Error unassigning habit: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def unassign_all_for_habit(
        self, 
        habit_id: str, 
        trainer_id: str
    ) -> Tuple[bool, str, int]:
        """
        Unassign a habit from all clients
        
        Returns:
            Tuple of (success, message, count_unassigned)
        """
        try:
            # Get all active assignments for this habit
            result = self.db.table('trainee_habit_assignments')\
                .select('*')\
                .eq('habit_id', habit_id)\
                .eq('trainer_id', trainer_id)\
                .eq('is_active', True)\
                .execute()
            
            if not result.data:
                return True, "No active assignments found", 0
            
            count = len(result.data)
            
            # Soft delete all
            update_result = self.db.table('trainee_habit_assignments')\
                .update({'is_active': False})\
                .eq('habit_id', habit_id)\
                .eq('trainer_id', trainer_id)\
                .execute()
            
            if update_result.data:
                log_info(f"Habit {habit_id} unassigned from {count} clients")
                return True, f"Unassigned from {count} client(s)", count
            else:
                return False, "Failed to unassign habit", 0
                
        except Exception as e:
            log_error(f"Error unassigning all: {str(e)}")
            return False, f"Error: {str(e)}", 0
    
    def verify_client_has_habit(
        self, 
        client_id: str, 
        habit_id: str
    ) -> bool:
        """
        Check if a client has an active assignment for a habit
        
        Returns:
            True if client has active assignment, False otherwise
        """
        try:
            result = self.db.table('trainee_habit_assignments')\
                .select('id')\
                .eq('client_id', client_id)\
                .eq('habit_id', habit_id)\
                .eq('is_active', True)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error verifying assignment: {str(e)}")
            return False
