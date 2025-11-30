    def get_flow_status(self, phone_number: str) -> Dict:
        """Get the status of a flow for a phone number"""
        try:
            result = self.supabase.table('flow_tokens').select('*').eq('phone_number', phone_number).eq('flow_type', 'trainer_onboarding').execute()
            
            if result.data:
                flow_token = result.data[0]
                return {
                    'has_active_flow': True,
                    'flow_token': flow_token['flow_token'],
                    'created_at': flow_token['created_at']
                }
            else:
                return {
                    'has_active_flow': False
                }
                
        except Exception as e:
            log_error(f"Error getting flow status: {str(e)}")
            return {
                'has_active_flow': False,
                'error': str(e)
            }