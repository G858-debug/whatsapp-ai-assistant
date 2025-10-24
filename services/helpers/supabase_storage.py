"""
Supabase Storage Helper
Handles file uploads to Supabase Storage for CSV exports
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta
import os
from utils.logger import log_info, log_error


class SupabaseStorageHelper:
    """Helper for uploading files to Supabase Storage"""
    
    def __init__(self, supabase_client, bucket_name: str = 'csv-exports'):
        self.db = supabase_client
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists and is public"""
        try:
            # Try to get bucket
            buckets = self.db.storage.list_buckets()
            bucket_exists = any(b['name'] == self.bucket_name for b in buckets)
            
            if not bucket_exists:
                # Create public bucket
                self.db.storage.create_bucket(
                    self.bucket_name,
                    options={'public': True}
                )
                log_info(f"Created public bucket: {self.bucket_name}")
            else:
                log_info(f"Bucket already exists: {self.bucket_name}")
                
        except Exception as e:
            log_error(f"Error ensuring bucket exists: {str(e)}")
            # Bucket might already exist, continue anyway
    
    def upload_csv(self, filepath: str, filename: str) -> Optional[str]:
        """
        Upload CSV file to Supabase Storage and return public URL
        
        Args:
            filepath: Local path to CSV file
            filename: Desired filename in storage
            
        Returns:
            Public URL of uploaded file, or None if failed
        """
        try:
            # Read file content
            with open(filepath, 'rb') as f:
                file_content = f.read()
            
            # Upload to Supabase Storage
            storage_path = f"{filename}"
            
            # Upload file
            self.db.storage.from_(self.bucket_name).upload(
                storage_path,
                file_content,
                file_options={
                    'content-type': 'text/csv',
                    'cache-control': '3600',
                    'upsert': 'true'  # Overwrite if exists
                }
            )
            
            # Get public URL
            public_url = self.db.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            log_info(f"File uploaded successfully: {storage_path}")
            log_info(f"Public URL: {public_url}")
            
            return public_url
            
        except Exception as e:
            log_error(f"Error uploading file to Supabase Storage: {str(e)}")
            return None
    
    def delete_file(self, filename: str) -> bool:
        """Delete file from Supabase Storage"""
        try:
            self.db.storage.from_(self.bucket_name).remove([filename])
            log_info(f"File deleted: {filename}")
            return True
        except Exception as e:
            log_error(f"Error deleting file: {str(e)}")
            return False
    
    def cleanup_old_files(self, days_old: int = 7) -> int:
        """
        Delete files older than specified days
        
        Args:
            days_old: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        try:
            # List all files in bucket
            files = self.db.storage.from_(self.bucket_name).list()
            
            deleted_count = 0
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            for file in files:
                # Check file age
                created_at = datetime.fromisoformat(file['created_at'].replace('Z', '+00:00'))
                
                if created_at < cutoff_date:
                    if self.delete_file(file['name']):
                        deleted_count += 1
            
            log_info(f"Cleaned up {deleted_count} old files")
            return deleted_count
            
        except Exception as e:
            log_error(f"Error cleaning up old files: {str(e)}")
            return 0
