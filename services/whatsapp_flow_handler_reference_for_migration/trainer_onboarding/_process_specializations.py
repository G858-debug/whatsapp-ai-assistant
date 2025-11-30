    def _process_specializations(self, single_spec: str, multi_specs: list) -> str:
        """Convert specialization IDs to readable text and handle multiple specializations"""
        try:
            # Mapping from actual flow IDs to readable text (from trainer_onboarding_flow.json)
            spec_mapping = {
                'personal_training': 'Personal Training',
                'group_fitness': 'Group Fitness',
                'strength_training': 'Strength Training',
                'cardio_fitness': 'Cardio Fitness',
                'yoga_pilates': 'Yoga & Pilates',
                'sports_coaching': 'Sports Coaching',
                'nutrition_coaching': 'Nutrition Coaching',
                'rehabilitation': 'Rehabilitation & Recovery',
                'general_fitness': 'General Fitness'
            }
            
            specializations = []
            
            # Handle single specialization
            if single_spec:
                if single_spec in spec_mapping:
                    specializations.append(spec_mapping[single_spec])
                else:
                    specializations.append(single_spec)  # Use as-is if not in mapping
            
            # Handle multiple specializations
            if multi_specs and isinstance(multi_specs, list):
                for spec in multi_specs:
                    if spec in spec_mapping:
                        specializations.append(spec_mapping[spec])
                    else:
                        specializations.append(spec)
            
            # Return comma-separated readable values
            return ', '.join(specializations) if specializations else 'General Fitness'
            
        except Exception as e:
            log_error(f"Error processing specializations: {str(e)}")
            return single_spec or 'General Fitness'