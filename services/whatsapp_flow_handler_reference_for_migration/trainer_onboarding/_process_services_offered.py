    def _process_services_offered(self, services: list) -> list:
        """Convert service IDs to readable text"""
        try:
            # Mapping from actual flow IDs (from business_setup screen)
            service_mapping = {
                'in_person_training': 'In-Person Training',
                'online_training': 'Online Training',
                'nutrition_planning': 'Nutrition Planning',
                'fitness_assessments': 'Fitness Assessments',
                'group_classes': 'Group Classes'
            }
            
            if not services or not isinstance(services, list):
                return []
            
            processed = []
            for service in services:
                if service in service_mapping:
                    processed.append(service_mapping[service])
                else:
                    processed.append(service)  # Use as-is if not in mapping
            
            return processed
            
        except Exception as e:
            log_error(f"Error processing services offered: {str(e)}")
            return services or []