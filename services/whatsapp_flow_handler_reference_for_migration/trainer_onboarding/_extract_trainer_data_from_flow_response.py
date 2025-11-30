    def _extract_trainer_data_from_flow_response(self, flow_response: Dict, phone_number: str) -> Dict:
        """Extract trainer data from WhatsApp flow response"""
        try:
            # Get form data from flow response
            # WhatsApp flows return data in different possible structures
            form_data = {}
            
            # Try different possible data structures
            if 'data' in flow_response:
                form_data = flow_response['data']
            elif 'flow_action_payload' in flow_response:
                form_data = flow_response['flow_action_payload'].get('data', {})
            elif 'response' in flow_response:
                form_data = flow_response['response']
            
            log_info(f"Extracted form data keys: {list(form_data.keys())}")
            
            # Map flow form fields to trainer data structure
            # Based on our trainer_onboarding_flow.json structure
            
            # Basic info (from basic_info screen)
            first_name = form_data.get('first_name', '')
            surname = form_data.get('surname', '')
            full_name = f"{first_name} {surname}".strip() if first_name or surname else ''
            email = form_data.get('email', '')
            city = form_data.get('city', '')
            
            # Business details (from business_details screen)
            business_name = form_data.get('business_name', '')
            specializations = form_data.get('specializations', [])  # Multiple specializations from CheckboxGroup
            experience_years = form_data.get('experience_years', '0-1')
            pricing_per_session = form_data.get('pricing_per_session', 500)
            
            # Availability (from availability screen)
            # Transform weekday availability data into expected format
            available_days, preferred_time_slots, working_hours = self._transform_availability_data(form_data)
            
            # Preferences (from preferences screen)
            subscription_plan = form_data.get('subscription_plan', 'free')
            
            # Business setup (from business_setup screen)
            services_offered = form_data.get('services_offered', [])  # CheckboxGroup
            
            # Pricing (from pricing_smart screen)
            pricing_flexibility = form_data.get('pricing_flexibility', [])  # CheckboxGroup
            
            # Terms (from terms_agreement screen)
            notification_preferences = form_data.get('notification_preferences', [])  # CheckboxGroup
            marketing_consent = form_data.get('marketing_consent', False)  # OptIn
            terms_accepted = form_data.get('terms_accepted', False)  # OptIn
            additional_notes = form_data.get('additional_notes', '')  # TextArea
            
            # Use the actual first_name and surname from flow
            # first_name and surname are already extracted above
            last_name = surname  # Flow uses 'surname' field
            
            # Ensure pricing is numeric
            try:
                pricing = float(pricing_per_session) if pricing_per_session else 500.0
            except (ValueError, TypeError):
                pricing = 500.0
            
            # Convert experience years to numeric for compatibility
            experience_numeric = 0
            if experience_years:
                if experience_years == '0-1':
                    experience_numeric = 1
                elif experience_years == '2-3':
                    experience_numeric = 2
                elif experience_years == '4-5':
                    experience_numeric = 4
                elif experience_years == '6-10':
                    experience_numeric = 7
                elif experience_years == '10+':
                    experience_numeric = 10
            
            # Handle specializations - convert from IDs to readable text if needed
            final_specialization = self._process_specializations('', specializations)
            
            # Process services offered - convert from IDs to readable text
            processed_services = self._process_services_offered(services_offered)
            
            # Process pricing flexibility - convert from IDs to readable text
            processed_pricing_flexibility = self._process_pricing_flexibility(pricing_flexibility)
            
            # Create trainer data structure compatible with existing registration system
            trainer_data = {
                'name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'email': email.lower() if email else '',
                'city': city,
                'location': city,  # For backward compatibility
                'business_name': business_name,
                'specialization': final_specialization,
                'experience': experience_numeric,  # Numeric for existing system
                'years_experience': experience_numeric,  # For backward compatibility
                'experience_years': experience_years,  # Original for new fields
                'pricing': pricing,  # For existing system
                'pricing_per_session': pricing,  # For new fields
                'available_days': available_days,
                'preferred_time_slots': preferred_time_slots,
                'working_hours': working_hours,  # JSONB structure with detailed availability
                'services_offered': processed_services,
                'pricing_flexibility': processed_pricing_flexibility,
                'subscription_plan': subscription_plan,
                'notification_preferences': notification_preferences,
                'marketing_consent': bool(marketing_consent),
                'terms_accepted': bool(terms_accepted),
                'additional_notes': additional_notes,
                'phone': phone_number,
                'whatsapp': phone_number,
                'registration_method': 'whatsapp_flow',
                'onboarding_method': 'flow'
            }
            
            log_info(f"Mapped trainer data for {full_name}: specialization={final_specialization}, pricing={pricing}")
            
            return trainer_data
            
        except Exception as e:
            log_error(f"Error extracting trainer data from flow response: {str(e)}")
            return {}