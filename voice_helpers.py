# voice_helpers.py
import os
import requests
import io
import logging
from typing import Dict, Optional
from pydub import AudioSegment

# Set up logging
log = logging.getLogger(__name__)

class VoiceProcessor:
    def __init__(self):
        self.whatsapp_token = os.getenv('ACCESS_TOKEN')  # Note: Changed from WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = os.getenv('PHONE_NUMBER_ID')  # Note: Changed from WHATSAPP_PHONE_NUMBER_ID
        
        # Only initialize OpenAI if you have the key
        self.openai_client = None
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_key)
                log.info("OpenAI client initialized successfully")
            except ImportError:
                log.warning("OpenAI not installed - voice features disabled")
    
    def download_whatsapp_media(self, media_id: str) -> bytes:
        """Download voice note from WhatsApp - FIXED VERSION"""
        try:
            # Step 1: Get media URL from WhatsApp
            url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {'Authorization': f'Bearer {self.whatsapp_token}'}
            
            log.info(f"Fetching media info from: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            media_info = response.json()
            log.info(f"Media info response: {media_info}")
            
            # Step 2: Get the actual media URL
            # The response should contain a 'url' field
            media_url = media_info.get('url')
            
            if not media_url:
                # Log what we actually got
                log.error(f"No URL in media info. Keys available: {list(media_info.keys())}")
                log.error(f"Full response: {media_info}")
                raise Exception(f"No URL found in media response. Got keys: {list(media_info.keys())}")
            
            # Step 3: Download the actual audio file
            log.info(f"Downloading audio from: {media_url[:50]}...")
            audio_response = requests.get(media_url, headers=headers)
            audio_response.raise_for_status()
            
            audio_content = audio_response.content
            log.info(f"Downloaded audio: {len(audio_content)} bytes")
            
            return audio_content
            
        except requests.exceptions.HTTPError as e:
            log.error(f"HTTP error downloading media: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to download media: HTTP {e.response.status_code}")
        except Exception as e:
            log.error(f"Failed to download media: {str(e)}")
            raise
    
    def transcribe_audio(self, audio_buffer: bytes) -> str:
        """Convert voice to text using OpenAI Whisper"""
        if not self.openai_client:
            raise Exception("OpenAI not configured for voice transcription")
        
        try:
            # WhatsApp sends audio in OGG format, but we need to handle it properly
            # Create a file-like object
            audio_file = io.BytesIO(audio_buffer)
            
            # Try to convert from OGG to a format OpenAI handles better
            try:
                # Load the audio using pydub
                audio = AudioSegment.from_file(audio_file, format="ogg")
                
                # Convert to MP3 (which OpenAI handles well)
                mp3_buffer = io.BytesIO()
                audio.export(mp3_buffer, format="mp3")
                mp3_buffer.seek(0)
                mp3_buffer.name = "audio.mp3"
                
                # Use the MP3 for transcription
                transcription_file = mp3_buffer
                log.info("Converted OGG to MP3 for transcription")
            except Exception as conv_error:
                log.warning(f"Could not convert audio format: {conv_error}. Using original.")
                audio_file.seek(0)
                audio_file.name = "audio.ogg"
                transcription_file = audio_file
            
            # Transcribe
            log.info("Starting transcription with Whisper...")
            transcription = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=transcription_file,
                language="en"  # You can make this dynamic later
            )
            
            text = transcription.text
            log.info(f"Transcription successful: {text[:50]}...")
            return text
            
        except Exception as e:
            log.error(f"Transcription failed: {str(e)}")
            raise
    
    def text_to_speech(self, text: str) -> bytes:
        """Convert text to voice using OpenAI TTS"""
        if not self.openai_client:
            raise Exception("OpenAI not configured for text-to-speech")
        
        try:
            log.info(f"Converting text to speech: {text[:50]}...")
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice="nova",  # Female voice, friendly tone
                input=text
            )
            
            # Get audio data
            audio_data = response.content
            
            # Convert to OGG format for WhatsApp
            try:
                # Convert MP3 to OGG with Opus codec (WhatsApp's preferred format)
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
                
                output_buffer = io.BytesIO()
                audio.export(output_buffer, format="ogg", codec="libopus")
                output_buffer.seek(0)
                
                log.info(f"Converted to OGG: {output_buffer.tell()} bytes")
                return output_buffer.getvalue()
            except Exception as e:
                log.warning(f"Could not convert to OGG, using MP3: {e}")
                return audio_data
                
        except Exception as e:
            log.error(f"Text-to-speech failed: {str(e)}")
            raise
    
    def send_voice_note(self, phone_number: str, audio_buffer: bytes) -> Dict:
        """Send voice note via WhatsApp"""
        try:
            # Upload audio to WhatsApp
            upload_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/media"
            
            files = {
                'file': ('voice_note.ogg', audio_buffer, 'audio/ogg; codecs=opus'),
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'type': 'audio'
            }
            
            headers = {
                'Authorization': f'Bearer {self.whatsapp_token}'
            }
            
            log.info(f"Uploading audio to WhatsApp...")
            upload_response = requests.post(
                upload_url, 
                headers=headers, 
                data=data, 
                files=files
            )
            
            if upload_response.status_code != 200:
                log.error(f"Upload failed: {upload_response.status_code} - {upload_response.text}")
                raise Exception(f"Failed to upload audio: {upload_response.text}")
            
            upload_result = upload_response.json()
            log.info(f"Upload response: {upload_result}")
            
            if 'id' not in upload_result:
                raise Exception(f"Failed to upload audio: {upload_result}")
            
            media_id = upload_result['id']
            log.info(f"Audio uploaded with ID: {media_id}")
            
            # Send the voice note message
            message_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
            
            message_data = {
                'messaging_product': 'whatsapp',
                'to': phone_number,
                'type': 'audio',
                'audio': {
                    'id': media_id
                }
            }
            
            log.info(f"Sending voice note to {phone_number}...")
            message_response = requests.post(
                message_url,
                headers={
                    'Authorization': f'Bearer {self.whatsapp_token}',
                    'Content-Type': 'application/json'
                },
                json=message_data
            )
            
            if message_response.status_code != 200:
                log.error(f"Send failed: {message_response.status_code} - {message_response.text}")
                raise Exception(f"Failed to send voice note: {message_response.text}")
            
            result = message_response.json()
            log.info(f"Voice note sent successfully: {result}")
            return result
            
        except Exception as e:
            log.error(f"Send voice note error: {str(e)}")
            raise
    
    def handle_voice_note_with_fallback(self, message: Dict, phone_number: str) -> Dict:
        """Handle voice note with proper error handling"""
        try:
            # Extract audio ID from message
            audio_data = message.get('audio', {})
            audio_id = audio_data.get('id')
            
            if not audio_id:
                log.error(f"No audio ID in message. Audio data: {audio_data}")
                raise Exception("No audio ID found in message")
            
            log.info(f"Processing voice note with ID: {audio_id}")
            
            # Download the audio
            audio_buffer = self.download_whatsapp_media(audio_id)
            
            # Check size
            if len(audio_buffer) > 16 * 1024 * 1024:
                raise Exception("Audio file too large (over 16MB)")
            
            # Transcribe
            text = self.transcribe_audio(audio_buffer)
            
            if not text or len(text.strip()) == 0:
                raise Exception("Could not understand the audio - transcription was empty")
            
            return {
                'text': text,
                'success': True,
                'should_reply_with_voice': True
            }
            
        except Exception as e:
            log.error(f"Voice processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
