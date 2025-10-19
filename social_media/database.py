"""Social Media Database Service - Handles all social media related database operations"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
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
    
    # ============================================
    # PERFORMANCE TRACKING METHODS
    # ============================================
    
    def save_content_performance(self, performance_data: Dict) -> str:
        """Save content performance data
        
        Args:
            performance_data: Dictionary containing performance information
                - hook_type: str - Type of content hook used
                - opening_line: str - The opening line of the content
                - engagement_rate: float - Engagement rate percentage
                - share_count: int - Number of shares
                - virality_score: float - Virality score
                - best_performing_hour: int - Best hour for posting (0-23)
                - audience_sentiment: str - Sentiment analysis result
                - post_id: str (optional) - Associated post ID
                - trainer_id: str - ID of the trainer
        
        Returns:
            str: Performance record UUID if successful, empty string if failed
        """
        try:
            # Generate UUID for the performance record
            performance_id = str(uuid.uuid4())
            
            # Prepare data for insertion
            db_data = {
                'id': performance_id,
                'hook_type': performance_data.get('hook_type', ''),
                'opening_line': performance_data.get('opening_line', ''),
                'engagement_rate': performance_data.get('engagement_rate', 0.0),
                'share_count': performance_data.get('share_count', 0),
                'virality_score': performance_data.get('virality_score', 0.0),
                'best_performing_hour': performance_data.get('best_performing_hour'),
                'audience_sentiment': performance_data.get('audience_sentiment'),
                'post_id': performance_data.get('post_id'),
                'trainer_id': performance_data.get('trainer_id'),
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Insert into database
            result = self.db.table('content_performance').insert(db_data).execute()
            
            if result.data:
                log_info(f"Content performance saved successfully with ID: {performance_id}")
                return performance_id
            else:
                log_error("Failed to save content performance - no data returned")
                return ""
                
        except Exception as e:
            log_error(f"Error saving content performance: {str(e)}")
            return ""
    
    def create_ab_test(self, test_data: Dict) -> str:
        """Create a new A/B test
        
        Args:
            test_data: Dictionary containing test information
                - variant_a_id: str - ID of variant A post
                - variant_b_id: str - ID of variant B post
                - metric_tested: str - Metric being tested
                - test_duration_hours: int - Duration of test in hours
                - trainer_id: str - ID of the trainer
        
        Returns:
            str: Test UUID if successful, empty string if failed
        """
        try:
            # Generate UUID for the test
            test_id = str(uuid.uuid4())
            
            # Prepare data for insertion
            db_data = {
                'id': test_id,
                'variant_a_id': test_data.get('variant_a_id'),
                'variant_b_id': test_data.get('variant_b_id'),
                'metric_tested': test_data.get('metric_tested'),
                'test_duration_hours': test_data.get('test_duration_hours'),
                'status': 'running',
                'trainer_id': test_data.get('trainer_id'),
                'started_at': datetime.now(self.sa_tz).isoformat(),
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Insert into database
            result = self.db.table('ab_tests').insert(db_data).execute()
            
            if result.data:
                log_info(f"A/B test created successfully with ID: {test_id}")
                return test_id
            else:
                log_error("Failed to create A/B test - no data returned")
                return ""
                
        except Exception as e:
            log_error(f"Error creating A/B test: {str(e)}")
            return ""
    
    def complete_ab_test(self, test_id: str, winner_id: str, performance_difference: float) -> bool:
        """Complete an A/B test with results
        
        Args:
            test_id: UUID of the test
            winner_id: UUID of the winning variant
            performance_difference: Performance difference percentage
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            update_data = {
                'winner_id': winner_id,
                'performance_difference': performance_difference,
                'status': 'completed',
                'ended_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.db.table('ab_tests').update(update_data).eq(
                'id', test_id
            ).execute()
            
            if result.data:
                log_info(f"A/B test {test_id} completed with winner {winner_id}")
                return True
            else:
                log_error(f"Failed to complete A/B test {test_id}")
                return False
                
        except Exception as e:
            log_error(f"Error completing A/B test: {str(e)}")
            return False
    
    def save_trending_topic(self, topic_data: Dict) -> str:
        """Save a trending topic
        
        Args:
            topic_data: Dictionary containing topic information
                - topic: str - The trending topic
                - relevance_score: float - Relevance score (0-100)
                - expiry_time: str - ISO datetime when topic expires
                - trainer_id: str - ID of the trainer
        
        Returns:
            str: Topic UUID if successful, empty string if failed
        """
        try:
            # Generate UUID for the topic
            topic_id = str(uuid.uuid4())
            
            # Prepare data for insertion
            db_data = {
                'id': topic_id,
                'topic': topic_data.get('topic', ''),
                'relevance_score': topic_data.get('relevance_score', 0.0),
                'expiry_time': topic_data.get('expiry_time'),
                'trainer_id': topic_data.get('trainer_id'),
                'discovered_at': datetime.now(self.sa_tz).isoformat(),
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'updated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            # Insert into database
            result = self.db.table('trending_topics').insert(db_data).execute()
            
            if result.data:
                log_info(f"Trending topic saved successfully with ID: {topic_id}")
                return topic_id
            else:
                log_error("Failed to save trending topic - no data returned")
                return ""
                
        except Exception as e:
            log_error(f"Error saving trending topic: {str(e)}")
            return ""
    
    def save_hashtag_performance(self, hashtag_data: Dict) -> str:
        """Save or update hashtag performance data
        
        Args:
            hashtag_data: Dictionary containing hashtag information
                - hashtag: str - The hashtag
                - avg_reach: int - Average reach
                - avg_engagement: float - Average engagement rate
                - performance_trend: str - Performance trend
                - trainer_id: str - ID of the trainer
        
        Returns:
            str: Hashtag performance UUID if successful, empty string if failed
        """
        try:
            # Check if hashtag performance already exists
            existing = self.db.table('hashtag_performance').select('id').eq(
                'hashtag', hashtag_data.get('hashtag')
            ).eq('trainer_id', hashtag_data.get('trainer_id')).execute()
            
            if existing.data:
                # Update existing record
                update_data = {
                    'avg_reach': hashtag_data.get('avg_reach', 0),
                    'avg_engagement': hashtag_data.get('avg_engagement', 0.0),
                    'last_used': datetime.now(self.sa_tz).isoformat(),
                    'performance_trend': hashtag_data.get('performance_trend', 'stable'),
                    'usage_count': hashtag_data.get('usage_count', 0),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }
                
                result = self.db.table('hashtag_performance').update(update_data).eq(
                    'hashtag', hashtag_data.get('hashtag')
                ).eq('trainer_id', hashtag_data.get('trainer_id')).execute()
                
                if result.data:
                    log_info(f"Updated hashtag performance for {hashtag_data.get('hashtag')}")
                    return existing.data[0]['id']
                else:
                    log_error(f"Failed to update hashtag performance for {hashtag_data.get('hashtag')}")
                    return ""
            else:
                # Create new record
                hashtag_id = str(uuid.uuid4())
                
                db_data = {
                    'id': hashtag_id,
                    'hashtag': hashtag_data.get('hashtag', ''),
                    'avg_reach': hashtag_data.get('avg_reach', 0),
                    'avg_engagement': hashtag_data.get('avg_engagement', 0.0),
                    'last_used': datetime.now(self.sa_tz).isoformat(),
                    'performance_trend': hashtag_data.get('performance_trend', 'stable'),
                    'usage_count': hashtag_data.get('usage_count', 0),
                    'trainer_id': hashtag_data.get('trainer_id'),
                    'created_at': datetime.now(self.sa_tz).isoformat(),
                    'updated_at': datetime.now(self.sa_tz).isoformat()
                }
                
                result = self.db.table('hashtag_performance').insert(db_data).execute()
                
                if result.data:
                    log_info(f"Hashtag performance saved successfully with ID: {hashtag_id}")
                    return hashtag_id
                else:
                    log_error("Failed to save hashtag performance - no data returned")
                    return ""
                
        except Exception as e:
            log_error(f"Error saving hashtag performance: {str(e)}")
            return ""
    
    # ============================================
    # ANALYTICS AND RETRIEVAL METHODS
    # ============================================
    
    def get_top_performing_hooks(self, trainer_id: str, limit: int = 10) -> List[Dict]:
        """Get top performing content hooks by engagement rate
        
        Args:
            trainer_id: UUID of the trainer
            limit: Maximum number of results to return
        
        Returns:
            List[Dict]: List of top performing hooks
        """
        try:
            result = self.db.table('content_performance').select(
                'hook_type', 'opening_line', 'engagement_rate', 'virality_score', 'share_count'
            ).eq('trainer_id', trainer_id).order(
                'engagement_rate', desc=True
            ).limit(limit).execute()
            
            if result.data:
                log_info(f"Retrieved {len(result.data)} top performing hooks for trainer {trainer_id}")
                return result.data
            else:
                log_info(f"No performance data found for trainer {trainer_id}")
                return []
                
        except Exception as e:
            log_error(f"Error getting top performing hooks: {str(e)}")
            return []
    
    def get_best_posting_times(self, trainer_id: str) -> Dict:
        """Get best posting times by day of week
        
        Args:
            trainer_id: UUID of the trainer
        
        Returns:
            Dict: Best posting times organized by day of week
        """
        try:
            # Get performance data for the trainer
            result = self.db.table('content_performance').select(
                'best_performing_hour', 'engagement_rate'
            ).eq('trainer_id', trainer_id).not_.is_('best_performing_hour', 'null').execute()
            
            if not result.data:
                log_info(f"No posting time data found for trainer {trainer_id}")
                return {}
            
            # Group by hour and calculate average engagement
            hour_performance = {}
            for record in result.data:
                hour = record['best_performing_hour']
                engagement = record['engagement_rate']
                
                if hour not in hour_performance:
                    hour_performance[hour] = {'total_engagement': 0, 'count': 0}
                
                hour_performance[hour]['total_engagement'] += engagement
                hour_performance[hour]['count'] += 1
            
            # Calculate averages and find best times
            best_times = {}
            for hour, data in hour_performance.items():
                avg_engagement = data['total_engagement'] / data['count']
                best_times[hour] = {
                    'avg_engagement': round(avg_engagement, 2),
                    'sample_count': data['count']
                }
            
            # Sort by engagement rate
            sorted_times = dict(sorted(best_times.items(), key=lambda x: x[1]['avg_engagement'], reverse=True))
            
            log_info(f"Retrieved best posting times for trainer {trainer_id}")
            return sorted_times
                
        except Exception as e:
            log_error(f"Error getting best posting times: {str(e)}")
            return {}
    
    def get_winning_content_patterns(self, trainer_id: str, limit: int = 5) -> List[Dict]:
        """Get winning content patterns from A/B tests
        
        Args:
            trainer_id: UUID of the trainer
            limit: Maximum number of results to return
        
        Returns:
            List[Dict]: List of winning content patterns
        """
        try:
            result = self.db.table('ab_tests').select(
                'winner_id', 'metric_tested', 'performance_difference', 'test_duration_hours'
            ).eq('trainer_id', trainer_id).eq('status', 'completed').not_.is_('winner_id', 'null').order(
                'performance_difference', desc=True
            ).limit(limit).execute()
            
            if result.data:
                # Get content details for winning posts
                winning_patterns = []
                for test in result.data:
                    winner_id = test['winner_id']
                    
                    # Get post content
                    post_result = self.db.table('social_posts').select(
                        'content', 'platform', 'created_at'
                    ).eq('id', winner_id).single().execute()
                    
                    if post_result.data:
                        pattern = {
                            'post_id': winner_id,
                            'content': post_result.data['content'],
                            'platform': post_result.data['platform'],
                            'metric_tested': test['metric_tested'],
                            'performance_difference': test['performance_difference'],
                            'test_duration_hours': test['test_duration_hours'],
                            'created_at': post_result.data['created_at']
                        }
                        winning_patterns.append(pattern)
                
                log_info(f"Retrieved {len(winning_patterns)} winning content patterns for trainer {trainer_id}")
                return winning_patterns
            else:
                log_info(f"No winning content patterns found for trainer {trainer_id}")
                return []
                
        except Exception as e:
            log_error(f"Error getting winning content patterns: {str(e)}")
            return []
    
    def get_trending_topics(self, trainer_id: str, limit: int = 10) -> List[Dict]:
        """Get current trending topics for content generation
        
        Args:
            trainer_id: UUID of the trainer
            limit: Maximum number of results to return
        
        Returns:
            List[Dict]: List of trending topics
        """
        try:
            current_time = datetime.now(self.sa_tz).isoformat()
            
            result = self.db.table('trending_topics').select(
                'topic', 'relevance_score', 'content_generated', 'discovered_at', 'expiry_time'
            ).eq('trainer_id', trainer_id).gt(
                'expiry_time', current_time
            ).order('relevance_score', desc=True).limit(limit).execute()
            
            if result.data:
                log_info(f"Retrieved {len(result.data)} trending topics for trainer {trainer_id}")
                return result.data
            else:
                log_info(f"No trending topics found for trainer {trainer_id}")
                return []
                
        except Exception as e:
            log_error(f"Error getting trending topics: {str(e)}")
            return []
    
    def get_hashtag_performance_summary(self, trainer_id: str, limit: int = 20) -> List[Dict]:
        """Get hashtag performance summary
        
        Args:
            trainer_id: UUID of the trainer
            limit: Maximum number of results to return
        
        Returns:
            List[Dict]: List of hashtag performance data
        """
        try:
            result = self.db.table('hashtag_performance').select(
                'hashtag', 'avg_reach', 'avg_engagement', 'performance_trend', 
                'usage_count', 'last_used'
            ).eq('trainer_id', trainer_id).order(
                'avg_engagement', desc=True
            ).limit(limit).execute()
            
            if result.data:
                log_info(f"Retrieved {len(result.data)} hashtag performance records for trainer {trainer_id}")
                return result.data
            else:
                log_info(f"No hashtag performance data found for trainer {trainer_id}")
                return []
                
        except Exception as e:
            log_error(f"Error getting hashtag performance summary: {str(e)}")
            return []
    
    def get_performance_analytics(self, trainer_id: str, days: int = 30) -> Dict:
        """Get comprehensive performance analytics
        
        Args:
            trainer_id: UUID of the trainer
            days: Number of days to analyze
        
        Returns:
            Dict: Comprehensive analytics data
        """
        try:
            # Calculate date range
            end_date = datetime.now(self.sa_tz)
            start_date = end_date - timedelta(days=days)
            
            # Get content performance data
            performance_result = self.db.table('content_performance').select(
                'engagement_rate', 'virality_score', 'share_count', 'best_performing_hour'
            ).eq('trainer_id', trainer_id).gte(
                'created_at', start_date.isoformat()
            ).execute()
            
            # Get A/B test results
            ab_test_result = self.db.table('ab_tests').select(
                'status', 'performance_difference'
            ).eq('trainer_id', trainer_id).gte(
                'created_at', start_date.isoformat()
            ).execute()
            
            # Calculate analytics
            analytics = {
                'period_days': days,
                'total_performance_records': len(performance_result.data) if performance_result.data else 0,
                'total_ab_tests': len(ab_test_result.data) if ab_test_result.data else 0,
                'avg_engagement_rate': 0.0,
                'avg_virality_score': 0.0,
                'total_shares': 0,
                'best_hours': {},
                'completed_tests': 0,
                'avg_performance_difference': 0.0
            }
            
            if performance_result.data:
                engagement_rates = [r['engagement_rate'] for r in performance_result.data if r['engagement_rate']]
                virality_scores = [r['virality_score'] for r in performance_result.data if r['virality_score']]
                shares = [r['share_count'] for r in performance_result.data if r['share_count']]
                
                analytics['avg_engagement_rate'] = round(sum(engagement_rates) / len(engagement_rates), 2) if engagement_rates else 0.0
                analytics['avg_virality_score'] = round(sum(virality_scores) / len(virality_scores), 2) if virality_scores else 0.0
                analytics['total_shares'] = sum(shares) if shares else 0
                
                # Analyze best performing hours
                hours = [r['best_performing_hour'] for r in performance_result.data if r['best_performing_hour'] is not None]
                if hours:
                    hour_counts = {}
                    for hour in hours:
                        hour_counts[hour] = hour_counts.get(hour, 0) + 1
                    analytics['best_hours'] = dict(sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:5])
            
            if ab_test_result.data:
                completed_tests = [t for t in ab_test_result.data if t['status'] == 'completed']
                analytics['completed_tests'] = len(completed_tests)
                
                if completed_tests:
                    differences = [t['performance_difference'] for t in completed_tests if t['performance_difference']]
                    analytics['avg_performance_difference'] = round(sum(differences) / len(differences), 2) if differences else 0.0
            
            log_info(f"Generated performance analytics for trainer {trainer_id} over {days} days")
            return analytics
                
        except Exception as e:
            log_error(f"Error getting performance analytics: {str(e)}")
            return {}