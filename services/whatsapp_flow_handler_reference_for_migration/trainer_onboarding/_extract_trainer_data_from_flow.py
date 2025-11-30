    def _extract_trainer_data_from_flow(self, action_payload: Dict) -> Dict:
        """Extract trainer data from new flow structure"""
        try:
            # Get phone number from flow token or context
            phone_number = self._get_phone_from_flow_token(action_payload.get('flow_token'))
            
            # Extract data from form responses
            form_data = action_payload.get('data', {})
            
            # Parse name (split first and last name)
            full_name = form_data.get('full_name', '')
            name_parts = full_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Parse pricing (ensure it's numeric)
            pricing_str = form_data.get('pricing_per_session', '500')
            try:
                pricing = float(pricing_str) if pricing_str else 500.0
            except (ValueError, TypeError):
                pricing = 500.0
            
            # Handle available days (could be string or list)
            available_days = form_data.get('available_days', [])
            if isinstance(available_days, str):
                available_days = [available_days]
            
            # Handle notification preferences (could be string or list)
            notification_prefs = form_data.get('notification_preferences', [])
            if isinstance(notification_prefs, str):
                notification_prefs = [notification_prefs]
            
            trainer_data = {
                'phone': phone_number,
                'name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'email': form_data.get('email', ''),
                'city': form_data.get('city', ''),
                'specialization': form_data.get('specialization', ''),
                'experience_years': form_data.get('experience_years', '0-1'),
                'pricing_per_session': pricing,
                'available_days': available_days,
                'preferred_time_slots': form_data.get('preferred_time_slots', ''),
                'subscription_plan': form_data.get('subscription_plan', 'free'),
                'notification_preferences': notification_prefs,
                'terms_accepted': bool(form_data.get('terms_accepted', False)),
                'marketing_consent': bool(form_data.get('marketing_consent', False)),
                'status': 'active',  # Changed from pending_approval to active
                'created_at': datetime.now().isoformat()
            }
            
            log_info(f"Extracted trainer data: {trainer_data['name']} ({trainer_data['email']})")
            return trainer_data
            
        except Exception as e:
            log_error(f"Error extracting trainer data from flow: {str(e)}")
            return {}