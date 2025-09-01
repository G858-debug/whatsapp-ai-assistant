from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pytz
import uuid
import base64
from io import BytesIO
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from utils.logger import log_error, log_info

class CalendarExportService:
    """Handle calendar export functionality including ICS files and email invites"""
    
    def __init__(self, supabase_client, config):
        self.db = supabase_client
        self.config = config
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Email configuration
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.smtp_username = config.SMTP_USERNAME
        self.smtp_password = config.SMTP_PASSWORD
        self.sender_email = config.SENDER_EMAIL
        
    def generate_ics_file(self, booking_data: Dict) -> str:
        """Generate ICS file content for booking(s)"""
        try:
            # Start ICS file
            ics_lines = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//Refiloe AI//Training Calendar//EN",
                "CALSCALE:GREGORIAN",
                "METHOD:REQUEST",
                "X-WR-CALNAME:Training Sessions",
                "X-WR-TIMEZONE:Africa/Johannesburg"
            ]
            
            # Add timezone definition
            ics_lines.extend([
                "BEGIN:VTIMEZONE",
                "TZID:Africa/Johannesburg",
                "BEGIN:STANDARD",
                "DTSTART:19700101T000000",
                "TZOFFSETFROM:+0200",
                "TZOFFSETTO:+0200",
                "TZNAME:SAST",
                "END:STANDARD",
                "END:VTIMEZONE"
            ])
            
            # Handle single booking or multiple bookings
            bookings = booking_data.get('sessions', [booking_data]) if 'sessions' in booking_data else [booking_data]
            
            for booking in bookings:
                ics_lines.extend(self._create_vevent(booking, booking_data))
            
            ics_lines.append("END:VCALENDAR")
            
            return "\r\n".join(ics_lines)
            
        except Exception as e:
            log_error(f"Error generating ICS file: {str(e)}")
            raise
    
    def _create_vevent(self, booking: Dict, context_data: Dict) -> List[str]:
        """Create VEVENT component for a booking"""
        try:
            # Parse date and time
            session_date = datetime.strptime(booking['session_date'], '%Y-%m-%d')
            time_parts = booking['session_time'].split(':')
            
            # Create datetime with timezone
            start_dt = self.sa_tz.localize(datetime(
                session_date.year, session_date.month, session_date.day,
                int(time_parts[0]), int(time_parts[1]) if len(time_parts) > 1 else 0
            ))
            
            # Default duration 1 hour
            end_dt = start_dt + timedelta(hours=1)
            
            # Format for ICS (UTC)
            start_utc = start_dt.astimezone(pytz.UTC)
            end_utc = end_dt.astimezone(pytz.UTC)
            
            # Generate unique ID
            uid = f"{booking.get('id', uuid.uuid4())}@refiloe.ai"
            
            # Get trainer and client info
            trainer = context_data.get('trainer', {})
            client = context_data.get('client', {})
            
            # Build event
            vevent = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.now(pytz.UTC).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{start_utc.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{end_utc.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:Training Session - {client.get('name', 'Client')}",
                f"DESCRIPTION:Personal Training Session\\n" +
                f"Trainer: {trainer.get('name', 'Trainer')}\\n" +
                f"Client: {client.get('name', 'Client')}\\n" +
                f"Type: {booking.get('session_type', 'Standard')}\\n" +
                f"Status: {booking.get('status', 'Confirmed').title()}\\n" +
                (f"Notes: {booking.get('notes', '')}" if booking.get('notes') else ""),
                f"LOCATION:{trainer.get('gym_location', 'TBD')}",
                f"ORGANIZER;CN={trainer.get('name', 'Trainer')}:mailto:{trainer.get('email', 'trainer@refiloe.ai')}",
            ]
            
            # Add attendee if client email available
            if client.get('email'):
                vevent.append(
                    f"ATTENDEE;CN={client.get('name', 'Client')};ROLE=REQ-PARTICIPANT;"
                    f"PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{client.get('email')}"
                )
            
            # Add alarm/reminder (15 minutes before)
            vevent.extend([
                "BEGIN:VALARM",
                "TRIGGER:-PT15M",
                "ACTION:DISPLAY",
                "DESCRIPTION:Training session in 15 minutes",
                "END:VALARM"
            ])
            
            vevent.append("END:VEVENT")
            
            return vevent
            
        except Exception as e:
            log_error(f"Error creating VEVENT: {str(e)}")
            return []
    
    def create_calendar_invite(self, booking: Dict, attendees: List[str]) -> Dict:
        """Create calendar invite with ICS attachment"""
        try:
            # Get booking details
            booking_info = self.db.table('bookings').select(
                '*, trainers(*), clients(*)'
            ).eq('id', booking['id']).single().execute()
            
            if not booking_info.data:
                return {'success': False, 'error': 'Booking not found'}
            
            # Generate ICS content
            ics_content = self.generate_ics_file({
                **booking_info.data,
                'trainer': booking_info.data.get('trainers'),
                'client': booking_info.data.get('clients')
            })
            
            # Create email with ICS attachment
            result = self.send_calendar_email(
                recipients=attendees,
                ics_content=ics_content,
                booking_info=booking_info.data
            )
            
            return result
            
        except Exception as e:
            log_error(f"Error creating calendar invite: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_calendar_email(self, recipients: List[str], ics_content: str, 
                           booking_info: Dict) -> Dict:
        """Send calendar invite via email"""
        try:
            if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
                log_error("Email configuration missing")
                return {'success': False, 'error': 'Email not configured'}
            
            # Create message
            msg = MIMEMultipart('mixed')
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"Training Session - {booking_info.get('session_date')}"
            
            # Email body
            trainer = booking_info.get('trainers', {})
            client = booking_info.get('clients', {})
            
            body_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Training Session Scheduled</h2>
                    <p>Your training session has been scheduled:</p>
                    <ul>
                        <li><strong>Date:</strong> {booking_info.get('session_date')}</li>
                        <li><strong>Time:</strong> {booking_info.get('session_time')}</li>
                        <li><strong>Trainer:</strong> {trainer.get('name', 'Your Trainer')}</li>
                        <li><strong>Location:</strong> {trainer.get('gym_location', 'TBD')}</li>
                    </ul>
                    <p>Please add this event to your calendar using the attached file.</p>
                    <p>Best regards,<br>{trainer.get('business_name', 'Refiloe AI')}</p>
                </body>
            </html>
            """
            
            # Attach HTML body
            msg.attach(MIMEText(body_html, 'html'))
            
            # Attach ICS file
            ics_part = MIMEBase('text', 'calendar', method='REQUEST')
            ics_part.set_payload(ics_content.encode('utf-8'))
            encoders.encode_base64(ics_part)
            ics_part.add_header('Content-Disposition', 'attachment', 
                               filename='training_session.ics')
            msg.attach(ics_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            log_info(f"Calendar invite sent to {recipients}")
            return {'success': True}
            
        except Exception as e:
            log_error(f"Error sending calendar email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def bulk_export_month(self, trainer_id: str, month: int, year: int) -> Dict:
        """Export all bookings for a month"""
        try:
            # Get date range
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # Get all bookings for the month
            bookings = self.db.table('bookings').select(
                '*, clients(name, email, whatsapp), trainers(name, email, business_name, gym_location)'
            ).eq('trainer_id', trainer_id).gte(
                'session_date', start_date.isoformat()
            ).lte('session_date', end_date.isoformat()).order(
                'session_date'
            ).order('session_time').execute()
            
            if not bookings.data:
                return {
                    'success': False,
                    'error': 'No bookings found for this month'
                }
            
            # Get trainer info
            trainer = self.db.table('trainers').select('*').eq(
                'id', trainer_id
            ).single().execute()
            
            return {
                'success': True,
                'bookings': bookings.data,
                'trainer': trainer.data,
                'month': month,
                'year': year,
                'count': len(bookings.data)
            }
            
        except Exception as e:
            log_error(f"Error exporting month: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def export_to_csv(self, bookings: List[Dict]) -> bytes:
        """Export bookings to CSV format"""
        try:
            output = BytesIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'Date', 'Time', 'Client', 'Phone', 'Email', 
                'Type', 'Status', 'Notes'
            ])
            
            # Data rows
            for booking in bookings:
                client = booking.get('clients', {})
                writer.writerow([
                    booking.get('session_date'),
                    booking.get('session_time'),
                    client.get('name', ''),
                    client.get('whatsapp', ''),
                    client.get('email', ''),
                    booking.get('session_type', 'standard'),
                    booking.get('status', ''),
                    booking.get('notes', '')
                ])
            
            return output.getvalue()
            
        except Exception as e:
            log_error(f"Error exporting to CSV: {str(e)}")
            raise
    
    def export_to_pdf(self, bookings: List[Dict], trainer_info: Dict) -> bytes:
        """Export bookings to PDF format"""
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title = Paragraph(
                f"Training Schedule - {trainer_info.get('business_name', 'Training Sessions')}",
                styles['Title']
            )
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Info
            info = Paragraph(
                f"Trainer: {trainer_info.get('name')}<br/>"
                f"Period: {bookings[0]['session_date']} to {bookings[-1]['session_date']}",
                styles['Normal']
            )
            story.append(info)
            story.append(Spacer(1, 12))
            
            # Table data
            data = [['Date', 'Time', 'Client', 'Type', 'Status']]
            
            for booking in bookings:
                client = booking.get('clients', {})
                data.append([
                    booking.get('session_date'),
                    booking.get('session_time'),
                    client.get('name', 'N/A'),
                    booking.get('session_type', 'standard'),
                    booking.get('status', 'confirmed')
                ])
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            doc.build(story)
            
            return buffer.getvalue()
            
        except Exception as e:
            log_error(f"Error exporting to PDF: {str(e)}")
            raise
    
    def get_email_preferences(self, trainer_id: str) -> Dict:
        """Get trainer's email preferences for calendar invites"""
        try:
            prefs = self.db.table('calendar_email_preferences').select('*').eq(
                'trainer_id', trainer_id
            ).single().execute()
            
            if prefs.data:
                return prefs.data
            
            # Return defaults if no preferences
            return {
                'send_on_booking': True,
                'send_on_update': True,
                'send_on_cancellation': True,
                'send_to_client': True,
                'send_to_trainer': False,
                'reminder_hours': 24
            }
            
        except Exception as e:
            log_error(f"Error getting email preferences: {str(e)}")
            return {}
    
    def update_email_preferences(self, trainer_id: str, preferences: Dict) -> Dict:
        """Update trainer's email preferences"""
        try:
            # Check if preferences exist
            existing = self.db.table('calendar_email_preferences').select('id').eq(
                'trainer_id', trainer_id
            ).execute()
            
            preferences['updated_at'] = datetime.now(self.sa_tz).isoformat()
            
            if existing.data:
                # Update existing
                result = self.db.table('calendar_email_preferences').update(
                    preferences
                ).eq('trainer_id', trainer_id).execute()
            else:
                # Insert new
                preferences['trainer_id'] = trainer_id
                preferences['created_at'] = datetime.now(self.sa_tz).isoformat()
                result = self.db.table('calendar_email_preferences').insert(
                    preferences
                ).execute()
            
            if result.data:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Failed to update preferences'}
                
        except Exception as e:
            log_error(f"Error updating email preferences: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_booking_notification(self, booking_id: str, event_type: str) -> Dict:
        """Send calendar notification based on event type"""
        try:
            # Get booking details
            booking = self.db.table('bookings').select(
                '*, trainers(*), clients(*)'
            ).eq('id', booking_id).single().execute()
            
            if not booking.data:
                return {'success': False, 'error': 'Booking not found'}
            
            trainer = booking.data.get('trainers', {})
            client = booking.data.get('clients', {})
            
            # Get email preferences
            prefs = self.get_email_preferences(trainer.get('id'))
            
            # Check if should send based on event type
            should_send = False
            subject_prefix = ""
            
            if event_type == 'created' and prefs.get('send_on_booking'):
                should_send = True
                subject_prefix = "New Booking: "
            elif event_type == 'updated' and prefs.get('send_on_update'):
                should_send = True
                subject_prefix = "Updated: "
            elif event_type == 'cancelled' and prefs.get('send_on_cancellation'):
                should_send = True
                subject_prefix = "Cancelled: "
            
            if not should_send:
                return {'success': True, 'message': 'Notification not required per preferences'}
            
            # Build recipient list
            recipients = []
            if prefs.get('send_to_client') and client.get('email'):
                recipients.append(client['email'])
            if prefs.get('send_to_trainer') and trainer.get('email'):
                recipients.append(trainer['email'])
            
            if not recipients:
                return {'success': True, 'message': 'No recipients with email addresses'}
            
            # Generate ICS content
            ics_content = self.generate_ics_file({
                **booking.data,
                'trainer': trainer,
                'client': client
            })
            
            # Send email
            return self.send_calendar_email(recipients, ics_content, booking.data)
            
        except Exception as e:
            log_error(f"Error sending booking notification: {str(e)}")
            return {'success': False, 'error': str(e)}