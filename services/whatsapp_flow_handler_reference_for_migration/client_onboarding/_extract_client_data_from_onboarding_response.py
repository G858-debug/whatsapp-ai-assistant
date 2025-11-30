    def _extract_client_data_from_onboarding_response(self, flow_response: Dict, client_phone: str) -> Optional[Dict]:
        """Extract client data from onboarding flow response"""
        try:
            # Get the response data
            response_data = flow_response.get('response', {})
            
            # Extract client information
            full_name = response_data.get('full_name', '').strip()
            email = response_data.get('email', '').strip()
            fitness_goals = response_data.get('fitness_goals', [])
            experience_level = response_data.get('experience_level', '')
            health_conditions = response_data.get('health_conditions', '').strip()
            availability = response_data.get('availability', [])
            
            if not full_name:
                log_error("Missing required client data: full_name")
                return None
            
            # Process fitness goals (convert from array to readable text)
            goals_map = {
                'lose_weight': 'Lose weight',
                'build_muscle': 'Build muscle',
                'get_stronger': 'Get stronger',
                'improve_fitness': 'Improve fitness',
                'train_for_event': 'Train for event'
            }
            
            if isinstance(fitness_goals, list):
                processed_goals = [goals_map.get(goal, goal) for goal in fitness_goals]
                fitness_goals_text = ', '.join(processed_goals)
            else:
                fitness_goals_text = str(fitness_goals)
            
            # Process experience level
            experience_map = {
                'beginner': 'Beginner',
                'intermediate': 'Intermediate',
                'advanced': 'Advanced',
                'athlete': 'Athlete'
            }
            experience_level_text = experience_map.get(experience_level, experience_level)
            
            # Process availability (convert from array to readable text)
            availability_map = {
                'early_morning': 'Early morning (5-8am)',
                'morning': 'Morning (8-12pm)',
                'afternoon': 'Afternoon (12-5pm)',
                'evening': 'Evening (5-8pm)',
                'flexible': 'Flexible'
            }
            
            if isinstance(availability, list):
                processed_availability = [availability_map.get(slot, slot) for slot in availability]
                availability_text = ', '.join(processed_availability)
            else:
                availability_text = str(availability)
            
            # Process health conditions
            if not health_conditions or health_conditions.lower() in ['none', 'n/a', 'nothing']:
                health_conditions = 'None specified'
            
            return {
                'name': full_name,
                'email': email if email else None,
                'fitness_goals': fitness_goals_text,
                'experience_level': experience_level_text,
                'health_conditions': health_conditions,
                'availability': availability_text,
                'trainer_id': None,  # No trainer assigned yet
                'requested_by': 'client'
            }
            
        except Exception as e:
            log_error(f"Error extracting client data from onboarding flow response: {str(e)}")
            return None