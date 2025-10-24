"""
Profile Command Handlers - Phase 1
Handles view, edit, and delete profile commands
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_view_profile(phone: str, role: str, user_id: str, db, whatsapp, reg_service) -> Dict:
    """Handle view profile command"""
    try:
        # Get user data from users table
        user_result = db.table('users').select('*').eq('phone_number', phone).execute()
        
        if not user_result.data:
            msg = "❌ I couldn't find your profile information."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'view_profile_not_found'}
        
        # Get role-specific data
        table = 'trainers' if role == 'trainer' else 'clients'
        id_column = 'trainer_id' if role == 'trainer' else 'client_id'
        
        role_result = db.table(table).select('*').eq(id_column, user_id).execute()
        
        if not role_result.data:
            msg = "❌ I couldn't find your profile information."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'view_profile_role_not_found'}
        
        role_data = role_result.data[0]
        
        # Get showable fields from config
        config_key = 'trainer' if role == 'trainer' else 'client'
        fields_config = reg_service.get_registration_fields(config_key)
        
        # Build profile message
        if role == 'trainer':
            profile_msg = _format_trainer_profile(role_data, user_id)
        else:
            profile_msg = _format_client_profile(role_data, user_id)
        
        whatsapp.send_message(phone, profile_msg)
        
        return {
            'success': True,
            'response': profile_msg,
            'handler': 'view_profile_success'
        }
        
    except Exception as e:
        log_error(f"Error viewing profile: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your profile.",
            'handler': 'view_profile_error'
        }


def _format_trainer_profile(data: Dict, trainer_id: str) -> str:
    """Format trainer profile for display"""
    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or data.get('name', 'N/A')
    
    profile = (
        f"👤 *Your Trainer Profile*\n\n"
        f"*ID:* {trainer_id}\n"
        f"*Name:* {name}\n"
        f"*Email:* {data.get('email', 'N/A')}\n"
        f"*Phone:* {data.get('whatsapp', 'N/A')}\n"
        f"*City:* {data.get('city', 'N/A')}\n"
    )
    
    if data.get('business_name'):
        profile += f"*Business:* {data['business_name']}\n"
    
    if data.get('specialization'):
        spec = data['specialization']
        if isinstance(spec, list):
            spec = ', '.join(spec)
        profile += f"*Specialization:* {spec}\n"
    
    if data.get('experience_years'):
        profile += f"*Experience:* {data['experience_years']}\n"
    
    if data.get('pricing_per_session'):
        profile += f"*Price per Session:* R{data['pricing_per_session']}\n"
    
    profile += f"\n💡 Type /edit-profile to update your information"
    
    return profile


def _format_client_profile(data: Dict, client_id: str) -> str:
    """Format client profile for display"""
    name = data.get('name', 'N/A')
    
    profile = (
        f"👤 *Your Client Profile*\n\n"
        f"*ID:* {client_id}\n"
        f"*Name:* {name}\n"
        f"*Email:* {data.get('email', 'N/A')}\n"
        f"*Phone:* {data.get('whatsapp', 'N/A')}\n"
    )
    
    if data.get('fitness_goals'):
        goals = data['fitness_goals']
        if isinstance(goals, list):
            goals = ', '.join(goals)
        profile += f"*Fitness Goals:* {goals}\n"
    
    if data.get('experience_level'):
        profile += f"*Experience Level:* {data['experience_level']}\n"
    
    if data.get('health_conditions'):
        profile += f"*Health Conditions:* {data['health_conditions']}\n"
    
    if data.get('availability'):
        avail = data['availability']
        if isinstance(avail, list):
            avail = ', '.join(avail)
        profile += f"*Availability:* {avail}\n"
    
    profile += f"\n💡 Type /edit-profile to update your information"
    
    return profile



def handle_edit_profile(phone: str, role: str, user_id: str, db, whatsapp, reg_service, task_service) -> Dict:
    """Handle edit profile command"""
    try:
        # Create edit_profile task
        task_id = task_service.create_task(
            user_id=user_id,
            role=role,
            task_type='edit_profile',
            task_data={
                'current_field_index': 0,
                'updates': {},
                'role': role
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the profile edit. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'edit_profile_task_error'}
        
        # Send intro message
        intro_msg = (
            "✏️ *Edit Your Profile*\n\n"
            "I'll go through each field. You can:\n"
            "• Type 'skip' to keep current value\n"
            "• Type new value to update\n"
            "• Type /stop to cancel\n\n"
            "Let's start! 👇"
        )
        whatsapp.send_message(phone, intro_msg)
        
        # Get first field
        fields = reg_service.get_registration_fields(role)
        if fields:
            first_field = fields[0]
            
            # Get current value
            table = 'trainers' if role == 'trainer' else 'clients'
            id_column = 'trainer_id' if role == 'trainer' else 'client_id'
            
            current_data = db.table(table).select('*').eq(id_column, user_id).execute()
            
            current_value = "Not set"
            if current_data.data:
                field_value = current_data.data[0].get(first_field['name'])
                if field_value:
                    if isinstance(field_value, list):
                        current_value = ', '.join(field_value)
                    else:
                        current_value = str(field_value)
            
            field_msg = (
                f"*{first_field['label']}*\n"
                f"Current: {current_value}\n\n"
                f"{first_field['prompt']}\n\n"
                f"(Type 'skip' to keep current value)"
            )
            whatsapp.send_message(phone, field_msg)
            
            return {
                'success': True,
                'response': field_msg,
                'handler': 'edit_profile_started'
            }
        else:
            msg = "❌ I couldn't load the profile fields."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'edit_profile_no_fields'}
        
    except Exception as e:
        log_error(f"Error starting profile edit: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't start profile editing.",
            'handler': 'edit_profile_error'
        }


def handle_delete_account(phone: str, role: str, user_id: str, db, whatsapp, auth_service, task_service) -> Dict:
    """Handle delete account command"""
    try:
        # Create delete_account task
        task_id = task_service.create_task(
            user_id=user_id,
            role=role,
            task_type='delete_account',
            task_data={
                'confirmed': False,
                'role': role
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the account deletion. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'delete_account_task_error'}
        
        # Send confirmation request
        warning_msg = (
            "⚠️ *Delete Account*\n\n"
            f"Are you sure you want to delete your *{role.title()}* account?\n\n"
            "*This will:*\n"
        )
        
        if role == 'trainer':
            warning_msg += (
                "• Remove all your trainer data\n"
                "• Remove you from all client lists\n"
                "• Delete all habits you created\n"
                "• Remove all habit assignments\n"
            )
        else:
            warning_msg += (
                "• Remove all your client data\n"
                "• Remove you from all trainer lists\n"
                "• Delete all your habit logs\n"
            )
        
        # Check if user has other role
        roles = auth_service.get_user_roles(phone)
        other_role = 'client' if role == 'trainer' else 'trainer'
        
        if roles[other_role]:
            warning_msg += f"\n✅ Your {other_role} account will remain active.\n"
        else:
            warning_msg += "\n⚠️ Your entire account will be deleted.\n"
        
        warning_msg += (
            "\n*This action cannot be undone!*\n\n"
            "Reply with:\n"
            "• 'YES DELETE' to confirm\n"
            "• 'CANCEL' or /stop to cancel"
        )
        
        whatsapp.send_message(phone, warning_msg)
        
        return {
            'success': True,
            'response': warning_msg,
            'handler': 'delete_account_confirmation'
        }
        
    except Exception as e:
        log_error(f"Error starting account deletion: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't start account deletion.",
            'handler': 'delete_account_error'
        }
