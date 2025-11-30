    def _process_pricing_flexibility(self, pricing_options: list) -> list:
        """Convert pricing flexibility IDs to readable text"""
        try:
            # Mapping from actual flow IDs (from pricing_smart screen)
            pricing_mapping = {
                'package_discounts': 'Package Discounts',
                'student_discounts': 'Student Discounts',
                'group_rates': 'Group Session Rates'
            }
            
            if not pricing_options or not isinstance(pricing_options, list):
                return []
            
            processed = []
            for option in pricing_options:
                if option in pricing_mapping:
                    processed.append(pricing_mapping[option])
                else:
                    processed.append(option)  # Use as-is if not in mapping
            
            return processed
            
        except Exception as e:
            log_error(f"Error processing pricing flexibility: {str(e)}")
            return pricing_options or []