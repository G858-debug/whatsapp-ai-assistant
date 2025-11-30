    def _transform_availability_data(self, form_data: Dict) -> tuple:
        """
        Transform weekday availability data from flow format to expected format.

        Flow sends: monday_preset, monday_hours, tuesday_preset, tuesday_hours, etc.
        Expected: available_days (list), preferred_time_slots (string), and working_hours (dict)

        Returns:
            tuple: (available_days: list, preferred_time_slots: str, working_hours: dict)
        """
        try:
            weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

            # Preset to time slot mapping
            preset_mapping = {
                'full_day': {'start': '00:00', 'end': '24:00'},
                'business': {'start': '08:00', 'end': '17:00'},
                'morning': {'start': '05:00', 'end': '12:00'},
                'evening': {'start': '17:00', 'end': '21:00'}
            }

            # Day abbreviations for short summary
            day_abbrev = {
                'monday': 'M',
                'tuesday': 'T',
                'wednesday': 'W',
                'thursday': 'Th',
                'friday': 'F',
                'saturday': 'Sa',
                'sunday': 'Su'
            }

            available_days = []
            short_slots = []
            working_hours = {}

            for day in weekdays:
                preset_key = f'{day}_preset'
                hours_key = f'{day}_hours'

                preset = form_data.get(preset_key, 'not_available')
                hours = form_data.get(hours_key, [])

                # Handle not available case
                if preset == 'not_available':
                    working_hours[day] = {'available': False}
                    continue

                # Add day to available days (capitalize first letter for consistency)
                available_days.append(day.capitalize())

                # Build working_hours entry for this day
                if preset == 'custom' and hours:
                    # Custom hours - use the array of hour slots
                    if isinstance(hours, list) and len(hours) > 0:
                        try:
                            # Get first hour's start and last hour's end
                            first_hour = hours[0].split('-')[0]
                            last_hour = hours[-1].split('-')[1]

                            # Create working_hours entry with slots
                            working_hours[day] = {
                                'start': f'{first_hour}:00',
                                'end': f'{last_hour}:00',
                                'available': True,
                                'slots': hours  # Keep the original slots array
                            }

                            # Create short summary
                            short_slots.append(f'{day_abbrev[day]}:{first_hour}-{last_hour}')
                        except (IndexError, AttributeError) as e:
                            log_warning(f"Error parsing custom hours for {day}: {str(e)}")
                            working_hours[day] = {'available': True}
                            short_slots.append(f'{day_abbrev[day]}:Custom')
                    else:
                        working_hours[day] = {'available': True}
                        short_slots.append(f'{day_abbrev[day]}:Custom')

                elif preset in preset_mapping:
                    # Use preset mapping
                    times = preset_mapping[preset]
                    working_hours[day] = {
                        'start': times['start'],
                        'end': times['end'],
                        'available': True
                    }

                    # Create short summary
                    if preset == 'full_day':
                        short_slots.append(f'{day_abbrev[day]}:Full')
                    else:
                        # Extract just the hours without :00
                        start_hour = times['start'].split(':')[0]
                        end_hour = times['end'].split(':')[0]
                        short_slots.append(f'{day_abbrev[day]}:{start_hour}-{end_hour}')
                else:
                    # Fallback for unknown presets
                    working_hours[day] = {'available': True}
                    short_slots.append(f'{day_abbrev[day]}:Avail')

            # Create short summary (under 50 chars)
            preferred_time_slots = ','.join(short_slots) if short_slots else 'Flexible'

            log_info(f"Transformed availability: days={available_days}, slots={preferred_time_slots}")
            log_info(f"Working hours: {json.dumps(working_hours)}")

            return available_days, preferred_time_slots, working_hours

        except Exception as e:
            log_error(f"Error transforming availability data: {str(e)}")
            # Return defaults on error
            return [], 'Flexible', {}