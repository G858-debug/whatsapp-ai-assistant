"""
Trainer Habit Assignment Commands
Handles habit assignment and client habit management
"""
from typing import Dict
from utils.logger import log_info, log_error


def handle_assign_habits(phone: str, trainer_id: str, db, whatsapp, task_service) -> Dict:
    """Handle /assign-habit command"""
    try:
        # Create assign_habit task
        task_id = task_service.create_task(
            user_id=trainer_id,
            role='trainer',
            task_type='assign_habit',
            task_data={'step': 'ask_habit_id'}
        )
        
        if not task_id:
            msg = "❌ I couldn't start the assignment process. Please try again."
            whatsapp.send_message(phone, msg)
            return {'success': False, 'response': msg, 'handler': 'assign_habit_task_error'}
        
        # Ask for habit ID
        msg = (
            "📌 *Assign Habit to Clients*\n\n"
            "Please provide the habit ID you want to assign.\n\n"
            "💡 Use /view-habits to see your habits and their IDs.\n\n"
            "Type /stop to cancel."
        )
        whatsapp.send_message(phone, msg)
        
        return {
            'success': True,
            'response': msg,
            'handler': 'assign_habit_started'
        }
        
    except Exception as e:
        log_error(f"Error in assign habit command: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I encountered an error. Please try again.",
            'handler': 'assign_habit_error'
        }


def handle_view_client_habits(phone: str, trainer_id: str, db, whatsapp) -> Dict:
    """Handle /view-habits command"""
    try:
        from services.habits.habit_service import HabitService
        
        habit_service = HabitService(db)
        success, msg, habits = habit_service.get_trainer_habits(trainer_id, active_only=True)
        
        if not success:
            error_msg = "❌ I couldn't load your habits. Please try again."
            whatsapp.send_message(phone, error_msg)
            return {'success': False, 'response': error_msg, 'handler': 'view_habits_error'}
        
        if not habits:
            msg = (
                "🎯 *Your Habits*\n\n"
                "You haven't created any habits yet.\n\n"
                "Use /create-habit to create your first habit!"
            )
            whatsapp.send_message(phone, msg)
            return {'success': True, 'response': msg, 'handler': 'view_habits_empty'}
        
        # Check if we need CSV or can display in chat
        if len(habits) <= 5:
            # Display in chat
            response_msg = f"🎯 *Your Habits* ({len(habits)})\n\n"
            
            for i, habit in enumerate(habits, 1):
                # Get assignment count
                assignment_count = habit_service.get_habit_assignment_count(habit.get('habit_id'))
                
                response_msg += f"*{i}. {habit.get('habit_name')}*\n"
                response_msg += f"   ID: `{habit.get('habit_id')}`\n"
                response_msg += f"   Target: {habit.get('target_value')} {habit.get('unit')}\n"
                response_msg += f"   Frequency: {habit.get('frequency')}\n"
                response_msg += f"   Assigned to: {assignment_count} client(s)\n"
                
                if habit.get('description'):
                    desc = habit['description'][:50] + '...' if len(habit['description']) > 50 else habit['description']
                    response_msg += f"   Description: {desc}\n"
                
                response_msg += "\n"
            
            response_msg += "💡 Use /assign-habit to assign habits to clients."
            
            whatsapp.send_message(phone, response_msg)
            return {'success': True, 'response': response_msg, 'handler': 'view_habits_chat'}
        
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
            writer.writerow(['Habit Name', 'Habit ID', 'Target Value', 'Unit', 'Frequency', 'Assigned Clients', 'Description', 'Created Date'])
            
            # Write data
            for habit in habits:
                assignment_count = habit_service.get_habit_assignment_count(habit.get('habit_id'))
                writer.writerow([
                    habit.get('habit_name', ''),
                    habit.get('habit_id', ''),
                    habit.get('target_value', ''),
                    habit.get('unit', ''),
                    habit.get('frequency', ''),
                    assignment_count,
                    habit.get('description', ''),
                    habit.get('created_at', '')[:10]
                ])
            
            csv_content = output.getvalue()
            
            # Save CSV to temporary file and upload to Supabase Storage
            try:
                # Create temp file
                temp_dir = tempfile.gettempdir()
                filename = f"habits_{trainer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
                        caption=f"🎯 Your {len(habits)} habits"
                    )
                    
                    if result.get('success'):
                        response_msg = (
                            f"✅ *Habit List Sent!*\n\n"
                            f"📄 CSV file with {len(habits)} habits has been sent.\n\n"
                            f"Tap the document above to download."
                        )
                        whatsapp.send_message(phone, response_msg)
                        
                        log_info(f"CSV file sent successfully: {filename}")
                        
                        # Clean up local file
                        try:
                            os.remove(filepath)
                        except:
                            pass
                        
                        return {'success': True, 'response': response_msg, 'handler': 'view_habits_csv_sent'}
                    else:
                        log_error(f"Failed to send document: {result.get('error')}")
                        raise Exception("Document send failed")
                else:
                    raise Exception("Upload to Supabase Storage failed")
                
            except Exception as csv_error:
                log_error(f"Error with CSV file delivery: {str(csv_error)}")
                
                # Fallback to text preview
                response_msg = (
                    f"🎯 *Your Habits* ({len(habits)})\n\n"
                    f"You have {len(habits)} habits.\n\n"
                    f"*Preview (first 5):*\n\n"
                )
                
                for i, habit in enumerate(habits[:5], 1):
                    response_msg += f"*{i}. {habit.get('habit_name')}*\n"
                    response_msg += f"   ID: `{habit.get('habit_id')}`\n\n"
                
                response_msg += f"\n⚠️ Could not send as downloadable file."
                
                whatsapp.send_message(phone, response_msg)
                
                return {'success': True, 'response': response_msg, 'handler': 'view_habits_csv_fallback'}
        
    except Exception as e:
        log_error(f"Error viewing habits: {str(e)}")
        return {
            'success': False,
            'response': "Sorry, I couldn't load your habits. Please try again.",
            'handler': 'view_habits_error'
        }