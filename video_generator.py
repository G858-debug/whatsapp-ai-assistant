import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

import aiohttp
import cv2
import numpy as np
from moviepy.editor import (
    AudioFileClip, CompositeVideoClip, ImageClip, TextClip, VideoFileClip,
    concatenate_videoclips, clips_array
)
from playwright.async_api import async_playwright
from remotion import render_media, render_still
from supabase import create_client, Client
import whisper
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoGenerator:
    """
    A comprehensive video generation class for creating various types of videos
    for the Refiloe AI trainer platform.
    """
    
    def __init__(self, config: Dict, database: Client):
        """
        Initialize the VideoGenerator with configuration and database objects.
        
        Args:
            config: Configuration dictionary containing API keys and settings
            database: Supabase database client instance
        """
        self.config = config
        self.database = database
        self.session = None
        
        # API configurations
        self.did_api_key = config.get('did_api_key')
        self.heygen_api_key = config.get('heygen_api_key')
        self.openai_api_key = config.get('openai_api_key')
        
        # Video settings
        self.video_settings = {
            'max_duration': 300,  # 5 minutes
            'min_duration': 15,   # 15 seconds
            'fps': 30,
            'quality': 'high'
        }
        
        # Platform-specific settings
        self.platform_settings = {
            'facebook_reels': {'aspect_ratio': (9, 16), 'max_duration': 90},
            'facebook_feed': {'aspect_ratio': (1, 1), 'max_duration': 240},
            'stories': {'aspect_ratio': (9, 16), 'max_duration': 15, 'safe_zone': 0.1}
        }
        
        # Initialize Whisper model for captions
        self.whisper_model = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def generate_ai_video_with_avatars(
        self, 
        script_text: str, 
        avatar_style: str = "professional"
    ) -> Dict[str, Union[str, Dict]]:
        """
        Generate AI avatar videos using D-ID or HeyGen API.
        
        Args:
            script_text: The script text for the video
            avatar_style: Style of avatar (professional/casual/energetic)
            
        Returns:
            Dictionary containing video URL and metadata
        """
        try:
            # Choose avatar based on style
            avatar_mapping = {
                "professional": "refiloe_professional",
                "casual": "refiloe_casual", 
                "energetic": "refiloe_energetic"
            }
            
            avatar_id = avatar_mapping.get(avatar_style, "refiloe_professional")
            
            # Try D-ID first, fallback to HeyGen
            try:
                result = await self._create_did_video(script_text, avatar_id)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"D-ID video creation failed: {e}")
                
            # Fallback to HeyGen
            result = await self._create_heygen_video(script_text, avatar_id)
            return result
            
        except Exception as e:
            logger.error(f"AI video generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "static_content"
            }

    async def _create_did_video(self, script_text: str, avatar_id: str) -> Dict:
        """Create video using D-ID API."""
        if not self.did_api_key:
            raise ValueError("D-ID API key not configured")
            
        url = "https://api.d-id.com/talks"
        headers = {
            "Authorization": f"Basic {self.did_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "script": {
                "type": "text",
                "input": script_text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": "en-US-JennyNeural"
                }
            },
            "source_url": f"https://d-id-public-bucket.s3.amazonaws.com/refiloe-avatars/{avatar_id}.jpg",
            "config": {
                "fluent": True,
                "pad_audio": 0.0
            }
        }
        
        async with self.session.post(url, headers=headers, json=data) as response:
            if response.status == 201:
                result = await response.json()
                return {
                    "success": True,
                    "video_url": result.get("result_url"),
                    "id": result.get("id"),
                    "provider": "d-id",
                    "metadata": {
                        "duration": result.get("duration"),
                        "created_at": datetime.now().isoformat()
                    }
                }
            else:
                raise Exception(f"D-ID API error: {response.status}")

    async def _create_heygen_video(self, script_text: str, avatar_id: str) -> Dict:
        """Create video using HeyGen API."""
        if not self.heygen_api_key:
            raise ValueError("HeyGen API key not configured")
            
        url = "https://api.heygen.com/v1/video.generate"
        headers = {
            "X-API-KEY": self.heygen_api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script_text,
                        "voice_id": "en-US-JennyNeural"
                    }
                }
            ],
            "dimension": {
                "width": 1920,
                "height": 1080
            }
        }
        
        async with self.session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return {
                    "success": True,
                    "video_url": result.get("video_url"),
                    "id": result.get("video_id"),
                    "provider": "heygen",
                    "metadata": {
                        "duration": result.get("duration"),
                        "created_at": datetime.now().isoformat()
                    }
                }
            else:
                raise Exception(f"HeyGen API error: {response.status}")

    async def generate_screen_recording_tutorial(
        self, 
        tutorial_type: str = "whatsapp_demo"
    ) -> Dict[str, Union[str, Dict]]:
        """
        Generate screen recording tutorials using Playwright.
        
        Args:
            tutorial_type: Type of tutorial to record
            
        Returns:
            Dictionary containing video file path and metadata
        """
        try:
            video_path = f"/tmp/refiloe_tutorial_{uuid.uuid4().hex}.mp4"
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    record_video_dir="/tmp",
                    record_video_size={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                if tutorial_type == "whatsapp_demo":
                    await self._record_whatsapp_demo(page)
                elif tutorial_type == "before_after":
                    await self._record_before_after_demo(page)
                else:
                    await self._record_generic_tutorial(page, tutorial_type)
                
                # Wait for video to be saved
                await page.wait_for_timeout(2000)
                await context.close()
                await browser.close()
                
                # Process the recorded video
                processed_path = await self._process_screen_recording(video_path)
                
                return {
                    "success": True,
                    "video_path": processed_path,
                    "metadata": {
                        "type": tutorial_type,
                        "duration": self._get_video_duration(processed_path),
                        "created_at": datetime.now().isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Screen recording generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "static_screenshots"
            }

    async def _record_whatsapp_demo(self, page):
        """Record WhatsApp Web demonstration."""
        # Navigate to WhatsApp Web
        await page.goto("https://web.whatsapp.com")
        await page.wait_for_timeout(3000)
        
        # Add captions and highlights
        await self._add_demo_captions(page, "Before Refiloe: Messy WhatsApp conversations")
        
        # Simulate chaotic WhatsApp usage
        await self._simulate_chaotic_whatsapp(page)
        
        await page.wait_for_timeout(2000)
        
        # Show transformation
        await self._add_demo_captions(page, "After Refiloe: Organized and efficient")
        await self._simulate_organized_whatsapp(page)
        
        await page.wait_for_timeout(2000)

    async def _record_before_after_demo(self, page):
        """Record before/after comparison demo."""
        # Before state
        await self._add_demo_captions(page, "BEFORE: Chaos and confusion")
        await page.goto("about:blank")
        await self._create_chaos_visualization(page)
        await page.wait_for_timeout(3000)
        
        # Transition
        await self._add_demo_captions(page, "Introducing Refiloe AI Trainer...")
        await page.wait_for_timeout(2000)
        
        # After state
        await self._add_demo_captions(page, "AFTER: Organized and efficient")
        await self._create_organization_visualization(page)
        await page.wait_for_timeout(3000)

    async def _add_demo_captions(self, page, text: str):
        """Add captions overlay to the page."""
        await page.evaluate(f"""
            const caption = document.createElement('div');
            caption.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 24px;
                font-weight: bold;
                z-index: 10000;
                text-align: center;
            `;
            caption.textContent = '{text}';
            document.body.appendChild(caption);
        """)

    async def _simulate_chaotic_whatsapp(self, page):
        """Simulate chaotic WhatsApp usage patterns."""
        # This would simulate the user's current chaotic WhatsApp state
        # For demo purposes, we'll create a visual representation
        await page.evaluate("""
            document.body.innerHTML = `
                <div style="background: #075e54; color: white; padding: 20px; height: 100vh;">
                    <h1 style="text-align: center; margin-bottom: 30px;">WhatsApp - Before Refiloe</h1>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div style="background: #128c7e; padding: 15px; border-radius: 10px;">
                            <h3>Unread Messages: 247</h3>
                            <p>Multiple group chats</p>
                            <p>Scattered conversations</p>
                            <p>Missed important updates</p>
                        </div>
                        <div style="background: #128c7e; padding: 15px; border-radius: 10px;">
                            <h3>Chaos Indicators</h3>
                            <p>❌ No organization</p>
                            <p>❌ Information overload</p>
                            <p>❌ Missed opportunities</p>
                            <p>❌ Stress and anxiety</p>
                        </div>
                    </div>
                </div>
            `;
        """)

    async def _simulate_organized_whatsapp(self, page):
        """Simulate organized WhatsApp usage with Refiloe."""
        await page.evaluate("""
            document.body.innerHTML = `
                <div style="background: #075e54; color: white; padding: 20px; height: 100vh;">
                    <h1 style="text-align: center; margin-bottom: 30px;">WhatsApp - After Refiloe</h1>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div style="background: #128c7e; padding: 15px; border-radius: 10px;">
                            <h3>Organized Messages: 0 unread</h3>
                            <p>✅ Prioritized conversations</p>
                            <p>✅ Smart categorization</p>
                            <p>✅ Important updates highlighted</p>
                        </div>
                        <div style="background: #128c7e; padding: 15px; border-radius: 10px;">
                            <h3>Refiloe Benefits</h3>
                            <p>✅ AI-powered organization</p>
                            <p>✅ Smart notifications</p>
                            <p>✅ Time-saving automation</p>
                            <p>✅ Peace of mind</p>
                        </div>
                    </div>
                </div>
            `;
        """)

    async def _create_chaos_visualization(self, page):
        """Create visual representation of chaos state."""
        await page.evaluate("""
            document.body.innerHTML = `
                <div style="background: linear-gradient(45deg, #ff6b6b, #ff8e8e); color: white; padding: 20px; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                    <h1 style="font-size: 48px; margin-bottom: 30px;">CHAOS</h1>
                    <div style="font-size: 24px; text-align: center;">
                        <p>❌ Overwhelming information</p>
                        <p>❌ Missed opportunities</p>
                        <p>❌ Stress and confusion</p>
                        <p>❌ Wasted time</p>
                    </div>
                </div>
            `;
        """)

    async def _create_organization_visualization(self, page):
        """Create visual representation of organized state."""
        await page.evaluate("""
            document.body.innerHTML = `
                <div style="background: linear-gradient(45deg, #4ecdc4, #44a08d); color: white; padding: 20px; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                    <h1 style="font-size: 48px; margin-bottom: 30px;">ORGANIZATION</h1>
                    <div style="font-size: 24px; text-align: center;">
                        <p>✅ Clear priorities</p>
                        <p>✅ Efficient workflows</p>
                        <p>✅ Peace of mind</p>
                        <p>✅ More time for what matters</p>
                    </div>
                </div>
            `;
        """)

    async def _process_screen_recording(self, video_path: str) -> str:
        """Process and enhance the screen recording."""
        try:
            # Load the video
            video = VideoFileClip(video_path)
            
            # Add intro/outro
            intro = self._create_intro_clip()
            outro = self._create_outro_clip()
            
            # Combine clips
            final_video = concatenate_videoclips([intro, video, outro])
            
            # Add captions
            final_video = self._add_video_captions(final_video)
            
            # Save processed video
            processed_path = video_path.replace('.mp4', '_processed.mp4')
            final_video.write_videofile(
                processed_path,
                fps=30,
                codec='libx264',
                audio_codec='aac'
            )
            
            # Clean up
            video.close()
            final_video.close()
            
            return processed_path
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return video_path

    def _create_intro_clip(self) -> VideoFileClip:
        """Create intro clip for tutorials."""
        # Create a simple intro with Refiloe branding
        intro_text = "Refiloe AI Trainer Tutorial"
        intro_clip = TextClip(
            intro_text,
            fontsize=50,
            color='white',
            font='Arial-Bold'
        ).set_duration(3).set_position('center')
        
        # Add background
        background = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(3)
        intro_video = CompositeVideoClip([background, intro_clip])
        
        return intro_video

    def _create_outro_clip(self) -> VideoFileClip:
        """Create outro clip for tutorials."""
        outro_text = "Try Refiloe AI Trainer Today!"
        outro_clip = TextClip(
            outro_text,
            fontsize=50,
            color='white',
            font='Arial-Bold'
        ).set_duration(3).set_position('center')
        
        # Add background
        background = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(3)
        outro_video = CompositeVideoClip([background, outro_clip])
        
        return outro_video

    def _add_video_captions(self, video: VideoFileClip) -> VideoFileClip:
        """Add captions to video."""
        # This is a simplified version - in production, you'd use proper caption timing
        captions = [
            ("Welcome to Refiloe AI Trainer", 0, 3),
            ("Transform your digital life", 3, 6),
            ("From chaos to organization", 6, 9)
        ]
        
        caption_clips = []
        for text, start, end in captions:
            caption = TextClip(
                text,
                fontsize=30,
                color='white',
                font='Arial-Bold'
            ).set_start(start).set_duration(end - start).set_position(('center', 'bottom'))
            caption_clips.append(caption)
        
        if caption_clips:
            return CompositeVideoClip([video] + caption_clips)
        return video

    async def generate_exercise_demo_video(
        self, 
        exercise_ids: List[str],
        workout_sequence: Optional[List[Dict]] = None
    ) -> Dict[str, Union[str, Dict]]:
        """
        Generate exercise demonstration videos from Supabase library.
        
        Args:
            exercise_ids: List of exercise IDs from Supabase
            workout_sequence: Optional custom workout sequence
            
        Returns:
            Dictionary containing compiled video path and metadata
        """
        try:
            # Fetch exercise videos from Supabase
            exercise_videos = await self._fetch_exercise_videos(exercise_ids)
            
            if not exercise_videos:
                raise ValueError("No exercise videos found")
            
            # Create workout sequence
            if not workout_sequence:
                workout_sequence = self._create_default_workout_sequence(exercise_videos)
            
            # Compile video
            compiled_video = await self._compile_exercise_video(exercise_videos, workout_sequence)
            
            return {
                "success": True,
                "video_path": compiled_video,
                "metadata": {
                    "exercise_count": len(exercise_videos),
                    "duration": self._get_video_duration(compiled_video),
                    "created_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Exercise demo generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "static_exercise_images"
            }

    async def _fetch_exercise_videos(self, exercise_ids: List[str]) -> List[Dict]:
        """Fetch exercise videos from Supabase."""
        try:
            response = self.database.table('exercise_videos').select('*').in_('id', exercise_ids).execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch exercise videos: {e}")
            return []

    def _create_default_workout_sequence(self, exercise_videos: List[Dict]) -> List[Dict]:
        """Create a default workout sequence."""
        sequence = []
        for i, exercise in enumerate(exercise_videos):
            sequence.append({
                "exercise_id": exercise['id'],
                "duration": exercise.get('duration', 30),
                "reps": exercise.get('reps', 10),
                "rest_time": 10 if i < len(exercise_videos) - 1 else 0
            })
        return sequence

    async def _compile_exercise_video(
        self, 
        exercise_videos: List[Dict], 
        workout_sequence: List[Dict]
    ) -> str:
        """Compile exercise videos into a workout video."""
        try:
            video_clips = []
            
            for i, exercise_data in enumerate(workout_sequence):
                exercise_id = exercise_data['exercise_id']
                duration = exercise_data['duration']
                reps = exercise_data['reps']
                
                # Find the exercise video
                exercise_video = next((e for e in exercise_videos if e['id'] == exercise_id), None)
                if not exercise_video:
                    continue
                
                # Load video clip
                video_path = exercise_video['video_url']
                clip = VideoFileClip(video_path)
                
                # Add text overlay with rep count and form tips
                text_overlay = self._create_exercise_text_overlay(exercise_video['name'], reps, duration)
                clip_with_text = CompositeVideoClip([clip, text_overlay])
                
                # Trim to desired duration
                if clip_with_text.duration > duration:
                    clip_with_text = clip_with_text.subclip(0, duration)
                
                video_clips.append(clip_with_text)
                
                # Add rest period if not last exercise
                if i < len(workout_sequence) - 1:
                    rest_clip = self._create_rest_period_clip(workout_sequence[i]['rest_time'])
                    video_clips.append(rest_clip)
            
            # Concatenate all clips
            final_video = concatenate_videoclips(video_clips)
            
            # Add intro and outro
            intro = self._create_workout_intro()
            outro = self._create_workout_outro()
            
            complete_video = concatenate_videoclips([intro, final_video, outro])
            
            # Save the compiled video
            output_path = f"/tmp/refiloe_workout_{uuid.uuid4().hex}.mp4"
            complete_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac'
            )
            
            # Clean up
            for clip in video_clips:
                clip.close()
            final_video.close()
            complete_video.close()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Video compilation failed: {e}")
            raise

    def _create_exercise_text_overlay(self, exercise_name: str, reps: int, duration: int) -> TextClip:
        """Create text overlay for exercise videos."""
        text = f"{exercise_name}\n{reps} reps • {duration}s"
        return TextClip(
            text,
            fontsize=40,
            color='white',
            font='Arial-Bold',
            stroke_color='black',
            stroke_width=2
        ).set_position(('center', 'bottom')).set_duration(duration)

    def _create_rest_period_clip(self, duration: int) -> VideoFileClip:
        """Create rest period clip."""
        if duration <= 0:
            return VideoFileClip("").set_duration(0)
        
        rest_text = f"Rest: {duration}s"
        text_clip = TextClip(
            rest_text,
            fontsize=50,
            color='white',
            font='Arial-Bold'
        ).set_duration(duration).set_position('center')
        
        background = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(duration)
        return CompositeVideoClip([background, text_clip])

    def _create_workout_intro(self) -> VideoFileClip:
        """Create workout intro clip."""
        intro_text = "Refiloe AI Trainer\nWorkout Session"
        intro_clip = TextClip(
            intro_text,
            fontsize=60,
            color='white',
            font='Arial-Bold'
        ).set_duration(5).set_position('center')
        
        background = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(5)
        return CompositeVideoClip([background, intro_clip])

    def _create_workout_outro(self) -> VideoFileClip:
        """Create workout outro clip."""
        outro_text = "Great job!\nKeep training with Refiloe AI"
        outro_clip = TextClip(
            outro_text,
            fontsize=50,
            color='white',
            font='Arial-Bold'
        ).set_duration(5).set_position('center')
        
        background = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(5)
        return CompositeVideoClip([background, outro_clip])

    async def generate_animated_explainer(
        self, 
        content_type: str,
        data: Dict,
        animation_style: str = "kinetic_typography"
    ) -> Dict[str, Union[str, Dict]]:
        """
        Generate animated explainer videos using Remotion or Lottie.
        
        Args:
            content_type: Type of content (statistics, transformation, infographic)
            data: Data to visualize
            animation_style: Style of animation
            
        Returns:
            Dictionary containing video path and metadata
        """
        try:
            if animation_style == "remotion":
                video_path = await self._create_remotion_animation(content_type, data)
            else:
                video_path = await self._create_lottie_animation(content_type, data)
            
            return {
                "success": True,
                "video_path": video_path,
                "metadata": {
                    "content_type": content_type,
                    "animation_style": animation_style,
                    "duration": self._get_video_duration(video_path),
                    "created_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Animated explainer generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "static_infographic"
            }

    async def _create_remotion_animation(self, content_type: str, data: Dict) -> str:
        """Create animation using Remotion."""
        try:
            # This is a simplified example - in production, you'd have a full Remotion setup
            output_path = f"/tmp/refiloe_animation_{uuid.uuid4().hex}.mp4"
            
            # Create a simple animated video using MoviePy as fallback
            return await self._create_fallback_animation(content_type, data, output_path)
            
        except Exception as e:
            logger.error(f"Remotion animation failed: {e}")
            raise

    async def _create_lottie_animation(self, content_type: str, data: Dict) -> str:
        """Create animation using Lottie."""
        try:
            # This would integrate with Lottie animation library
            # For now, we'll create a fallback animation
            output_path = f"/tmp/refiloe_lottie_{uuid.uuid4().hex}.mp4"
            return await self._create_fallback_animation(content_type, data, output_path)
            
        except Exception as e:
            logger.error(f"Lottie animation failed: {e}")
            raise

    async def _create_fallback_animation(self, content_type: str, data: Dict, output_path: str) -> str:
        """Create fallback animation using MoviePy."""
        try:
            clips = []
            
            if content_type == "statistics":
                clips = self._create_statistics_animation(data)
            elif content_type == "transformation":
                clips = self._create_transformation_animation(data)
            elif content_type == "infographic":
                clips = self._create_infographic_animation(data)
            else:
                clips = self._create_generic_animation(data)
            
            # Concatenate clips
            final_video = concatenate_videoclips(clips)
            
            # Write video
            final_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac'
            )
            
            # Clean up
            for clip in clips:
                clip.close()
            final_video.close()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Fallback animation creation failed: {e}")
            raise

    def _create_statistics_animation(self, data: Dict) -> List[VideoFileClip]:
        """Create statistics animation."""
        clips = []
        
        # Title slide
        title = TextClip(
            "Refiloe AI Trainer Statistics",
            fontsize=60,
            color='white',
            font='Arial-Bold'
        ).set_duration(3).set_position('center')
        
        background = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(3)
        title_clip = CompositeVideoClip([background, title])
        clips.append(title_clip)
        
        # Statistics slides
        stats = data.get('statistics', {})
        for stat_name, stat_value in stats.items():
            stat_text = f"{stat_name}: {stat_value}"
            stat_clip = TextClip(
                stat_text,
                fontsize=50,
                color='white',
                font='Arial-Bold'
            ).set_duration(2).set_position('center')
            
            stat_bg = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(2)
            stat_video = CompositeVideoClip([stat_bg, stat_clip])
            clips.append(stat_video)
        
        return clips

    def _create_transformation_animation(self, data: Dict) -> List[VideoFileClip]:
        """Create transformation animation."""
        clips = []
        
        # Before state
        before_text = "BEFORE: Chaos and Confusion"
        before_clip = TextClip(
            before_text,
            fontsize=50,
            color='red',
            font='Arial-Bold'
        ).set_duration(3).set_position('center')
        
        before_bg = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(3)
        before_video = CompositeVideoClip([before_bg, before_clip])
        clips.append(before_video)
        
        # Transformation
        transform_text = "TRANSFORMATION IN PROGRESS..."
        transform_clip = TextClip(
            transform_text,
            fontsize=40,
            color='yellow',
            font='Arial-Bold'
        ).set_duration(2).set_position('center')
        
        transform_bg = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(2)
        transform_video = CompositeVideoClip([transform_bg, transform_clip])
        clips.append(transform_video)
        
        # After state
        after_text = "AFTER: Organized and Efficient"
        after_clip = TextClip(
            after_text,
            fontsize=50,
            color='green',
            font='Arial-Bold'
        ).set_duration(3).set_position('center')
        
        after_bg = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(3)
        after_video = CompositeVideoClip([after_bg, after_clip])
        clips.append(after_video)
        
        return clips

    def _create_infographic_animation(self, data: Dict) -> List[VideoFileClip]:
        """Create infographic animation."""
        clips = []
        
        # This would create more sophisticated infographic animations
        # For now, we'll create a simple version
        
        infographic_text = "Refiloe AI Trainer\nKey Benefits"
        infographic_clip = TextClip(
            infographic_text,
            fontsize=50,
            color='white',
            font='Arial-Bold'
        ).set_duration(5).set_position('center')
        
        infographic_bg = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(5)
        infographic_video = CompositeVideoClip([infographic_bg, infographic_clip])
        clips.append(infographic_video)
        
        return clips

    def _create_generic_animation(self, data: Dict) -> List[VideoFileClip]:
        """Create generic animation."""
        clips = []
        
        generic_text = "Refiloe AI Trainer\nYour Digital Life Assistant"
        generic_clip = TextClip(
            generic_text,
            fontsize=50,
            color='white',
            font='Arial-Bold'
        ).set_duration(5).set_position('center')
        
        generic_bg = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(5)
        generic_video = CompositeVideoClip([generic_bg, generic_clip])
        clips.append(generic_video)
        
        return clips

    async def generate_video_script(
        self, 
        video_type: str,
        target_audience: str = "general",
        duration: int = 60
    ) -> Dict[str, Union[str, Dict]]:
        """
        Generate AI-optimized scripts for videos.
        
        Args:
            video_type: Type of video (tutorial, demo, explainer, testimonial)
            target_audience: Target audience (general, professionals, students)
            duration: Target duration in seconds
            
        Returns:
            Dictionary containing script and metadata
        """
        try:
            # Generate script using AI
            script = await self._generate_ai_script(video_type, target_audience, duration)
            
            # Add timing markers
            script_with_timing = self._add_timing_markers(script, duration)
            
            # Optimize for engagement
            optimized_script = self._optimize_script_for_engagement(script_with_timing)
            
            return {
                "success": True,
                "script": optimized_script,
                "metadata": {
                    "video_type": video_type,
                    "target_audience": target_audience,
                    "duration": duration,
                    "word_count": len(optimized_script.split()),
                    "created_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "template_script"
            }

    async def _generate_ai_script(self, video_type: str, target_audience: str, duration: int) -> str:
        """Generate script using AI."""
        if not self.openai_api_key:
            # Fallback to template-based script generation
            return self._generate_template_script(video_type, target_audience, duration)
        
        try:
            prompt = self._create_script_prompt(video_type, target_audience, duration)
            
            # This would integrate with OpenAI API
            # For now, we'll use a template-based approach
            return self._generate_template_script(video_type, target_audience, duration)
            
        except Exception as e:
            logger.error(f"AI script generation failed: {e}")
            return self._generate_template_script(video_type, target_audience, duration)

    def _create_script_prompt(self, video_type: str, target_audience: str, duration: int) -> str:
        """Create prompt for AI script generation."""
        return f"""
        Create a {duration}-second video script for Refiloe AI Trainer.
        
        Video Type: {video_type}
        Target Audience: {target_audience}
        
        Requirements:
        - Include a strong hook in the first 3 seconds
        - Deliver clear value proposition
        - Include social proof and benefits
        - End with a compelling call-to-action
        - Optimize for watch time and engagement
        - Use conversational, engaging tone
        - Include specific examples and use cases
        
        Format the script with timing markers and speaking notes.
        """

    def _generate_template_script(self, video_type: str, target_audience: str, duration: int) -> str:
        """Generate script using templates."""
        templates = {
            "tutorial": self._get_tutorial_script_template(),
            "demo": self._get_demo_script_template(),
            "explainer": self._get_explainer_script_template(),
            "testimonial": self._get_testimonial_script_template()
        }
        
        base_script = templates.get(video_type, templates["explainer"])
        
        # Customize for target audience
        if target_audience == "professionals":
            base_script = self._customize_for_professionals(base_script)
        elif target_audience == "students":
            base_script = self._customize_for_students(base_script)
        
        # Adjust for duration
        return self._adjust_script_duration(base_script, duration)

    def _get_tutorial_script_template(self) -> str:
        """Get tutorial script template."""
        return """
        [0-3s] Hook: "Tired of drowning in digital chaos? I'm about to show you how to transform your digital life in just 5 minutes."
        
        [3-15s] Problem: "Most people struggle with information overload, missed opportunities, and constant digital stress. Sound familiar?"
        
        [15-45s] Solution: "Meet Refiloe, your AI trainer that organizes your digital world. Watch as I demonstrate how Refiloe transforms chaos into clarity."
        
        [45-55s] Benefits: "With Refiloe, you'll save hours daily, never miss important updates, and finally have peace of mind in your digital life."
        
        [55-60s] CTA: "Ready to transform your digital life? Click the link below to try Refiloe AI Trainer today!"
        """

    def _get_demo_script_template(self) -> str:
        """Get demo script template."""
        return """
        [0-3s] Hook: "Watch this transformation from digital chaos to organized efficiency."
        
        [3-20s] Before: "This is how most people's digital lives look - overwhelming, chaotic, and stressful."
        
        [20-40s] Demo: "Now watch what happens when Refiloe AI Trainer takes over. See how it automatically organizes, prioritizes, and streamlines everything."
        
        [40-55s] After: "The result? A calm, organized digital environment where you're in control and nothing important gets missed."
        
        [55-60s] CTA: "Experience this transformation yourself. Try Refiloe AI Trainer now!"
        """

    def _get_explainer_script_template(self) -> str:
        """Get explainer script template."""
        return """
        [0-3s] Hook: "What if I told you there's a way to eliminate digital stress forever?"
        
        [3-15s] Problem: "Digital overwhelm affects 89% of people. Information overload, missed opportunities, and constant anxiety."
        
        [15-35s] Solution: "Refiloe AI Trainer uses advanced AI to organize your digital life. It learns your patterns, prioritizes what matters, and automates the rest."
        
        [35-50s] Benefits: "Users report 3x productivity increase, 2 hours saved daily, and 95% reduction in digital stress."
        
        [50-60s] CTA: "Join thousands who've transformed their digital lives. Start your free trial today!"
        """

    def _get_testimonial_script_template(self) -> str:
        """Get testimonial script template."""
        return """
        [0-3s] Hook: "Sarah went from digital chaos to organized success in just one week."
        
        [3-20s] Story: "Sarah was drowning in emails, missed deadlines, and constant digital stress. Her productivity was at an all-time low."
        
        [20-40s] Transformation: "Then she discovered Refiloe AI Trainer. Within days, her inbox was organized, priorities were clear, and she was back in control."
        
        [40-55s] Results: "Now Sarah saves 2 hours daily, never misses important updates, and has the peace of mind she always wanted."
        
        [55-60s] CTA: "Ready for your transformation? Try Refiloe AI Trainer today!"
        """

    def _customize_for_professionals(self, script: str) -> str:
        """Customize script for professionals."""
        return script.replace("digital chaos", "professional overwhelm").replace(
            "digital stress", "workplace inefficiency"
        )

    def _customize_for_students(self, script: str) -> str:
        """Customize script for students."""
        return script.replace("digital chaos", "academic overwhelm").replace(
            "digital stress", "study stress"
        )

    def _adjust_script_duration(self, script: str, target_duration: int) -> str:
        """Adjust script duration."""
        # This is a simplified version - in production, you'd have more sophisticated duration adjustment
        if target_duration <= 30:
            # Short version
            return script.split('\n')[0] + "\n" + script.split('\n')[-1]
        elif target_duration >= 120:
            # Extended version
            return script + "\n\n[60-120s] Additional benefits and use cases..."
        else:
            return script

    def _add_timing_markers(self, script: str, duration: int) -> str:
        """Add timing markers to script."""
        # This would parse the script and add precise timing markers
        return script

    def _optimize_script_for_engagement(self, script: str) -> str:
        """Optimize script for maximum engagement."""
        # This would apply engagement optimization techniques
        return script

    async def add_captions_and_branding(
        self, 
        video_path: str,
        branding_options: Optional[Dict] = None
    ) -> Dict[str, Union[str, Dict]]:
        """
        Add captions and branding to videos.
        
        Args:
            video_path: Path to the video file
            branding_options: Optional branding customization
            
        Returns:
            Dictionary containing enhanced video path and metadata
        """
        try:
            # Load video
            video = VideoFileClip(video_path)
            
            # Generate captions using Whisper
            captions = await self._generate_captions(video_path)
            
            # Add captions to video
            video_with_captions = self._add_captions_to_video(video, captions)
            
            # Add branding
            video_with_branding = self._add_branding_to_video(video_with_captions, branding_options)
            
            # Add progress bar for longer videos
            if video.duration > 60:
                video_with_progress = self._add_progress_bar(video_with_branding)
            else:
                video_with_progress = video_with_branding
            
            # Add animated CTAs and end screens
            final_video = self._add_ctas_and_end_screens(video_with_progress)
            
            # Save enhanced video
            enhanced_path = video_path.replace('.mp4', '_enhanced.mp4')
            final_video.write_videofile(
                enhanced_path,
                fps=30,
                codec='libx264',
                audio_codec='aac'
            )
            
            # Clean up
            video.close()
            video_with_captions.close()
            video_with_branding.close()
            if video.duration > 60:
                video_with_progress.close()
            final_video.close()
            
            return {
                "success": True,
                "video_path": enhanced_path,
                "metadata": {
                    "original_duration": video.duration,
                    "enhanced_duration": final_video.duration,
                    "captions_added": True,
                    "branding_added": True,
                    "created_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Caption and branding addition failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "original_video"
            }

    async def _generate_captions(self, video_path: str) -> List[Dict]:
        """Generate captions using Whisper AI."""
        try:
            if not self.whisper_model:
                self.whisper_model = whisper.load_model("base")
            
            # Extract audio
            video = VideoFileClip(video_path)
            audio_path = video_path.replace('.mp4', '_audio.wav')
            video.audio.write_audiofile(audio_path)
            video.close()
            
            # Transcribe audio
            result = self.whisper_model.transcribe(audio_path)
            
            # Format captions
            captions = []
            for segment in result["segments"]:
                captions.append({
                    "text": segment["text"],
                    "start": segment["start"],
                    "end": segment["end"]
                })
            
            # Clean up audio file
            os.remove(audio_path)
            
            return captions
            
        except Exception as e:
            logger.error(f"Caption generation failed: {e}")
            return []

    def _add_captions_to_video(self, video: VideoFileClip, captions: List[Dict]) -> VideoFileClip:
        """Add captions to video."""
        if not captions:
            return video
        
        caption_clips = []
        for caption in captions:
            text_clip = TextClip(
                caption["text"],
                fontsize=30,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2
            ).set_start(caption["start"]).set_duration(caption["end"] - caption["start"]).set_position(('center', 'bottom'))
            caption_clips.append(text_clip)
        
        if caption_clips:
            return CompositeVideoClip([video] + caption_clips)
        return video

    def _add_branding_to_video(self, video: VideoFileClip, branding_options: Optional[Dict]) -> VideoFileClip:
        """Add branding to video."""
        try:
            # Create watermark
            watermark = self._create_watermark(branding_options)
            
            # Add watermark to video
            watermarked_video = CompositeVideoClip([video, watermark])
            
            return watermarked_video
            
        except Exception as e:
            logger.error(f"Branding addition failed: {e}")
            return video

    def _create_watermark(self, branding_options: Optional[Dict]) -> TextClip:
        """Create watermark for branding."""
        watermark_text = "Refiloe AI Trainer"
        watermark = TextClip(
            watermark_text,
            fontsize=20,
            color='white',
            font='Arial-Bold',
            stroke_color='black',
            stroke_width=1
        ).set_position(('right', 'top')).set_duration(video.duration)
        
        return watermark

    def _add_progress_bar(self, video: VideoFileClip) -> VideoFileClip:
        """Add progress bar for longer videos."""
        try:
            # Create progress bar
            progress_bar = self._create_progress_bar(video.duration)
            
            # Add to video
            video_with_progress = CompositeVideoClip([video, progress_bar])
            
            return video_with_progress
            
        except Exception as e:
            logger.error(f"Progress bar addition failed: {e}")
            return video

    def _create_progress_bar(self, duration: float) -> VideoFileClip:
        """Create animated progress bar."""
        # This would create an animated progress bar
        # For now, we'll create a simple static one
        progress_text = "Progress"
        progress_clip = TextClip(
            progress_text,
            fontsize=20,
            color='white',
            font='Arial-Bold'
        ).set_position(('left', 'bottom')).set_duration(duration)
        
        return progress_clip

    def _add_ctas_and_end_screens(self, video: VideoFileClip) -> VideoFileClip:
        """Add CTAs and end screens."""
        try:
            # Add CTA overlay
            cta_overlay = self._create_cta_overlay()
            
            # Add end screen
            end_screen = self._create_end_screen()
            
            # Combine with video
            final_video = CompositeVideoClip([video, cta_overlay])
            
            # Add end screen
            final_video = concatenate_videoclips([final_video, end_screen])
            
            return final_video
            
        except Exception as e:
            logger.error(f"CTA and end screen addition failed: {e}")
            return video

    def _create_cta_overlay(self) -> TextClip:
        """Create CTA overlay."""
        cta_text = "Try Refiloe AI Trainer Today!"
        cta_clip = TextClip(
            cta_text,
            fontsize=30,
            color='yellow',
            font='Arial-Bold',
            stroke_color='black',
            stroke_width=2
        ).set_position(('center', 'top')).set_duration(5)
        
        return cta_clip

    def _create_end_screen(self) -> VideoFileClip:
        """Create end screen."""
        end_text = "Thanks for watching!\nSubscribe for more Refiloe content"
        end_clip = TextClip(
            end_text,
            fontsize=40,
            color='white',
            font='Arial-Bold'
        ).set_duration(3).set_position('center')
        
        background = ImageClip(np.zeros((1080, 1920, 3), dtype=np.uint8)).set_duration(3)
        end_video = CompositeVideoClip([background, end_clip])
        
        return end_video

    async def optimize_for_platform(
        self, 
        video_path: str,
        platform: str,
        additional_options: Optional[Dict] = None
    ) -> Dict[str, Union[str, Dict]]:
        """
        Optimize video for specific social media platforms.
        
        Args:
            video_path: Path to the video file
            platform: Target platform (facebook_reels, facebook_feed, stories)
            additional_options: Additional optimization options
            
        Returns:
            Dictionary containing optimized video path and metadata
        """
        try:
            # Get platform settings
            platform_config = self.platform_settings.get(platform, self.platform_settings['facebook_feed'])
            
            # Load video
            video = VideoFileClip(video_path)
            
            # Optimize for platform
            optimized_video = self._optimize_video_for_platform(video, platform_config, additional_options)
            
            # Save optimized video
            optimized_path = video_path.replace('.mp4', f'_{platform}.mp4')
            optimized_video.write_videofile(
                optimized_path,
                fps=30,
                codec='libx264',
                audio_codec='aac'
            )
            
            # Clean up
            video.close()
            optimized_video.close()
            
            return {
                "success": True,
                "video_path": optimized_path,
                "metadata": {
                    "platform": platform,
                    "aspect_ratio": platform_config['aspect_ratio'],
                    "max_duration": platform_config.get('max_duration', 240),
                    "original_duration": video.duration,
                    "optimized_duration": optimized_video.duration,
                    "created_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Platform optimization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "original_video"
            }

    def _optimize_video_for_platform(
        self, 
        video: VideoFileClip, 
        platform_config: Dict, 
        additional_options: Optional[Dict]
    ) -> VideoFileClip:
        """Optimize video for specific platform."""
        try:
            # Get target dimensions
            target_ratio = platform_config['aspect_ratio']
            max_duration = platform_config.get('max_duration', 240)
            
            # Calculate target dimensions
            if target_ratio == (9, 16):  # Vertical
                target_width, target_height = 1080, 1920
            elif target_ratio == (1, 1):  # Square
                target_width, target_height = 1080, 1080
            else:  # Default to 16:9
                target_width, target_height = 1920, 1080
            
            # Resize video
            resized_video = video.resize((target_width, target_height))
            
            # Trim to max duration if needed
            if resized_video.duration > max_duration:
                resized_video = resized_video.subclip(0, max_duration)
            
            # Add safe zones for stories if needed
            if platform_config.get('safe_zone'):
                resized_video = self._add_safe_zones(resized_video, platform_config['safe_zone'])
            
            return resized_video
            
        except Exception as e:
            logger.error(f"Video optimization failed: {e}")
            return video

    def _add_safe_zones(self, video: VideoFileClip, safe_zone_ratio: float) -> VideoFileClip:
        """Add safe zones for stories."""
        try:
            # Create safe zone overlay
            safe_zone_overlay = self._create_safe_zone_overlay(video.size, safe_zone_ratio)
            
            # Add to video
            video_with_safe_zones = CompositeVideoClip([video, safe_zone_overlay])
            
            return video_with_safe_zones
            
        except Exception as e:
            logger.error(f"Safe zone addition failed: {e}")
            return video

    def _create_safe_zone_overlay(self, video_size: Tuple[int, int], safe_zone_ratio: float) -> VideoFileClip:
        """Create safe zone overlay."""
        width, height = video_size
        
        # Calculate safe zone dimensions
        safe_width = int(width * (1 - safe_zone_ratio))
        safe_height = int(height * (1 - safe_zone_ratio))
        
        # Create safe zone indicator
        safe_zone_text = "Safe Zone"
        safe_zone_clip = TextClip(
            safe_zone_text,
            fontsize=20,
            color='red',
            font='Arial-Bold'
        ).set_position(('left', 'top')).set_duration(video.duration)
        
        return safe_zone_clip

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration."""
        try:
            video = VideoFileClip(video_path)
            duration = video.duration
            video.close()
            return duration
        except Exception as e:
            logger.error(f"Failed to get video duration: {e}")
            return 0.0

    async def _record_generic_tutorial(self, page, tutorial_type: str):
        """Record generic tutorial."""
        await page.goto("about:blank")
        await self._add_demo_captions(page, f"Refiloe AI Trainer - {tutorial_type}")
        await page.wait_for_timeout(3000)

    # Error handling and retry logic
    async def _retry_operation(self, operation, max_retries: int = 3, delay: float = 1.0):
        """Retry operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Operation failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
                delay *= 2

    def _create_fallback_content(self, content_type: str) -> str:
        """Create fallback content when video generation fails."""
        fallbacks = {
            "ai_avatar": "static_avatar_image.jpg",
            "screen_recording": "static_screenshot.png",
            "exercise_demo": "static_exercise_image.jpg",
            "animated_explainer": "static_infographic.png",
            "video_script": "template_script.txt"
        }
        return fallbacks.get(content_type, "static_content.jpg")

    # Utility methods
    def _validate_config(self) -> bool:
        """Validate configuration."""
        required_keys = ['did_api_key', 'heygen_api_key', 'openai_api_key']
        return all(key in self.config for key in required_keys)

    def _log_operation(self, operation: str, success: bool, duration: float):
        """Log operation results."""
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"{operation} - {status} - Duration: {duration:.2f}s")

    async def cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")


# Example usage and configuration
async def main():
    """Example usage of VideoGenerator class."""
    
    # Configuration
    config = {
        'did_api_key': 'your_did_api_key',
        'heygen_api_key': 'your_heygen_api_key',
        'openai_api_key': 'your_openai_api_key'
    }
    
    # Initialize Supabase client
    supabase_url = "your_supabase_url"
    supabase_key = "your_supabase_key"
    database = create_client(supabase_url, supabase_key)
    
    # Initialize VideoGenerator
    async with VideoGenerator(config, database) as video_gen:
        
        # Generate AI avatar video
        avatar_result = await video_gen.generate_ai_video_with_avatars(
            script_text="Welcome to Refiloe AI Trainer!",
            avatar_style="professional"
        )
        print("Avatar video result:", avatar_result)
        
        # Generate screen recording tutorial
        tutorial_result = await video_gen.generate_screen_recording_tutorial(
            tutorial_type="whatsapp_demo"
        )
        print("Tutorial result:", tutorial_result)
        
        # Generate exercise demo video
        exercise_result = await video_gen.generate_exercise_demo_video(
            exercise_ids=["ex1", "ex2", "ex3"]
        )
        print("Exercise demo result:", exercise_result)
        
        # Generate animated explainer
        animation_result = await video_gen.generate_animated_explainer(
            content_type="statistics",
            data={"statistics": {"users": 1000, "satisfaction": "95%"}},
            animation_style="kinetic_typography"
        )
        print("Animation result:", animation_result)
        
        # Generate video script
        script_result = await video_gen.generate_video_script(
            video_type="tutorial",
            target_audience="professionals",
            duration=60
        )
        print("Script result:", script_result)
        
        # Add captions and branding
        if avatar_result.get("success"):
            enhanced_result = await video_gen.add_captions_and_branding(
                video_path=avatar_result["video_url"]
            )
            print("Enhanced video result:", enhanced_result)
        
        # Optimize for platform
        if tutorial_result.get("success"):
            optimized_result = await video_gen.optimize_for_platform(
                video_path=tutorial_result["video_path"],
                platform="facebook_reels"
            )
            print("Optimized video result:", optimized_result)


if __name__ == "__main__":
    asyncio.run(main())