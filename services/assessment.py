from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import log_error, log_info
import json

class EnhancedAssessmentService:
    """Service for managing fitness assessments"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
        
    def create_default_template(self, trainer_id: str) -> str:
        """Create a default assessment template for trainer"""
        try:
            template_data = {
                'trainer_id': trainer_id,
                'template_name': 'Default Template',
                'is_active': True,
                'completed_by': 'client',
                'frequency': 'quarterly',
                'sections': {
                    'health': {
                        'enabled': True,
                        'required': True,
                        'questions': self._get_default_health_questions()
                    },
                    'lifestyle': {
                        'enabled': True,
                        'required': True,
                        'questions': self._get_default_lifestyle_questions()
                    },
                    'measurements': {
                        'enabled': True,
                        'required': True,
                        'fields': self._get_default_measurements()
                    },
                    'fitness_tests': {
                        'enabled': True,
                        'required': False,
                        'tests': self._get_default_fitness_tests()
                    },
                    'photos': {
                        'enabled': True,
                        'required': False,
                        'angles': ['front', 'side', 'back']
                    }
                }
            }

            result = self.db.table('assessment_templates').insert(template_data).execute()
            return result.data[0]['id'] if result.data else None

        except Exception as e:
            log_error(f"Error creating default template: {str(e)}")
            return None

    def validate_assessment_submission(self, assessment_id: str, data: Dict) -> Tuple[bool, str]:
        """Validate submitted assessment data"""
        try:
            assessment = self.db.table('fitness_assessments').select(
                '*', 'template:assessment_templates(*)'
            ).eq('id', assessment_id).single().execute()

            if not assessment.data:
                return False, "Assessment not found"

            template = assessment.data['template']
            errors = []

            # Validate required sections
            for section, config in template['sections'].items():
                if config['enabled'] and config['required']:
                    if section not in data or not data[section]:
                        errors.append(f"{section.title()} section is required")

            # Validate measurements
            if 'measurements' in data:
                for field in template['sections']['measurements']['fields']:
                    if field['required'] and (
                        field['name'] not in data['measurements'] or 
                        not str(data['measurements'][field['name']]).strip()
                    ):
                        errors.append(f"Measurement {field['name']} is required")

            return len(errors) == 0, "\n".join(errors)

        except Exception as e:
            log_error(f"Validation error: {str(e)}")
            return False, "Internal validation error"

    def create_assessment(self, trainer_id: str, client_id: str, template_id: Optional[str] = None) -> Dict:
        """Create a new assessment for a client"""
        try:
            # Use default template if none specified
            if not template_id:
                template_id = self._get_default_template_id(trainer_id)
                if not template_id:
                    template_id = self.create_default_template(trainer_id)
            
            assessment_data = {
                'trainer_id': trainer_id,
                'client_id': client_id,
                'template_id': template_id,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'due_date': (datetime.now() + timedelta(days=7)).isoformat()
            }
            
            result = self.db.table('fitness_assessments').insert(assessment_data).execute()
            
            if result.data:
                log_info(f"Assessment created for client {client_id}")
                return {'success': True, 'assessment_id': result.data[0]['id']}
            
            return {'success': False, 'error': 'Failed to create assessment'}
            
        except Exception as e:
            log_error(f"Error creating assessment: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def submit_assessment(self, assessment_id: str, data: Dict) -> Dict:
        """Submit assessment responses"""
        try:
            # Validate submission
            is_valid, error_msg = self.validate_assessment_submission(assessment_id, data)
            
            if not is_valid:
                return {'success': False, 'error': error_msg}
            
            # Update assessment with responses
            update_data = {
                'responses': data,
                'status': 'completed',
                'completed_at': datetime.now().isoformat()
            }
            
            result = self.db.table('fitness_assessments').update(
                update_data
            ).eq('id', assessment_id).execute()
            
            if result.data:
                log_info(f"Assessment {assessment_id} submitted successfully")
                return {'success': True, 'message': 'Assessment submitted successfully'}
            
            return {'success': False, 'error': 'Failed to submit assessment'}
            
        except Exception as e:
            log_error(f"Error submitting assessment: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_client_assessments(self, client_id: str) -> List[Dict]:
        """Get all assessments for a client"""
        try:
            result = self.db.table('fitness_assessments').select(
                '*, template:assessment_templates(template_name)'
            ).eq('client_id', client_id).order('created_at', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            log_error(f"Error fetching assessments: {str(e)}")
            return []
    
    def get_latest_assessment(self, client_id: str) -> Optional[Dict]:
        """Get the most recent completed assessment for a client"""
        try:
            result = self.db.table('fitness_assessments').select('*').eq(
                'client_id', client_id
            ).eq('status', 'completed').order(
                'completed_at', desc=True
            ).limit(1).execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            log_error(f"Error fetching latest assessment: {str(e)}")
            return None
    
    def _get_default_template_id(self, trainer_id: str) -> Optional[str]:
        """Get the default template ID for a trainer"""
        try:
            result = self.db.table('assessment_templates').select('id').eq(
                'trainer_id', trainer_id
            ).eq('is_active', True).eq(
                'template_name', 'Default Template'
            ).single().execute()
            
            return result.data['id'] if result.data else None
            
        except Exception as e:
            log_error(f"Error fetching default template: {str(e)}")
            return None
    
    def _get_default_health_questions(self) -> List[Dict]:
        """Get default health assessment questions"""
        return [
            {
                "id": "medical_conditions",
                "text": "Do you have any medical conditions?",
                "type": "multiselect",
                "options": ["Diabetes", "Hypertension", "Heart Disease", "Asthma", "Arthritis", "None"],
                "required": True
            },
            {
                "id": "medications",
                "text": "Are you currently taking any medications?",
                "type": "text",
                "required": False
            },
            {
                "id": "injuries",
                "text": "Do you have any current injuries or physical limitations?",
                "type": "text",
                "required": True
            },
            {
                "id": "pain_areas",
                "text": "Do you experience pain in any areas?",
                "type": "multiselect",
                "options": ["Lower Back", "Knees", "Shoulders", "Neck", "Hips", "None"],
                "required": True
            }
        ]
    
    def _get_default_lifestyle_questions(self) -> List[Dict]:
        """Get default lifestyle questions"""
        return [
            {
                "id": "exercise_frequency",
                "text": "How often do you currently exercise?",
                "type": "select",
                "options": ["Never", "1-2 times/week", "3-4 times/week", "5+ times/week"],
                "required": True
            },
            {
                "id": "diet_quality",
                "text": "How would you rate your current diet?",
                "type": "select",
                "options": ["Poor", "Fair", "Good", "Excellent"],
                "required": True
            },
            {
                "id": "sleep_hours",
                "text": "How many hours of sleep do you get per night?",
                "type": "select",
                "options": ["Less than 5", "5-6", "7-8", "More than 8"],
                "required": True
            },
            {
                "id": "stress_level",
                "text": "What is your current stress level?",
                "type": "select",
                "options": ["Low", "Moderate", "High", "Very High"],
                "required": True
            },
            {
                "id": "water_intake",
                "text": "How many glasses of water do you drink daily?",
                "type": "select",
                "options": ["Less than 4", "4-6", "7-8", "More than 8"],
                "required": True
            }
        ]
    
    def _get_default_measurements(self) -> List[Dict]:
        """Get default measurement fields"""
        return [
            {
                "name": "weight",
                "label": "Weight (kg)",
                "type": "number",
                "required": True,
                "min": 30,
                "max": 300
            },
            {
                "name": "height",
                "label": "Height (cm)",
                "type": "number",
                "required": True,
                "min": 100,
                "max": 250
            },
            {
                "name": "body_fat_percentage",
                "label": "Body Fat %",
                "type": "number",
                "required": False,
                "min": 3,
                "max": 60
            },
            {
                "name": "waist",
                "label": "Waist (cm)",
                "type": "number",
                "required": False,
                "min": 40,
                "max": 200
            },
            {
                "name": "chest",
                "label": "Chest (cm)",
                "type": "number",
                "required": False,
                "min": 50,
                "max": 200
            },
            {
                "name": "hips",
                "label": "Hips (cm)",
                "type": "number",
                "required": False,
                "min": 50,
                "max": 200
            },
            {
                "name": "bicep_left",
                "label": "Left Bicep (cm)",
                "type": "number",
                "required": False,
                "min": 15,
                "max": 60
            },
            {
                "name": "bicep_right",
                "label": "Right Bicep (cm)",
                "type": "number",
                "required": False,
                "min": 15,
                "max": 60
            },
            {
                "name": "thigh_left",
                "label": "Left Thigh (cm)",
                "type": "number",
                "required": False,
                "min": 25,
                "max": 100
            },
            {
                "name": "thigh_right",
                "label": "Right Thigh (cm)",
                "type": "number",
                "required": False,
                "min": 25,
                "max": 100
            }
        ]
    
    def _get_default_fitness_tests(self) -> List[Dict]:
        """Get default fitness test fields"""
        return [
            {
                "name": "pushups",
                "label": "Push-ups (max reps)",
                "type": "number",
                "required": False,
                "min": 0,
                "max": 200
            },
            {
                "name": "plank",
                "label": "Plank Hold (seconds)",
                "type": "number",
                "required": False,
                "min": 0,
                "max": 600
            },
            {
                "name": "squats",
                "label": "Bodyweight Squats (max reps)",
                "type": "number",
                "required": False,
                "min": 0,
                "max": 200
            },
            {
                "name": "resting_heart_rate",
                "label": "Resting Heart Rate (bpm)",
                "type": "number",
                "required": False,
                "min": 40,
                "max": 120
            },
            {
                "name": "blood_pressure_systolic",
                "label": "Blood Pressure - Systolic",
                "type": "number",
                "required": False,
                "min": 80,
                "max": 200
            },
            {
                "name": "blood_pressure_diastolic",
                "label": "Blood Pressure - Diastolic",
                "type": "number",
                "required": False,
                "min": 50,
                "max": 120
            }
        ]