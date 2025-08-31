# [Previous code remains the same until create_default_template]

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

    def _get_default_health_questions(self) -> List[Dict]:
        """Get default health assessment questions"""
        return [
            {
                "id": "medical_conditions",
                "text": "Do you have any medical conditions?",
                "type": "multiselect",
                "options": ["Diabetes", "Hypertension", "Heart Disease", "None"],
                "required": True
            },
            # Add more default health questions
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
            # Add more measurement fields
        ]
