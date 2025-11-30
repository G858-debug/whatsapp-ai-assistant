    def _extract_client_data_from_flow_response(self, flow_response: Dict, trainer_phone: str) -> Optional[Dict]:
        """Extract client data from flow response"""
        try:
            # Log what we receive for debugging
            log_info(f"Extracting client data from response: {json.dumps(flow_response, indent=2)}")

            # The data comes directly in flow_response, not nested
            response_data = flow_response

            # Extract basic client information - these fields should be at the top level
            client_name = response_data.get('client_name', '').strip()
            client_phone = response_data.get('client_phone', '').strip()
            client_email = response_data.get('client_email', '').strip()

            if not client_name or not client_phone:
                log_error(f"Missing required client data: name={client_name}, phone={client_phone}")
                log_error(f"Available keys in response_data: {list(response_data.keys())}")
                return None

            # Extract fitness-related fields
            fitness_goals = response_data.get('fitness_goals', [])
            if isinstance(fitness_goals, str):
                fitness_goals = [goal.strip() for goal in fitness_goals.split(',')]

            experience_level = response_data.get('experience_level', 'beginner')

            # IMPORTANT: sessions_per_week should be a small number (1-7), not a price
            sessions_per_week = response_data.get('sessions_per_week', '2')
            # Validate it's reasonable (if it's > 20, it's probably a data error)
            try:
                sessions_int = int(sessions_per_week)
                if sessions_int > 20:
                    log_warning(f"Sessions per week seems incorrect: {sessions_per_week}, defaulting to 2")
                    sessions_per_week = '2'
            except (ValueError, TypeError):
                sessions_per_week = '2'

            preferred_times = response_data.get('preferred_times', [])
            if isinstance(preferred_times, str):
                preferred_times = [time.strip() for time in preferred_times.split(',')]

            # Extract health information
            health_conditions = response_data.get('health_conditions', '').strip()
            medications = response_data.get('medications', '').strip()
            additional_notes = response_data.get('additional_notes', '').strip()

            # Extract pricing information
            pricing_choice = response_data.get('pricing_choice', 'use_default')
            custom_price_amount = response_data.get('custom_price_amount', '').strip()

            # Calculate final price
            final_price = None
            if pricing_choice == 'custom_price' and custom_price_amount:
                try:
                    final_price = float(custom_price_amount)
                    log_info(f"Using custom price: R{final_price}")
                except (ValueError, TypeError):
                    log_warning(f"Invalid custom price: {custom_price_amount}")

            # Handle package deal (boolean from OptIn component)
            has_package_deal = response_data.get('has_package_deal', False)
            if isinstance(has_package_deal, str):
                has_package_deal = has_package_deal.lower() in ('true', 'yes', '1')
            else:
                has_package_deal = bool(has_package_deal)

            # Build the extracted data - using keys expected by calling code
            extracted_data = {
                'name': client_name,
                'phone': client_phone,
                'email': client_email if client_email else None,
                'fitness_goals': fitness_goals,
                'experience_level': experience_level,
                'sessions_per_week': sessions_per_week,
                'preferred_times': preferred_times,
                'health_conditions': health_conditions if health_conditions else None,
                'medications': medications if medications else None,
                'additional_notes': additional_notes if additional_notes else None,
                'pricing_choice': pricing_choice,
                'custom_price': final_price,
                'calculated_price': final_price,  # Same as custom_price for compatibility
                'has_package_deal': has_package_deal,
                'package_deal_details': None,  # Not included in new flow format
                'invitation_method': 'type_details'  # FIXED: Use allowed database value
            }

            log_info(f"Successfully extracted client data: {client_name} ({client_phone})")
            return extracted_data

        except Exception as e:
            log_error(f"Error extracting client data: {str(e)}")
            log_error(f"Flow response keys: {list(flow_response.keys())}")
            return None