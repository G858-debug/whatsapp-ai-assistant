#!/usr/bin/env python3
"""
Social Media System Test Suite

This module tests each component of the social media automation system independently
before deployment. It uses test data and doesn't post to real Facebook.

Usage:
    python social_media/test_system.py

Author: Refiloe AI Assistant
Created: 2024
"""

import os
import sys
import yaml
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import with error handling
try:
    import pytz
    from utils.logger import log_info, log_error, log_warning
    from social_media.database import SocialMediaDatabase
    from social_media.content_generator import ContentGenerator
    from social_media.image_generator import ImageGenerator
    from social_media.facebook_poster import FacebookPoster
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install required dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Test configuration
TEST_CONFIG = {
    'test_mode': True,
    'cleanup_after_test': True,
    'test_trainer_id': 'test_trainer_123',
    'test_post_count': 3,
    'test_image_count': 1
}

class SocialMediaSystemTester:
    """Test suite for social media automation system"""
    
    def __init__(self):
        """Initialize test environment"""
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        self.test_results = []
        self.test_data = {
            'posts': [],
            'images': [],
            'post_ids': []
        }
        
        # Initialize Supabase client for testing
        self.supabase_client = self._init_supabase_client()
        
        # Initialize components
        self.db = None
        self.content_generator = None
        self.image_generator = None
        self.facebook_poster = None
        
        log_info("Social Media System Tester initialized")
    
    def _init_supabase_client(self):
        """Initialize Supabase client for testing"""
        try:
            from supabase import create_client, Client
            
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_ANON_KEY')
            
            if not url or not key:
                log_warning("Supabase credentials not found. Some tests will be skipped.")
                return None
            
            client = create_client(url, key)
            log_info("Supabase client initialized for testing")
            return client
            
        except Exception as e:
            log_error(f"Failed to initialize Supabase client: {str(e)}")
            return None
    
    def run_all_tests(self):
        """Run all test functions and display results"""
        print("\n🧪 Testing Social Media System")
        print("=" * 40)
        
        # Test functions in order
        test_functions = [
            ("Config Loading", self.test_config),
            ("Database Connection", self.test_database),
            ("Content Generation", self.test_content_generation),
            ("Image Generation", self.test_image_generation),
            ("Facebook API Connection", self.test_facebook_api),
            ("Full Workflow", self.test_full_workflow)
        ]
        
        # Run each test
        for test_name, test_func in test_functions:
            print(f"\n🔍 Testing {test_name}...")
            try:
                result = test_func()
                self.test_results.append((test_name, result))
                
                if result['success']:
                    print(f"✅ {test_name} - PASSED")
                    if result.get('details'):
                        print(f"   {result['details']}")
                else:
                    print(f"❌ {test_name} - FAILED")
                    if result.get('error'):
                        print(f"   Error: {result['error']}")
                        
            except Exception as e:
                print(f"❌ {test_name} - ERROR")
                print(f"   Exception: {str(e)}")
                self.test_results.append((test_name, {'success': False, 'error': str(e)}))
        
        # Display summary
        self._display_summary()
        
        # Cleanup test data
        if TEST_CONFIG['cleanup_after_test']:
            self._cleanup_test_data()
    
    def test_config(self) -> Dict:
        """Test config.yaml loads correctly"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            
            if not os.path.exists(config_path):
                return {
                    'success': False,
                    'error': f'Config file not found: {config_path}'
                }
            
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            # Validate required sections
            required_sections = [
                'posting_schedule',
                'content_themes',
                'ai_influencer_settings',
                'image_generation',
                'facebook_settings'
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in config:
                    missing_sections.append(section)
            
            if missing_sections:
                return {
                    'success': False,
                    'error': f'Missing config sections: {missing_sections}'
                }
            
            # Validate AI influencer settings
            ai_settings = config.get('ai_influencer_settings', {})
            if not ai_settings.get('name'):
                return {
                    'success': False,
                    'error': 'AI influencer name not configured'
                }
            
            return {
                'success': True,
                'details': f"Config loaded successfully. AI: {ai_settings.get('name', 'Unknown')}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error loading config: {str(e)}'
            }
    
    def test_database(self) -> Dict:
        """Test database connections and table creation"""
        try:
            if not self.supabase_client:
                return {
                    'success': False,
                    'error': 'Supabase client not available'
                }
            
            # Initialize database service
            self.db = SocialMediaDatabase(self.supabase_client)
            
            # Test basic connection by querying a table
            try:
                # Try to query social_posts table
                result = self.supabase_client.table('social_posts').select('id').limit(1).execute()
                
                return {
                    'success': True,
                    'details': f"Database connection successful. Found {len(result.data) if result.data else 0} existing posts."
                }
                
            except Exception as db_error:
                # If table doesn't exist, that's okay for testing
                if "relation" in str(db_error).lower() and "does not exist" in str(db_error).lower():
                    return {
                        'success': True,
                        'details': "Database connection successful. Tables will be created when needed."
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Database query failed: {str(db_error)}'
                    }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Database connection failed: {str(e)}'
            }
    
    def test_content_generation(self) -> Dict:
        """Generate 3 test posts, verify structure"""
        try:
            if not self.supabase_client:
                return {
                    'success': False,
                    'error': 'Supabase client not available'
                }
            
            # Initialize content generator
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            self.content_generator = ContentGenerator(config_path, self.supabase_client)
            
            # Generate test posts
            test_posts = []
            themes = ['admin_hacks', 'relatable_trainer_life', 'client_management_tips']
            
            for i, theme in enumerate(themes):
                try:
                    post = self.content_generator.generate_single_post(theme, 'single_image_with_caption')
                    
                    if post and post.get('content'):
                        test_posts.append(post)
                        log_info(f"Generated test post {i+1}: {theme}")
                    else:
                        log_warning(f"Failed to generate post for theme: {theme}")
                        
                except Exception as e:
                    log_error(f"Error generating post for {theme}: {str(e)}")
            
            if not test_posts:
                return {
                    'success': False,
                    'error': 'No posts were generated successfully'
                }
            
            # Validate post structure
            required_fields = ['content', 'theme', 'format', 'platform', 'status']
            validation_errors = []
            
            for i, post in enumerate(test_posts):
                for field in required_fields:
                    if field not in post:
                        validation_errors.append(f"Post {i+1} missing field: {field}")
            
            if validation_errors:
                return {
                    'success': False,
                    'error': f'Post validation failed: {validation_errors}'
                }
            
            # Store test posts for cleanup
            self.test_data['posts'] = test_posts
            
            return {
                'success': True,
                'details': f"Generated {len(test_posts)} test posts with valid structure"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Content generation test failed: {str(e)}'
            }
    
    def test_image_generation(self) -> Dict:
        """Generate 1 test image, verify upload to Supabase"""
        try:
            if not self.supabase_client:
                return {
                    'success': False,
                    'error': 'Supabase client not available'
                }
            
            # Check if Replicate API token is available
            replicate_token = os.getenv('REPLICATE_API_TOKEN')
            if not replicate_token:
                return {
                    'success': False,
                    'error': 'REPLICATE_API_TOKEN not found in environment'
                }
            
            # Initialize image generator
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            self.image_generator = ImageGenerator(config_path, self.supabase_client)
            
            # Generate test image
            test_prompt = "Professional personal trainer in a modern gym setting, motivational atmosphere"
            image_result = self.image_generator.generate_influencer_image(test_prompt, "professional")
            
            if 'error' in image_result:
                return {
                    'success': False,
                    'error': f'Image generation failed: {image_result["error"]}'
                }
            
            # Validate image result structure
            required_fields = ['image_url', 'storage_path', 'image_id']
            for field in required_fields:
                if field not in image_result:
                    return {
                        'success': False,
                        'error': f'Image result missing field: {field}'
                    }
            
            # Store test image for cleanup
            self.test_data['images'].append(image_result)
            
            return {
                'success': True,
                'details': f"Generated test image: {image_result.get('image_id', 'unknown')}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Image generation test failed: {str(e)}'
            }
    
    def test_facebook_api(self) -> Dict:
        """Test Facebook API connection (don't post, just verify token)"""
        try:
            # Get Facebook credentials
            page_access_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
            page_id = os.getenv('FACEBOOK_PAGE_ID')
            
            if not page_access_token or not page_id:
                return {
                    'success': False,
                    'error': 'Facebook credentials not found in environment variables'
                }
            
            # Initialize Facebook poster
            self.facebook_poster = FacebookPoster(page_access_token, page_id, self.supabase_client)
            
            # Test credentials by getting page info
            page_info = self.facebook_poster.get_page_info()
            
            if not page_info or not page_info.get('id'):
                return {
                    'success': False,
                    'error': 'Failed to retrieve page information'
                }
            
            return {
                'success': True,
                'details': f"Facebook API connection successful. Page: {page_info.get('name', 'Unknown')}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Facebook API test failed: {str(e)}'
            }
    
    def test_full_workflow(self) -> Dict:
        """Complete test: Generate post, generate image, save to database, mark as published"""
        try:
            if not self.supabase_client:
                return {
                    'success': False,
                    'error': 'Supabase client not available'
                }
            
            # Initialize all components
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            
            if not self.db:
                self.db = SocialMediaDatabase(self.supabase_client)
            
            if not self.content_generator:
                self.content_generator = ContentGenerator(config_path, self.supabase_client)
            
            if not self.image_generator:
                self.image_generator = ImageGenerator(config_path, self.supabase_client)
            
            # Step 1: Generate a test post
            log_info("Step 1: Generating test post...")
            post = self.content_generator.generate_single_post('admin_hacks', 'single_image_with_caption')
            
            if not post or not post.get('content'):
                return {
                    'success': False,
                    'error': 'Failed to generate test post'
                }
            
            # Step 2: Generate image for the post
            log_info("Step 2: Generating test image...")
            image_prompt = f"Admin tips for personal trainers: {post.get('title', '')}"
            image_result = self.image_generator.generate_influencer_image(image_prompt, "professional")
            
            if 'error' in image_result:
                log_warning("Image generation failed, continuing without image")
                post['image_data'] = None
            else:
                post['image_data'] = image_result
            
            # Step 3: Save post to database
            log_info("Step 3: Saving post to database...")
            post['trainer_id'] = TEST_CONFIG['test_trainer_id']
            post['scheduled_time'] = (datetime.now(self.sa_tz) + timedelta(hours=1)).isoformat()
            
            post_id = self.db.save_post(post)
            
            if not post_id:
                return {
                    'success': False,
                    'error': 'Failed to save post to database'
                }
            
            # Store for cleanup
            self.test_data['post_ids'].append(post_id)
            
            # Step 4: Update post status to published (simulate)
            log_info("Step 4: Simulating post publication...")
            success = self.db.update_post_status(post_id, 'published')
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to update post status'
                }
            
            # Step 5: Verify post was saved correctly
            log_info("Step 5: Verifying post in database...")
            saved_posts = self.db.get_trainer_posts(TEST_CONFIG['test_trainer_id'], 'published', 1)
            
            if not saved_posts or saved_posts[0]['id'] != post_id:
                return {
                    'success': False,
                    'error': 'Post not found in database after saving'
                }
            
            return {
                'success': True,
                'details': f"Full workflow completed successfully. Post ID: {post_id}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Full workflow test failed: {str(e)}'
            }
    
    def _display_summary(self):
        """Display test summary"""
        print("\n" + "=" * 40)
        
        passed = sum(1 for _, result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Test Results: {passed}/{total} passed")
        
        if passed == total:
            print("🎉 All tests passed! System is ready for deployment.")
        else:
            print("⚠️  Some tests failed. Please fix issues before deployment.")
            
            # Show failed tests
            failed_tests = [name for name, result in self.test_results if not result['success']]
            if failed_tests:
                print(f"\nFailed tests: {', '.join(failed_tests)}")
        
        print("=" * 40)
    
    def _cleanup_test_data(self):
        """Clean up test data from database"""
        try:
            if not self.supabase_client or not self.test_data['post_ids']:
                return
            
            log_info("Cleaning up test data...")
            
            # Delete test posts
            for post_id in self.test_data['post_ids']:
                try:
                    self.supabase_client.table('social_posts').delete().eq('id', post_id).execute()
                    log_info(f"Deleted test post: {post_id}")
                except Exception as e:
                    log_error(f"Failed to delete test post {post_id}: {str(e)}")
            
            # Delete test images
            for image in self.test_data['images']:
                try:
                    if 'db_image_id' in image:
                        self.supabase_client.table('social_images').delete().eq('id', image['db_image_id']).execute()
                        log_info(f"Deleted test image: {image['db_image_id']}")
                except Exception as e:
                    log_error(f"Failed to delete test image: {str(e)}")
            
            log_info("Test data cleanup completed")
            
        except Exception as e:
            log_error(f"Error during cleanup: {str(e)}")


def main():
    """Main function to run all tests"""
    print("🚀 Starting Social Media System Tests...")
    
    # Check environment variables
    required_env_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'ANTHROPIC_API_KEY',
        'REPLICATE_API_TOKEN'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("Some tests may be skipped or fail.")
        print()
    
    # Run tests
    tester = SocialMediaSystemTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()