from datetime import datetime, timedelta
import pytz
import json
import secrets
import re
from typing import Dict, List, Optional, Tuple
from flask import url_for

from utils.logger import log_error, log_info

class EnhancedAssessmentService:
    """Enhanced fitness assessment service with AI understanding and web forms"""
    
    def __init__(self, config, supabase_client, ai_service=None):
        self.config = config
        self.db = supabase_client
        self.ai_service = ai_service  # Claude API service
        self.sa_tz = pytz.timezone(config.TIMEZONE)
        
        # Base URL for web forms
        self.base_url = config.DASHBOARD_BASE_URL if hasattr(config, 'DASHBOARD_BASE_URL') else 'https://web-production-26de5.up.railway.app'
    
    def understand_assessment_intent(self, message: str, trainer_id: str) -> Dict:
        """Use AI to understand assessment-related intent from natural language"""
        
        # Keywords that might indicate assessment intent
        assessment_keywords = [
            'assessment', 'assess', 'evaluation', 'fitness test', 'fitness check',
            'check progress', 'measure', 'test fitness', 'fitness level',
            'initial consultation', 'onboarding', 'intake form', 'health check',
            'body measurements', 'fitness goals', 'health questionnaire'
        ]
        
        view_keywords = [
            'view', 'show', 'see', 'check', 'look at', 'display', 'results',
            'report', 'summary', 'data', 'information', 'details'
        ]
        
        progress_keywords = [
            'progress', 'improvement', 'changes', 'results', 'gains',
            'transformation', 'before after', 'comparison', 'track'
        ]
        
        message_lower = message.lower()
        
        # Determine intent
        intent = {
            'type': None,
            'client_name': None,
            'confidence': 0
        }
        
        # Check for client name
        client_name_pattern = r'\b(?:for|of|on)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        name_match = re.search(client_name_pattern, message, re.IGNORECASE)
        if name_match:
            intent['client_name'] = name_match.group(1)
        
        # Determine action type
        if any(keyword in message_lower for keyword in assessment_keywords):
            if any(keyword in message_lower for keyword in view_keywords):
                intent['type'] = 'view_assessment'
                intent['confidence'] = 0.9
            elif any(keyword in message_lower for keyword in ['start', 'begin', 'initiate', 'do', 'conduct', 'perform']):
                intent['type'] = 'start_assessment'
                intent['confidence'] = 0.9
            else:
                intent['type'] = 'assessment_general'
                intent['confidence'] = 0.7
        
        elif any(keyword in message_lower for keyword in progress_keywords):
            intent['type'] = 'track_progress'
            intent['confidence'] = 0.8
        
        # Use AI for more complex understanding if available
        if self.ai_service and intent['confidence'] < 0.7:
            ai_intent = self.get_ai_intent(message, trainer_id)
            if ai_intent:
                intent.update(ai_intent)
        
        return intent
    
    def get_ai_intent(self, message: str, trainer_id: str) -> Optional[Dict]:
        """Use Claude to understand intent"""
        try:
            # Get trainer's clients for context
            clients = self.db.table('clients').select('name').eq(
                'trainer_id', trainer_id
            ).execute()
            
            client_names = [c['name'] for c in clients.data] if clients.data else []
            
            prompt = f"""Analyze this message about fitness assessments.
            
Trainer's clients: {', '.join(client_names)}
Message: "{message}"

Determine:
1. Intent: start_assessment, view_assessment, track_progress, or none
2. Client name mentioned (must be from the client list)
3. Confidence (0-1)

Return JSON only:
{{"type": "...", "client_name": "...", "confidence": 0.0}}"""
            
            # Call AI service (implement based on your Claude integration)
            # This is a placeholder - integrate with your actual AI service
            # response = self.ai_service.analyze(prompt)
            
            return None  # Placeholder
            
        except Exception as e:
            log_error(f"Error in AI intent analysis: {str(e)}")
            return None
    
    def create_assessment_with_template(self, trainer_id: str, client_id: str, 
                                       client_name: str = None) -> Dict:
        """Create assessment using trainer's template"""
        try:
            # Get trainer's active template
            template = self.db.table('assessment_templates').select('*').eq(
                'trainer_id', trainer_id
            ).eq('is_active', True).execute()
            
            if not template.data:
                # Create default template if none exists
                template_id = self.create_default_template(trainer_id)
            else:
                template_id = template.data[0]['id']
                template = template.data[0]
            
            # Generate secure access token
            access_token = secrets.token_urlsafe(32)
            
            # Create assessment
            assessment_data = {
                'trainer_id': trainer_id,
                'client_id': client_id,
                'template_id': template_id,
                'assessment_type': 'initial',
                'status': 'pending',
                'access_token': access_token,
                'token_expires_at': (datetime.now(self.sa_tz) + timedelta(days=7)).isoformat(),
                'completed_by': template.get('completed_by', 'client') if template else 'client'
            }
            
            result = self.db.table('fitness_assessments').insert(assessment_data).execute()
            
            if result.data:
                assessment_id = result.data[0]['id']
                
                # Generate form URL
                form_url = f"{self.base_url}/assessment/{access_token}"
                
                # Schedule reminders if needed
                if template and template.get('frequency') != 'once':
                    self.schedule_next_assessment(assessment_id, template)
                
                return {
                    'success': True,
                    'assessment_id': assessment_id,
                    'form_url': form_url,
                    'completed_by': assessment_data['completed_by'],
                    'message': self.get_assessment_message(
                        client_name or 'the client',
                        form_url,
                        assessment_data['completed_by']
                    )
                }
            
        except Exception as e:
            log_error(f"Error creating assessment: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to create assessment'
            }
    
    def get_assessment_message(self, client_name: str, form_url: str, 
                              completed_by: str) -> str:
        """Generate appropriate message based on who completes the assessment"""
        
        if completed_by == 'trainer':
            return f"""📋 *Fitness Assessment for {client_name}*

I've created an assessment form for you to complete during your session with {client_name}.

🔗 *Assessment Link:*
{form_url}

This link will open a form where you can:
• Record health information
• Input measurements
• Document fitness test results
• Upload progress photos

The form saves automatically as you go. Complete it whenever convenient during your session!

Valid for 7 days."""
        
        else:  # Client completes
            return f"""🎯 *FITNESS ASSESSMENT*

Hi {client_name}! 👋

Your trainer has requested a fitness assessment to create your personalized program!

🔗 *Your Assessment Link:*
{form_url}

Click the link to:
✅ Answer health questions
✅ Share your fitness goals
✅ Input measurements
✅ Complete simple fitness tests
✅ Upload progress photos (optional)

⏱️ Takes about 10-15 minutes
📱 Works perfectly on your phone
💾 Saves automatically as you go

This link expires in 7 days. You can pause and resume anytime!

Ready to start your fitness journey? 💪"""
    
    def create_default_template(self, trainer_id: str) -> str:
        """Create a default assessment template for trainer"""
        try:
            # Get core questions from library
            core_questions = self.db.table('question_library').select('*').eq(
                'is_core', True
            ).order('display_order').execute()
            
            # Organize by category
            health_q = [q['id'] for q in core_questions.data if q['category'] == 'health']
            lifestyle_q = [q['id'] for q in core_questions.data if q['category'] == 'lifestyle']
            goals_q = [q['id'] for q in core_questions.data if q['category'] == 'goals']
            measurements_q = [q['id'] for q in core_questions.data if q['category'] == 'measurements']
            tests_q = [q['id'] for q in core_questions.data if q['category'] == 'tests']
            
            template_data = {
                'trainer_id': trainer_id,
                'template_name': 'Default Template',
                'is_active': True,
                'completed_by': 'client',
                'frequency': 'quarterly',
                'include_health': True,
                'include_lifestyle': True,
                'include_goals': True,
                'include_measurements': True,
                'include_tests': True,
                'include_photos': True,
                'health_questions': json.dumps(health_q),
                'lifestyle_questions': json.dumps(lifestyle_q),
                'goals_questions': json.dumps(goals_q),
                'measurement_fields': json.dumps(measurements_q),
                'test_fields': json.dumps(tests_q)
            }
            
            result = self.db.table('assessment_templates').insert(template_data).execute()
            
            if result.data:
                log_info(f"Created default template for trainer {trainer_id}")
                return result.data[0]['id']
                
        except Exception as e:
            log_error(f"Error creating default template: {str(e)}")
            return None
    
    def get_assessment_results(self, trainer_id: str, client_id: Optional[str] = None,
                              assessment_id: Optional[str] = None) -> Dict:
        """Get assessment results for viewing"""
        try:
            query = self.db.table('fitness_assessments').select(
                '''*, 
                clients(name, whatsapp),
                physical_measurements(*),
                fitness_goals(*),
                fitness_test_results(*),
                assessment_photos(*)'''
            )
            
            if assessment_id:
                query = query.eq('id', assessment_id)
            elif client_id:
                query = query.eq('client_id', client_id)
            else:
                query = query.eq('trainer_id', trainer_id)
            
            query = query.eq('status', 'completed').order('assessment_date', desc=True)
            
            results = query.execute()
            
            if not results.data:
                return {
                    'success': False,
                    'message': 'No completed assessments found'
                }
            
            # Format results for display
            assessments = []
            for assess in results.data:
                # Calculate progress if multiple assessments
                progress = self.calculate_progress(client_id) if client_id else None
                
                assessment_data = {
                    'id': assess['id'],
                    'date': assess['assessment_date'],
                    'client_name': assess['clients']['name'] if assess.get('clients') else 'Unknown',
                    'measurements': assess.get('physical_measurements', []),
                    'goals': assess.get('fitness_goals', []),
                    'tests': assess.get('fitness_test_results', []),
                    'photos': assess.get('assessment_photos', []),
                    'progress': progress,
                    'red_flags': assess.get('red_flags', []),
                    'requires_clearance': assess.get('requires_medical_clearance', False)
                }
                
                assessments.append(assessment_data)
            
            return {
                'success': True,
                'assessments': assessments,
                'count': len(assessments)
            }
            
        except Exception as e:
            log_error(f"Error getting assessment results: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to retrieve assessments'
            }
    
    def calculate_progress(self, client_id: str) -> Dict:
        """Calculate progress between assessments"""
        try:
            # Get last two completed assessments
            assessments = self.db.table('physical_measurements').select('*').eq(
                'client_id', client_id
            ).order('measurement_date', desc=True).limit(2).execute()
            
            if len(assessments.data) < 2:
                return None
            
            latest = assessments.data[0]
            previous = assessments.data[1]
            
            progress = {
                'weight_change': (latest.get('weight_kg', 0) - previous.get('weight_kg', 0)) if latest.get('weight_kg') and previous.get('weight_kg') else None,
                'bmi_change': (latest.get('bmi', 0) - previous.get('bmi', 0)) if latest.get('bmi') and previous.get('bmi') else None,
                'waist_change': (latest.get('waist', 0) - previous.get('waist', 0)) if latest.get('waist') and previous.get('waist') else None,
                'body_fat_change': (latest.get('body_fat_percentage', 0) - previous.get('body_fat_percentage', 0)) if latest.get('body_fat_percentage') and previous.get('body_fat_percentage') else None
            }
            
            # Get fitness test improvements
            tests = self.db.table('fitness_test_results').select('*').eq(
                'client_id', client_id
            ).order('test_date', desc=True).limit(2).execute()
            
            if len(tests.data) >= 2:
                latest_test = tests.data[0]
                previous_test = tests.data[1]
                
                progress['pushups_change'] = (latest_test.get('push_ups_count', 0) - previous_test.get('push_ups_count', 0)) if latest_test.get('push_ups_count') is not None else None
                progress['plank_change'] = (latest_test.get('plank_hold_seconds', 0) - previous_test.get('plank_hold_seconds', 0)) if latest_test.get('plank_hold_seconds') is not None else None
            
            return progress
            
        except Exception as e:
            log_error(f"Error calculating progress: {str(e)}")
            return None
    
    def schedule_next_assessment(self, assessment_id: str, template: Dict):
        """Schedule the next assessment based on frequency"""
        try:
            frequency = template.get('frequency', 'quarterly')
            
            # Calculate next date
            if frequency == 'monthly':
                next_date = datetime.now(self.sa_tz) + timedelta(days=30)
            elif frequency == 'quarterly':
                next_date = datetime.now(self.sa_tz) + timedelta(days=90)
            elif frequency == 'biannual':
                next_date = datetime.now(self.sa_tz) + timedelta(days=180)
            elif frequency == 'annual':
                next_date = datetime.now(self.sa_tz) + timedelta(days=365)
            else:
                return
            
            # Get assessment details
            assessment = self.db.table('fitness_assessments').select(
                'trainer_id, client_id'
            ).eq('id', assessment_id).execute()
            
            if assessment.data:
                # Create reminder
                reminder_data = {
                    'trainer_id': assessment.data[0]['trainer_id'],
                    'client_id': assessment.data[0]['client_id'],
                    'template_id': template['id'],
                    'due_date': next_date.isoformat(),
                    'reminder_type': 'due_date',
                    'status': 'pending'
                }
                
                self.db.table('assessment_reminders').insert(reminder_data).execute()
                
                log_info(f"Scheduled next assessment for {next_date.date()}")
                
        except Exception as e:
            log_error(f"Error scheduling assessment: {str(e)}")
    
    def check_and_send_reminders(self):
        """Check for due assessment reminders and send them"""
        try:
            # Get pending reminders due today or overdue
            today = datetime.now(self.sa_tz)
            
            reminders = self.db.table('assessment_reminders').select(
                '*, clients(name, whatsapp), trainers(name, whatsapp)'
            ).eq('status', 'pending').lte('due_date', today.isoformat()).execute()
            
            for reminder in reminders.data:
                # Send reminder based on template settings
                template = self.db.table('assessment_templates').select('*').eq(
                    'id', reminder['template_id']
                ).execute()
                
                if template.data:
                    completed_by = template.data[0].get('completed_by', 'client')
                    
                    if completed_by == 'trainer':
                        # Remind trainer
                        message = f"""📋 Assessment Reminder

It's time for {reminder['clients']['name']}'s fitness assessment!

This helps track progress and adjust their program.

Reply 'Start assessment for {reminder['clients']['name']}' when ready."""
                        
                        # Send via WhatsApp service
                        # self.whatsapp.send_message(reminder['trainers']['whatsapp'], message)
                    
                    else:
                        # Remind client
                        message = f"""🎯 Time for Your Fitness Assessment!

Hi {reminder['clients']['name']}! 

It's time for your periodic fitness assessment to track your amazing progress! 💪

Your trainer will send you the assessment link shortly.

This helps us optimize your training program!"""
                        
                        # Send via WhatsApp service
                        # self.whatsapp.send_message(reminder['clients']['whatsapp'], message)
                    
                    # Mark reminder as sent
                    self.db.table('assessment_reminders').update({
                        'status': 'sent',
                        'sent_at': today.isoformat()
                    }).eq('id', reminder['id']).execute()
                    
        except Exception as e:
            log_error(f"Error sending reminders: {str(e)}")
    
    def format_assessment_summary(self, assessment_data: Dict) -> str:
        """Format assessment data for WhatsApp display"""
        
        assess = assessment_data['assessments'][0] if assessment_data.get('assessments') else None
        
        if not assess:
            return "No assessment data available."
        
        # Format date
        date = datetime.fromisoformat(assess['date']).strftime('%d %B %Y')
        
        summary = f"""📊 *FITNESS ASSESSMENT RESULTS*
*Client:* {assess['client_name']}
*Date:* {date}

"""
        
        # Add measurements if available
        if assess['measurements']:
            m = assess['measurements'][0]
            summary += f"""📏 *Measurements:*
• Weight: {m.get('weight_kg', 'N/A')}kg
• Height: {m.get('height_cm', 'N/A')}cm
• BMI: {m.get('bmi', 'N/A')}
• Waist: {m.get('waist', 'N/A')}cm
"""
        
        # Add goals if available
        if assess['goals']:
            g = assess['goals'][0]
            summary += f"""
🎯 *Goals:*
• Primary: {g.get('primary_goal', 'N/A').replace('_', ' ').title()}
• Target: {g.get('goal_description', 'N/A')}
• Timeline: {g.get('timeline_weeks', 'N/A')} weeks
"""
        
        # Add test results if available
        if assess['tests']:
            t = assess['tests'][0]
            summary += f"""
💪 *Fitness Tests:*
• Push-ups: {t.get('push_ups_count', 0)}
• Plank: {t.get('plank_hold_seconds', 0)} seconds
• Squats: {t.get('squat_reps', 0)}
"""
        
        # Add progress if available
        if assess.get('progress'):
            p = assess['progress']
            if p.get('weight_change') is not None:
                summary += f"""
📈 *Progress Since Last Assessment:*
• Weight: {p['weight_change']:+.1f}kg
• Push-ups: {p.get('pushups_change', 0):+d} more
• Plank: {p.get('plank_change', 0):+d} seconds longer
"""
        
        # Add warnings if any
        if assess.get('requires_clearance'):
            summary += "\n⚠️ *Note:* Medical clearance required before intensive training"
        
        # Add photo count
        if assess.get('photos'):
            summary += f"\n📸 {len(assess['photos'])} progress photos on file"
        
        return summary
