"""
Client Relationship Commands - Phase 2
Handles client commands for managing trainer relationships
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_search_trainer(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /search-trainer command"""
    try:
        # Create search_trainer task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='search_trainer',
            task_data={'step': 'ask_search_term'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the search. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'search_trainer_task_error'}
        
        # Ask for search term
        msg = (
            "🔍 *Search for Trainers*\n\n"
            "Please enter the trainer's name you want to search for.\n\n"
            "💡 I'll show you up to 5 matching trainers.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'search_trainer_started'
        }
        
    except Exception as e:
        log_error(f"Error in search trainer command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'search_trainer_error'
        }


def handle_invite_trainer(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /invite-trainer command"""
    try:
        # Create invite_trainer task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='invite_trainer',
            task_data={'step': 'ask_trainer_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the invitation process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'invite_trainer_task_error'}
        
        # Ask for trainer ID
        msg = (
            "👥 *Invite Trainer*\n\n"
            "Please provide the trainer ID you want to invite.\n\n"
            "💡 Use /search-trainer to find trainers first.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'invite_trainer_started'
        }
        
    except Exception as e:
        log_error(f"Error in invite trainer command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'invite_trainer_error'
        }


def handle_view_trainers(phone: str, client_id: str, db, whatsapp) -> Dict:
    """Handle /view-trainers command"""
    try:
        from services.relationships import RelationshipService
        
        rel_service = RelationshipService(db)
        trainers = rel_service.get_client_trainers(client_id, status='active')
        
        if not trainers:
            msg = (
                "📋 *Your Trainers*\n\n"
                "You don't have any trainers yet.\n\n"
                "Use /search-trainer to find trainers\n"
                "or /invite-trainer to invite a specific trainer."
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_trainers_empty'}
        
        # Check if we need CSV or can display in chat
        if len(trainers) <= 5:
            # Display in chat
            msg = f"📋 *Your Trainers* ({len(trainers)})\n\n"
            
            for i, rel in enumerate(trainers, 1):
                trainer = rel.get('trainers', {})
                msg += f"*{i}. {trainer.get('name', 'N/A')}*\n"
                msg += f"   ID: {trainer.get('trainer_id', 'N/A')}\n"
                msg += f"   Phone: {trainer.get('whatsapp', 'N/A')}\n"
                
                if trainer.get('specialization'):
                    msg += f"   Specialization: {trainer['specialization']}\n"
                if trainer.get('experience_years'):
                    msg += f"   Experience: {trainer['experience_years']}\n"
                
                msg += f"   Connected: {rel.get('created_at', 'N/A')[:10]}\n\n"
            
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_trainers_chat'}
        
        else:
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
            writer.writerow(['Name', 'Trainer ID', 'Phone', 'Email', 'Specialization', 'Experience', 'City', 'Connected Date'])
            
            # Write data
            for rel in trainers:
                trainer = rel.get('trainers', {})
                writer.writerow([
                    trainer.get('name', ''),
                    trainer.get('trainer_id', ''),
                    trainer.get('whatsapp', ''),
                    trainer.get('email', ''),
                    trainer.get('specialization', ''),
                    trainer.get('experience_years', ''),
                    trainer.get('city', ''),
                    rel.get('created_at', '')[:10]
                ])
            
            csv_content = output.getvalue()
            
            # Save CSV to temporary file and upload to Supabase Storage
            try:
                # Create temp file
                temp_dir = tempfile.gettempdir()
                filename = f"trainers_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
                        caption=f"📋 Your {len(trainers)} trainers"
                    )
                    
                    if result.get('success'):
                        msg = (
                            f"✅ *Trainer List Sent!*\n\n"
                            f"📄 CSV file with {len(trainers)} trainers has been sent.\n\n"
                            f"Tap the document above to download."
                        )
                        whatsapp.send_message(phone, msg)
                        
                        log_info(f"CSV file sent successfully: {filename}")
                        
                        # Clean up local file
                        try:
                            os.remove(filepath)
                        except:
                            pass
                        
                        return {'success': True, 'response': msg, 'handler': 'view_trainers_csv_sent'}
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
                    f"📋 *Your Trainers* ({len(trainers)})\n\n"
                    f"You have {len(trainers)} trainers.\n\n"
                    f"*Preview (first 10 rows):*\n"
                )
                
                # Add preview of first 10 rows
                lines = csv_content.split('\n')[:11]  # Header + 10 rows
                for line in lines:
                    if line.strip():
                        msg += f"`{line[:100]}`\n"
                
                msg += f"\n⚠️ Could not send as downloadable file. Showing preview instead."
                
                whatsapp.send_message(phone, msg)
                
                return {'success': True, 'response': msg, 'handler': 'view_trainers_csv_fallback'}
        
    except Exception as e:
        log_error(f"Error viewing trainers: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your trainers. Please try again.",
            'handler': 'view_trainers_error'
        }


def handle_remove_trainer(phone: str, client_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /remove-trainer command"""
    try:
        # Create remove_trainer task
        task_id = task_service.create_task(
            user_id=client_id,
            role='client',
            task_type='remove_trainer',
            task_data={'step': 'ask_trainer_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the removal process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'remove_trainer_task_error'}
        
        # Ask for trainer ID
        msg = (
            "🗑️ *Remove Trainer*\n\n"
            "Please provide the trainer ID you want to remove.\n\n"
            "⚠️ This will remove them from your trainer list and delete all habit assignments from them.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'remove_trainer_started'
        }
        
    except Exception as e:
        log_error(f"Error in remove trainer command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'remove_trainer_error'
        }
