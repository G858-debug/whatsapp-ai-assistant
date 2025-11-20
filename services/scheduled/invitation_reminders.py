"""
Invitation Reminders Service
Handles automatic reminders and expiry for client invitations
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pytz
from utils.logger import log_info, log_error


class InvitationReminderService:
    """Service for managing invitation reminders and expiry"""

    def __init__(self, supabase_client, whatsapp_service):
        self.db = supabase_client
        self.whatsapp = whatsapp_service
        self.sa_tz = pytz.timezone('Africa/Johannesburg')

    def process_all_reminders(self) -> Dict:
        """Process all invitation reminders (24h, 72h, 7d)"""
        try:
            log_info("Starting invitation reminders processing")

            results = {
                '24h_reminders': self.send_24h_client_reminders(),
                '72h_reminders': self.send_72h_trainer_notifications(),
                '7d_expiries': self.process_7d_expiries()
            }

            total_sent = sum([
                results['24h_reminders'].get('sent', 0),
                results['72h_reminders'].get('sent', 0),
                results['7d_expiries'].get('sent', 0)
            ])

            total_errors = sum([
                results['24h_reminders'].get('errors', 0),
                results['72h_reminders'].get('errors', 0),
                results['7d_expiries'].get('errors', 0)
            ])

            log_info(f"Invitation reminders completed: {total_sent} sent, {total_errors} errors")

            return {
                'success': True,
                'total_sent': total_sent,
                'total_errors': total_errors,
                'details': results
            }

        except Exception as e:
            log_error(f"Error processing invitation reminders: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def send_24h_client_reminders(self) -> Dict:
        """Send 24-hour reminders to clients who haven't responded"""
        try:
            log_info("Checking for 24-hour client reminders")

            now = datetime.now(self.sa_tz)
            reminder_time = now - timedelta(hours=24)

            # Get invitations created ~24 hours ago (±1 hour window) that are still pending
            window_start = (reminder_time - timedelta(hours=1)).isoformat()
            window_end = (reminder_time + timedelta(hours=1)).isoformat()

            invitations = self.db.table('client_invitations').select(
                '*, trainers!client_invitations_trainer_id_fkey(trainer_id, name, first_name, last_name, business_name)'
            ).eq('status', 'pending').gte(
                'created_at', window_start
            ).lte(
                'created_at', window_end
            ).execute()

            sent_count = 0
            error_count = 0

            for invitation in (invitations.data or []):
                # Check if 24h reminder was already sent
                reminder_sent = self._check_reminder_sent(invitation['id'], '24h_client')
                if reminder_sent:
                    continue

                try:
                    trainer = invitation.get('trainers', {})
                    trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()
                    if not trainer_name:
                        trainer_name = trainer.get('business_name', 'Your trainer')

                    client_name = invitation.get('client_name', 'there')
                    client_phone = invitation.get('client_phone')

                    if not client_phone:
                        log_error(f"No phone number for invitation {invitation['id']}")
                        error_count += 1
                        continue

                    # Send reminder message
                    message = (
                        f"👋 *Reminder: Training Invitation*\n\n"
                        f"Hi {client_name}!\n\n"
                        f"Yesterday, *{trainer_name}* sent you an invitation to train together.\n\n"
                        f"We haven't heard back from you yet. If you're interested in starting your fitness journey with {trainer_name}, "
                        f"please respond to accept or decline the invitation.\n\n"
                        f"Looking forward to hearing from you! 💪"
                    )

                    # Send message with buttons
                    trainer_string_id = trainer.get('trainer_id')
                    buttons = [
                        {'id': f'approve_new_client_{trainer_string_id}', 'title': '✅ Accept'},
                        {'id': f'reject_new_client_{trainer_string_id}', 'title': '❌ Decline'}
                    ]

                    result = self.whatsapp.send_button_message(client_phone, message, buttons)

                    if result.get('success'):
                        sent_count += 1
                        # Log reminder sent
                        self._log_reminder_sent(invitation['id'], '24h_client', client_phone)
                        log_info(f"Sent 24h reminder to {client_phone} for invitation {invitation['id']}")
                    else:
                        error_count += 1
                        log_error(f"Failed to send 24h reminder to {client_phone}: {result.get('error')}")

                except Exception as e:
                    error_count += 1
                    log_error(f"Error sending 24h reminder for invitation {invitation['id']}: {str(e)}")

            log_info(f"24h reminders: {sent_count} sent, {error_count} errors")
            return {'sent': sent_count, 'errors': error_count, 'total': len(invitations.data or [])}

        except Exception as e:
            log_error(f"Error in send_24h_client_reminders: {str(e)}")
            return {'sent': 0, 'errors': 1, 'error': str(e)}

    def send_72h_trainer_notifications(self) -> Dict:
        """Send 72-hour notifications to trainers about pending invitations"""
        try:
            log_info("Checking for 72-hour trainer notifications")

            now = datetime.now(self.sa_tz)
            notification_time = now - timedelta(hours=72)

            # Get invitations created ~72 hours ago (±1 hour window) that are still pending
            window_start = (notification_time - timedelta(hours=1)).isoformat()
            window_end = (notification_time + timedelta(hours=1)).isoformat()

            invitations = self.db.table('client_invitations').select(
                '*, trainers!client_invitations_trainer_id_fkey(trainer_id, name, first_name, last_name, phone)'
            ).eq('status', 'pending').gte(
                'created_at', window_start
            ).lte(
                'created_at', window_end
            ).execute()

            sent_count = 0
            error_count = 0

            for invitation in (invitations.data or []):
                # Check if 72h notification was already sent
                reminder_sent = self._check_reminder_sent(invitation['id'], '72h_trainer')
                if reminder_sent:
                    continue

                try:
                    trainer = invitation.get('trainers', {})
                    trainer_phone = trainer.get('phone')
                    client_name = invitation.get('client_name', 'your client')

                    if not trainer_phone:
                        log_error(f"No phone number for trainer in invitation {invitation['id']}")
                        error_count += 1
                        continue

                    # Send notification message with action buttons
                    trainer_string_id = trainer.get('trainer_id')
                    message = (
                        f"⏰ *Pending Invitation Update*\n\n"
                        f"Hi! Just a heads up:\n\n"
                        f"*{client_name}* hasn't responded to your training invitation yet (sent 3 days ago).\n\n"
                        f"What would you like to do?"
                    )

                    buttons = [
                        {'id': f'resend_invite_{invitation["id"]}', 'title': '🔄 Resend'},
                        {'id': f'cancel_invite_{invitation["id"]}', 'title': '❌ Cancel'},
                        {'id': f'contact_client_{invitation["id"]}', 'title': '📞 Contact'}
                    ]

                    result = self.whatsapp.send_button_message(trainer_phone, message, buttons)

                    if result.get('success'):
                        sent_count += 1
                        # Log notification sent
                        self._log_reminder_sent(invitation['id'], '72h_trainer', trainer_phone)
                        log_info(f"Sent 72h notification to trainer {trainer_phone} for invitation {invitation['id']}")
                    else:
                        error_count += 1
                        log_error(f"Failed to send 72h notification to {trainer_phone}: {result.get('error')}")

                except Exception as e:
                    error_count += 1
                    log_error(f"Error sending 72h notification for invitation {invitation['id']}: {str(e)}")

            log_info(f"72h notifications: {sent_count} sent, {error_count} errors")
            return {'sent': sent_count, 'errors': error_count, 'total': len(invitations.data or [])}

        except Exception as e:
            log_error(f"Error in send_72h_trainer_notifications: {str(e)}")
            return {'sent': 0, 'errors': 1, 'error': str(e)}

    def process_7d_expiries(self) -> Dict:
        """Process 7-day invitation expiries and notify trainers"""
        try:
            log_info("Checking for 7-day invitation expiries")

            now = datetime.now(self.sa_tz)
            expiry_time = now - timedelta(days=7)

            # Get invitations created ~7 days ago (±2 hour window) that are still pending
            window_start = (expiry_time - timedelta(hours=2)).isoformat()
            window_end = (expiry_time + timedelta(hours=2)).isoformat()

            invitations = self.db.table('client_invitations').select(
                '*, trainers!client_invitations_trainer_id_fkey(trainer_id, name, first_name, last_name, phone)'
            ).eq('status', 'pending').gte(
                'created_at', window_start
            ).lte(
                'created_at', window_end
            ).execute()

            sent_count = 0
            error_count = 0
            expired_count = 0

            for invitation in (invitations.data or []):
                # Check if 7d expiry notification was already sent
                reminder_sent = self._check_reminder_sent(invitation['id'], '7d_expiry')
                if reminder_sent:
                    continue

                try:
                    # Update invitation status to expired
                    self.db.table('client_invitations').update({
                        'status': 'expired',
                        'updated_at': now.isoformat()
                    }).eq('id', invitation['id']).execute()

                    expired_count += 1

                    trainer = invitation.get('trainers', {})
                    trainer_phone = trainer.get('phone')
                    client_name = invitation.get('client_name', 'your client')

                    if not trainer_phone:
                        log_error(f"No phone number for trainer in invitation {invitation['id']}")
                        error_count += 1
                        continue

                    # Send expiry notification to trainer
                    trainer_string_id = trainer.get('trainer_id')
                    message = (
                        f"⏰ *Invitation Expired*\n\n"
                        f"The training invitation you sent to *{client_name}* has expired after 7 days without a response.\n\n"
                        f"Don't worry! You can send a new invitation anytime when you're ready to connect again.\n\n"
                        f"💡 *Tip:* Consider reaching out directly to check if they're still interested."
                    )

                    result = self.whatsapp.send_message(trainer_phone, message)

                    if result.get('success'):
                        sent_count += 1
                        # Log expiry notification sent
                        self._log_reminder_sent(invitation['id'], '7d_expiry', trainer_phone)
                        log_info(f"Sent 7d expiry notification to trainer {trainer_phone} for invitation {invitation['id']}")
                    else:
                        error_count += 1
                        log_error(f"Failed to send 7d expiry notification to {trainer_phone}: {result.get('error')}")

                except Exception as e:
                    error_count += 1
                    log_error(f"Error processing 7d expiry for invitation {invitation['id']}: {str(e)}")

            log_info(f"7d expiries: {expired_count} expired, {sent_count} notifications sent, {error_count} errors")
            return {
                'sent': sent_count,
                'expired': expired_count,
                'errors': error_count,
                'total': len(invitations.data or [])
            }

        except Exception as e:
            log_error(f"Error in process_7d_expiries: {str(e)}")
            return {'sent': 0, 'expired': 0, 'errors': 1, 'error': str(e)}

    def resend_invitation(self, invitation_id: str) -> Dict:
        """Resend an invitation (used for manual resend and 72h action button, invitation_id is UUID)"""
        try:
            # Get invitation details
            result = self.db.table('client_invitations').select(
                '*, trainers!client_invitations_trainer_id_fkey(trainer_id, name, first_name, last_name, business_name)'
            ).eq('id', invitation_id).execute()

            if not result.data:
                return {'success': False, 'error': 'Invitation not found'}

            invitation = result.data[0]

            # Only resend if pending or expired
            if invitation['status'] not in ['pending', 'expired']:
                return {'success': False, 'error': f"Cannot resend invitation with status: {invitation['status']}"}

            # Update invitation status and created_at to reset timers
            now = datetime.now(self.sa_tz)
            self.db.table('client_invitations').update({
                'status': 'pending',
                'created_at': now.isoformat(),
                'updated_at': now.isoformat()
            }).eq('id', invitation_id).execute()

            # Resend invitation message
            trainer = invitation.get('trainers', {})
            trainer_name = trainer.get('name') or f"{trainer.get('first_name', '')} {trainer.get('last_name', '')}".strip()
            if not trainer_name:
                trainer_name = trainer.get('business_name', 'Your trainer')

            client_name = invitation.get('client_name', 'there')
            client_phone = invitation.get('client_phone')
            prefilled_data = invitation.get('prefilled_data', {})

            if not client_phone:
                return {'success': False, 'error': 'No client phone number'}

            # Build message
            message = (
                f"🎯 *Training Invitation*\n\n"
                f"Hi {client_name}! 👋\n\n"
                f"*{trainer_name}* has invited you to train together!\n\n"
            )

            if prefilled_data:
                message += "📋 *Your Profile:*\n"
                message += f"• Name: {client_name}\n"
                if prefilled_data.get('email') and prefilled_data['email'].lower() not in ['skip', 'none']:
                    message += f"• Email: {prefilled_data['email']}\n"
                if prefilled_data.get('fitness_goals'):
                    message += f"• Goals: {prefilled_data['fitness_goals']}\n"
                if prefilled_data.get('experience_level'):
                    message += f"• Experience: {prefilled_data['experience_level']}\n"
                message += "\n"

            message += f"✅ Do you accept this invitation and want to train with {trainer_name}?"

            # Send with buttons
            trainer_string_id = trainer.get('trainer_id')
            buttons = [
                {'id': f'approve_new_client_{trainer_string_id}', 'title': '✅ Accept'},
                {'id': f'reject_new_client_{trainer_string_id}', 'title': '❌ Decline'}
            ]

            send_result = self.whatsapp.send_button_message(client_phone, message, buttons)

            if send_result.get('success'):
                log_info(f"Resent invitation {invitation_id} to {client_phone}")
                return {'success': True, 'message': 'Invitation resent successfully'}
            else:
                return {'success': False, 'error': send_result.get('error', 'Failed to send message')}

        except Exception as e:
            log_error(f"Error resending invitation {invitation_id}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def cancel_invitation(self, invitation_id: str) -> Dict:
        """Cancel an invitation (used for 72h action button, invitation_id is UUID)"""
        try:
            # Update invitation status
            now = datetime.now(self.sa_tz)
            result = self.db.table('client_invitations').update({
                'status': 'cancelled',
                'updated_at': now.isoformat()
            }).eq('id', invitation_id).execute()

            if result.data:
                log_info(f"Cancelled invitation {invitation_id}")
                return {'success': True, 'message': 'Invitation cancelled'}
            else:
                return {'success': False, 'error': 'Failed to cancel invitation'}

        except Exception as e:
            log_error(f"Error cancelling invitation {invitation_id}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _check_reminder_sent(self, invitation_id: str, reminder_type: str) -> bool:
        """Check if a reminder has already been sent for this invitation (invitation_id is UUID)"""
        try:
            result = self.db.table('invitation_reminder_logs').select('id').eq(
                'invitation_id', invitation_id
            ).eq('reminder_type', reminder_type).execute()

            return bool(result.data)

        except Exception as e:
            log_error(f"Error checking reminder sent: {str(e)}")
            return False

    def _log_reminder_sent(self, invitation_id: str, reminder_type: str, sent_to: str):
        """Log that a reminder was sent (invitation_id is UUID)"""
        try:
            now = datetime.now(self.sa_tz)
            log_data = {
                'invitation_id': invitation_id,
                'reminder_type': reminder_type,
                'sent_to': sent_to,
                'sent_at': now.isoformat(),
                'created_at': now.isoformat()
            }

            self.db.table('invitation_reminder_logs').insert(log_data).execute()

        except Exception as e:
            log_error(f"Error logging reminder sent: {str(e)}")
