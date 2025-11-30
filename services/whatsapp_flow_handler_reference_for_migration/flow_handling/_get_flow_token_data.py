    def _get_flow_token_data(self, token: str) -> Optional[Dict]:
        """Retrieve flow token data"""
        try:
            result = self.supabase.table('flow_tokens').select('*').eq(
                'token', token
            ).gte('expires_at', datetime.now().isoformat()).execute()
            
            if result.data:
                return result.data[0]['data']
            return None
            
        except Exception as e:
            log_error(f"Error retrieving flow token data: {str(e)}")
            return None