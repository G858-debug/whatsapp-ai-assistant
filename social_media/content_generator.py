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
    
    def generate_batch(self, num_posts: int, week_number: int, use_hooks: bool = False) -> List[Dict]:
        """Generate multiple posts at once
        
        Args:
            num_posts: Number of posts to generate
            week_number: Week number for scheduling context
            use_hooks: Whether to use hook-based generation for viral content
            
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
                    
                    # Generate the post
                    post = self.generate_single_post(theme, format_type, use_hook=use_hooks)
                    
                    if post:
                        # Add scheduling metadata
                        post['week_number'] = week_number
                        post['day_number'] = day + 1
                        post['post_index'] = post_idx + 1
                        post['scheduled_time'] = self._calculate_scheduled_time(day, post_idx, posting_times)
                        
                        generated_posts.append(post)
                        post_count += 1
                        
                        # Add delay to avoid rate limiting
                        time.sleep(1)
                    else:
                        log_warning(f"Failed to generate post {post_count + 1}")
            
            log_info(f"Successfully generated {len(generated_posts)} posts")
            return generated_posts
            
        except Exception as e:
            log_error(f"Error in batch generation: {str(e)}")
            return []
    
    def generate_single_post(self, theme: str, format_type: str, use_hook: bool = False) -> Dict:
        """Generate one post
        
        Args:
            theme: Content theme from config (admin_hacks, relatable, etc)
            format_type: Post format (single_image, text_only, carousel)
            use_hook: Whether to use hook-based generation for viral content
            
        Returns:
            Dict: Structured post data
        """
        log_info(f"Generating single post - Theme: {theme}, Format: {format_type}, Hook-based: {use_hook}")
        
        try:
            if use_hook:
                # Use hook-based generation for viral content
                return self.generate_hook_based_post(theme, format_type)
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
    
    def create_claude_prompt(self, theme: str, format_type: str, hook_type: str = None) -> str:
        """Build prompt for Claude based on theme, format, and hook type
        
        Args:
            theme: Content theme from config
            format_type: Post format type
            hook_type: Hook category from config (pain_point, success_story, controversial, quick_win)
            
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