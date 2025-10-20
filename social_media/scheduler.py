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
from .video_generator import VideoGenerator  # New import


class SocialMediaScheduler:
    """
    Main scheduler class for social media automation system.
    
    This class orchestrates the entire social media automation workflow:
    - Daily content generation (6:00 AM SAST)
    - Daily video generation (5:00 AM SAST)
    - Frequent content posting (every 30 minutes)
    - Daily analytics collection (11:00 PM SAST)
    - Weekly compilation videos (Sunday 6:00 PM)
    
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
            
            # Initialize video generator
            self.video_generator = VideoGenerator(
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
            
            # Video content mix configuration
            self.video_content_mix = {
                'quick_tips': 3,
                'trainer_stories': 2, 
                'educational_reels': 2,
                'long_form': 1
            }
            
            log_info("SocialMediaScheduler initialized successfully with video support")
            
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
                    'week_1': {'posts_per_day': 6, 'times': ['05:30', '08:00', '12:00', '15:00', '18:00', '21:00']},
                    'week_2_to_4': {'posts_per_day': 5, 'times': ['06:00', '09:00', '13:00', '17:00', '20:00']},
                    'week_5_plus': {'posts_per_day': 4, 'times': ['07:00', '12:00', '16:00', '20:00']}
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
                'default': ThreadPoolExecutor(max_workers=5)  # Increased for video processing
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
            
            log_info("APScheduler configured for Railway deployment with video support")
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
        1. Generate videos (daily at 5:00 AM SAST)
        2. Generate content (daily at 6:00 AM SAST)
        3. Post content (every 30 minutes)
        4. Collect analytics (daily at 11:00 PM SAST)
        5. Weekly compilation (Sunday at 6:00 PM SAST)
        6. Check trending topics (every 2 hours)
        7. Analyze performance (every 6 hours)
        8. Check content queue (every hour)
        """
        try:
            # VIDEO GENERATION JOB - Runs first to create videos for the day
            self.scheduler.add_job(
                self.job_generate_daily_videos,
                CronTrigger(hour=5, minute=0, timezone=self.sa_tz),
                id='generate_daily_videos',
                name='Generate Daily Videos',
                replace_existing=True
            )
            
            # Add existing jobs
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
            
            # Add new jobs for enhanced content management
            self.scheduler.add_job(
                self.job_check_trending_topics,
                IntervalTrigger(hours=2),
                id='check_trending_topics',
                name='Check Trending Topics',
                replace_existing=True
            )
            
            self.scheduler.add_job(
                self.job_analyze_performance,
                IntervalTrigger(hours=6),
                id='analyze_performance',
                name='Analyze Content Performance',
                replace_existing=True
            )
            
            # Emergency content check every hour
            self.scheduler.add_job(
                self.job_check_content_queue,
                IntervalTrigger(hours=1),
                id='check_content_queue',
                name='Check Content Queue',
                replace_existing=True
            )
            
            # WEEKLY VIDEO COMPILATION - Sundays at 6PM
            self.scheduler.add_job(
                self.generate_weekly_compilation,
                CronTrigger(day_of_week='sun', hour=18, minute=0, timezone=self.sa_tz),
                id='weekly_video_compilation',
                name='Generate Weekly Video Compilation',
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            log_info("Social media scheduler started successfully with video automation")
            
            # Check for missed jobs on startup
            self._check_missed_jobs()
            
        except Exception as e:
            log_error(f"Failed to start scheduler: {str(e)}")
            raise
    
    def job_generate_daily_videos(self):
        """
        DAILY JOB (5:00 AM SAST)
        
        Generate 5-7 videos per day based on schedule:
        - Mix of quick tips (3), trainer stories (2), educational reels (2)
        - Uses trending audio from Facebook/Instagram
        - Schedules videos at peak engagement times
        """
        try:
            log_info("Starting daily video generation job")
            
            # Calculate current week number
            week_number = self.calculate_week_number()
            
            # Get trending audio for today
            trending_audio = self._get_trending_audio()
            
            # Generate different video types
            videos_generated = []
            
            # Generate quick tip videos (15-30 seconds)
            for i in range(self.video_content_mix['quick_tips']):
                video = self._generate_quick_tip_video(trending_audio)
                if video:
                    videos_generated.append(video)
                    log_info(f"Generated quick tip video {i+1}")
            
            # Generate trainer story videos (30-60 seconds)
            for i in range(self.video_content_mix['trainer_stories']):
                video = self._generate_trainer_story_video(trending_audio)
                if video:
                    videos_generated.append(video)
                    log_info(f"Generated trainer story video {i+1}")
            
            # Generate educational reel videos (60-90 seconds)
            for i in range(self.video_content_mix['educational_reels']):
                video = self._generate_educational_reel(trending_audio)
                if video:
                    videos_generated.append(video)
                    log_info(f"Generated educational reel {i+1}")
            
            # Schedule videos at peak times
            peak_times = self._get_peak_video_times()
            
            for idx, video in enumerate(videos_generated):
                if idx < len(peak_times):
                    scheduled_time = peak_times[idx]
                    self._save_video_post(video, scheduled_time)
                    log_info(f"Scheduled video for {scheduled_time}")
            
            log_info(f"Daily video generation completed: {len(videos_generated)} videos created")
            
            # Track video generation metrics
            self._track_video_generation_metrics(videos_generated)
            
        except Exception as e:
            log_error(f"Error in daily video generation job: {str(e)}")
            self._send_error_notification("Video Generation", str(e))
    
    def generate_reactive_video(self, trending_topic: Dict):
        """
        Generate quick video response for trending topics.
        
        Args:
            trending_topic: Dictionary containing trending topic information
        """
        try:
            log_info(f"Generating reactive video for trending topic: {trending_topic['title']}")
            
            # Create video script based on trending topic
            script = self.video_generator.generate_video_script(
                theme='trending_response',
                duration=30,
                style='quick_response',
                topic_data=trending_topic
            )
            
            if not script:
                log_error("Failed to generate reactive video script")
                return None
            
            # Use AI avatar to create quick response video
            video_result = self.video_generator.generate_ai_video_with_avatars(
                script_text=script['script_text'],
                avatar_style='energetic',
                duration=30
            )
            
            if video_result and 'video_url' in video_result:
                # Schedule for immediate posting (within 2 hours)
                scheduled_time = datetime.now(self.sa_tz) + timedelta(hours=1)
                
                video_post = {
                    'video_url': video_result['video_url'],
                    'thumbnail_url': video_result.get('thumbnail_url'),
                    'video_type': 'reactive_content',
                    'video_duration': 30,
                    'caption': f"🔥 HOT TOPIC: {trending_topic['title']}\n\n{script.get('caption', '')}",
                    'trending_topic_id': trending_topic.get('id'),
                    'is_reactive': True
                }
                
                self._save_video_post(video_post, scheduled_time)
                log_info(f"Reactive video scheduled for {scheduled_time}")
                
                return video_post
            
        except Exception as e:
            log_error(f"Error generating reactive video: {str(e)}")
            return None
    
    def generate_weekly_compilation(self):
        """
        WEEKLY JOB (Sunday 6:00 PM)
        
        Create week's highlights video:
        - Compile best moments, tips, and wins
        - Add countdown timers and transitions
        - Schedule for Monday morning motivation
        """
        try:
            log_info("Starting weekly compilation video generation")
            
            # Get week's best performing content
            best_posts = self._get_weeks_best_posts()
            
            if not best_posts:
                log_warning("No posts found for weekly compilation")
                return
            
            # Create compilation video
            compilation_data = {
                'posts': best_posts,
                'title': f"Week {self.calculate_week_number()} Highlights",
                'duration': 120,  # 2 minutes
                'style': 'motivational_compilation'
            }
            
            video_result = self.video_generator.generate_compilation_video(compilation_data)
            
            if video_result and 'video_url' in video_result:
                # Schedule for Monday morning (6 AM)
                monday_morning = datetime.now(self.sa_tz)
                days_until_monday = (7 - monday_morning.weekday()) % 7
                if days_until_monday == 0:  # If today is Monday
                    days_until_monday = 7  # Schedule for next Monday
                
                scheduled_time = (monday_morning + timedelta(days=days_until_monday)).replace(
                    hour=6, minute=0, second=0, microsecond=0
                )
                
                compilation_post = {
                    'video_url': video_result['video_url'],
                    'thumbnail_url': video_result.get('thumbnail_url'),
                    'video_type': 'weekly_compilation',
                    'video_duration': 120,
                    'caption': f"🎯 WEEK {self.calculate_week_number()} HIGHLIGHTS!\n\n"
                              f"Here's what we learned this week 💪\n\n"
                              f"Which tip will you implement first? Comment below! 👇",
                    'is_compilation': True
                }
                
                self._save_video_post(compilation_post, scheduled_time)
                log_info(f"Weekly compilation scheduled for {scheduled_time}")
                
        except Exception as e:
            log_error(f"Error generating weekly compilation: {str(e)}")
            self._send_error_notification("Weekly Compilation", str(e))
    
    def job_generate_content(self):
        """
        DAILY JOB (6:00 AM SAST)
        
        Generate content for the next 7 days with video prioritization:
        - 60% of all content should be video
        - Generate text versions alongside videos
        - A/B testing with different hooks
        """
        try:
            log_info("Starting daily content generation job with video priority")
            
            # Calculate current week number
            week_number = self.calculate_week_number()
            log_info(f"Current week number: {week_number}")
            
            # Get posting schedule for this week
            week_schedule = self._get_week_schedule(week_number)
            posts_per_day = week_schedule.get('posts_per_day', 1)
            posting_times = week_schedule.get('times', ['09:00'])
            
            # Calculate content distribution (60% video, 40% static)
            base_posts = posts_per_day * 7
            video_posts_needed = int(base_posts * 0.6)
            static_posts_needed = base_posts - video_posts_needed
            
            # Generate 2x for A/B testing + 20% reserve
            total_posts = int(static_posts_needed * 2.2)
            
            log_info(f"Generating {total_posts} static posts and leveraging {video_posts_needed} videos")
            
            # Generate static content batch with different hook types
            generated_posts = self.content_generator.generate_batch(
                total_posts, 
                week_number,
                hook_variations=True
            )
            
            # For each video already generated, create a text-only version
            videos_in_queue = self._get_todays_scheduled_videos()
            
            for video in videos_in_queue[:video_posts_needed]:
                # Generate text version of video content
                text_version = self._create_text_version_of_video(video)
                if text_version:
                    generated_posts.append(text_version)
            
            if not generated_posts:
                log_error("No content generated")
                return
            
            # Process posts as before (A/B testing, variants, reserve)
            self._process_and_schedule_posts(generated_posts, week_schedule)
            
            log_info("Content generation with video prioritization completed")
            
        except Exception as e:
            log_error(f"Error in content generation job: {str(e)}")
            self._send_error_notification("Content Generation", str(e))
    
    def _generate_quick_tip_video(self, trending_audio: Optional[Dict]) -> Optional[Dict]:
        """Generate a quick tip video (15-30 seconds)."""
        try:
            # Generate script for quick tip
            script = self.video_generator.generate_video_script(
                theme='admin_hacks',
                duration=20,
                style='quick_tip'
            )
            
            if not script:
                return None
            
            # Create screen recording showing the tip
            video_result = self.video_generator.generate_screen_recording_tutorial(
                script=script,
                show_whatsapp=True,
                highlight_actions=True
            )
            
            if video_result and 'video_url' in video_result:
                return {
                    'video_url': video_result['video_url'],
                    'thumbnail_url': video_result.get('thumbnail_url'),
                    'video_type': 'quick_tip',
                    'video_duration': 20,
                    'caption': script.get('caption', ''),
                    'script_id': script.get('id'),
                    'trending_audio_id': trending_audio.get('id') if trending_audio else None
                }
            
            return None
            
        except Exception as e:
            log_error(f"Error generating quick tip video: {str(e)}")
            return None
    
    def _generate_trainer_story_video(self, trending_audio: Optional[Dict]) -> Optional[Dict]:
        """Generate a trainer story video (30-60 seconds)."""
        try:
            # Generate story script
            script = self.video_generator.generate_video_script(
                theme='relatable_trainer_life',
                duration=45,
                style='story'
            )
            
            if not script:
                return None
            
            # Use AI avatar to tell the story
            video_result = self.video_generator.generate_ai_video_with_avatars(
                script_text=script['script_text'],
                avatar_style='casual',
                duration=45
            )
            
            if video_result and 'video_url' in video_result:
                return {
                    'video_url': video_result['video_url'],
                    'thumbnail_url': video_result.get('thumbnail_url'),
                    'video_type': 'trainer_story',
                    'video_duration': 45,
                    'caption': script.get('caption', ''),
                    'script_id': script.get('id'),
                    'trending_audio_id': trending_audio.get('id') if trending_audio else None
                }
            
            return None
            
        except Exception as e:
            log_error(f"Error generating trainer story video: {str(e)}")
            return None
    
    def _generate_educational_reel(self, trending_audio: Optional[Dict]) -> Optional[Dict]:
        """Generate an educational reel (60-90 seconds)."""
        try:
            # Generate educational script
            script = self.video_generator.generate_video_script(
                theme='client_management_tips',
                duration=75,
                style='educational'
            )
            
            if not script:
                return None
            
            # Create animated explainer video
            video_result = self.video_generator.generate_animated_explainer(
                script=script,
                include_data_viz=True,
                style='professional'
            )
            
            if video_result and 'video_url' in video_result:
                return {
                    'video_url': video_result['video_url'],
                    'thumbnail_url': video_result.get('thumbnail_url'),
                    'video_type': 'educational_reel',
                    'video_duration': 75,
                    'caption': script.get('caption', ''),
                    'script_id': script.get('id'),
                    'trending_audio_id': trending_audio.get('id') if trending_audio else None
                }
            
            return None
            
        except Exception as e:
            log_error(f"Error generating educational reel: {str(e)}")
            return None
    
    def _get_trending_audio(self) -> Optional[Dict]:
        """Get trending audio for video content."""
        try:
            # Query trending audio from database
            result = self.supabase_client.table('trending_audio').select('*').eq(
                'platform', 'facebook'
            ).gte(
                'trend_score', 70
            ).order(
                'trend_score', desc=True
            ).limit(1).execute()
            
            if result.data:
                return result.data[0]
            
            return None
            
        except Exception as e:
            log_error(f"Error getting trending audio: {str(e)}")
            return None
    
    def _get_peak_video_times(self) -> List[datetime]:
        """Get peak engagement times for video content."""
        try:
            # Video peak times are slightly different from static content
            video_peak_hours = [6, 8, 12, 15, 18, 20, 21]
            
            today = datetime.now(self.sa_tz).date()
            peak_times = []
            
            for hour in video_peak_hours:
                peak_time = self.sa_tz.localize(
                    datetime.combine(today, datetime.min.time().replace(hour=hour, minute=0))
                )
                
                # Only add future times
                if peak_time > datetime.now(self.sa_tz):
                    peak_times.append(peak_time)
            
            return peak_times
            
        except Exception as e:
            log_error(f"Error getting peak video times: {str(e)}")
            return []
    
    def _save_video_post(self, video_data: Dict, scheduled_time: datetime):
        """Save video post to database."""
        try:
            post_data = {
                'content': video_data.get('caption', ''),
                'video_url': video_data['video_url'],
                'thumbnail_url': video_data.get('thumbnail_url'),
                'video_type': video_data.get('video_type', 'general'),
                'video_duration': video_data.get('video_duration', 30),
                'format': 'video',
                'scheduled_time': scheduled_time.isoformat(),
                'status': 'scheduled',
                'platform': 'facebook',
                'script_id': video_data.get('script_id'),
                'trending_audio_id': video_data.get('trending_audio_id'),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.supabase_client.table('social_posts').insert(post_data).execute()
            
            if result.data:
                log_info(f"Video post saved: {result.data[0]['id']}")
                
                # Add to video generation queue for processing
                self._add_to_video_queue(result.data[0]['id'], video_data)
            else:
                log_error("Failed to save video post")
                
        except Exception as e:
            log_error(f"Error saving video post: {str(e)}")
    
    def _add_to_video_queue(self, post_id: str, video_data: Dict):
        """Add video to generation queue for tracking."""
        try:
            queue_data = {
                'post_id': post_id,
                'task_type': video_data.get('video_type', 'general'),
                'priority': 5,
                'video_duration': video_data.get('video_duration', 30),
                'video_style': video_data.get('style', 'default'),
                'status': 'completed',
                'generated_video_url': video_data['video_url'],
                'generated_thumbnail_url': video_data.get('thumbnail_url'),
                'completed_at': datetime.now(self.sa_tz).isoformat(),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            self.supabase_client.table('video_generation_queue').insert(queue_data).execute()
            
        except Exception as e:
            log_error(f"Error adding to video queue: {str(e)}")
    
    def _track_video_generation_metrics(self, videos: List[Dict]):
        """Track metrics for generated videos."""
        try:
            metrics = {
                'total_videos': len(videos),
                'quick_tips': len([v for v in videos if v.get('video_type') == 'quick_tip']),
                'trainer_stories': len([v for v in videos if v.get('video_type') == 'trainer_story']),
                'educational_reels': len([v for v in videos if v.get('video_type') == 'educational_reel']),
                'generated_at': datetime.now(self.sa_tz).isoformat()
            }
            
            log_info(f"Video generation metrics: {metrics}")
            
        except Exception as e:
            log_error(f"Error tracking video metrics: {str(e)}")
    
    def _get_weeks_best_posts(self) -> List[Dict]:
        """Get the week's best performing posts for compilation."""
        try:
            # Get posts from last 7 days with high engagement
            seven_days_ago = datetime.now(self.sa_tz) - timedelta(days=7)
            
            result = self.supabase_client.table('social_posts').select(
                '*, social_analytics(*)'
            ).eq('status', 'published').gte(
                'published_time', seven_days_ago.isoformat()
            ).order(
                'engagement_rate', desc=True
            ).limit(10).execute()
            
            return result.data or []
            
        except Exception as e:
            log_error(f"Error getting week's best posts: {str(e)}")
            return []
    
    def _get_todays_scheduled_videos(self) -> List[Dict]:
        """Get videos scheduled for today."""
        try:
            today_start = datetime.now(self.sa_tz).replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            result = self.supabase_client.table('social_posts').select('*').eq(
                'format', 'video'
            ).gte(
                'scheduled_time', today_start.isoformat()
            ).lt(
                'scheduled_time', today_end.isoformat()
            ).execute()
            
            return result.data or []
            
        except Exception as e:
            log_error(f"Error getting today's scheduled videos: {str(e)}")
            return []
    
    def _create_text_version_of_video(self, video: Dict) -> Optional[Dict]:
        """Create a text-only version of video content for cross-posting."""
        try:
            return {
                'title': f"[Text Version] {video.get('title', 'Video Content')}",
                'content': video.get('caption', ''),
                'theme': 'video_text_version',
                'format': 'text_only',
                'related_video_id': video.get('id'),
                'is_video_companion': True
            }
        except Exception as e:
            log_error(f"Error creating text version of video: {str(e)}")
            return None
    
    def _process_and_schedule_posts(self, posts: List[Dict], week_schedule: Dict):
        """Process and schedule posts with A/B testing and reserves."""
        try:
            posts_per_day = week_schedule.get('posts_per_day', 1)
            base_posts = posts_per_day * 7
            
            # Split posts into groups
            main_posts = posts[:base_posts]
            variant_posts = posts[base_posts:base_posts * 2] if len(posts) > base_posts else []
            reserve_content = posts[base_posts * 2:] if len(posts) > base_posts * 2 else []
            
            # Mark variant posts
            for post in variant_posts:
                post['is_variant'] = True
                post['variant_type'] = 'ab_test'
            
            # Mark reserve posts
            for post in reserve_content:
                post['is_reserve'] = True
                post['reserve_type'] = 'trending_response'
            
            # Generate scheduled times
            start_date = date.today() + timedelta(days=1)
            scheduled_times = self.generate_scheduled_times(start_date, 7, week_schedule)
            
            # Save all posts
            self.content_generator.save_generated_posts(main_posts, scheduled_times)
            self.content_generator.save_generated_posts(variant_posts, [])
            self.content_generator.save_generated_posts(reserve_content, [])
            
            log_info(f"Processed {len(posts)} posts with scheduling")
            
        except Exception as e:
            log_error(f"Error processing and scheduling posts: {str(e)}")
    
    # ... [Keep all other existing methods from the original file] ...
    
    def stop(self):
        """Stop the scheduler gracefully."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                log_info("Social media scheduler stopped")
        except Exception as e:
            log_error(f"Error stopping scheduler: {str(e)}")

    # [Continue with all remaining methods from the original file...]
    # Including: job_post_content, job_collect_analytics, job_check_trending_topics,
    # job_analyze_performance, job_check_content_queue, and all helper methods
    
    # All existing methods remain unchanged below this point
    # ... [Include all remaining methods from the original file] ...


# Factory function for easy integration
def create_social_media_scheduler(app, supabase_client):
    """
    Factory function to create and configure social media scheduler.
    
    Args:
        app: Flask app instance
        supabase_client: Supabase client instance
        
    Returns:
        SocialMediaScheduler: Configured scheduler instance with video support
    """
    try:
        scheduler = SocialMediaScheduler(app, supabase_client)
        return scheduler
    except Exception as e:
        log_error(f"Failed to create social media scheduler: {str(e)}")
        return None
