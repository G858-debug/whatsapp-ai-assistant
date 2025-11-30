    def _extract_profile_edit_data_from_flow_response(self, flow_response: Dict, phone_number: str, user_type: str) -> Dict:
        """Extract profile edit data from WhatsApp flow response"""
        try:
            # Get form data from flow response
            form_data = {}
            
            # Try different possible data structures
            if 'data' in flow_response:
                form_data = flow_response['data']
            elif 'flow_action_payload' in flow_response:
                form_data = flow_response['flow_action_payload'].get('data', {})
            elif 'response' in flow_response:
                form_data = flow_response['response']
            
            log_info(f"Extracted profile edit form data keys: {list(form_data.keys())}")
            
            # Only include fields that have values (user wants to update)
            update_data = {}
            
            if user_type == 'trainer':
                # Process trainer-specific fields
                if form_data.get('first_name'):
                    update_data['first_name'] = form_data['first_name']
                if form_data.get('surname'):
                    update_data['last_name'] = form_data['surname']
                if form_data.get('email'):
                    update_data['email'] = form_data['email'].lower()
                if form_data.get('city'):
                    update_data['city'] = form_data['city']
                if form_data.get('business_name'):
                    update_data['business_name'] = form_data['business_name']
                if form_data.get('specializations'):
                    update_data['specialization'] = self._process_specializations('', form_data['specializations'])
                if form_data.get('experience_years') and form_data['experience_years'] != '':
                    update_data['experience_years'] = form_data['experience_years']
                    # Also update numeric field
                    exp_map = {'0-1': 1, '2-3': 2, '4-5': 4, '6-10': 7, '10+': 10}
                    update_data['years_experience'] = exp_map.get(form_data['experience_years'], 0)
                if form_data.get('pricing_per_session'):
                    try:
                        update_data['pricing_per_session'] = float(form_data['pricing_per_session'])
                    except (ValueError, TypeError):
                        pass
                if form_data.get('available_days'):
                    update_data['available_days'] = form_data['available_days']
                if form_data.get('preferred_time_slots') and form_data['preferred_time_slots'] != '':
                    update_data['preferred_time_slots'] = form_data['preferred_time_slots']
                if form_data.get('subscription_plan') and form_data['subscription_plan'] != '':
                    update_data['subscription_plan'] = form_data['subscription_plan']
                if form_data.get('notification_preferences'):
                    update_data['notification_preferences'] = form_data['notification_preferences']
                if form_data.get('marketing_consent') is not None:
                    update_data['marketing_consent'] = bool(form_data['marketing_consent'])
                if form_data.get('services_offered'):
                    update_data['services_offered'] = self._process_services_offered(form_data['services_offered'])
                if form_data.get('pricing_flexibility'):
                    update_data['pricing_flexibility'] = self._process_pricing_flexibility(form_data['pricing_flexibility'])
                if form_data.get('additional_notes'):
                    update_data['additional_notes'] = form_data['additional_notes']
                    
            elif user_type == 'client':
                # Process client-specific fields
                if form_data.get('name'):
                    update_data['name'] = form_data['name']
                if form_data.get('email'):
                    update_data['email'] = form_data['email'].lower()
                if form_data.get('fitness_goals'):
                    update_data['fitness_goals'] = form_data['fitness_goals']
                if form_data.get('availability'):
                    update_data['availability'] = form_data['availability']
                if form_data.get('notification_preferences'):
                    update_data['notification_preferences'] = form_data['notification_preferences']
                if form_data.get('marketing_consent') is not None:
                    update_data['marketing_consent'] = bool(form_data['marketing_consent'])
            
            # Update timestamp
            if update_data:
                from datetime import datetime
                update_data['updated_at'] = datetime.now().isoformat()
            
            log_info(f"Profile edit data for {phone_number} ({user_type}): {list(update_data.keys())}")
            
            return update_data
            
        except Exception as e:
            log_error(f"Error extracting profile edit data: {str(e)}")
            return {}