"""
 Handle Reset Command
Handle /reset_me command to completely reset user data from all 9 core tables
"""
from typing import Dict, Optional, List
from datetime import datetime
from utils.logger import log_info, log_error

def _handle_reset_command(self, phone: str) -> Dict:
    """Handle /reset_me command to completely reset user data from all 9 core tables"""
    try:
        from app import app
        whatsapp_service = app.config['services']['whatsapp']
        
        # Safety check - only allow for specific test numbers
        ALLOWED_RESET_NUMBERS = [
            '27731863036',  # Your test number from logs
            '27837896738',  # Add other test numbers as needed
            "8801902604456",
            "8801876078348",

        ]
        
        if phone not in ALLOWED_RESET_NUMBERS:
            response = "⚠️ Reset command is currently only available for test accounts.\n\nIf you need to reset your account, please contact support."
            whatsapp_service.send_message(phone, response)
            return {'success': True, 'response': response}
        
        # Track what happens
        debug_info = []
        deleted_count = 0
        
        # Delete from trainers
        try:
            result = self.db.table('trainers').delete().eq('whatsapp', phone).execute()
            if result.data:
                deleted_count += len(result.data)
                debug_info.append(f"✓ Deleted {len(result.data)} trainer record(s)")
            else:
                debug_info.append("• No trainer records found")
        except Exception as e:
            debug_info.append(f"✗ Trainer delete error: {str(e)[:50]}")
        
        # Delete from clients
        try:
            result = self.db.table('clients').delete().eq('whatsapp', phone).execute()
            if result.data:
                deleted_count += len(result.data)
                debug_info.append(f"✓ Deleted {len(result.data)} client record(s)")
            else:
                debug_info.append("• No client records found")
        except Exception as e:
            debug_info.append(f"✗ Client delete error: {str(e)[:50]}")

        # Delete from users table
        try:
            result = self.db.table('users').delete().eq('phone_number', phone).execute()
            if result.data:
                deleted_count += len(result.data)
                debug_info.append(f"✓ Deleted {len(result.data)} user record(s)")
            else:
                debug_info.append("• No user records found")
        except Exception as e:
            debug_info.append(f"✗ User delete error: {str(e)[:50]}")

        # Delete conversation states
        try:
            result = self.db.table('conversation_states').delete().eq('phone_number', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted conversation state")
            else:
                debug_info.append("• No conversation state found")
        except Exception as e:
            debug_info.append(f"✗ Conversation state error: {str(e)[:50]}")
        
        # Delete message history
        try:
            result = self.db.table('message_history').delete().eq('phone_number', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted {len(result.data)} messages")
            else:
                debug_info.append("• No message history found")
        except Exception as e:
            debug_info.append(f"✗ Message history error: {str(e)[:50]}")
        
        # Delete registration sessions
        try:
            result = self.db.table('registration_sessions').delete().eq('phone', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted registration session")
            else:
                debug_info.append("• No registration session found")
        except Exception as e:
            debug_info.append(f"✗ Registration session error: {str(e)[:50]}")
        
        # Delete registration states (note: plural, and use phone_number column)
        try:
            result = self.db.table('registration_states').delete().eq('phone_number', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted {len(result.data)} registration state(s)")
            else:
                debug_info.append("• No registration states found")
        except Exception as e:
            debug_info.append(f"✗ Registration states error: {str(e)[:50]}")

        # Delete registration analytics (use phone_number column)
        try:
            result = self.db.table('registration_analytics').delete().eq('phone_number', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted {len(result.data)} analytics record(s)")
            else:
                debug_info.append("• No registration analytics found")
        except Exception as e:
            debug_info.append(f"✗ Registration analytics error: {str(e)[:50]}")
        
        # Delete flow tokens
        try:
            result = self.db.table('flow_tokens').delete().eq('phone_number', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted {len(result.data)} flow token(s)")
            else:
                debug_info.append("• No flow tokens found")
        except Exception as e:
            debug_info.append(f"✗ Flow tokens error: {str(e)[:50]}")
        
        # Delete processed messages (legacy table)
        try:
            result = self.db.table('processed_messages').delete().eq('phone_number', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted {len(result.data)} processed messages")
            else:
                debug_info.append("• No processed messages found")
        except Exception as e:
            debug_info.append(f"✗ Processed messages error: {str(e)[:50]}")

        # Delete trainer tasks
        try:
            result = self.db.table('trainer_tasks').delete().eq('trainer_id', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted {len(result.data)} trainer task(s)")
            else:
                debug_info.append("• No trainer tasks found")
        except Exception as e:
            debug_info.append(f"✗ Trainer tasks error: {str(e)[:50]}")

        # Delete client tasks
        try:
            result = self.db.table('client_tasks').delete().eq('client_id', phone).execute()
            if result.data:
                debug_info.append(f"✓ Deleted {len(result.data)} client task(s)")
            else:
                debug_info.append("• No client tasks found")
        except Exception as e:
            debug_info.append(f"✗ Client tasks error: {str(e)[:50]}")

        log_info(f"Reset for {phone} - Results: {debug_info}")
        
        # Count successful deletions
        successful_deletions = len([item for item in debug_info if item.startswith("✓")])
        
        # Send detailed response
        response = (
            "🔧 *Complete Account Reset Results:*\n\n" +
            "\n".join(debug_info) +
            f"\n\n📊 *Summary:*\n"
            f"• Tables processed: 9 core tables\n"
            f"• Successful operations: {successful_deletions}\n"
            f"• Total records deleted: {deleted_count}\n\n"
            "✨ Your account has been completely reset!\n"
            "You can now say 'Hi' to start fresh! 🚀"
        )
        
        whatsapp_service.send_message(phone, response)
        return {'success': True, 'response': response}
        
    except Exception as e:
        error_msg = str(e)
        log_error(f"Error resetting user {phone}: {error_msg}")
        
        # Send detailed error
        response = (
            f"❌ Reset failed!\n\n"
            f"Error: {error_msg[:200]}\n\n"
            "This usually means:\n"
            "• Database connection issue\n"
            "• Missing tables\n"
            "• Permission problem\n\n"
            "Try again or check the logs."
        )
        
        try:
            from app import app
            whatsapp_service = app.config['services']['whatsapp']
            whatsapp_service.send_message(phone, response)
        except:
            pass
        
        return {'success': False, 'response': response}
