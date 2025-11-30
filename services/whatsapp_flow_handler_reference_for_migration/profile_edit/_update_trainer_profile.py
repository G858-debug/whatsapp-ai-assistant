    def _update_trainer_profile(self, phone_number: str, update_data: Dict) -> Dict:
        """Update trainer profile with provided data"""
        try:
            if not update_data:
                return {'success': False, 'error': 'No data to update'}
            
            # Update trainer record
            result = self.supabase.table('trainers').update(update_data).eq('whatsapp', phone_number).execute()
            
            if result.data:
                log_info(f"Updated trainer profile for {phone_number}: {list(update_data.keys())}")
                return {'success': True, 'updated_fields': list(update_data.keys())}
            else:
                return {'success': False, 'error': 'No trainer record found to update'}
                
        except Exception as e:
            log_error(f"Error updating trainer profile: {str(e)}")
            return {'success': False, 'error': str(e)}