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
        self.model = "claude-sonnet-4-20250514"  # Using the specified model
        
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
        log_info(f"Generating single post - Theme: {theme}, Format: {format_type}, Hook-based: {hook_type}")
        
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
                # Use standard generation
                # Create Claude prompt
                prompt = self.create_claude_prompt(theme, format_type)
                
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
        
        # Get hook configuration if provided
        hook_config = {}
        hook_template = ""
        if hook_type:
            hook_config = self.config.get('hook_categories', {}).get(hook_type, {})
            hook_template = hook_config.get('template', '')
        
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
{f"HOOK DESCRIPTION: {hook_config.get('description', '')}" if hook_type else ""}

HOOK FORMULA:
{f"Use this specific opening template: {hook_template}" if hook_type and hook_template else "Create a compelling opening that grabs attention immediately"}

SCROLL-STOPPER REQUIREMENT:
- The first 7 words MUST grab attention and make people stop scrolling
- Use power words, numbers, or emotional triggers
- Create curiosity or urgency

SHAREABILITY SCORE REQUIREMENT:
- Include something surprising, valuable, or controversial enough to share
- Add specific numbers, statistics, or results
- Make it relatable to trainer experiences
- Include actionable insights

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

{f"HOOK EXAMPLES FOR {hook_type.upper()}:{chr(10)}{chr(10).join(f'- {example}' for example in hook_config.get('examples', [])[:3])}" if hook_type else ""}

FORMAT SPECIFIC INSTRUCTIONS:
{self._get_format_instructions(format_type)}

CONTENT GENERATION PROCESS:
1. Generate 3 different content variations
2. For each variation, score it on:
   - Emotional impact (1-10): How much does it make trainers feel?
   - Shareability (1-10): How likely are trainers to share this?
   - Actionability (1-10): How clear and useful are the next steps?
3. Select the variation with the highest combined score
4. Ensure the chosen content includes viral elements (numbers, emotions, controversy)

OUTPUT FORMAT:
Please provide your response in the following JSON format:
{{
    "variations": [
        {{
            "content": "First content variation",
            "emotional_impact": 8,
            "shareability": 7,
            "actionability": 9,
            "total_score": 24
        }},
        {{
            "content": "Second content variation", 
            "emotional_impact": 6,
            "shareability": 8,
            "actionability": 7,
            "total_score": 21
        }},
        {{
            "content": "Third content variation",
            "emotional_impact": 9,
            "shareability": 9,
            "actionability": 8,
            "total_score": 26
        }}
    ],
    "selected_variation": {{
        "content": "The best performing content variation",
        "emotional_impact": 9,
        "shareability": 9,
        "actionability": 8,
        "total_score": 26,
        "selection_reason": "Why this variation was chosen"
    }},
    "title": "Compelling headline for the selected post",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "carousel_slides": [list of slide topics if carousel format],
    "engagement_hook": "Question or call-to-action for engagement",
    "tone": "The emotional tone of the post",
    "key_points": [list of main points covered],
    "viral_elements": ["List of viral elements included (numbers, emotions, controversy)"]
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
    
    def _get_hook_templates(self) -> Dict[str, str]:
        """Get hook templates for different hook types
        
        Returns:
            Dict[str, str]: Mapping of hook types to their templates
        """
        return {
            'pain_point': "Every trainer knows the feeling when [specific situation]",
            'success_story': "[Time period] ago, [trainer name] was [struggle]. Today they [achievement]",
            'controversial': "Hot take: [widely accepted practice] is actually [contrarian view]",
            'quick_win': "The [time] [tool/method] that [specific result]"
        }
    
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
                
                # Handle new response format with variations
                if 'selected_variation' in post_data:
                    # Use the selected variation as the main content
                    selected = post_data['selected_variation']
                    post_data['content'] = selected.get('content', post_data.get('content', ''))
                    post_data['emotional_impact'] = selected.get('emotional_impact', 0)
                    post_data['shareability'] = selected.get('shareability', 0)
                    post_data['actionability'] = selected.get('actionability', 0)
                    post_data['total_score'] = selected.get('total_score', 0)
                    post_data['selection_reason'] = selected.get('selection_reason', '')
                    
                    # Keep all variations for analysis
                    post_data['all_variations'] = post_data.get('variations', [])
                    
                    # Remove the selected_variation key to avoid duplication
                    if 'selected_variation' in post_data:
                        del post_data['selected_variation']
                
                # Ensure required fields exist
                if 'content' not in post_data:
                    post_data['content'] = response
                if 'title' not in post_data:
                    post_data['title'] = f"{theme.replace('_', ' ').title()} Post"
                if 'hashtags' not in post_data:
                    post_data['hashtags'] = self._generate_hashtags(theme)
                if 'engagement_hook' not in post_data:
                    post_data['engagement_hook'] = "What's your experience with this?"
                if 'tone' not in post_data:
                    post_data['tone'] = "encouraging"
                if 'key_points' not in post_data:
                    post_data['key_points'] = []
                    
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
    
    def generate_hook_based_post(self, theme: str = None, format_type: str = None) -> Dict:
        """Generate content optimized for a specific hook type with viral elements
        
        Args:
            theme: Optional specific theme, otherwise randomly selected
            format_type: Optional specific format, otherwise randomly selected
            
        Returns:
            Dict: Structured post data optimized for the selected hook
        """
        log_info("Generating hook-based post with viral elements")
        
        try:
            # Select hook type based on configured percentages
            hook_type = self._select_hook_type()
            
            # Select theme and format if not provided
            if not theme:
                theme = self._select_theme()
            if not format_type:
                format_type = self._select_format()
            
            # Create enhanced prompt with hook focus
            prompt = self.create_claude_prompt(theme, format_type, hook_type)
            
            # Add viral elements instruction
            viral_prompt_addition = """

VIRAL ELEMENTS TO INCLUDE:
- Specific numbers and statistics (e.g., "increased by 40%", "saved 2 hours daily")
- Emotional triggers (frustration, excitement, relief, surprise)
- Controversial or contrarian statements
- Personal stories or case studies
- Time-sensitive or urgent language
- Power words (secret, proven, guaranteed, breakthrough, game-changer)
- Questions that create curiosity
- Bold claims backed by results

Make this content impossible to scroll past!"""
            
            full_prompt = prompt + viral_prompt_addition
            
            # Call Claude API with retry logic
            response = self._call_claude_with_retry(full_prompt)
            
            if not response:
                log_error("Failed to get response from Claude API for hook-based post")
                return {}
            
            # Parse response into structured format
            post_data = self._parse_claude_response(response, theme, format_type)
            
            if post_data:
                # Add hook-specific metadata
                post_data['hook_type'] = hook_type
                post_data['optimized_for_virality'] = True
                post_data['generation_method'] = 'hook_based'
                
                log_info(f"Successfully generated hook-based post: {hook_type} - {theme} - {format_type}")
                return post_data
            else:
                log_error("Failed to parse Claude response for hook-based post")
                return {}
                
        except Exception as e:
            log_error(f"Error generating hook-based post: {str(e)}")
            return {}
    
    def _select_hook_type(self) -> str:
        """Select hook type based on configured percentages
        
        Returns:
            str: Selected hook type name
        """
        hook_categories = self.config.get('hook_categories', {})
        if not hook_categories:
            return 'pain_point'
        
        # Create weighted selection
        hook_weights = []
        hook_names = []
        
        for hook_type, config in hook_categories.items():
            percentage = config.get('percentage', 0)
            if percentage > 0:
                hook_weights.append(percentage)
                hook_names.append(hook_type)
        
        if not hook_names:
            return 'pain_point'
        
        return random.choices(hook_names, weights=hook_weights)[0]
    
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
    
    def get_available_hook_types(self) -> List[str]:
        """Get list of available hook types
        
        Returns:
            List[str]: List of hook type names
        """
        hook_categories = self.config.get('hook_categories', {})
        return list(hook_categories.keys())
    
    def get_hook_examples(self, hook_type: str) -> List[str]:
        """Get examples for a specific hook type
        
        Args:
            hook_type: Hook type name
            
        Returns:
            List[str]: List of example hooks
        """
        hook_categories = self.config.get('hook_categories', {})
        return hook_categories.get(hook_type, {}).get('examples', [])
    
    def generate_post_with_hook(self, theme: str, format_type: str, hook_type: str) -> Dict:
        """Generate content with a specific hook type
        
        Args:
            theme: Content theme from config
            format_type: Post format type
            hook_type: Specific hook type to use
            
        Returns:
            Dict: Structured post data optimized for the specified hook
        """
        log_info(f"Generating post with specific hook - Theme: {theme}, Format: {format_type}, Hook: {hook_type}")
        
        try:
            # Create enhanced prompt with specific hook focus
            prompt = self.create_claude_prompt(theme, format_type, hook_type)
            
            # Add viral elements instruction
            viral_prompt_addition = """

VIRAL ELEMENTS TO INCLUDE:
- Specific numbers and statistics (e.g., "increased by 40%", "saved 2 hours daily")
- Emotional triggers (frustration, excitement, relief, surprise)
- Controversial or contrarian statements
- Personal stories or case studies
- Time-sensitive or urgent language
- Power words (secret, proven, guaranteed, breakthrough, game-changer)
- Questions that create curiosity
- Bold claims backed by results

Make this content impossible to scroll past!"""
            
            full_prompt = prompt + viral_prompt_addition
            
            # Call Claude API with retry logic
            response = self._call_claude_with_retry(full_prompt)
            
            if not response:
                log_error("Failed to get response from Claude API for specific hook post")
                return {}
            
            # Parse response into structured format
            post_data = self._parse_claude_response(response, theme, format_type)
            
            if post_data:
                # Add hook-specific metadata
                post_data['hook_type'] = hook_type
                post_data['optimized_for_virality'] = True
                post_data['generation_method'] = 'specific_hook'
                
                log_info(f"Successfully generated post with hook {hook_type}: {theme} - {format_type}")
                return post_data
            else:
                log_error("Failed to parse Claude response for specific hook post")
                return {}
                
        except Exception as e:
            log_error(f"Error generating post with specific hook: {str(e)}")
            return {}
    
    def create_video_script(self, theme: str, duration: int = 60, style: str = "educational") -> Dict:
        """Generate time-coded video scripts with exact wording and visual cues
        
        Args:
            theme: Content theme for the video
            duration: Video duration in seconds (30, 60, 90, 120)
            style: Video style (educational, motivational, behind_scenes, tutorial, story)
            
        Returns:
            Dict: Structured video script with time codes, visual cues, and CTAs
        """
        log_info(f"Creating video script - Theme: {theme}, Duration: {duration}s, Style: {style}")
        
        try:
            # Get video-specific hooks
            video_hooks = self._get_video_hooks()
            selected_hook = random.choice(video_hooks)
            
            # Create video script prompt
            prompt = self._create_video_script_prompt(theme, duration, style, selected_hook)
            
            # Call Claude API
            response = self._call_claude_with_retry(prompt)
            
            if not response:
                log_error("Failed to get response from Claude API for video script")
                return {}
            
            # Parse video script response
            script_data = self._parse_video_script_response(response, theme, duration, style)
            
            if script_data:
                log_info(f"Successfully generated video script: {theme} - {duration}s - {style}")
                return script_data
            else:
                log_error("Failed to parse video script response")
                return {}
                
        except Exception as e:
            log_error(f"Error creating video script: {str(e)}")
            return {}
    
    def generate_video_series(self, topic: str, num_videos: int = 6) -> List[Dict]:
        """Generate a series of connected video scripts that build on each other
        
        Args:
            topic: Main topic for the video series
            num_videos: Number of videos in the series (5-7 recommended)
            
        Returns:
            List[Dict]: List of video scripts with cliffhangers and teasers
        """
        log_info(f"Generating video series - Topic: {topic}, Videos: {num_videos}")
        
        try:
            series_scripts = []
            
            # Create series outline first
            series_outline = self._create_series_outline(topic, num_videos)
            
            for i, video_info in enumerate(series_outline):
                # Generate script for each video
                script = self.create_video_script(
                    theme=video_info['theme'],
                    duration=video_info['duration'],
                    style=video_info['style']
                )
                
                if script:
                    # Add series metadata
                    script['series_info'] = {
                        'series_topic': topic,
                        'video_number': i + 1,
                        'total_videos': num_videos,
                        'is_series': True,
                        'previous_video': series_outline[i-1]['title'] if i > 0 else None,
                        'next_video': series_outline[i+1]['title'] if i < len(series_outline) - 1 else None
                    }
                    
                    # Add cliffhanger for next video (except last)
                    if i < len(series_outline) - 1:
                        script['cliffhanger'] = self._generate_cliffhanger(series_outline[i+1])
                    
                    # Add teaser for previous video (except first)
                    if i > 0:
                        script['teaser'] = self._generate_teaser(series_outline[i-1])
                    
                    series_scripts.append(script)
            
            log_info(f"Successfully generated {len(series_scripts)} video scripts for series: {topic}")
            return series_scripts
            
        except Exception as e:
            log_error(f"Error generating video series: {str(e)}")
            return []
    
    def _get_video_hooks(self) -> List[str]:
        """Get video-specific hooks optimized for social media retention
        
        Returns:
            List[str]: List of video hook templates
        """
        return [
            "Stop scrolling if you're a trainer who...",
            "POV: You just lost another client because...",
            "The #1 mistake trainers make that...",
            "Watch this 30-second hack that...",
            "I wish someone told me this when I started training...",
            "The secret that changed my training business...",
            "Why 90% of trainers fail at this...",
            "This one thing saved me 5 hours per week...",
            "The mistake that cost me $10k last year...",
            "If you're struggling with [problem], this is for you..."
        ]
    
    def _create_video_script_prompt(self, theme: str, duration: int, style: str, hook: str) -> str:
        """Create prompt for video script generation
        
        Args:
            theme: Content theme
            duration: Video duration in seconds
            style: Video style
            hook: Video hook to use
            
        Returns:
            str: Formatted prompt for video script generation
        """
        # Get AI influencer settings
        ai_settings = self.config.get('ai_influencer_settings', {})
        personality = ai_settings.get('personality_traits', [])
        speaking_style = ai_settings.get('speaking_style', {})
        
        # Calculate timing breakdown
        hook_duration = 3  # First 3 seconds for hook
        main_content_duration = duration - hook_duration - 5  # 5 seconds for CTA
        cta_duration = 5
        
        prompt = f"""You are {ai_settings.get('name', 'Refiloe')}, creating a {duration}-second video script for personal trainers.

VIDEO SPECIFICATIONS:
- Duration: {duration} seconds
- Style: {style}
- Theme: {theme}
- Hook: {hook}

PERSONALITY & VOICE:
- {', '.join(personality)}
- Voice: {speaking_style.get('voice', 'First person')}
- Tone: {speaking_style.get('tone', 'Conversational and engaging')}

RETENTION OPTIMIZATION:
- Hook MUST grab attention in first 3 seconds
- Use power words and emotional triggers
- Include specific numbers and statistics
- Create curiosity and urgency
- Make it impossible to scroll past

VIDEO STRUCTURE:
1. Hook (0-3s): {hook}
2. Main Content (3-{duration-5}s): Core message with visual cues
3. CTA ({duration-5}-{duration}s): Strong call-to-action

VISUAL CUES TO INCLUDE:
- Text overlays for key points
- Gestures and expressions
- Props or demonstrations
- Screen recordings if applicable
- Transitions between topics

TRENDING ELEMENTS:
- Use current social media language
- Include relevant hashtags in script
- Reference popular challenges or trends
- Use engaging visual descriptions

CALL-TO-ACTION OPTIONS:
- "Comment 'ADMIN' for the free guide"
- "Share this with a trainer who needs it"
- "Save this for your next client"
- "Which tip will you try first?"
- "Follow for more trainer hacks"

OUTPUT FORMAT:
Please provide your response in the following JSON format:
{{
    "title": "Compelling video title",
    "hook": "The exact opening hook text",
    "script": [
        {{
            "time_start": 0,
            "time_end": 3,
            "text": "Hook text with exact wording",
            "visual_cue": "Visual instruction (e.g., 'Point to camera, serious expression')",
            "tone": "Urgent, attention-grabbing"
        }},
        {{
            "time_start": 3,
            "time_end": {duration-5},
            "text": "Main content with exact wording",
            "visual_cue": "Visual instruction (e.g., 'Show demonstration, text overlay')",
            "tone": "Educational, engaging"
        }},
        {{
            "time_start": {duration-5},
            "time_end": {duration},
            "text": "Call-to-action with exact wording",
            "visual_cue": "Visual instruction (e.g., 'Point to comment section, encouraging smile')",
            "tone": "Encouraging, action-oriented"
        }}
    ],
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "visual_notes": "Overall visual direction and style",
    "retention_hooks": ["List of retention elements used"],
    "cta_type": "The type of call-to-action used",
    "estimated_retention": "High/Medium/Low based on hook strength"
}}

Generate a script that will keep trainers watching until the end!"""

        return prompt
    
    def _parse_video_script_response(self, response: str, theme: str, duration: int, style: str) -> Dict:
        """Parse video script response from Claude
        
        Args:
            response: Raw response from Claude
            theme: Content theme
            duration: Video duration
            style: Video style
            
        Returns:
            Dict: Structured video script data
        """
        try:
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                script_data = json.loads(json_str)
            else:
                # Fallback: create basic structure
                script_data = {
                    "title": f"{theme.replace('_', ' ').title()} Video Script",
                    "hook": "Stop scrolling if you're a trainer who...",
                    "script": [
                        {
                            "time_start": 0,
                            "time_end": 3,
                            "text": "Hook text",
                            "visual_cue": "Point to camera",
                            "tone": "Urgent"
                        }
                    ],
                    "hashtags": ["#PersonalTrainer", "#FitnessCoach"],
                    "visual_notes": "Engaging visual content",
                    "retention_hooks": ["Attention-grabbing hook"],
                    "cta_type": "Comment engagement",
                    "estimated_retention": "High"
                }
            
            # Add metadata
            script_data.update({
                'theme': theme,
                'duration': duration,
                'style': style,
                'platform': 'video',
                'content_type': 'video_script',
                'created_at': datetime.now(self.sa_tz).isoformat(),
                'metadata': {
                    'ai_generated': True,
                    'model_used': self.model,
                    'generation_time': datetime.now(self.sa_tz).isoformat()
                }
            })
            
            return script_data
            
        except Exception as e:
            log_error(f"Error parsing video script response: {str(e)}")
            return {}
    
    def _create_series_outline(self, topic: str, num_videos: int) -> List[Dict]:
        """Create outline for video series
        
        Args:
            topic: Main series topic
            num_videos: Number of videos in series
            
        Returns:
            List[Dict]: List of video information for the series
        """
        # Create series progression
        series_structure = {
            'client_management': [
                {'theme': 'client_onboarding', 'duration': 60, 'style': 'tutorial', 'title': 'The Perfect Client Onboarding Process'},
                {'theme': 'client_retention', 'duration': 60, 'style': 'educational', 'title': 'How to Keep Clients Long-Term'},
                {'theme': 'client_communication', 'duration': 45, 'style': 'tips', 'title': 'Communication Hacks That Work'},
                {'theme': 'client_progress_tracking', 'duration': 60, 'style': 'tutorial', 'title': 'Track Progress Like a Pro'},
                {'theme': 'client_problem_solving', 'duration': 45, 'style': 'story', 'title': 'Handling Difficult Client Situations'},
                {'theme': 'client_success_stories', 'duration': 60, 'style': 'motivational', 'title': 'Celebrating Client Wins'}
            ],
            'business_growth': [
                {'theme': 'pricing_strategy', 'duration': 60, 'style': 'educational', 'title': 'How to Price Your Services Right'},
                {'theme': 'marketing_basics', 'duration': 45, 'style': 'tips', 'title': 'Marketing That Actually Works'},
                {'theme': 'social_media_strategy', 'duration': 60, 'style': 'tutorial', 'title': 'Social Media for Trainers'},
                {'theme': 'networking_tips', 'duration': 45, 'style': 'educational', 'title': 'Build Your Network'},
                {'theme': 'scaling_business', 'duration': 60, 'style': 'strategic', 'title': 'Scale Without Losing Quality'},
                {'theme': 'success_mindset', 'duration': 45, 'style': 'motivational', 'title': 'Mindset for Success'}
            ],
            'training_techniques': [
                {'theme': 'exercise_progression', 'duration': 60, 'style': 'tutorial', 'title': 'Master Exercise Progressions'},
                {'theme': 'form_corrections', 'duration': 45, 'style': 'educational', 'title': 'Fix Form Issues Fast'},
                {'theme': 'program_design', 'duration': 60, 'style': 'tutorial', 'title': 'Design Programs That Work'},
                {'theme': 'injury_prevention', 'duration': 45, 'style': 'educational', 'title': 'Keep Clients Injury-Free'},
                {'theme': 'motivation_techniques', 'duration': 60, 'style': 'motivational', 'title': 'Motivate Any Client'},
                {'theme': 'advanced_techniques', 'duration': 60, 'style': 'tutorial', 'title': 'Advanced Training Methods'}
            ]
        }
        
        # Select appropriate series structure based on topic
        topic_key = topic.lower().replace(' ', '_')
        if topic_key in series_structure:
            base_series = series_structure[topic_key]
        else:
            # Default series structure
            base_series = series_structure['business_growth']
        
        # Return the requested number of videos
        return base_series[:num_videos]
    
    def _generate_cliffhanger(self, next_video: Dict) -> str:
        """Generate cliffhanger for next video
        
        Args:
            next_video: Information about the next video in series
            
        Returns:
            str: Cliffhanger text
        """
        cliffhangers = [
            f"Next time, I'll show you {next_video['title'].lower()} - you won't want to miss this!",
            f"Coming up: {next_video['title']} - this changed everything for me!",
            f"Stay tuned for the next video where I reveal {next_video['title'].lower()}",
            f"Don't miss next week's video: {next_video['title']}",
            f"The next video will blow your mind - {next_video['title']}!"
        ]
        
        return random.choice(cliffhangers)
    
    def _generate_teaser(self, previous_video: Dict) -> str:
        """Generate teaser for previous video
        
        Args:
            previous_video: Information about the previous video in series
            
        Returns:
            str: Teaser text
        """
        teasers = [
            f"If you missed last week's video on {previous_video['title'].lower()}, check it out!",
            f"Building on what we covered in {previous_video['title']}...",
            f"Following up on {previous_video['title'].lower()} from last time...",
            f"As promised in {previous_video['title']}, here's the next step...",
            f"Continuing from where we left off with {previous_video['title'].lower()}..."
        ]
        
        return random.choice(teasers)
    
    def get_trending_audio_suggestions(self, platform: str = "facebook") -> List[Dict]:
        """Get trending audio suggestions for video content
        
        Args:
            platform: Social media platform (facebook, instagram, tiktok)
            
        Returns:
            List[Dict]: List of trending audio with metadata
        """
        log_info(f"Getting trending audio suggestions for {platform}")
        
        # Mock trending audio data - in production, this would integrate with platform APIs
        trending_audio = {
            'facebook': [
                {
                    'name': 'Motivational Beat 2024',
                    'duration': 30,
                    'genre': 'motivational',
                    'bpm': 120,
                    'usage_count': '2.3M',
                    'trending_score': 95,
                    'best_for': ['workout_motivation', 'success_stories', 'transformation']
                },
                {
                    'name': 'Epic Cinematic Sound',
                    'duration': 60,
                    'genre': 'cinematic',
                    'bpm': 140,
                    'usage_count': '1.8M',
                    'trending_score': 88,
                    'best_for': ['before_after', 'achievement', 'dramatic_reveals']
                },
                {
                    'name': 'Upbeat Training Mix',
                    'duration': 45,
                    'genre': 'electronic',
                    'bpm': 128,
                    'usage_count': '3.1M',
                    'trending_score': 92,
                    'best_for': ['exercise_demos', 'quick_tips', 'energy_boost']
                }
            ],
            'instagram': [
                {
                    'name': 'Viral Hook Sound',
                    'duration': 15,
                    'genre': 'trending',
                    'bpm': 110,
                    'usage_count': '5.2M',
                    'trending_score': 98,
                    'best_for': ['quick_hacks', 'attention_grabbers', 'viral_content']
                },
                {
                    'name': 'Success Story Audio',
                    'duration': 30,
                    'genre': 'inspirational',
                    'bpm': 100,
                    'usage_count': '2.7M',
                    'trending_score': 89,
                    'best_for': ['client_stories', 'transformation', 'motivation']
                }
            ]
        }
        
        return trending_audio.get(platform, trending_audio['facebook'])
    
    def match_content_to_trending_audio(self, script_data: Dict, platform: str = "facebook") -> Dict:
        """Match video script to trending audio and adjust timing
        
        Args:
            script_data: Video script data
            platform: Target platform for audio matching
            
        Returns:
            Dict: Updated script with audio integration
        """
        log_info(f"Matching content to trending audio for {platform}")
        
        try:
            # Get trending audio suggestions
            trending_audio = self.get_trending_audio_suggestions(platform)
            
            # Find best matching audio based on content theme and duration
            script_duration = script_data.get('duration', 60)
            script_theme = script_data.get('theme', 'general')
            
            # Score audio based on duration match and theme relevance
            best_audio = None
            best_score = 0
            
            for audio in trending_audio:
                score = 0
                
                # Duration match (prefer exact or close match)
                duration_diff = abs(audio['duration'] - script_duration)
                if duration_diff == 0:
                    score += 50
                elif duration_diff <= 15:
                    score += 30
                elif duration_diff <= 30:
                    score += 15
                
                # Theme relevance
                if script_theme in audio.get('best_for', []):
                    score += 30
                
                # Trending score
                score += audio.get('trending_score', 0) * 0.2
                
                if score > best_score:
                    best_score = score
                    best_audio = audio
            
            if best_audio:
                # Adjust script timing to match audio
                script_data['trending_audio'] = best_audio
                script_data['audio_timing'] = self._calculate_audio_timing(script_data, best_audio)
                script_data['beat_sync_notes'] = self._generate_beat_sync_notes(best_audio)
                
                log_info(f"Matched script to trending audio: {best_audio['name']}")
            
            return script_data
            
        except Exception as e:
            log_error(f"Error matching content to trending audio: {str(e)}")
            return script_data
    
    def _calculate_audio_timing(self, script_data: Dict, audio: Dict) -> Dict:
        """Calculate timing adjustments for audio synchronization
        
        Args:
            script_data: Video script data
            audio: Selected trending audio data
            
        Returns:
            Dict: Audio timing information
        """
        script_duration = script_data.get('duration', 60)
        audio_duration = audio['duration']
        bpm = audio.get('bpm', 120)
        
        # Calculate beat intervals
        beat_interval = 60 / bpm  # seconds per beat
        
        # Adjust script timing if needed
        timing_adjustment = audio_duration - script_duration
        
        return {
            'original_duration': script_duration,
            'audio_duration': audio_duration,
            'adjustment_needed': timing_adjustment,
            'beat_interval': beat_interval,
            'total_beats': int(audio_duration / beat_interval),
            'sync_points': self._calculate_sync_points(script_data, beat_interval)
        }
    
    def _calculate_sync_points(self, script_data: Dict, beat_interval: float) -> List[Dict]:
        """Calculate key sync points for beat matching
        
        Args:
            script_data: Video script data
            beat_interval: Seconds per beat
            
        Returns:
            List[Dict]: Sync points for visual/audio alignment
        """
        sync_points = []
        script_segments = script_data.get('script', [])
        
        for segment in script_segments:
            start_time = segment.get('time_start', 0)
            end_time = segment.get('time_end', 0)
            
            # Find nearest beat for start and end
            start_beat = round(start_time / beat_interval)
            end_beat = round(end_time / beat_interval)
            
            sync_points.append({
                'segment': segment.get('text', '')[:50] + '...',
                'start_beat': start_beat,
                'end_beat': end_beat,
                'beat_aligned_start': start_beat * beat_interval,
                'beat_aligned_end': end_beat * beat_interval
            })
        
        return sync_points
    
    def _generate_beat_sync_notes(self, audio: Dict) -> List[str]:
        """Generate notes for syncing content to audio beats
        
        Args:
            audio: Audio metadata
            
        Returns:
            List[str]: Beat sync instructions
        """
        bpm = audio.get('bpm', 120)
        genre = audio.get('genre', 'general')
        
        notes = [
            f"Sync key points to the {bpm} BPM beat",
            f"Use {genre} style transitions between segments",
            f"Match energy changes to beat drops",
            "Emphasize important words on strong beats",
            "Use quick cuts during high-energy sections"
        ]
        
        if bpm > 130:
            notes.append("Fast-paced editing for high energy")
        elif bpm < 100:
            notes.append("Slower, more deliberate pacing")
        
        return notes
    
    def get_video_cta_options(self, cta_type: str = "engagement") -> List[str]:
        """Get video call-to-action options optimized for conversion
        
        Args:
            cta_type: Type of CTA (engagement, lead_gen, social_proof, action)
            
        Returns:
            List[str]: List of CTA options
        """
        cta_options = {
            'engagement': [
                "Comment 'ADMIN' for the free guide",
                "Which tip will you try first?",
                "Tag a trainer who needs this",
                "What's your biggest challenge? Comment below",
                "Save this for your next client",
                "Double tap if this helped you"
            ],
            'lead_gen': [
                "DM me 'GUIDE' for the free resource",
                "Comment 'YES' if you want the template",
                "Link in bio for the complete guide",
                "Send me a message for the checklist",
                "Comment 'MORE' for additional tips"
            ],
            'social_proof': [
                "Share this with a trainer who needs it",
                "Repost this to help other trainers",
                "Send this to your trainer friends",
                "Share your results in the comments",
                "Show this to your training partner"
            ],
            'action': [
                "Try this today and let me know how it goes",
                "Implement this and share your results",
                "Test this with your next client",
                "Practice this technique this week",
                "Apply this tip and tag me in your post"
            ]
        }
        
        return cta_options.get(cta_type, cta_options['engagement'])
    
    def optimize_script_for_retention(self, script_data: Dict) -> Dict:
        """Optimize video script for maximum retention
        
        Args:
            script_data: Video script data
            
        Returns:
            Dict: Optimized script with retention improvements
        """
        log_info("Optimizing script for retention")
        
        try:
            # Ensure hook is in first 3 seconds
            script_segments = script_data.get('script', [])
            if script_segments and script_segments[0]['time_end'] > 3:
                # Adjust first segment to end at 3 seconds
                script_segments[0]['time_end'] = 3
                script_segments[0]['text'] = script_segments[0]['text'][:100] + "..."  # Truncate if needed
            
            # Add retention hooks throughout
            retention_hooks = [
                "But wait, there's more...",
                "Here's the secret...",
                "This is where it gets interesting...",
                "The best part is...",
                "You won't believe what happens next...",
                "This changed everything for me...",
                "Here's what most trainers miss..."
            ]
            
            # Add retention hooks at strategic points
            for i, segment in enumerate(script_segments[1:], 1):
                if i % 2 == 0 and len(segment['text']) > 50:
                    hook = random.choice(retention_hooks)
                    segment['text'] = f"{hook} {segment['text']}"
            
            # Optimize CTA for maximum conversion
            cta_segment = script_segments[-1] if script_segments else None
            if cta_segment:
                cta_options = self.get_video_cta_options('engagement')
                cta_segment['text'] = random.choice(cta_options)
                cta_segment['visual_cue'] = "Point to comment section with encouraging expression"
            
            # Add retention score
            script_data['retention_optimization'] = {
                'hook_timing': 'First 3 seconds' if script_segments and script_segments[0]['time_end'] <= 3 else 'Needs adjustment',
                'retention_hooks_added': len([s for s in script_segments if any(hook in s['text'] for hook in retention_hooks)]),
                'cta_optimized': True,
                'estimated_retention_improvement': '15-25%'
            }
            
            script_data['script'] = script_segments
            
            log_info("Script optimized for retention")
            return script_data
            
        except Exception as e:
            log_error(f"Error optimizing script for retention: {str(e)}")
            return script_data