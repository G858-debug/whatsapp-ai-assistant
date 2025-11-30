    def _get_phone_from_flow_token(self, flow_token: str) -> Optional[str]:
        """Get phone number from flow token"""
        try:
            result = self.supabase.table('flow_tokens').select('phone_number').eq('flow_token', flow_token).execute()
            if result.data:
                return result.data[0]['phone_number']
        except Exception as e:
            log_error(f"Error getting phone from flow token: {str(e)}")
        return None