"""
Social Media Scheduler - Orchestrates the entire social media automation system

This module provides the main scheduler class that coordinates content generation,
posting, and analytics collection for Refiloe's social media automation system.
It integrates with Flask and works seamlessly on Railway with single dyno deployment.

Author: Refiloe AI Assistant
Created: 2024
"""

import os
import yaml
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from utils.logger import log_info, log_error, log_warning
from .database import SocialMediaDatabase
from .content_generator import ContentGenerator
from .image_generator import ImageGenerator
from .facebook_poster import FacebookPoster


class SocialMediaScheduler:
    """
    Main scheduler class for social media automation system.
    
    This class orchestrates the entire social media automation workflow:
    - Daily content generation (6:00 AM SAST)
    - Frequent content posting (every 30 minutes)
    - Daily analytics collection (11:00 PM SAST)
    
    Designed to work with Flask and Railway single dyno deployment.
    """
    
    def __init__(self, app, supabase_client):
        """
        Initialize scheduler with all components.
        
        Args:
            app: Flask app instance
            supabase_client: Supabase client for database operations
        """
        try:
            self.app = app
            self.supabase_client = supabase_client
            self.sa_tz = pytz.timezone('Africa/Johannesburg')
            
            # Load configuration
            self.config = self._load_config()
            
            # Initialize components
            self.db = SocialMediaDatabase(supabase_client)
            self.content_generator = ContentGenerator(
                'social_media/config.yaml', 
                supabase_client
            )
            self.image_generator = ImageGenerator(
                'social_media/config.yaml',
                supabase_client
            )
            
            # Initialize Facebook poster with credentials from environment
            page_access_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
            page_id = os.getenv('FACEBOOK_PAGE_ID')
            
            if not page_access_token or not page_id:
                log_warning("Facebook credentials not found. Social media posting will be disabled.")
                self.facebook_poster = None
            else:
                self.facebook_poster = FacebookPoster(page_access_token, page_id, supabase_client)
            
            # Setup APScheduler
            self.scheduler = self._setup_scheduler()
            
            # Get launch date from config for week calculation
            self.launch_date = self._get_launch_date()
            
            log_info("SocialMediaScheduler initialized successfully")
            
        except Exception as e:
            log_error(f"Failed to initialize SocialMediaScheduler: {str(e)}")
            raise
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            log_info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            log_error(f"Failed to load config: {str(e)}")
            # Return minimal default config
            return {
                'posting_schedule': {
                    'week_1': {'posts_per_day': 3, 'times': ['08:00', '12:00', '20:00']},
                    'week_2_to_4': {'posts_per_day': 2, 'times': ['12:00', '20:00']},
                    'week_5_plus': {'posts_per_day': 1, 'times': ['20:00']}
                },
                'launch_date': '2024-01-01'
            }
    
    def _setup_scheduler(self) -> BackgroundScheduler:
        """Setup APScheduler with proper configuration for Railway."""
        try:
            # Configure job stores and executors
            jobstores = {
                'default': MemoryJobStore()
            }
            
            executors = {
                'default': ThreadPoolExecutor(max_workers=3)
            }
            
            job_defaults = {
                'coalesce': True,  # Combine multiple pending jobs into one
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
            }
            
            # Create scheduler
            scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=self.sa_tz
            )
            
            log_info("APScheduler configured for Railway deployment")
            return scheduler
            
        except Exception as e:
            log_error(f"Failed to setup scheduler: {str(e)}")
            raise
    
    def _get_launch_date(self) -> date:
        """Get launch date from config for week calculation."""
        try:
            launch_str = self.config.get('launch_date', '2024-01-01')
            return datetime.strptime(launch_str, '%Y-%m-%d').date()
        except Exception as e:
            log_warning(f"Invalid launch date in config, using default: {str(e)}")
            return date(2024, 1, 1)
    
    def start(self):
        """
        Start the scheduler and register all jobs.
        
        Jobs:
        1. Generate content (daily at 6:00 AM SAST)
        2. Post content (every 30 minutes)
        3. Collect analytics (daily at 11:00 PM SAST)
        """
        try:
            # Add jobs to scheduler
            self.scheduler.add_job(
                self.job_generate_content,
                CronTrigger(hour=6, minute=0, timezone=self.sa_tz),
                id='generate_content',
                name='Generate Daily Content',
                replace_existing=True
            )
            
            self.scheduler.add_job(
                self.job_post_content,
                IntervalTrigger(minutes=30),
                id='post_content',
                name='Post Scheduled Content',
                replace_existing=True
            )
            
            self.scheduler.add_job(
                self.job_collect_analytics,
                CronTrigger(hour=23, minute=0, timezone=self.sa_tz),
                id='collect_analytics',
                name='Collect Daily Analytics',
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            log_info("Social media scheduler started successfully")
            
            # Check for missed jobs on startup
            self._check_missed_jobs()
            
        except Exception as e:
            log_error(f"Failed to start scheduler: {str(e)}")
            raise
    
    def stop(self):
        """Stop the scheduler gracefully."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                log_info("Social media scheduler stopped")
        except Exception as e:
            log_error(f"Error stopping scheduler: {str(e)}")
    
    def job_generate_content(self):
        """
        DAILY JOB (6:00 AM SAST)
        
        Generate content for the next 7 days:
        1. Calculate current week number
        2. Get posting schedule for this week
        3. Generate content for next 7 days
        4. Generate images for posts
        5. Save everything to database with scheduled times
        """
        try:
            log_info("Starting daily content generation job")
            
            # Calculate current week number
            week_number = self.calculate_week_number()
            log_info(f"Current week number: {week_number}")
            
            # Get posting schedule for this week
            week_schedule = self._get_week_schedule(week_number)
            posts_per_day = week_schedule.get('posts_per_day', 1)
            posting_times = week_schedule.get('times', ['09:00'])
            
            # Calculate total posts needed for next 7 days
            total_posts = posts_per_day * 7
            log_info(f"Generating {total_posts} posts for week {week_number}")
            
            # Generate content batch
            generated_posts = self.content_generator.generate_batch(
                total_posts, 
                week_number
            )
            
            if not generated_posts:
                log_error("No content generated")
                return
            
            # Generate scheduled times
            start_date = date.today() + timedelta(days=1)  # Start from tomorrow
            scheduled_times = self.generate_scheduled_times(
                start_date, 7, week_schedule
            )
            
            # Generate images for posts that need them
            posts_with_images = []
            for i, post in enumerate(generated_posts):
                try:
                    # Check if post needs images
                    if post.get('format') in ['single_image_with_caption', 'carousel_style']:
                        # Generate image for this post
                        image_prompt = self._create_image_prompt(post)
                        image_result = self.image_generator.generate_influencer_image(
                            image_prompt, 
                            self._get_image_style(post)
                        )
                        
                        if image_result and 'error' not in image_result:
                            post['image_data'] = image_result
                            log_info(f"Generated image for post {i+1}")
                        else:
                            log_warning(f"Failed to generate image for post {i+1}")
                    
                    posts_with_images.append(post)
                    
                except Exception as e:
                    log_error(f"Error generating image for post {i+1}: {str(e)}")
                    posts_with_images.append(post)  # Add post without image
            
            # Save posts to database
            saved_post_ids = self.content_generator.save_generated_posts(
                posts_with_images, 
                scheduled_times
            )
            
            log_info(f"Content generation completed: {len(saved_post_ids)} posts saved")
            
        except Exception as e:
            log_error(f"Error in content generation job: {str(e)}")
            self._send_error_notification("Content Generation", str(e))
    
    def job_post_content(self):
        """
        FREQUENT JOB (Every 30 minutes)
        
        Check for posts scheduled to be published now:
        1. Check current time
        2. Get posts scheduled for this time (±15 min window)
        3. Post each to Facebook
        4. Update database with results
        """
        try:
            log_info("Starting content posting job")
            
            if not self.facebook_poster:
                log_warning("Facebook poster not available, skipping posting job")
                return
            
            # Get current time in SA timezone
            now = datetime.now(self.sa_tz)
            
            # Define time window (±15 minutes)
            window_start = now - timedelta(minutes=15)
            window_end = now + timedelta(minutes=15)
            
            # Get posts scheduled for this time window
            scheduled_posts = self._get_posts_in_time_window(window_start, window_end)
            
            if not scheduled_posts:
                log_info("No posts scheduled for current time window")
                return
            
            log_info(f"Found {len(scheduled_posts)} posts to publish")
            
            # Post each scheduled post
            for post in scheduled_posts:
                try:
                    self._publish_post(post)
                except Exception as e:
                    log_error(f"Error publishing post {post.get('id', 'unknown')}: {str(e)}")
                    # Mark post as failed
                    self.db.update_post_status(post['id'], 'failed')
            
        except Exception as e:
            log_error(f"Error in content posting job: {str(e)}")
            self._send_error_notification("Content Posting", str(e))
    
    def job_collect_analytics(self):
        """
        DAILY JOB (11:00 PM SAST)
        
        Collect analytics for published posts:
        1. Get all published posts from last 7 days
        2. Fetch analytics from Facebook
        3. Save to database
        """
        try:
            log_info("Starting analytics collection job")
            
            if not self.facebook_poster:
                log_warning("Facebook poster not available, skipping analytics job")
                return
            
            # Get published posts from last 7 days
            seven_days_ago = datetime.now(self.sa_tz) - timedelta(days=7)
            published_posts = self._get_published_posts_since(seven_days_ago)
            
            if not published_posts:
                log_info("No published posts found for analytics collection")
                return
            
            log_info(f"Collecting analytics for {len(published_posts)} posts")
            
            # Collect analytics for each post
            for post in published_posts:
                try:
                    facebook_post_id = post.get('facebook_post_id')
                    if not facebook_post_id:
                        log_warning(f"Post {post['id']} has no Facebook post ID")
                        continue
                    
                    # Fetch analytics from Facebook
                    analytics = self.facebook_poster.get_post_insights(facebook_post_id)
                    
                    if analytics:
                        # Save analytics to database
                        self.db.save_analytics(post['id'], analytics)
                        log_info(f"Analytics collected for post {post['id']}")
                    else:
                        log_warning(f"No analytics data for post {post['id']}")
                    
                    # Add delay to avoid rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    log_error(f"Error collecting analytics for post {post['id']}: {str(e)}")
            
            log_info("Analytics collection completed")
            
        except Exception as e:
            log_error(f"Error in analytics collection job: {str(e)}")
            self._send_error_notification("Analytics Collection", str(e))
    
    def calculate_week_number(self) -> int:
        """
        Calculate which week we're in based on launch date.
        
        Returns:
            int: Week number (1, 2, 3, etc.)
        """
        try:
            today = date.today()
            days_since_launch = (today - self.launch_date).days
            week_number = (days_since_launch // 7) + 1
            return max(1, week_number)  # Ensure week number is at least 1
        except Exception as e:
            log_error(f"Error calculating week number: {str(e)}")
            return 1
    
    def generate_scheduled_times(self, start_date: date, days: int, week_schedule: Dict) -> List[datetime]:
        """
        Create list of scheduled times for posts.
        
        Args:
            start_date: Starting date for scheduling
            days: Number of days to schedule
            week_schedule: Posting schedule configuration
            
        Returns:
            List[datetime]: List of scheduled datetime objects in SAST timezone
        """
        try:
            posts_per_day = week_schedule.get('posts_per_day', 1)
            posting_times = week_schedule.get('times', ['09:00'])
            
            scheduled_times = []
            
            for day in range(days):
                current_date = start_date + timedelta(days=day)
                
                for post_idx in range(posts_per_day):
                    # Select posting time
                    if post_idx < len(posting_times):
                        time_str = posting_times[post_idx]
                    else:
                        time_str = posting_times[-1]  # Use last available time
                    
                    # Parse time
                    hour, minute = map(int, time_str.split(':'))
                    
                    # Create datetime in SA timezone
                    scheduled_dt = self.sa_tz.localize(
                        datetime.combine(current_date, datetime.min.time().replace(hour=hour, minute=minute))
                    )
                    
                    scheduled_times.append(scheduled_dt)
            
            log_info(f"Generated {len(scheduled_times)} scheduled times")
            return scheduled_times
            
        except Exception as e:
            log_error(f"Error generating scheduled times: {str(e)}")
            return []
    
    def _get_week_schedule(self, week_number: int) -> Dict:
        """Get posting schedule for specific week number."""
        try:
            posting_schedule = self.config.get('posting_schedule', {})
            
            if week_number == 1:
                return posting_schedule.get('week_1', {'posts_per_day': 3, 'times': ['08:00', '12:00', '20:00']})
            elif 2 <= week_number <= 4:
                return posting_schedule.get('week_2_to_4', {'posts_per_day': 2, 'times': ['12:00', '20:00']})
            else:
                return posting_schedule.get('week_5_plus', {'posts_per_day': 1, 'times': ['20:00']})
                
        except Exception as e:
            log_error(f"Error getting week schedule: {str(e)}")
            return {'posts_per_day': 1, 'times': ['09:00']}
    
    def _get_posts_in_time_window(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get posts scheduled within time window."""
        try:
            result = self.supabase_client.table('social_posts').select('*').eq(
                'status', 'scheduled'
            ).gte(
                'scheduled_time', start_time.isoformat()
            ).lte(
                'scheduled_time', end_time.isoformat()
            ).execute()
            
            return result.data or []
            
        except Exception as e:
            log_error(f"Error getting posts in time window: {str(e)}")
            return []
    
    def _get_published_posts_since(self, since_date: datetime) -> List[Dict]:
        """Get published posts since specific date."""
        try:
            result = self.supabase_client.table('social_posts').select('*').eq(
                'status', 'published'
            ).gte(
                'published_time', since_date.isoformat()
            ).execute()
            
            return result.data or []
            
        except Exception as e:
            log_error(f"Error getting published posts: {str(e)}")
            return []
    
    def _publish_post(self, post: Dict):
        """Publish a single post to Facebook."""
        try:
            post_id = post['id']
            content = post.get('content', '')
            
            # Prepare post data
            post_data = {
                'content_text': content
            }
            
            # Add images if available
            if post.get('image_data'):
                # Upload image to Facebook
                image_url = post['image_data'].get('image_url')
                if image_url:
                    facebook_image_id = self.facebook_poster.upload_image(image_url)
                    post_data['image_ids'] = [{'media_fbid': facebook_image_id}]
            
            # Post to Facebook
            result = self.facebook_poster.post_to_page(post_data)
            
            if result['success']:
                # Update post status
                self.db.mark_post_published(post_id, result['post_id'])
                log_info(f"Successfully published post {post_id}")
            else:
                # Mark as failed
                self.db.update_post_status(post_id, 'failed')
                log_error(f"Failed to publish post {post_id}: {result['error']}")
                
        except Exception as e:
            log_error(f"Error publishing post: {str(e)}")
            raise
    
    def _create_image_prompt(self, post: Dict) -> str:
        """Create image prompt based on post content."""
        try:
            theme = post.get('theme', 'general')
            title = post.get('title', '')
            content = post.get('content', '')
            
            # Create context based on theme
            context_map = {
                'admin_hacks': 'showing admin tools and organization',
                'relatable_trainer_life': 'in a gym setting with clients',
                'client_management_tips': 'working with clients professionally',
                'engagement_questions': 'engaging with the community'
            }
            
            context = context_map.get(theme, 'in a professional setting')
            
            return f"{title} - {context}, {content[:100]}..."
            
        except Exception as e:
            log_error(f"Error creating image prompt: {str(e)}")
            return "Professional personal trainer in a motivational setting"
    
    def _get_image_style(self, post: Dict) -> str:
        """Get image style based on post theme."""
        theme = post.get('theme', 'general')
        
        style_map = {
            'admin_hacks': 'professional',
            'relatable_trainer_life': 'casual',
            'client_management_tips': 'professional',
            'engagement_questions': 'social'
        }
        
        return style_map.get(theme, 'professional')
    
    def _check_missed_jobs(self):
        """Check for missed jobs on startup and handle them."""
        try:
            log_info("Checking for missed jobs on startup")
            
            # Check if content generation was missed today
            today = datetime.now(self.sa_tz).date()
            today_posts = self.supabase_client.table('social_posts').select('id').gte(
                'created_at', today.isoformat()
            ).execute()
            
            if not today_posts.data:
                log_warning("No posts found for today, running content generation")
                self.job_generate_content()
            
        except Exception as e:
            log_error(f"Error checking missed jobs: {str(e)}")
    
    def _send_error_notification(self, job_name: str, error_message: str):
        """Send error notification (placeholder for Refiloe notification system)."""
        try:
            # TODO: Integrate with existing Refiloe notification system
            log_error(f"CRITICAL ERROR in {job_name}: {error_message}")
            # This would typically send a notification to administrators
        except Exception as e:
            log_error(f"Failed to send error notification: {str(e)}")
    
    def get_scheduler_status(self) -> Dict:
        """Get current scheduler status and job information."""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            return {
                'running': self.scheduler.running,
                'jobs': jobs,
                'timezone': str(self.sa_tz),
                'launch_date': self.launch_date.isoformat(),
                'current_week': self.calculate_week_number()
            }
            
        except Exception as e:
            log_error(f"Error getting scheduler status: {str(e)}")
            return {'error': str(e)}


# Factory function for easy integration
def create_social_media_scheduler(app, supabase_client):
    """
    Factory function to create and configure social media scheduler.
    
    Args:
        app: Flask app instance
        supabase_client: Supabase client instance
        
    Returns:
        SocialMediaScheduler: Configured scheduler instance
    """
    try:
        scheduler = SocialMediaScheduler(app, supabase_client)
        return scheduler
    except Exception as e:
        log_error(f"Failed to create social media scheduler: {str(e)}")
        return None