    def _create_trainer_record_direct(self, trainer_data: Dict, flow_token: str) -> Optional[str]:
        """Create trainer record directly in database (fallback method)"""
        try:
            from datetime import datetime
            
            # Prepare data for database
            db_data = {
                'name': trainer_data.get('name', ''),
                'first_name': trainer_data.get('first_name', ''),
                'last_name': trainer_data.get('last_name', ''),
                'whatsapp': trainer_data.get('phone', ''),
                'email': trainer_data.get('email', ''),
                'city': trainer_data.get('city', ''),
                'specialization': trainer_data.get('specialization', ''),
                'years_experience': trainer_data.get('experience', 0),
                'pricing_per_session': trainer_data.get('pricing', 500),
                'status': 'active',
                'registration_method': 'whatsapp_flow',
                'flow_token': flow_token,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Add optional fields if available
            if trainer_data.get('available_days'):
                db_data['available_days'] = json.dumps(trainer_data['available_days'])
            if trainer_data.get('preferred_time_slots'):
                db_data['preferred_time_slots'] = trainer_data['preferred_time_slots']
            if trainer_data.get('subscription_plan'):
                db_data['subscription_plan'] = trainer_data['subscription_plan']
            if trainer_data.get('notification_preferences'):
                db_data['notification_preferences'] = json.dumps(trainer_data['notification_preferences'])
            
            # Insert into database
            result = self.supabase.table('trainers').insert(db_data).execute()
            
            if result.data:
                trainer_id = result.data[0]['id']
                log_info(f"Created trainer record directly: {trainer_id}")
                
                # Send confirmation message
                confirmation_message = self._create_confirmation_message(trainer_data)
                self.whatsapp_service.send_message(trainer_data['phone'], confirmation_message)
                
                return trainer_id
            else:
                log_error("Failed to create trainer record - no data returned")
                return None
                
        except Exception as e:
            log_error(f"Error creating trainer record directly: {str(e)}")
            return None