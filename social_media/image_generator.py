"""Social Media Image Generator - Generates AI influencer images using Replicate API"""
import os
import yaml
import uuid
import requests
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
import pytz
from utils.logger import log_info, log_error, log_warning
import replicate
from social_media.database import SocialMediaDatabase


class ImageGenerator:
    """Generates consistent AI influencer images for social media posts using Replicate API"""
    
    def __init__(self, config_path: str, supabase_client):
        """Initialize Replicate and load config
        
        Args:
            config_path: Path to config.yaml file
            supabase_client: Supabase client instance
        """
        try:
            # Initialize Replicate
            self.replicate_token = os.getenv('REPLICATE_API_TOKEN')
            if not self.replicate_token:
                raise ValueError("REPLICATE_API_TOKEN environment variable not set")
            
            replicate.Client(api_token=self.replicate_token)
            self.client = replicate
            
            # Initialize database service
            self.db = SocialMediaDatabase(supabase_client)
            
            # Load configuration
            self.config = self._load_config(config_path)
            
            # Set timezone
            self.sa_tz = pytz.timezone('Africa/Johannesburg')
            
            # Cache for base prompts to optimize costs
            self._prompt_cache = {}
            
            log_info("ImageGenerator initialized successfully")
            
        except Exception as e:
            log_error(f"Failed to initialize ImageGenerator: {str(e)}")
            raise
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file
        
        Args:
            config_path: Path to config.yaml file
            
        Returns:
            Dict: Configuration dictionary
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            log_info(f"Configuration loaded from {config_path}")
            return config
            
        except Exception as e:
            log_error(f"Failed to load config from {config_path}: {str(e)}")
            raise
    
    def generate_influencer_image(self, prompt: str, style: str = "professional") -> Dict:
        """Generate AI influencer image
        
        Args:
            prompt: Description of scene/context
            style: Style modifier (professional, casual, workout, etc)
            
        Returns:
            Dict: Image data containing {image_url, storage_path, image_id}
        """
        try:
            log_info(f"Generating influencer image with style: {style}")
            
            # Build complete prompt
            full_prompt = self.build_prompt(prompt, style)
            log_info(f"Generated prompt: {full_prompt[:100]}...")
            
            # Generate image with retry logic
            image_url = self._generate_with_retry(full_prompt)
            
            if not image_url:
                log_error("Failed to generate image after all retries")
                return {"error": "Image generation failed"}
            
            # Generate filename and download/upload
            filename = f"influencer_{uuid.uuid4().hex[:8]}_{style}.png"
            storage_path = self.download_and_upload(image_url, filename)
            
            if not storage_path:
                log_error("Failed to upload image to storage")
                return {"error": "Image upload failed"}
            
            # Generate image ID
            image_id = str(uuid.uuid4())
            
            # Save image metadata to database
            image_data = {
                'image_url': image_url,
                'storage_path': storage_path,
                'image_type': 'influencer_photo',
                'file_size': 0,  # Will be updated after download
                'dimensions': {'width': 1024, 'height': 1024},
                'alt_text': f"AI generated influencer image: {prompt}",
                'metadata': {
                    'style': style,
                    'original_prompt': prompt,
                    'generated_at': datetime.now(self.sa_tz).isoformat()
                }
            }
            
            db_image_id = self.db.save_image(image_data)
            
            result = {
                'image_url': image_url,
                'storage_path': storage_path,
                'image_id': image_id,
                'db_image_id': db_image_id,
                'style': style,
                'prompt': full_prompt
            }
            
            log_info(f"Successfully generated image: {image_id}")
            return result
            
        except Exception as e:
            log_error(f"Error generating influencer image: {str(e)}")
            return {"error": str(e)}
    
    def build_prompt(self, context: str, style: str) -> str:
        """Build complete prompt for Stable Diffusion
        
        Args:
            context: Description of scene/context
            style: Style modifier (professional, casual, workout, etc)
            
        Returns:
            str: Complete prompt for Stable Diffusion
        """
        try:
            # Get base prompt from config
            base_prompt = self.config.get('image_generation', {}).get('base_prompt', 
                "Professional personal trainer, friendly African woman, Refiloe")
            
            # Get style modifiers
            style_modifiers = self._get_style_modifiers(style)
            
            # Quality tags
            quality_tags = "high quality, detailed, 4k, professional photography, sharp focus, well lit"
            
            # Build complete prompt
            full_prompt = f"{base_prompt}, {context}, {style_modifiers}, {quality_tags}"
            
            # Add Lora trigger words if available
            full_prompt = self.add_lora_to_prompt(full_prompt, "")
            
            return full_prompt
            
        except Exception as e:
            log_error(f"Error building prompt: {str(e)}")
            return f"Professional personal trainer, {context}, high quality, detailed"
    
    def _get_style_modifiers(self, style: str) -> str:
        """Get style-specific modifiers for the prompt
        
        Args:
            style: Style name (professional, casual, workout, etc)
            
        Returns:
            str: Style modifiers for the prompt
        """
        style_map = {
            'professional': 'professional office setting, business attire, confident posture, natural lighting',
            'casual': 'relaxed setting, casual athletic wear, friendly smile, warm lighting',
            'workout': 'fitness studio, athletic wear, dynamic pose, bright lighting, energetic atmosphere',
            'motivational': 'inspiring background, confident expression, uplifting atmosphere, bright lighting',
            'educational': 'clean background, approachable expression, teaching pose, clear lighting',
            'social': 'social setting, friendly expression, community atmosphere, natural lighting'
        }
        
        return style_map.get(style.lower(), style_map['professional'])
    
    def download_and_upload(self, replicate_url: str, filename: str) -> str:
        """Download image from Replicate and upload to Supabase Storage
        
        Args:
            replicate_url: URL of the generated image from Replicate
            filename: Desired filename for the stored image
            
        Returns:
            str: Storage path if successful, empty string if failed
        """
        try:
            log_info(f"Downloading image from: {replicate_url}")
            
            # Download image
            response = requests.get(replicate_url, timeout=30)
            response.raise_for_status()
            
            # Upload to Supabase Storage
            storage_path = f"social-media-images/{filename}"
            
            # Upload to Supabase Storage bucket
            upload_result = self.db.db.storage.from_('social-media-images').upload(
                storage_path, 
                response.content,
                file_options={"content-type": "image/png"}
            )
            
            if upload_result:
                log_info(f"Image uploaded successfully to: {storage_path}")
                return storage_path
            else:
                log_error("Failed to upload image to Supabase Storage")
                return ""
                
        except Exception as e:
            log_error(f"Error downloading/uploading image: {str(e)}")
            return ""
    
    def generate_batch(self, prompts: List[str]) -> List[Dict]:
        """Generate multiple images efficiently
        
        Args:
            prompts: List of prompt dictionaries with 'prompt' and 'style' keys
            
        Returns:
            List[Dict]: List of image data for each generated image
        """
        try:
            log_info(f"Generating batch of {len(prompts)} images")
            
            # Use asyncio for concurrent generation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                results = loop.run_until_complete(self._generate_batch_async(prompts))
                return results
            finally:
                loop.close()
                
        except Exception as e:
            log_error(f"Error generating batch: {str(e)}")
            return []
    
    async def _generate_batch_async(self, prompts: List[str]) -> List[Dict]:
        """Async implementation of batch generation
        
        Args:
            prompts: List of prompt dictionaries
            
        Returns:
            List[Dict]: List of generated image data
        """
        try:
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests
            
            async def generate_single(prompt_data):
                async with semaphore:
                    return self.generate_influencer_image(
                        prompt_data.get('prompt', ''),
                        prompt_data.get('style', 'professional')
                    )
            
            # Generate all images concurrently
            tasks = [generate_single(prompt) for prompt in prompts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and return valid results
            valid_results = [r for r in results if isinstance(r, dict) and 'error' not in r]
            
            log_info(f"Batch generation completed: {len(valid_results)}/{len(prompts)} successful")
            return valid_results
            
        except Exception as e:
            log_error(f"Error in async batch generation: {str(e)}")
            return []
    
    def add_lora_to_prompt(self, prompt: str, lora_trigger: str) -> str:
        """Add Lora trigger words to prompt
        
        Args:
            prompt: Base prompt
            lora_trigger: Lora trigger words (currently placeholder)
            
        Returns:
            str: Prompt with Lora trigger words added
        """
        # PLACEHOLDER: For when Lora file arrives
        # Currently returns prompt unchanged
        if lora_trigger:
            return f"{lora_trigger}, {prompt}"
        return prompt
    
    def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Generate image with retry logic
        
        Args:
            prompt: Complete prompt for image generation
            max_retries: Maximum number of retry attempts
            
        Returns:
            Optional[str]: Image URL if successful, None if failed
        """
        for attempt in range(max_retries):
            try:
                log_info(f"Generating image (attempt {attempt + 1}/{max_retries})")
                
                # Generate image using Replicate
                output = self.client.run(
                    "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                    input={
                        "prompt": prompt,
                        "width": 1024,
                        "height": 1024,
                        "num_inference_steps": 20,
                        "guidance_scale": 7.5,
                        "num_outputs": 1
                    }
                )
                
                if output and len(output) > 0:
                    image_url = output[0]
                    log_info(f"Image generated successfully: {image_url}")
                    return image_url
                else:
                    log_warning(f"Empty output from Replicate (attempt {attempt + 1})")
                    
            except Exception as e:
                log_error(f"Error generating image (attempt {attempt + 1}): {str(e)}")
                
                if attempt < max_retries - 1:
                    log_info(f"Retrying in 5 seconds...")
                    import time
                    time.sleep(5)
                else:
                    log_error("All retry attempts failed")
        
        return None
    
    def check_existing_image(self, prompt_hash: str) -> Optional[Dict]:
        """Check if a similar image already exists to avoid regeneration
        
        Args:
            prompt_hash: Hash of the prompt to check for
            
        Returns:
            Optional[Dict]: Existing image data if found, None otherwise
        """
        try:
            # Query database for existing images with similar prompt hash
            result = self.db.db.table('social_images').select('*').eq(
                'metadata->>prompt_hash', prompt_hash
            ).execute()
            
            if result.data:
                log_info(f"Found existing image for prompt hash: {prompt_hash}")
                return result.data[0]
            
            return None
            
        except Exception as e:
            log_error(f"Error checking existing image: {str(e)}")
            return None
    
    def get_generation_stats(self) -> Dict:
        """Get statistics about image generation
        
        Returns:
            Dict: Statistics about generated images
        """
        try:
            # Get total images generated
            total_result = self.db.db.table('social_images').select('id', count='exact').execute()
            total_images = total_result.count if total_result.count else 0
            
            # Get images by style
            style_result = self.db.db.table('social_images').select(
                'metadata->>style'
            ).execute()
            
            style_counts = {}
            if style_result.data:
                for item in style_result.data:
                    style = item.get('metadata', {}).get('style', 'unknown')
                    style_counts[style] = style_counts.get(style, 0) + 1
            
            # Get recent generation activity (last 7 days)
            from datetime import timedelta
            week_ago = datetime.now(self.sa_tz) - timedelta(days=7)
            
            recent_result = self.db.db.table('social_images').select('id', count='exact').gte(
                'created_at', week_ago.isoformat()
            ).execute()
            recent_images = recent_result.count if recent_result.count else 0
            
            stats = {
                'total_images': total_images,
                'recent_images': recent_images,
                'style_distribution': style_counts,
                'last_updated': datetime.now(self.sa_tz).isoformat()
            }
            
            log_info(f"Retrieved generation stats: {stats}")
            return stats
            
        except Exception as e:
            log_error(f"Error getting generation stats: {str(e)}")
            return {
                'total_images': 0,
                'recent_images': 0,
                'style_distribution': {},
                'error': str(e)
            }