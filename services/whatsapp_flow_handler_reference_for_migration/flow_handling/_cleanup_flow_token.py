    def _cleanup_flow_token(self, token: str) -> bool:
        """Clean up used flow token"""
        try:
            result = self.supabase.table('flow_tokens').delete().eq('token', token).execute()
            return bool(result.data)
            
        except Exception as e:
            log_error(f"Error cleaning up flow token: {str(e)}")
            return False  