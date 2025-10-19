"""Social Media Content Generator - AI-powered content creation for personal trainers"""
import os
import yaml
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pytz
from anthropic import Anthropic
from utils.logger import log_info, log_error, log_warning
from .database import SocialMediaDatabase


class ContentGenerator:
    """AI-powered content generator for personal trainers using Claude API"""
    
    def __init__(self, config_path: str, supabase_client):
        """Load config and initialize Claude client
        
        Args:
            config_path: Path to config.yaml file
            supabase_client: Supabase client instance for database operations
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.db = SocialMediaDatabase(supabase_client)
        self.sa_tz = pytz.timezone('Africa/Johannesburg')
        
        # Initialize Claude client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        self.claude_client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"  # Using the specified model
        
        log_info("ContentGenerator initialized successfully")
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file
        
        Returns:
            Dict: Configuration dictionary
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            log_info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            log_error(f"Error loading config from {self.config_path}: {str(e)}")
            # Return minimal default config
            return {
                'content_themes': {
                    'admin_hacks': {'percentage': 40, 'examples': []},
                    'relatable_trainer_life': {'percentage': 30, 'examples': []},
                    'client_management_tips': {'percentage': 20, 'examples': []},
                    'engagement_questions': {'percentage': 10, 'examples': []}
                },
                'ai_influencer_settings': {
                    'name': 'Refiloe',
                    'personality_traits': ['Encouraging', 'Friendly'],
                    'speaking_style': {'voice': 'First person', 'tone': 'Conversational'}
                }
            }
    
    def generate_batch(self, num_posts: int, week_number: int, hook_variations: bool = False, emergency_mode: bool = False) -> List[Dict]:
        """Generate multiple posts at once
        
        Args:
            num_posts: Number of posts to generate
            week_number: Week number for scheduling context
            hook_variations: Whether to generate different hook types for A/B testing
            emergency_mode: Whether to generate emergency content quickly
            
        Returns:
            List[Dict]: List of generated posts with metadata
        """
        log_info(f"Starting batch generation of {num_posts} posts for week {week_number}")
        
        try:
            # Get posting schedule for the week
            schedule = self.db.get_posting_schedule(week_number)
            posts_per_day = schedule.get('posts_per_day', 1)
            posting_times = schedule.get('posting_times', ['09:00'])
            
            # Calculate how many days we need to cover
            days_needed = (num_posts + posts_per_day - 1) // posts_per_day
            
            generated_posts = []
            post_count = 0
            
            # Generate posts for each day
            for day in range(days_needed):
                if post_count >= num_posts:
                    break
                
                # Calculate posts for this day
                posts_this_day = min(posts_per_day, num_posts - post_count)
                
                for post_idx in range(posts_this_day):
                    if post_count >= num_posts:
                        break
                    
                    # Select theme based on percentages
                    theme = self._select_theme()
                    
                    # Select format
                    format_type = self._select_format()
                    
                    # Select hook type if variations are enabled
                    hook_type = None
                    if hook_variations:
                        hook_type = self._select_hook_type(post_count)
                    
                    # Generate the post
                    post = self.generate_single_post(theme, format_type, hook_type=hook_type, emergency_mode=emergency_mode)
                    
                    if post:
                        # Add scheduling metadata
                        post['week_number'] = week_number
                        post['day_number'] = day + 1
                        post['post_index'] = post_idx + 1
                        post['scheduled_time'] = self._calculate_scheduled_time(day, post_idx, posting_times)
                        
                        # Add hook type if specified
                        if hook_type:
                            post['hook_type'] = hook_type
                        
                        generated_posts.append(post)
                        post_count += 1
                        
                        # Add delay to avoid rate limiting (shorter for emergency mode)
                        delay = 0.5 if emergency_mode else 1
                        time.sleep(delay)
                    else:
                        log_warning(f"Failed to generate post {post_count + 1}")
            
            log_info(f"Successfully generated {len(generated_posts)} posts")
            return generated_posts
            
        except Exception as e:
            log_error(f"Error in batch generation: {str(e)}")
            return []
    
    def generate_single_post(self, theme: str, format_type: str, hook_type: str = None, emergency_mode: bool = False) -> Dict:
        """Generate one post
        
        Args:
            theme: Content theme from config (admin_hacks, relatable, etc)
            format_type: Post format (single_image, text_only, carousel)
            hook_type: Type of hook to use for the post
            emergency_mode: Whether to generate emergency content quickly
            
        Returns:
            Dict: Structured post data
        """
        log_info(f"Generating single post - Theme: {theme}, Format: {format_type}")
        
        try:
            # Create Claude prompt
            prompt = self.create_claude_prompt(theme, format_type, hook_type, emergency_mode)
            
            # Call Claude API with retry logic
            response = self._call_claude_with_retry(prompt)
            
            if not response:
                log_error("Failed to get response from Claude API")
                return {}
            
            # Parse response into structured format
            post_data = self._parse_claude_response(response, theme, format_type)
            
            if post_data:
                log_info(f"Successfully generated post: {theme} - {format_type}")
                return post_data
            else:
                log_error("Failed to parse Claude response")
                return {}
                
        except Exception as e:
            log_error(f"Error generating single post: {str(e)}")
            return {}
    
    def create_claude_prompt(self, theme: str, format_type: str, hook_type: str = None, emergency_mode: bool = False) -> str:
        """Build prompt for Claude based on theme and format
        
        Args:
            theme: Content theme from config
            format_type: Post format type
            hook_type: Type of hook to use for the post
            emergency_mode: Whether to generate emergency content quickly
            
        Returns:
            str: Formatted prompt for Claude
        """
        # Get theme configuration
        theme_config = self.config.get('content_themes', {}).get(theme, {})
        theme_examples = theme_config.get('examples', [])
        
        # Get AI influencer settings
        ai_settings = self.config.get('ai_influencer_settings', {})
        personality = ai_settings.get('personality_traits', [])
        speaking_style = ai_settings.get('speaking_style', {})
        emoji_guidelines = ai_settings.get('emoji_guidelines', {})
        
        # Build the prompt
        prompt = f"""You are {ai_settings.get('name', 'Refiloe')}, an AI influencer for personal trainers worldwide.

PERSONALITY & VOICE:
- {', '.join(personality)}
- Voice: {speaking_style.get('voice', 'First person')}
- Tone: {speaking_style.get('tone', 'Conversational and supportive')}
- Approach: Like talking to a knowledgeable friend

CONTENT THEME: {theme.replace('_', ' ').title()}
Theme Description: {theme_config.get('description', '')}

POST FORMAT: {format_type.replace('_', ' ').title()}

{f"HOOK TYPE: {hook_type.replace('_', ' ').title()}" if hook_type else ""}
{f"HOOK INSTRUCTIONS: {self._get_hook_instructions(hook_type)}" if hook_type else ""}

CONTENT REQUIREMENTS:
- Target audience: Personal trainers worldwide
- Length: 150-200 words for captions
- Use 1-3 emojis strategically: {emoji_guidelines.get('preferred_emojis', [])}
- End with an engaging question or call-to-action
- Be relatable and understanding of trainer challenges
- Include practical, actionable advice
{f"- EMERGENCY MODE: Generate content quickly with high engagement potential" if emergency_mode else ""}

EMOJI GUIDELINES:
- Max per post: {emoji_guidelines.get('max_per_post', 3)}
- Placement: {emoji_guidelines.get('placement_strategy', [])}
- Preferred emojis: {emoji_guidelines.get('preferred_emojis', [])}

CONTENT EXAMPLES FOR THIS THEME:
{chr(10).join(f"- {example}" for example in theme_examples[:3])}

FORMAT SPECIFIC INSTRUCTIONS:
{self._get_format_instructions(format_type)}

OUTPUT FORMAT:
Please provide your response in the following JSON format:
{{
    "title": "Compelling headline for the post",
    "content": "Full post content with emojis and engagement hook",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "carousel_slides": [list of slide topics if carousel format],
    "engagement_hook": "Question or call-to-action for engagement",
    "tone": "The emotional tone of the post",
    "key_points": [list of main points covered]
}}

Generate engaging, valuable content that personal trainers will love and share!"""

        return prompt
    
    def _select_hook_type(self, post_index: int) -> str:
        """Select hook type for A/B testing
        
        Args:
            post_index: Index of the post in the batch
            
        Returns:
            str: Hook type to use
        """
        hook_types = [
            'question_hook',      # Start with a question
            'statistic_hook',     # Start with a surprising statistic
            'story_hook',         # Start with a personal story
            'tip_hook',           # Start with a practical tip
            'challenge_hook',     # Start with a challenge or problem
            'benefit_hook'        # Start with a benefit or outcome
        ]
        
        # Cycle through hook types for variety
        return hook_types[post_index % len(hook_types)]
    
    def _get_hook_instructions(self, hook_type: str) -> str:
        """Get instructions for specific hook type
        
        Args:
            hook_type: Type of hook to use
            
        Returns:
            str: Hook-specific instructions
        """
        hook_instructions = {
            'question_hook': "Start with an engaging question that makes trainers think about their own experience",
            'statistic_hook': "Start with a surprising or interesting statistic related to personal training",
            'story_hook': "Start with a brief personal story or client experience that's relatable",
            'tip_hook': "Start with a practical, actionable tip that trainers can implement immediately",
            'challenge_hook': "Start by acknowledging a common challenge trainers face",
            'benefit_hook': "Start by highlighting a specific benefit or outcome trainers can achieve"
        }
        
        return hook_instructions.get(hook_type, "Create an engaging opening that hooks the reader")
    
    def _get_format_instructions(self, format_type: str) -> str:
        """Get format-specific instructions
        
        Args:
            format_type: Type of post format
            
        Returns:
            str: Format-specific instructions
        """
        format_instructions = {
            'single_image_with_caption': """
- Create a compelling caption for a single image post
- Focus on one main message or tip
- Make it visually engaging and shareable
- Include a clear call-to-action""",
            
            'carousel_style': """
- Create content for a carousel post (5-7 slides)
- First slide: Title/headline with attention-grabbing hook
- Middle slides: Step-by-step process, tips, or examples
- Last slide: Summary and call-to-action
- Each slide should be self-contained but connected""",
            
            'video_with_caption': """
- Create a caption for a short video (30-90 seconds)
- Describe what the video shows
- Include key takeaways
- Encourage viewers to watch and engage""",
            
            'text_only': """
- Create a text-only post that's highly engaging
- Use formatting (line breaks, emojis) for visual appeal
- Focus on storytelling or sharing insights
- Make it shareable and comment-worthy"""
        }
        
        return format_instructions.get(format_type, "Create engaging content for this format.")
    
    def _call_claude_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Call Claude API with retry logic
        
        Args:
            prompt: Prompt to send to Claude
            max_retries: Maximum number of retry attempts
            
        Returns:
            Optional[str]: Claude's response or None if failed
        """
        for attempt in range(max_retries):
            try:
                response = self.claude_client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=0.7,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                if response.content and len(response.content) > 0:
                    return response.content[0].text
                else:
                    log_warning(f"Empty response from Claude (attempt {attempt + 1})")
                    
            except Exception as e:
                log_error(f"Claude API error (attempt {attempt + 1}): {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    log_info(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    log_error("Max retries reached for Claude API call")
        
        return None
    
    def _parse_claude_response(self, response: str, theme: str, format_type: str) -> Dict:
        """Parse Claude's response into structured post data
        
        Args:
            response: Raw response from Claude
            theme: Content theme
            format_type: Post format
            
        Returns:
            Dict: Structured post data
        """
        try:
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                post_data = json.loads(json_str)
            else:
                # Fallback: create structured data from text response
                post_data = {
                    "title": f"{theme.replace('_', ' ').title()} Post",
                    "content": response,
                    "hashtags": self._generate_hashtags(theme),
                    "engagement_hook": "What's your experience with this?",
                    "tone": "encouraging",
                    "key_points": []
                }
            
            # Add metadata
            post_data.update({
                'theme': theme,
                'format': format_type,
                'platform': 'facebook',
                'status': 'draft',
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'metadata': {
                    'ai_generated': True,
                    'model_used': self.model,
                    'generation_time': datetime.now(self.sa_tz).isoformat()
                }
            })
            
            return post_data
            
        except Exception as e:
            log_error(f"Error parsing Claude response: {str(e)}")
            return {}
    
    def _generate_hashtags(self, theme: str) -> List[str]:
        """Generate relevant hashtags for the theme
        
        Args:
            theme: Content theme
            
        Returns:
            List[str]: List of hashtags
        """
        hashtag_mapping = {
            'admin_hacks': ['#PersonalTrainer', '#TrainerHacks', '#AdminTips', '#FitnessBusiness', '#TrainerTools'],
            'relatable_trainer_life': ['#TrainerLife', '#PersonalTrainer', '#FitnessCoach', '#TrainerStruggles', '#FitnessMotivation'],
            'client_management_tips': ['#ClientManagement', '#PersonalTrainer', '#FitnessCoach', '#TrainerTips', '#FitnessBusiness'],
            'engagement_questions': ['#PersonalTrainer', '#FitnessCommunity', '#TrainerLife', '#FitnessMotivation', '#TrainerSupport']
        }
        
        base_hashtags = hashtag_mapping.get(theme, ['#PersonalTrainer', '#FitnessCoach', '#TrainerTips'])
        
        # Add some random hashtags from the config
        config_hashtags = self.config.get('facebook_settings', {}).get('hashtag_strategy', {})
        primary_hashtags = config_hashtags.get('primary_hashtags', [])
        secondary_hashtags = config_hashtags.get('secondary_hashtags', [])
        
        # Combine and limit to 5-8 hashtags
        all_hashtags = base_hashtags + primary_hashtags + secondary_hashtags
        selected_hashtags = random.sample(all_hashtags, min(8, len(all_hashtags)))
        
        return selected_hashtags[:8]
    
    def _select_theme(self) -> str:
        """Select theme based on configured percentages
        
        Returns:
            str: Selected theme name
        """
        themes = self.config.get('content_themes', {})
        if not themes:
            return 'relatable_trainer_life'
        
        # Create weighted selection
        theme_weights = []
        theme_names = []
        
        for theme, config in themes.items():
            percentage = config.get('percentage', 0)
            if percentage > 0:
                theme_weights.append(percentage)
                theme_names.append(theme)
        
        if not theme_names:
            return 'relatable_trainer_life'
        
        return random.choices(theme_names, weights=theme_weights)[0]
    
    def _select_format(self) -> str:
        """Select post format based on configuration
        
        Returns:
            str: Selected format type
        """
        formats = self.config.get('post_formats', {})
        enabled_formats = []
        
        for format_name, format_config in formats.items():
            if format_config.get('enabled', False):
                enabled_formats.append(format_name)
        
        if not enabled_formats:
            return 'single_image_with_caption'
        
        return random.choice(enabled_formats)
    
    def _calculate_scheduled_time(self, day_offset: int, post_index: int, posting_times: List[str]) -> str:
        """Calculate scheduled time for a post
        
        Args:
            day_offset: Days from today
            post_index: Index of post within the day
            posting_times: List of posting times for the day
            
        Returns:
            str: ISO datetime string for scheduled time
        """
        # Get base date (today + day_offset)
        base_date = datetime.now(self.sa_tz) + timedelta(days=day_offset)
        
        # Select posting time
        if post_index < len(posting_times):
            time_str = posting_times[post_index]
        else:
            time_str = posting_times[-1]  # Use last available time
        
        # Parse time
        hour, minute = map(int, time_str.split(':'))
        
        # Create scheduled datetime
        scheduled_dt = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return scheduled_dt.isoformat()
    
    def save_generated_posts(self, posts: List[Dict], scheduled_times: List[datetime] = None) -> List[str]:
        """Save posts to database with scheduled times
        
        Args:
            posts: List of generated post data
            scheduled_times: Optional list of specific scheduled times
            
        Returns:
            List[str]: List of post UUIDs that were saved
        """
        log_info(f"Saving {len(posts)} generated posts to database")
        
        saved_post_ids = []
        
        for i, post in enumerate(posts):
            try:
                # Use provided scheduled time or the one in post data
                if scheduled_times and i < len(scheduled_times):
                    post['scheduled_time'] = scheduled_times[i].isoformat()
                elif 'scheduled_time' not in post:
                    # Default to 1 hour from now
                    default_time = datetime.now(self.sa_tz) + timedelta(hours=1)
                    post['scheduled_time'] = default_time.isoformat()
                
                # Ensure required fields
                post.setdefault('platform', 'facebook')
                post.setdefault('status', 'draft')
                post.setdefault('trainer_id', 'refiloe_ai')  # Default trainer ID for AI-generated content
                
                # Save to database
                post_id = self.db.save_post(post)
                
                if post_id:
                    saved_post_ids.append(post_id)
                    log_info(f"Saved post {i+1}/{len(posts)} with ID: {post_id}")
                else:
                    log_error(f"Failed to save post {i+1}/{len(posts)}")
                    
            except Exception as e:
                log_error(f"Error saving post {i+1}: {str(e)}")
        
        log_info(f"Successfully saved {len(saved_post_ids)} out of {len(posts)} posts")
        return saved_post_ids
    
    def get_theme_examples(self, theme: str) -> List[str]:
        """Get examples for a specific theme
        
        Args:
            theme: Theme name
            
        Returns:
            List[str]: List of example topics
        """
        themes = self.config.get('content_themes', {})
        return themes.get(theme, {}).get('examples', [])
    
    def get_available_themes(self) -> List[str]:
        """Get list of available content themes
        
        Returns:
            List[str]: List of theme names
        """
        themes = self.config.get('content_themes', {})
        return list(themes.keys())
    
    def get_available_formats(self) -> List[str]:
        """Get list of available post formats
        
        Returns:
            List[str]: List of enabled format names
        """
        formats = self.config.get('post_formats', {})
        enabled_formats = []
        
        for format_name, format_config in formats.items():
            if format_config.get('enabled', False):
                enabled_formats.append(format_name)
        
        return enabled_formats