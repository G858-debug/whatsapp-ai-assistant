"""
Habit Service - Core habit management operations
Handles CRUD operations for fitness habits
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


def log_error(message: str):
    """Log error message"""
    print(f"[ERROR] {message}")


def log_info(message: str):
    """Log info message"""
    print(f"[INFO] {message}")


class HabitService:
    """Service for managing fitness habits"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    def create_habit(
        self, 
        trainer_id: str, 
        habit_data: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new fitness habit
        
        Args:
            trainer_id: Trainer's unique ID
            habit_data: Dict containing habit_name, description, target_value, unit, frequency
            
        Returns:
            Tuple of (success, message, habit_id)
        """
        try:
            # Generate unique habit_id
            habit_name = habit_data.get('habit_name', '')
            habit_id = self._generate_habit_id(habit_name)
            
            # Prepare habit record
            habit_record = {
                'habit_id': habit_id,
                'trainer_id': trainer_id,
                'habit_name': habit_data.get('habit_name'),
                'description': habit_data.get('description'),
                'target_value': float(habit_data.get('target_value')),
                'unit': habit_data.get('unit'),
                'frequency': habit_data.get('frequency', 'daily'),
                'is_active': True
            }
            
            # Insert into database
            result = self.db.table('fitness_habits').insert(habit_record).execute()
            
            if result.data:
                log_info(f"Habit created successfully: {habit_id}")
                return True, f"Habit '{habit_data.get('habit_name')}' created successfully with ID: {habit_id}", habit_id
            else:
                log_error("Failed to create habit - no data returned")
                return False, "Failed to create habit", None
                
        except Exception as e:
            log_error(f"Error creating habit: {str(e)}")
            return False, f"Error creating habit: {str(e)}", None
    
    def _generate_habit_id(self, habit_name: str) -> str:
        """
        Generate unique habit ID (5-7 characters)
        Format: HAB + name-based + numbers
        Example: HAB123, HABWAT45
        """
        # Clean habit name - take first 3 letters
        clean_name = re.sub(r'[^a-zA-Z]', '', habit_name.upper())
        name_part = clean_name[:3] if len(clean_name) >= 3 else clean_name.ljust(3, 'X')
        
        # Try to generate unique ID
        for i in range(100):
            if i == 0:
                # First try: HAB + name_part
                habit_id = f"HAB{name_part}"
            else:
                # Add numbers for uniqueness
                habit_id = f"HAB{name_part}{i}"
            
            # Check if ID exists (case-insensitive)
            try:
                result = self.db.table('fitness_habits').select('habit_id').ilike('habit_id', habit_id).execute()
                if not result.data:
                    return habit_id
            except Exception as e:
                log_error(f"Error checking habit_id uniqueness: {str(e)}")
                continue
        
        # Fallback: use timestamp-based ID
        timestamp = datetime.now().strftime('%H%M%S')
        return f"HAB{timestamp[-6:]}"
    
    def get_habit_by_id(self, habit_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get habit by habit_id (case-insensitive)
        
        Returns:
            Tuple of (success, message, habit_data)
        """
        try:
            result = self.db.table('fitness_habits').select('*').ilike('habit_id', habit_id).execute()
            
            if result.data and len(result.data) > 0:
                return True, "Habit found", result.data[0]
            else:
                return False, "Habit not found", None
                
        except Exception as e:
            log_error(f"Error getting habit: {str(e)}")
            return False, f"Error: {str(e)}", None
    
    def get_trainer_habits(
        self, 
        trainer_id: str, 
        active_only: bool = True
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Get all habits created by a trainer
        
        Returns:
            Tuple of (success, message, habits_list)
        """
        try:
            query = self.db.table('fitness_habits').select('*').eq('trainer_id', trainer_id)
            
            if active_only:
                query = query.eq('is_active', True)
            
            result = query.order('created_at', desc=True).execute()
            
            if result.data:
                return True, f"Found {len(result.data)} habits", result.data
            else:
                return True, "No habits found", []
                
        except Exception as e:
            log_error(f"Error getting trainer habits: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def update_habit(
        self, 
        habit_id: str, 
        trainer_id: str, 
        updates: Dict
    ) -> Tuple[bool, str]:
        """
        Update habit details
        
        Args:
            habit_id: Habit ID to update
            trainer_id: Trainer ID (for verification)
            updates: Dict of fields to update
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify habit belongs to trainer
            success, msg, habit = self.get_habit_by_id(habit_id)
            if not success or not habit:
                return False, "Habit not found"
            
            if habit.get('trainer_id') != trainer_id:
                return False, "You don't have permission to edit this habit"
            
            # Prepare updates
            allowed_fields = ['habit_name', 'description', 'target_value', 'unit', 'frequency']
            update_data = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not update_data:
                return False, "No valid fields to update"
                
            # Add updated timestamp
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Convert target_value to float if present
            if 'target_value' in update_data:
                update_data['target_value'] = float(update_data['target_value'])
            
            # Update in database (use exact habit_id from database)
            result = self.db.table('fitness_habits').update(update_data).eq('habit_id', habit.get('habit_id')).execute()
            
            if result.data:
                log_info(f"Habit updated successfully: {habit_id}")
                return True, "Habit updated successfully"
            else:
                return False, "Failed to update habit"
                
        except Exception as e:
            log_error(f"Error updating habit: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def delete_habit(
        self, 
        habit_id: str, 
        trainer_id: str
    ) -> Tuple[bool, str]:
        """
        Soft delete a habit (set is_active = False)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify habit belongs to trainer
            success, msg, habit = self.get_habit_by_id(habit_id)
            if not success or not habit:
                return False, "Habit not found"
            
            if habit.get('trainer_id') != trainer_id:
                return False, "You don't have permission to delete this habit"
            
            # Soft delete (use exact habit_id from database)
            result = self.db.table('fitness_habits').update({'is_active': False}).eq('habit_id', habit.get('habit_id')).execute()
            
            if result.data:
                log_info(f"Habit deleted successfully: {habit_id}")
                # Also deactivate all assignments
                self.db.table('trainee_habit_assignments')\
                    .update({'is_active': False})\
                    .eq('habit_id', habit_id)\
                    .execute()
                return True, "Habit deleted successfully"
            else:
                return False, "Failed to delete habit"
                
        except Exception as e:
            log_error(f"Error deleting habit: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def search_habits(
        self, 
        trainer_id: str, 
        search_term: str
    ) -> Tuple[bool, str, List[Dict]]:
        """
        Search trainer's habits by name
        
        Returns:
            Tuple of (success, message, habits_list)
        """
        try:
            result = self.db.table('fitness_habits')\
                .select('*')\
                .eq('trainer_id', trainer_id)\
                .eq('is_active', True)\
                .ilike('habit_name', f'%{search_term}%')\
                .execute()
            
            if result.data:
                return True, f"Found {len(result.data)} habits", result.data
            else:
                return True, "No habits found", []
                
        except Exception as e:
            log_error(f"Error searching habits: {str(e)}")
            return False, f"Error: {str(e)}", []
    
    def get_habit_assignment_count(self, habit_id: str) -> int:
        """
        Get count of active assignments for a habit
        
        Returns:
            Number of active assignments
        """
        try:
            result = self.db.table('trainee_habit_assignments')\
                .select('id', count='exact')\
                .eq('habit_id', habit_id)\
                .eq('is_active', True)\
                .execute()
            
            return result.count if result.count else 0
            
        except Exception as e:
            log_error(f"Error getting assignment count: {str(e)}")
            return 0
