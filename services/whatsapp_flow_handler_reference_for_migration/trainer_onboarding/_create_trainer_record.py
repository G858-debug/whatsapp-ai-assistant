    def _create_trainer_record(self, trainer_data: Dict, flow_token: str) -> Optional[str]:
        """Create trainer record in database"""
        try:
            # Prepare data for database
            db_data = {
                'name': trainer_data['name'],
                'whatsapp': trainer_data['phone'],
                'email': trainer_data['email'],
                'city': trainer_data['city'],
                'specialization': trainer_data['specialization'],
                'experience_years': trainer_data['experience_years'],
                'pricing_per_session': trainer_data['pricing_per_session'],
                'available_days': json.dumps(trainer_data['available_days']),
                'preferred_time_slots': trainer_data['preferred_time_slots'],
                'subscription_plan': trainer_data['subscription_plan'],
                'notification_preferences': json.dumps(trainer_data['notification_preferences']),
                'terms_accepted': trainer_data['terms_accepted'],
                'marketing_consent': trainer_data['marketing_consent'],
                'status': 'pending_approval',
                'flow_token': flow_token,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Insert into database
            result = self.supabase.table('trainers').insert(db_data).execute()
            
            if result.data:
                trainer_id = result.data[0]['id']
                log_info(f"Created trainer record: {trainer_id}")
                return trainer_id
            else:
                log_error("Failed to create trainer record")
                return None
                
        except Exception as e:
            log_error(f"Error creating trainer record: {str(e)}")
            return None