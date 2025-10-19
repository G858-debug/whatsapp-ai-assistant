"""Social Media Database Service - Handles all social media related database operations"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import pytz
import uuid
from utils.logger import log_info, log_error


class SocialMediaDatabase:
    """Database service for social media operations"""
    
    def __init__(self, supabase_client):
        """Initialize the social media database service
        
        Args:
            supabase_client: Supabase client instance
        """
        self.db = supabase_client
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
    
    def save_post(self, post_data: Dict) -> str:
        """Save generated post to database
        
        Args:
            post_data: Dictionary containing post information
                - content: str - Post content
                - platform: str - Social media platform
                - scheduled_time: str - ISO datetime string
                - status: str - Post status (draft, scheduled, published)
                - trainer_id: str - ID of the trainer
                - template_id: str (optional) - Content template used
                - metadata: dict (optional) - Additional post metadata
        
        Returns:
            str: Post UUID if successful, empty string if failed
        """
        try:
            # Generate UUID for the post
            post_id = str(uuid.uuid4())
            
            # Prepare data for insertion
            db_data = {
                'id': post_id,
                'content': post_data.get('content', ''),
                'platform': post_data.get('platform', 'facebook'),
                'scheduled_time': post_data.get('scheduled_time'),
                'status': post_data.get('status', 'draft'),
                'trainer_id': post_data.get('trainer_id'),
                'template_id': post_data.get('template_id'),
                'metadata': post_data.get('metadata', {}),
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Insert into database
            result = self.db.table('social_posts').insert(db_data).execute()
            
            if result.data:
                log_info(f"Post saved successfully with ID: {post_id}")
                return post_id
            else:
                log_error("Failed to save post - no data returned")
                return ""
                
        except Exception as e:
            log_error(f"Error saving post: {str(e)}")
            return ""
    
    def get_scheduled_posts(self, date: datetime) -> List[Dict]:
        """Get all posts scheduled for a specific date
        
        Args:
            date: datetime object for the target date
        
        Returns:
            List[Dict]: List of scheduled posts for the date
        """
        try:
            # Convert date to start and end of day in SA timezone
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Convert to SA timezone
            start_sa = self.sa_tz.localize(start_of_day)
            end_sa = self.sa_tz.localize(end_of_day)
            
            # Query scheduled posts for the date
            result = self.db.table('social_posts').select('*').eq(
                'status', 'scheduled'
            ).gte(
                'scheduled_time', start_sa.isoformat()
            ).lte(
                'scheduled_time', end_sa.isoformat()
            ).order('scheduled_time').execute()
            
            if result.data:
                log_info(f"Found {len(result.data)} scheduled posts for {date.date()}")
                return result.data
            else:
                log_info(f"No scheduled posts found for {date.date()}")
                return []
                
        except Exception as e:
            log_error(f"Error getting scheduled posts: {str(e)}")
            return []
    
    def mark_post_published(self, post_id: str, facebook_post_id: str) -> bool:
        """Update post status to published and save Facebook post ID
        
        Args:
            post_id: UUID of the post to update
            facebook_post_id: Facebook's post ID from their API
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare update data
            update_data = {
                'status': 'published',
                'facebook_post_id': facebook_post_id,
                'published_time': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Update the post
            result = self.db.table('social_posts').update(update_data).eq(
                'id', post_id
            ).execute()
            
            if result.data:
                log_info(f"Post {post_id} marked as published with Facebook ID: {facebook_post_id}")
                return True
            else:
                log_error(f"Failed to update post {post_id} - no data returned")
                return False
                
        except Exception as e:
            log_error(f"Error marking post as published: {str(e)}")
            return False
    
    def save_image(self, image_data: Dict) -> str:
        """Save image metadata to database
        
        Args:
            image_data: Dictionary containing image information
                - post_id: str - Associated post ID
                - image_url: str - URL of the uploaded image
                - image_type: str - Type of image (photo, graphic, etc.)
                - file_size: int - Size of the image file in bytes
                - dimensions: dict - Width and height of the image
                - alt_text: str (optional) - Alt text for accessibility
        
        Returns:
            str: Image UUID if successful, empty string if failed
        """
        try:
            # Generate UUID for the image
            image_id = str(uuid.uuid4())
            
            # Prepare data for insertion
            db_data = {
                'id': image_id,
                'post_id': image_data.get('post_id'),
                'image_url': image_data.get('image_url'),
                'image_type': image_data.get('image_type', 'photo'),
                'file_size': image_data.get('file_size', 0),
                'dimensions': image_data.get('dimensions', {}),
                'alt_text': image_data.get('alt_text', ''),
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Insert into database
            result = self.db.table('social_images').insert(db_data).execute()
            
            if result.data:
                log_info(f"Image saved successfully with ID: {image_id}")
                return image_id
            else:
                log_error("Failed to save image - no data returned")
                return ""
                
        except Exception as e:
            log_error(f"Error saving image: {str(e)}")
            return ""
    
    def get_posting_schedule(self, week_number: int) -> Dict:
        """Get posting configuration for specific week
        
        Args:
            week_number: Week number (1-52)
        
        Returns:
            Dict: Posting schedule configuration
                - posts_per_day: int - Number of posts per day
                - posting_times: List[str] - Times to post (HH:MM format)
                - platforms: List[str] - Platforms to post to
        """
        try:
            # Query posting schedule for the week
            result = self.db.table('posting_schedule').select('*').eq(
                'week_number', week_number
            ).eq('is_active', True).execute()
            
            if result.data:
                schedule = result.data[0]
                log_info(f"Retrieved posting schedule for week {week_number}")
                return {
                    'posts_per_day': schedule.get('posts_per_day', 1),
                    'posting_times': schedule.get('posting_times', ['09:00']),
                    'platforms': schedule.get('platforms', ['facebook']),
                    'content_types': schedule.get('content_types', ['motivational']),
                    'week_number': schedule.get('week_number'),
                    'is_active': schedule.get('is_active', True)
                }
            else:
                # Return default schedule if none found
                log_info(f"No posting schedule found for week {week_number}, using defaults")
                return {
                    'posts_per_day': 1,
                    'posting_times': ['09:00'],
                    'platforms': ['facebook'],
                    'content_types': ['motivational'],
                    'week_number': week_number,
                    'is_active': True
                }
                
        except Exception as e:
            log_error(f"Error getting posting schedule: {str(e)}")
            return {
                'posts_per_day': 1,
                'posting_times': ['09:00'],
                'platforms': ['facebook'],
                'content_types': ['motivational'],
                'week_number': week_number,
                'is_active': True
            }
    
    def save_analytics(self, post_id: str, analytics_data: Dict) -> bool:
        """Save or update analytics for a post
        
        Args:
            post_id: UUID of the post
            analytics_data: Dictionary containing analytics information
                - likes: int - Number of likes
                - comments: int - Number of comments
                - shares: int - Number of shares
                - reach: int - Number of people reached
                - impressions: int - Number of impressions
                - clicks: int - Number of clicks
                - engagement_rate: float (optional) - Calculated engagement rate
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Calculate engagement rate if not provided
            likes = analytics_data.get('likes', 0)
            comments = analytics_data.get('comments', 0)
            shares = analytics_data.get('shares', 0)
            reach = analytics_data.get('reach', 0)
            
            # Calculate engagement rate: (likes + comments + shares) / reach * 100
            if reach > 0:
                engagement_rate = ((likes + comments + shares) / reach) * 100
            else:
                engagement_rate = analytics_data.get('engagement_rate', 0.0)
            
            # Prepare data for upsert
            db_data = {
                'post_id': post_id,
                'likes': likes,
                'comments': comments,
                'shares': shares,
                'reach': reach,
                'impressions': analytics_data.get('impressions', 0),
                'clicks': analytics_data.get('clicks', 0),
                'engagement_rate': round(engagement_rate, 2),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Check if analytics already exist for this post
            existing = self.db.table('social_analytics').select('id').eq(
                'post_id', post_id
            ).execute()
            
            if existing.data:
                # Update existing analytics
                result = self.db.table('social_analytics').update(db_data).eq(
                    'post_id', post_id
                ).execute()
                log_info(f"Updated analytics for post {post_id}")
            else:
                # Insert new analytics
                db_data['id'] = str(uuid.uuid4())
                db_data['created_at'] = datetime.now(self.sa_tz).isoformat()
                result = self.db.table('social_analytics').insert(db_data).execute()
                log_info(f"Created new analytics for post {post_id}")
            
            if result.data:
                return True
            else:
                log_error(f"Failed to save analytics for post {post_id}")
                return False
                
        except Exception as e:
            log_error(f"Error saving analytics: {str(e)}")
            return False
    
    def get_content_templates(self, template_type: Optional[str] = None) -> List[Dict]:
        """Get active content templates
        
        Args:
            template_type: Optional filter for template type (motivational, educational, promotional, etc.)
        
        Returns:
            List[Dict]: List of active content templates
        """
        try:
            # Build query
            query = self.db.table('content_templates').select('*').eq('is_active', True)
            
            # Add type filter if specified
            if template_type:
                query = query.eq('template_type', template_type)
            
            # Execute query and order by priority
            result = query.order('priority', desc=False).execute()
            
            if result.data:
                log_info(f"Retrieved {len(result.data)} content templates" + 
                        (f" of type '{template_type}'" if template_type else ""))
                return result.data
            else:
                log_info("No content templates found")
                return []
                
        except Exception as e:
            log_error(f"Error getting content templates: {str(e)}")
            return []
    
    def get_post_analytics(self, post_id: str) -> Optional[Dict]:
        """Get analytics for a specific post
        
        Args:
            post_id: UUID of the post
        
        Returns:
            Optional[Dict]: Analytics data if found, None otherwise
        """
        try:
            result = self.db.table('social_analytics').select('*').eq(
                'post_id', post_id
            ).single().execute()
            
            if result.data:
                log_info(f"Retrieved analytics for post {post_id}")
                return result.data
            else:
                log_info(f"No analytics found for post {post_id}")
                return None
                
        except Exception as e:
            log_error(f"Error getting post analytics: {str(e)}")
            return None
    
    def get_trainer_posts(self, trainer_id: str, status: Optional[str] = None, 
                         limit: int = 50) -> List[Dict]:
        """Get posts for a specific trainer
        
        Args:
            trainer_id: UUID of the trainer
            status: Optional status filter (draft, scheduled, published)
            limit: Maximum number of posts to return
        
        Returns:
            List[Dict]: List of posts for the trainer
        """
        try:
            # Build query
            query = self.db.table('social_posts').select('*').eq('trainer_id', trainer_id)
            
            # Add status filter if specified
            if status:
                query = query.eq('status', status)
            
            # Execute query and order by creation date
            result = query.order('created_at', desc=True).limit(limit).execute()
            
            if result.data:
                log_info(f"Retrieved {len(result.data)} posts for trainer {trainer_id}")
                return result.data
            else:
                log_info(f"No posts found for trainer {trainer_id}")
                return []
                
        except Exception as e:
            log_error(f"Error getting trainer posts: {str(e)}")
            return []
    
    def update_post_status(self, post_id: str, status: str) -> bool:
        """Update the status of a post
        
        Args:
            post_id: UUID of the post
            status: New status (draft, scheduled, published, failed)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('social_posts').update(update_data).eq(
                'id', post_id
            ).execute()
            
            if result.data:
                log_info(f"Updated post {post_id} status to {status}")
                return True
            else:
                log_error(f"Failed to update post {post_id} status")
                return False
                
        except Exception as e:
            log_error(f"Error updating post status: {str(e)}")
            return False