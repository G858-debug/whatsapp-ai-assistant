"""
Trainer Relationship Invitation Commands
Handles client invitation and creation
"""
from typing import Dict
from utils.logger import log_info, log_error
import re


def handle_invite_client(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /invite-trainee command"""
    try:
        # Create invite_trainee task - use phone for task identification
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='invite_trainee',
            task_data={
                'step': 'ask_client_id',
                'trainer_id': trainer_id
            }
        )
        
        if not task_id:
            msg = "❌ I couldn't start the invitation process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'invite_trainee_task_error'}
        
        # Ask for client ID or phone number
        msg = (
            "👥 *Invite Existing Client*\n\n"
            "Please provide the client ID or phone number you want to invite.\n\n"
            "The client must already be registered in the system.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'invite_trainee_started'
        }
        
    except Exception as e:
        log_error(f"Error in invite trainee command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'invite_trainee_error'
        }


def handle_create_client(phone: str, trainer_id: str, db, whatsapp, reg_service, task_service) -> Dict:
    """Handle /create-trainee command - now asks to create or link"""
    try:
        # Create task to ask for choice - use phone for task identification
        task_id = task_service.create_task(
            user_id=phone,
            role='trainer',
            task_type='create_trainee',
            task_data={
                'step': 'ask_create_or_link',
                'trainer_id': trainer_id
            }
        )

        if not task_id:
            msg = "❌ I couldn't start the process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'create_trainee_task_error'}

        # Ask if they want to create new or link existing
        msg = (
            "👥 *Add Client*\n\n"
            "How would you like to add a client?\n\n"
            "1️⃣ *Create New* - Create a new client account and send them an invitation to accept\n\n"
            "2️⃣ *Link Existing* - Link with a client who's already registered (you'll need their Client ID or phone number)\n\n"
            "💡 *Tip:* Type /stop to cancel\n\n"
            "Reply with *1* or *2*"
        )
        whatsapp.send_message(phone, msg)

        return {
            'success': True,
            'response': msg,
            'handler': 'create_trainee_started'
        }

    except Exception as e:
        log_error(f"Error in create trainee command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'create_trainee_error'
        }


def handle_resend_invite(phone: str, trainer_id: str, message: str, db, whatsapp) -> Dict:
    """Handle /resend-invite [client-name] command"""
    try:
        from services.scheduled.invitation_reminders import InvitationReminderService

        # Extract client name from command
        # Expected format: /resend-invite John Doe
        match = re.match(r'/resend-invite\s+(.+)', message, re.IGNORECASE)

        if not match:
            msg = (
                "❌ *Invalid Format*\n\n"
                "Please provide the client name.\n\n"
                "*Usage:* /resend-invite [client-name]\n"
                "*Example:* /resend-invite John Doe"
            )
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'resend_invite_format_error'}

        client_name = match.group(1).strip()

        # Get trainer UUID
        trainer_result = db.table('trainers').select('id').ilike('trainer_id', trainer_id).execute()

        if not trainer_result.data:
            msg = "❌ Trainer not found. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'resend_invite_trainer_error'}

        trainer_uuid = trainer_result.data[0]['id']

        # Find pending invitations for this trainer and client name
        invitations = db.table('client_invitations').select('id, client_name, client_phone, status, created_at').eq(
            'trainer_id', trainer_uuid
        ).ilike('client_name', f'%{client_name}%').execute()

        if not invitations.data:
            msg = (
                f"❌ *No Invitations Found*\n\n"
                f"I couldn't find any invitations for a client matching '{client_name}'.\n\n"
                f"💡 *Tip:* Make sure the name is correct or try creating a new invitation with /create-trainee"
            )
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'resend_invite_not_found'}

        # Filter to pending or expired invitations
        pending_invitations = [inv for inv in invitations.data if inv['status'] in ['pending', 'expired']]

        if not pending_invitations:
            msg = (
                f"ℹ️ *No Pending Invitations*\n\n"
                f"All invitations for '{client_name}' have already been accepted or declined.\n\n"
                f"💡 *Tip:* You can create a new invitation with /create-trainee"
            )
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'resend_invite_no_pending'}

        # If multiple matches, show list
        if len(pending_invitations) > 1:
            msg = f"📋 *Multiple Invitations Found for '{client_name}':*\n\n"
            for inv in pending_invitations:
                msg += f"• {inv['client_name']} ({inv['client_phone']}) - Status: {inv['status']}\n"
            msg += f"\n💡 Use the exact name to resend a specific invitation."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'resend_invite_multiple'}

        # Resend the invitation
        invitation = pending_invitations[0]
        invitation_reminder_service = InvitationReminderService(db, whatsapp)

        result = invitation_reminder_service.resend_invitation(invitation['id'])

        if result.get('success'):
            msg = (
                f"✅ *Invitation Resent!*\n\n"
                f"The invitation has been resent to *{invitation['client_name']}* at {invitation['client_phone']}.\n\n"
                f"They will receive a WhatsApp message with the invitation details."
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'resend_invite_success'}
        else:
            msg = f"❌ Failed to resend invitation: {result.get('error', 'Unknown error')}"
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'resend_invite_failed'}

    except Exception as e:
        log_error(f"Error in resend invite command: {str(e)}")
        msg = "❌ Sorry, I encountered an error while resending the invitation. Please try again."
        whatsapp.send_message(phone, msg)
        return {
            'success': False,
            'response': msg,
            'handler': 'resend_invite_error'
        }