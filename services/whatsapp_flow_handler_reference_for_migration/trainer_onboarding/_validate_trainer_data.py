    def _validate_trainer_data(self, trainer_data: Dict) -> Dict:
        """Validate trainer data from flow"""
        errors = []
        
        required_fields = [
            'name', 'email', 'city', 'specialization', 
            'experience_years', 'pricing_per_session',
            'available_days', 'preferred_time_slots',
            'subscription_plan', 'terms_accepted'
        ]
        
        for field in required_fields:
            if not trainer_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate email format
        if trainer_data.get('email') and '@' not in trainer_data['email']:
            errors.append("Invalid email format")
        
        # Validate pricing
        if trainer_data.get('pricing_per_session', 0) < 100:
            errors.append("Pricing must be at least R100")
        
        # Validate terms acceptance
        if not trainer_data.get('terms_accepted'):
            errors.append("Terms and conditions must be accepted")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }