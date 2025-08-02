from supabase import create_client, Client
from utils.logger import log_info, log_error

def init_supabase(url: str, key: str) -> Client:
    """Initialize Supabase client"""
    try:
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        
        client = create_client(url, key)
        log_info("Supabase client initialized successfully")
        return client
        
    except Exception as e:
        log_error(f"Failed to initialize Supabase: {str(e)}")
        raise
