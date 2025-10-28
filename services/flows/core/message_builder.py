"""
Message Builder
Builds consistent messages for flows
"""
from typing import Dict, List, Optional


class MessageBuilder:
    """Builds consistent messages for conversation flows"""
    
    def build_welcome_message(self, role: str, user_id: str, name: str = None) -> str:
        """Build welcome message after successful registration/login"""
        display_name = name or "there"
        
        if role == 'trainer':
            return (
                f"🎉 *Welcome to Refiloe, {display_name}!*\n\n"
                f"*Your Trainer ID:* {user_id}\n\n"
                f"You're all set! Here's what you can do:\n\n"
                f"👥 *Manage Clients:*\n"
                f"• /invite-trainee - Invite existing clients\n"
                f"• /create-trainee - Create new client accounts\n"
                f"• /view-trainees - View your clients\n\n"
                f"🎯 *Manage Habits:*\n"
                f"• /create-habit - Create fitness habits\n"
                f"• /assign-habit - Assign habits to clients\n"
                f"• /view-habits - View all your habits\n\n"
                f"📊 *Track Progress:*\n"
                f"• /view-trainee-progress - View client progress\n"
                f"• /trainee-weekly-report - Generate reports\n\n"
                f"Type /help anytime for all commands!"
            )
        else:
            return (
                f"🎉 *Welcome to Refiloe, {display_name}!*\n\n"
                f"*Your Client ID:* {user_id}\n\n"
                f"You're all set! Here's what you can do:\n\n"
                f"👨‍💼 *Find Trainers:*\n"
                f"• /search-trainer - Search for trainers\n"
                f"• /invite-trainer - Invite a trainer\n"
                f"• /view-trainers - View your trainers\n\n"
                f"🎯 *Track Habits:*\n"
                f"• /view-my-habits - View assigned habits\n"
                f"• /log-habits - Log your daily habits\n"
                f"• /view-progress - View your progress\n\n"
                f"📊 *Generate Reports:*\n"
                f"• /weekly-report - Get weekly summary\n"
                f"• /monthly-report - Get monthly summary\n\n"
                f"Type /help anytime for all commands!"
            )
    
    def build_progress_message(self, current_step: int, total_steps: int, 
                              next_prompt: str) -> str:
        """Build progress message with next prompt"""
        if total_steps > 1:
            return f"✅ Got it! ({current_step}/{total_steps})\n\n{next_prompt}"
        else:
            return next_prompt
    
    def build_validation_error_message(self, error_msg: str, field_prompt: str) -> str:
        """Build validation error message"""
        return f"❌ {error_msg}\n\n{field_prompt}\n\nPlease try again."
    
    def build_completion_message(self, action: str, details: str = None) -> str:
        """Build completion message"""
        base_msg = f"✅ *{action} Completed Successfully!*\n\n"
        
        if details:
            base_msg += f"{details}\n\n"
        
        base_msg += "Is there anything else I can help you with?"
        
        return base_msg
    
    def build_cancellation_message(self, action: str) -> str:
        """Build cancellation message"""
        return (
            f"❌ *{action} Cancelled*\n\n"
            f"The {action.lower()} has been cancelled.\n\n"
            f"Type /help to see what else I can do for you."
        )
    
    def build_error_message(self, action: str, retry_command: str = None) -> str:
        """Build error message"""
        msg = (
            f"❌ *Error Occurred*\n\n"
            f"Sorry, I encountered an error during {action.lower()}.\n\n"
        )
        
        if retry_command:
            msg += f"Please try again with {retry_command} or contact support if the issue persists."
        else:
            msg += "Please try again or contact support if the issue persists."
        
        return msg
    
    def build_field_selection_message(self, fields: List[Dict], current_values: Dict) -> str:
        """Build field selection message for profile editing"""
        msg = "📝 *Edit Profile*\n\nCurrent information:\n\n"
        
        for i, field in enumerate(fields, 1):
            field_name = field.get('name', '')
            field_label = field.get('label', field_name)
            current_value = current_values.get(field_name, 'Not set')
            
            msg += f"{i}. *{field_label}:* {current_value}\n"
        
        msg += (
            f"\n💡 *To edit fields:*\n"
            f"Type the numbers of fields you want to edit (e.g., \"1,3,5\")\n"
            f"Or type \"all\" to edit all fields.\n\n"
            f"Type /stop to cancel."
        )
        
        return msg
    
    def build_confirmation_message(self, action: str, details: str, 
                                  confirm_text: str = "yes", 
                                  cancel_text: str = "no") -> str:
        """Build confirmation message"""
        return (
            f"⚠️ *Confirm {action}*\n\n"
            f"{details}\n\n"
            f"Are you sure you want to proceed?\n\n"
            f"Type \"{confirm_text}\" to confirm or \"{cancel_text}\" to cancel."
        )
    
    def build_list_message(self, title: str, items: List[Dict], 
                          item_formatter: callable) -> str:
        """Build list message with formatted items"""
        if not items:
            return f"📋 *{title}*\n\nNo items found."
        
        msg = f"📋 *{title}*\n\n"
        
        for i, item in enumerate(items, 1):
            formatted_item = item_formatter(item, i)
            msg += f"{formatted_item}\n\n"
        
        return msg.rstrip()
    
    def build_search_results_message(self, search_term: str, results: List[Dict], 
                                   result_formatter: callable) -> str:
        """Build search results message"""
        if not results:
            return (
                f"🔍 *Search Results*\n\n"
                f"❌ No results found for '{search_term}'.\n\n"
                f"Try a different search term or type /stop to cancel."
            )
        
        msg = f"🔍 *Search Results for '{search_term}'*\n\n"
        
        for i, result in enumerate(results, 1):
            formatted_result = result_formatter(result, i)
            msg += f"{formatted_result}\n\n"
        
        return msg.rstrip()