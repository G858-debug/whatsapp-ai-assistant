    def _update_client_profile(self, phone_number: str, update_data: Dict) -> Dict:
        """Update client profile with provided data"""
        try:
            if not update_data:
                return {'success': False, 'error': 'No data to update'}
            
            # Update client record
            result = self.supabase.table('clients').update(update_data).eq('whatsapp', phone_number).execute()
            
            if result.data:
                log_info(f"Updated client profile for {phone_number}: {list(update_data.keys())}")
                return {'success': True, 'updated_fields': list(update_data.keys())}
            else:
                return {'success': False, 'error': 'No client record found to update'}
                
        except Exception as e:
            log_error(f"Error updating client profile: {str(e)}")
            return {'success': False, 'error': str(e)}