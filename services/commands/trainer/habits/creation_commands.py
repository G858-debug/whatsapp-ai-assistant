"""
Trainer Habit Creation Commands
Handles habit creation, editing, and deletion
"""
from typing import Dict
from utils.logger import log_info, log_error
import json


def handle_create_habit(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /create-habit command"""
    try:
        # Load habit creation fields
        try:
            with open('config/habit_creation_inputs.json', 'r') as f:
                config = json.load(f)
                fields = config.get('fields', [])
        except Exception as e:
            log_error(f"Error loading habit creation config: {str(e)}")
            msg = "❌ I couldn't load the habit creation form. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'create_habit_config_error'}
        
        # Create create_habit task
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='create_habit',
            task_data={
                'current_field_index': 0,
                'collected_data': {}
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the habit creation process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'create_habit_task_error'}
        
        # Send intro message
        intro_msg = (
            "🎯 *Create New Habit*\n\n"
            f"I'll ask you {len(fields)} questions to create a fitness habit.\n\n"
            "💡 *Tip:* You can type /stop at any time to cancel.\n\n"
            "Let's start! 👇"
        )
        whatsapp.send_message(phone, intro_msg)
        
        # Send first field prompt
        first_field = fields[0]
        whatsapp.send_message(phone, first_field['prompt'])
        
        return {
            'success': True,
            'response': first_field['prompt'],
            'handler': 'create_habit_started'
        }
        
    except Exception as e:
        log_error(f"Error in create habit command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'create_habit_error'
        }


def handle_edit_habit(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /edit-habit command"""
    try:
        # Create edit_habit task
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='edit_habit',
            task_data={'step': 'ask_habit_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the editing process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'edit_habit_task_error'}
        
        # Ask for habit ID
        msg = (
            "✏️ *Edit Habit*\n\n"
            "Please provide the habit ID you want to edit.\n\n"
            "💡 Use /view-habits to see your habits and their IDs.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'edit_habit_started'
        }
        
    except Exception as e:
        log_error(f"Error in edit habit command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'edit_habit_error'
        }


def handle_delete_habit(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /delete-habit command"""
    try:
        # Create delete_habit task
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='delete_habit',
            task_data={'step': 'ask_habit_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the deletion process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'delete_habit_task_error'}
        
        # Ask for habit ID
        msg = (
            "🗑️ *Delete Habit*\n\n"
            "Please provide the habit ID you want to delete.\n\n"
            "⚠️ *Warning:* This will remove the habit from all assigned clients.\n\n"
            "💡 Use /view-habits to see your habits and their IDs.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'delete_habit_started'
        }
        
    except Exception as e:
        log_error(f"Error in delete habit command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'delete_habit_error'
        }