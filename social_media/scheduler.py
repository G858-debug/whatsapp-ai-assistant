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
        
        Generate content for the next 7 days with A/B testing and reserve content:
        1. Calculate current week number
        2. Get posting schedule for this week
        3. Generate 2x the needed posts for A/B testing
        4. Mark half as variants for testing
        5. Include different hook types for each batch
        6. Generate 20% reserve content for trending topic responses
        7. Generate images for posts
        8. Save everything to database with scheduled times
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
            base_posts = posts_per_day * 7
            # Generate 2x for A/B testing + 20% reserve content
            total_posts = int(base_posts * 2.2)
            reserve_posts = int(base_posts * 0.2)
            ab_test_posts = base_posts * 2
            
            log_info(f"Generating {total_posts} posts for week {week_number} (A/B testing + reserve)")
            
            # Generate content batch with different hook types
            generated_posts = self.content_generator.generate_batch(
                total_posts, 
                week_number,
                hook_variations=True  # Enable different hook types
            )
            
            if not generated_posts:
                log_error("No content generated")
                return
            
            # Split posts into A/B test groups and reserve
            main_posts = generated_posts[:base_posts]
            variant_posts = generated_posts[base_posts:ab_test_posts]
            reserve_content = generated_posts[ab_test_posts:ab_test_posts + reserve_posts]
            
            # Mark variant posts
            for post in variant_posts:
                post['is_variant'] = True
                post['variant_type'] = 'ab_test'
            
            # Mark reserve posts
            for post in reserve_content:
                post['is_reserve'] = True
                post['reserve_type'] = 'trending_response'
            
            # Generate scheduled times for main posts
            start_date = date.today() + timedelta(days=1)  # Start from tomorrow
            scheduled_times = self.generate_scheduled_times(
                start_date, 7, week_schedule
            )
            
            # Process all posts (main, variants, and reserve)
            all_posts = main_posts + variant_posts + reserve_content
            posts_with_images = []
            
            for i, post in enumerate(all_posts):
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
            
            # Save main posts with scheduled times
            main_posts_with_images = posts_with_images[:len(main_posts)]
            saved_main_ids = self.content_generator.save_generated_posts(
                main_posts_with_images, 
                scheduled_times
            )
            
            # Save variant posts (scheduled for later review)
            variant_posts_with_images = posts_with_images[len(main_posts):len(main_posts) + len(variant_posts)]
            saved_variant_ids = self.content_generator.save_generated_posts(
                variant_posts_with_images, 
                []  # No immediate scheduling for variants
            )
            
            # Save reserve posts (no scheduling)
            reserve_posts_with_images = posts_with_images[len(main_posts) + len(variant_posts):]
            saved_reserve_ids = self.content_generator.save_generated_posts(
                reserve_posts_with_images, 
                []  # No immediate scheduling for reserve
            )
            
            log_info(f"Content generation completed:")
            log_info(f"  - Main posts: {len(saved_main_ids)}")
            log_info(f"  - Variant posts: {len(saved_variant_ids)}")
            log_info(f"  - Reserve posts: {len(saved_reserve_ids)}")
            
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
    
    def job_check_trending_topics(self):
        """
        FREQUENT JOB (Every 2 hours)
        
        Check for trending fitness/business topics and generate reactive content:
        1. Search for trending topics in fitness/business
        2. Check if topics are relevant to our content
        3. Generate reactive content for hot topics
        4. Schedule immediate posting for time-sensitive content
        """
        try:
            log_info("Starting trending topics check job")
            
            # Search for trending topics (placeholder - would integrate with real API)
            trending_topics = self._search_trending_topics()
            
            if not trending_topics:
                log_info("No trending topics found")
                return
            
            log_info(f"Found {len(trending_topics)} trending topics")
            
            # Check each topic for relevance and generate content
            for topic in trending_topics:
                try:
                    if self._is_topic_relevant(topic):
                        log_info(f"Generating reactive content for trending topic: {topic['title']}")
                        
                        # Generate reactive content
                        reactive_content = self._generate_reactive_content(topic)
                        
                        if reactive_content:
                            # Schedule for immediate posting (within 2 hours)
                            scheduled_time = datetime.now(self.sa_tz) + timedelta(hours=1)
                            
                            # Save reactive post
                            self._save_reactive_post(reactive_content, scheduled_time, topic)
                            log_info(f"Reactive content scheduled for {scheduled_time}")
                        
                except Exception as e:
                    log_error(f"Error processing trending topic {topic.get('title', 'unknown')}: {str(e)}")
            
            log_info("Trending topics check completed")
            
        except Exception as e:
            log_error(f"Error in trending topics job: {str(e)}")
            self._send_error_notification("Trending Topics Check", str(e))
    
    def job_analyze_performance(self):
        """
        FREQUENT JOB (Every 6 hours)
        
        Analyze content performance and adjust strategy:
        1. Check engagement on recent posts
        2. Identify high-performing content patterns
        3. Adjust upcoming content generation based on what's working
        4. Boost high-performing content
        """
        try:
            log_info("Starting performance analysis job")
            
            # Get recent posts with analytics
            recent_posts = self._get_recent_posts_with_analytics()
            
            if not recent_posts:
                log_info("No recent posts found for analysis")
                return
            
            # Analyze performance patterns
            performance_insights = self._analyze_performance_patterns(recent_posts)
            
            if performance_insights:
                # Update content generation strategy
                self._update_content_strategy(performance_insights)
                
                # Boost high-performing content
                self.boost_high_performers(performance_insights)
                
                log_info("Performance analysis and strategy updates completed")
            else:
                log_info("No significant performance patterns found")
            
        except Exception as e:
            log_error(f"Error in performance analysis job: {str(e)}")
            self._send_error_notification("Performance Analysis", str(e))
    
    def job_check_content_queue(self):
        """
        FREQUENT JOB (Every hour)
        
        Check content queue and generate emergency content if needed:
        1. Check how much content is scheduled
        2. If less than 12 hours of content remaining, generate emergency content
        3. Ensure content pipeline stays full
        """
        try:
            log_info("Starting content queue check job")
            
            # Check content availability for next 12 hours
            twelve_hours_from_now = datetime.now(self.sa_tz) + timedelta(hours=12)
            
            # Count scheduled posts in next 12 hours
            scheduled_posts = self._get_posts_in_time_window(
                datetime.now(self.sa_tz), 
                twelve_hours_from_now
            )
            
            if len(scheduled_posts) < 3:  # Less than 3 posts in 12 hours
                log_warning("Content queue running low, generating emergency content")
                self._generate_emergency_content()
            else:
                log_info(f"Content queue healthy: {len(scheduled_posts)} posts scheduled")
            
        except Exception as e:
            log_error(f"Error in content queue check job: {str(e)}")
            self._send_error_notification("Content Queue Check", str(e))
    
    def _search_trending_topics(self) -> List[Dict]:
        """Search for trending fitness/business topics (placeholder implementation)."""
        try:
            # This would integrate with real APIs like Google Trends, Twitter API, etc.
            # For now, return mock data
            trending_topics = [
                {
                    'title': 'New Year Fitness Resolutions',
                    'trend_score': 85,
                    'category': 'fitness',
                    'keywords': ['new year', 'fitness', 'resolutions', 'gym'],
                    'relevance_score': 0.9
                },
                {
                    'title': 'Remote Work Wellness',
                    'trend_score': 72,
                    'category': 'business',
                    'keywords': ['remote work', 'wellness', 'productivity', 'health'],
                    'relevance_score': 0.7
                }
            ]
            
            # Filter by relevance score
            relevant_topics = [topic for topic in trending_topics if topic['relevance_score'] > 0.6]
            return relevant_topics
            
        except Exception as e:
            log_error(f"Error searching trending topics: {str(e)}")
            return []
    
    def _is_topic_relevant(self, topic: Dict) -> bool:
        """Check if a trending topic is relevant to our content strategy."""
        try:
            # Check if topic matches our content themes
            fitness_keywords = ['fitness', 'workout', 'gym', 'training', 'health', 'wellness']
            business_keywords = ['business', 'productivity', 'management', 'entrepreneur', 'success']
            
            topic_title = topic.get('title', '').lower()
            topic_keywords = [kw.lower() for kw in topic.get('keywords', [])]
            
            # Check for fitness or business relevance
            fitness_match = any(keyword in topic_title or keyword in topic_keywords for keyword in fitness_keywords)
            business_match = any(keyword in topic_title or keyword in topic_keywords for keyword in business_keywords)
            
            return fitness_match or business_match
            
        except Exception as e:
            log_error(f"Error checking topic relevance: {str(e)}")
            return False
    
    def _generate_reactive_content(self, topic: Dict) -> Optional[Dict]:
        """Generate reactive content based on trending topic."""
        try:
            # Create reactive content based on trending topic
            reactive_content = {
                'title': f"Hot Topic: {topic['title']}",
                'content': f"🔥 {topic['title']} is trending right now! Here's how personal trainers can leverage this trend...",
                'theme': 'trending_topic',
                'format': 'text_only',
                'is_reactive': True,
                'trending_topic_id': topic.get('id'),
                'trend_score': topic.get('trend_score', 0)
            }
            
            return reactive_content
            
        except Exception as e:
            log_error(f"Error generating reactive content: {str(e)}")
            return None
    
    def _save_reactive_post(self, content: Dict, scheduled_time: datetime, topic: Dict):
        """Save reactive post to database."""
        try:
            post_data = {
                'content': content['content'],
                'title': content['title'],
                'theme': content['theme'],
                'format': content['format'],
                'scheduled_time': scheduled_time.isoformat(),
                'status': 'scheduled',
                'is_reactive': True,
                'trending_topic': topic['title'],
                'trend_score': topic.get('trend_score', 0),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.supabase_client.table('social_posts').insert(post_data).execute()
            
            if result.data:
                log_info(f"Reactive post saved: {result.data[0]['id']}")
            else:
                log_error("Failed to save reactive post")
                
        except Exception as e:
            log_error(f"Error saving reactive post: {str(e)}")
    
    def _get_recent_posts_with_analytics(self) -> List[Dict]:
        """Get recent posts with their analytics data."""
        try:
            # Get posts from last 7 days with analytics
            seven_days_ago = datetime.now(self.sa_tz) - timedelta(days=7)
            
            result = self.supabase_client.table('social_posts').select(
                '*, analytics(*)'
            ).eq('status', 'published').gte(
                'published_time', seven_days_ago.isoformat()
            ).execute()
            
            return result.data or []
            
        except Exception as e:
            log_error(f"Error getting recent posts with analytics: {str(e)}")
            return []
    
    def _analyze_performance_patterns(self, posts: List[Dict]) -> Optional[Dict]:
        """Analyze performance patterns from recent posts."""
        try:
            if not posts:
                return None
            
            # Calculate average engagement metrics
            total_likes = sum(post.get('analytics', {}).get('likes', 0) for post in posts)
            total_comments = sum(post.get('analytics', {}).get('comments', 0) for post in posts)
            total_shares = sum(post.get('analytics', {}).get('shares', 0) for post in posts)
            
            avg_likes = total_likes / len(posts) if posts else 0
            avg_comments = total_comments / len(posts) if posts else 0
            avg_shares = total_shares / len(posts) if posts else 0
            
            # Identify high-performing posts (2x average engagement)
            high_performers = []
            for post in posts:
                analytics = post.get('analytics', {})
                engagement = analytics.get('likes', 0) + analytics.get('comments', 0) + analytics.get('shares', 0)
                avg_engagement = avg_likes + avg_comments + avg_shares
                
                if engagement >= avg_engagement * 2:
                    high_performers.append(post)
            
            # Analyze content patterns
            theme_performance = {}
            format_performance = {}
            
            for post in posts:
                theme = post.get('theme', 'unknown')
                format_type = post.get('format', 'unknown')
                analytics = post.get('analytics', {})
                engagement = analytics.get('likes', 0) + analytics.get('comments', 0) + analytics.get('shares', 0)
                
                if theme not in theme_performance:
                    theme_performance[theme] = {'total_engagement': 0, 'count': 0}
                theme_performance[theme]['total_engagement'] += engagement
                theme_performance[theme]['count'] += 1
                
                if format_type not in format_performance:
                    format_performance[format_type] = {'total_engagement': 0, 'count': 0}
                format_performance[format_type]['total_engagement'] += engagement
                format_performance[format_type]['count'] += 1
            
            # Calculate average engagement per theme/format
            for theme in theme_performance:
                theme_performance[theme]['avg_engagement'] = (
                    theme_performance[theme]['total_engagement'] / theme_performance[theme]['count']
                )
            
            for format_type in format_performance:
                format_performance[format_type]['avg_engagement'] = (
                    format_performance[format_type]['total_engagement'] / format_performance[format_type]['count']
                )
            
            insights = {
                'high_performers': high_performers,
                'theme_performance': theme_performance,
                'format_performance': format_performance,
                'avg_engagement': avg_likes + avg_comments + avg_shares,
                'total_posts_analyzed': len(posts)
            }
            
            return insights
            
        except Exception as e:
            log_error(f"Error analyzing performance patterns: {str(e)}")
            return None
    
    def _update_content_strategy(self, insights: Dict):
        """Update content generation strategy based on performance insights."""
        try:
            # Update strategy based on high-performing themes and formats
            best_themes = sorted(
                insights['theme_performance'].items(),
                key=lambda x: x[1]['avg_engagement'],
                reverse=True
            )[:3]
            
            best_formats = sorted(
                insights['format_performance'].items(),
                key=lambda x: x[1]['avg_engagement'],
                reverse=True
            )[:3]
            
            # Save strategy updates to database
            strategy_update = {
                'best_themes': [theme[0] for theme in best_themes],
                'best_formats': [format_type[0] for format_type in best_formats],
                'updated_at': datetime.now(self.sa_tz).isoformat(),
                'avg_engagement': insights['avg_engagement']
            }
            
            # This would update a strategy table in the database
            log_info(f"Content strategy updated: {strategy_update}")
            
        except Exception as e:
            log_error(f"Error updating content strategy: {str(e)}")
    
    def boost_high_performers(self, insights: Dict):
        """Boost high-performing content by creating variations."""
        try:
            high_performers = insights.get('high_performers', [])
            
            if not high_performers:
                log_info("No high-performing posts to boost")
                return
            
            log_info(f"Boosting {len(high_performers)} high-performing posts")
            
            for post in high_performers:
                try:
                    # Create variations of successful posts
                    variations = self._create_post_variations(post)
                    
                    # Schedule variations at peak times
                    for variation in variations:
                        # Schedule for next peak time (evening)
                        peak_time = datetime.now(self.sa_tz).replace(hour=20, minute=0, second=0, microsecond=0)
                        if peak_time <= datetime.now(self.sa_tz):
                            peak_time += timedelta(days=1)
                        
                        self._save_boosted_post(variation, peak_time, post['id'])
                        
                except Exception as e:
                    log_error(f"Error boosting post {post.get('id', 'unknown')}: {str(e)}")
            
            log_info("High performer boosting completed")
            
        except Exception as e:
            log_error(f"Error in boost_high_performers: {str(e)}")
    
    def _create_post_variations(self, original_post: Dict) -> List[Dict]:
        """Create variations of a successful post."""
        try:
            variations = []
            original_content = original_post.get('content', '')
            
            # Create different hook variations
            hook_variations = [
                f"🔥 HOT TIP: {original_content}",
                f"💡 PRO TIP: {original_content}",
                f"⚡ QUICK WIN: {original_content}",
                f"🎯 GAME CHANGER: {original_content}"
            ]
            
            for i, variation_content in enumerate(hook_variations[:2]):  # Limit to 2 variations
                variation = {
                    'title': f"{original_post.get('title', '')} (Variation {i+1})",
                    'content': variation_content,
                    'theme': original_post.get('theme', 'general'),
                    'format': original_post.get('format', 'text_only'),
                    'is_boosted': True,
                    'original_post_id': original_post['id'],
                    'variation_type': f'hook_variation_{i+1}'
                }
                variations.append(variation)
            
            return variations
            
        except Exception as e:
            log_error(f"Error creating post variations: {str(e)}")
            return []
    
    def _save_boosted_post(self, content: Dict, scheduled_time: datetime, original_post_id: str):
        """Save boosted post variation to database."""
        try:
            post_data = {
                'content': content['content'],
                'title': content['title'],
                'theme': content['theme'],
                'format': content['format'],
                'scheduled_time': scheduled_time.isoformat(),
                'status': 'scheduled',
                'is_boosted': True,
                'original_post_id': original_post_id,
                'variation_type': content.get('variation_type'),
                'created_at': datetime.now(self.sa_tz).isoformat()
            }
            
            result = self.supabase_client.table('social_posts').insert(post_data).execute()
            
            if result.data:
                log_info(f"Boosted post saved: {result.data[0]['id']}")
            else:
                log_error("Failed to save boosted post")
                
        except Exception as e:
            log_error(f"Error saving boosted post: {str(e)}")
    
    def _generate_emergency_content(self):
        """Generate emergency content when queue runs low."""
        try:
            log_info("Generating emergency content")
            
            # Generate 5 emergency posts
            emergency_posts = self.content_generator.generate_batch(
                5, 
                self.calculate_week_number(),
                emergency_mode=True
            )
            
            if not emergency_posts:
                log_error("No emergency content generated")
                return
            
            # Schedule emergency posts for next 12 hours
            now = datetime.now(self.sa_tz)
            emergency_times = []
            
            for i in range(len(emergency_posts)):
                # Schedule every 2-3 hours
                scheduled_time = now + timedelta(hours=(i + 1) * 2.5)
                emergency_times.append(scheduled_time)
            
            # Mark as emergency content
            for post in emergency_posts:
                post['is_emergency'] = True
                post['emergency_type'] = 'queue_refill'
            
            # Save emergency posts
            saved_ids = self.content_generator.save_generated_posts(
                emergency_posts, 
                emergency_times
            )
            
            log_info(f"Emergency content generated: {len(saved_ids)} posts")
            
        except Exception as e:
            log_error(f"Error generating emergency content: {str(e)}")

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
    
    def get_content_queue_status(self) -> Dict:
        """Get current content queue status and statistics."""
        try:
            now = datetime.now(self.sa_tz)
            next_24_hours = now + timedelta(hours=24)
            
            # Count scheduled posts in next 24 hours
            scheduled_posts = self._get_posts_in_time_window(now, next_24_hours)
            
            # Count reserve content
            reserve_posts = self.supabase_client.table('social_posts').select('id').eq(
                'is_reserve', True
            ).eq('status', 'scheduled').execute()
            
            # Count variant posts
            variant_posts = self.supabase_client.table('social_posts').select('id').eq(
                'is_variant', True
            ).eq('status', 'scheduled').execute()
            
            return {
                'scheduled_posts_24h': len(scheduled_posts),
                'reserve_content_available': len(reserve_posts.data or []),
                'variant_posts_available': len(variant_posts.data or []),
                'queue_healthy': len(scheduled_posts) >= 3,
                'last_updated': now.isoformat()
            }
            
        except Exception as e:
            log_error(f"Error getting content queue status: {str(e)}")
            return {'error': str(e)}
    
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