# voice_helpers.py
import os
import requests
from openai import OpenAI
import io
import base64
from pydub import AudioSegment

class VoiceProcessor:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.whatsapp_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    def download_whatsapp_media(self, media_id):
        """Download voice note from WhatsApp"""
        # Get media URL
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        headers = {
            'Authorization': f'Bearer {self.whatsapp_token}'
        }
        
        response = requests.get(url, headers=headers)
        media_info = response.json()
        
        # Download the actual file
        audio_response = requests.get(media_info['url'], headers=headers)
        
        return audio_response.content
    
    def transcribe_audio(self, audio_buffer):
        """Convert voice to text using OpenAI Whisper"""
        try:
            # Create a file-like object from the buffer
            audio_file = io.BytesIO(audio_buffer)
            audio_file.name = "audio.ogg"  # WhatsApp usually sends .ogg files
            
            # Transcribe using OpenAI Whisper
            transcription = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"  # You can add Afrikaans "af" support later
            )
            
            return transcription.text
        except Exception as e:
            print(f"Transcription error: {str(e)}")
            raise
    
    def text_to_speech(self, text):
        """Convert text to voice using OpenAI TTS"""
        try:
            # Generate speech
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice="nova",  # Female voice, friendly tone
                input=text
            )
            
            # Get audio data
            audio_data = response.content
            
            # Convert to format WhatsApp accepts (OGG with Opus codec)
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            
            # Export as OGG
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="ogg", codec="libopus")
            
            return output_buffer.getvalue()
        except Exception as e:
            print(f"Text-to-speech error: {str(e)}")
            raise
    
    def send_voice_note(self, phone_number, audio_buffer):
        """Send voice note via WhatsApp"""
        try:
            # First, upload the audio to WhatsApp
            upload_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/media"
            
            files = {
                'file': ('voice_note.ogg', audio_buffer, 'audio/ogg'),
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'type': 'audio'
            }
            
            headers = {
                'Authorization': f'Bearer {self.whatsapp_token}'
            }
            
            # Upload the audio
            upload_response = requests.post(
                upload_url, 
                headers=headers, 
                data=data, 
                files=files
            )
            upload_result = upload_response.json()
            
            if 'id' not in upload_result:
                raise Exception(f"Failed to upload audio: {upload_result}")
            
            media_id = upload_result['id']
            
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
            
            message_response = requests.post(
                message_url,
                headers={
                    'Authorization': f'Bearer {self.whatsapp_token}',
                    'Content-Type': 'application/json'
                },
                json=message_data
            )
            
            return message_response.json()
        except Exception as e:
            print(f"Send voice note error: {str(e)}")
            raise
