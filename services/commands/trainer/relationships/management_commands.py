"""
Trainer Relationship Management Commands
Handles client viewing and removal
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_view_trainees(phone: str, trainer_id: str, db, whatsapp) -> Dict:
    """Handle /view-trainees command"""
    try:
        from services.relationships import RelationshipService
        
        rel_service = RelationshipService(db)
        clients = rel_service.get_trainer_clients(trainer_id, status='active')
        
        if not clients:
            msg = (
                "📋 *Your Clients*\n\n"
                "You don't have any clients yet.\n\n"
                "Use /invite-trainee to invite an existing client\n"
                "or /create-trainee to create a new client account."
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_trainees_empty'}
        
        # Check if we need dashboard or can display in chat
        if len(clients) <= 3:
            # Display in chat with dashboard option
            msg = f"📋 *Your Clients* ({len(clients)})\n\n"
            
            for i, client in enumerate(clients, 1):
                rel = client.get('relationship', {})
                msg += f"*{i}. {client.get('name', 'N/A')}*\n"
                msg += f"   ID: {client.get('client_id', 'N/A')}\n"
                msg += f"   Phone: {client.get('whatsapp', 'N/A')}\n"
                
                if client.get('fitness_goals'):
                    msg += f"   Goals: {client['fitness_goals']}\n"
                
                msg += f"   Joined: {rel.get('created_at', 'N/A')[:10]}\n\n"
            
            # Add dashboard option
            msg += "🌐 *Want a better view?*\nUse the web dashboard for search, filter, and management features!"
            
            buttons = [
                {'id': '/dashboard-clients', 'title': '🌐 Web Dashboard'},
                {'id': '/help', 'title': '📚 Help'}
            ]
            whatsapp.send_button_message(phone, msg, buttons)
            return {'success': True, 'response': msg, 'handler': 'view_trainees_chat'}
        
        else:
            # Too many clients - recommend dashboard
            from services.commands.dashboard import generate_dashboard_link
            
            dashboard_result = generate_dashboard_link(trainer_id, 'trainer', db, whatsapp)
            
            if dashboard_result['success']:
                return dashboard_result
            
            # Fallback to CSV if dashboard fails
            # Generate CSV
            import csv
            import io
            import os
            import tempfile
            from datetime import datetime
            from services.helpers.supabase_storage import SupabaseStorageHelper
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Name', 'Client ID', 'Phone', 'Email', 'Goals', 'Experience', 'Joined Date'])
            
            # Write data
            for client in clients:
                rel = client.get('relationship', {})
                writer.writerow([
                    client.get('name', ''),
                    client.get('client_id', ''),
                    client.get('whatsapp', ''),
                    client.get('email', ''),
                    client.get('fitness_goals', ''),
                    client.get('experience_level', ''),
                    rel.get('created_at', '')[:10]
                ])
            
            csv_content = output.getvalue()
            
            # Save CSV to temporary file and upload to Supabase Storage
            try:
                # Create temp file
                temp_dir = tempfile.gettempdir()
                filename = f"clients_{trainer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = os.path.join(temp_dir, filename)
                
                # Write CSV to file
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_content)
                
                # Upload to Supabase Storage
                storage_helper = SupabaseStorageHelper(db)
                public_url = storage_helper.upload_csv(filepath, filename)
                
                if public_url:
                    # Send as downloadable document
                    result = whatsapp.send_document(
                        phone,
                        public_url,
                        filename=filename,
                        caption=f"📋 Your {len(clients)} clients"
                    )
                    
                    if result.get('success'):
                        msg = (
                            f"✅ *Client List Sent!*\n\n"
                            f"📄 CSV file with {len(clients)} clients has been sent.\n\n"
                            f"Tap the document above to download."
                        )
                        whatsapp.send_message(phone, msg)
                        
                        log_info(f"CSV file sent successfully: {filename}")
                        
                        # Clean up local file
                        try:
                            os.remove(filepath)
                        except:
                            pass
                        
                        return {'success': True, 'response': msg, 'handler': 'view_trainees_csv_sent'}
                    else:
                        # Document send failed, send preview
                        log_error(f"Failed to send document: {result.get('error')}")
                        raise Exception("Document send failed")
                else:
                    # Upload failed, send preview
                    raise Exception("Upload to Supabase Storage failed")
                
            except Exception as csv_error:
                log_error(f"Error with CSV file delivery: {str(csv_error)}")
                
                # Fallback to text preview
                msg = (
                    f"📋 *Your Clients* ({len(clients)})\n\n"
                    f"You have {len(clients)} clients.\n\n"
                    f"*Preview (first 10 rows):*\n"
                )
                
                # Add preview of first 10 rows
                lines = csv_content.split('\n')[:11]  # Header + 10 rows
                for line in lines:
                    if line.strip():
                        msg += f"`{line[:100]}`\n"
                
                msg += f"\n⚠️ Could not send as downloadable file. Showing preview instead."
                
                whatsapp.send_message(phone, msg)
                
                return {'success': True, 'response': msg, 'handler': 'view_trainees_csv_fallback'}
        
    except Exception as e:
        log_error(f"Error viewing trainees: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your clients. Please try again.",
            'handler': 'view_trainees_error'
        }


def handle_remove_trainee(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /remove-trainee command"""
    try:
        # Create remove_trainee task
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='remove_trainee',
            task_data={'step': 'ask_client_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the removal process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'remove_trainee_task_error'}
        
        # Ask for client ID
        msg = (
            "🗑️ *Remove Client*\n\n"
            "Please provide the client ID you want to remove.\n\n"
            "⚠️ This will remove them from your client list and delete all habit assignments.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'remove_trainee_started'
        }
        
    except Exception as e:
        log_error(f"Error in remove trainee command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'remove_trainee_error'
        }