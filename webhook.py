from flask import Flask, request, jsonify
import os
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Environment variables
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'texts_to_refiloe_radebe')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Simple in-memory storage
client_contexts = {}

@app.route('/')
def home():
    return "Personal Trainer AI Assistant is running! 💪 (Minimal Version)"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Webhook verification for WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    print(f"Verification attempt - Mode: {mode}, Token: {token}")
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge
    else:
        print("Webhook verification failed!")
        return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def handle_message():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        print("=== FULL WEBHOOK DATA ===")
        print(json.dumps(data, indent=2))
        print("=== END WEBHOOK DATA ===")
        
        # Debug: Check what's in the value object
        if data.get('entry') and data['entry'][0].get('changes'):
            value = data['entry'][0]['changes'][0].get('value', {})
            print(f"=== VALUE OBJECT KEYS: {list(value.keys())} ===")
            
            if 'messages' in value:
                print(f"=== FOUND MESSAGES: {value['messages']} ===")
            else:
                print("=== NO MESSAGES KEY FOUND ===")
                
            if 'statuses' in value:
                print(f"=== FOUND STATUSES: {value['statuses']} ===")
        
        # Check if this is a message
        if (data.get('entry') and 
            data['entry'][0].get('changes') and 
            data['entry'][0]['changes'][0].get('value', {}).get('messages')):
            
            messages = data['entry'][0]['changes'][0]['value']['messages']
            
            for message in messages:
                phone_number = message['from']
                message_id = message['id']
                
                # Handle text messages
                if 'text' in message:
                    message_text = message['text']['body']
                    print(f"Text message from {phone_number}: {message_text}")
                    
                    # Process with Claude AI
                    response = process_message_with_claude(phone_number, message_text)
                    send_whatsapp_message(phone_number, response)
                
                # Handle voice messages (placeholder for now)
                elif 'audio' in message or 'voice' in message:
                    print(f"Voice message from {phone_number}")
                    send_whatsapp_message(phone_number, "Voice processing will be added soon! Please send a text message for now.")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_message_with_claude(phone_number, message_text):
    """Process message using Claude API with direct HTTP requests"""
    
    if not ANTHROPIC_API_KEY:
        return "Hi! I'm your AI assistant for personal trainers. I can help with scheduling, invoicing, and client management. (AI processing is being set up)"
    
    try:
        # Get or create client context
        if phone_number not in client_contexts:
            client_contexts[phone_number] = {
                'messages': [],
                'created_at': datetime.now().isoformat()
            }
        
        # Add message to context
        client_contexts[phone_number]['messages'].append({
            'timestamp': datetime.now().isoformat(),
            'message': message_text,
            'type': 'user'
        })
        
        # Keep only last 5 messages for context
        if len(client_contexts[phone_number]['messages']) > 5:
            client_contexts[phone_number]['messages'] = client_contexts[phone_number]['messages'][-5:]
        
        # Build conversation history
        conversation_history = "\n".join([
            f"Client: {msg['message']}" for msg in client_contexts[phone_number]['messages'][-3:]
            if msg['type'] == 'user'
        ])
        
        # Create Claude prompt
        system_prompt = """You are an AI virtual assistant for personal trainers and fitness professionals. Help with:

- CLIENT SCHEDULING: Booking, rescheduling, cancellations
- INVOICING: Creating invoices, payment reminders  
- COLLECTIONS: Following up on payments professionally
- CLIENT COMMUNICATION: Professional responses, motivation
- BASIC ADMIN: Task management, appointment tracking

Keep responses concise for WhatsApp. Be professional but friendly.

Recent conversation:
{conversation_history}

Respond to the latest message:"""

        # Call Claude API directly with simpler format
        claude_url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        # Simpler prompt for testing
        simple_prompt = f"You are a helpful assistant for personal trainers. The client said: '{message_text}'. Give a brief, helpful response about personal training business."
        
        data = {
            "model": "claude-3-haiku-20240307",  # Using faster, cheaper model for testing
            "max_tokens": 200,
            "messages": [
                {"role": "user", "content": simple_prompt}
            ]
        }
        
        print(f"Calling Claude API with data: {json.dumps(data, indent=2)}")
        response = requests.post(claude_url, headers=headers, json=data)
        print(f"Claude API response status: {response.status_code}")
        print(f"Claude API response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['content'][0]['text']
            print(f"AI Response: {ai_response}")
            
            # Add AI response to context
            client_contexts[phone_number]['messages'].append({
                'timestamp': datetime.now().isoformat(),
                'message': ai_response,
                'type': 'assistant'
            })
            
            return ai_response
        else:
            print(f"Claude API error: {response.status_code} - {response.text}")
            return "I'm having trouble processing your request. Please try again in a moment."
        
    except Exception as e:
        print(f"Error with Claude API: {str(e)}")
        
        # Smart fallback responses based on keywords
        message_lower = message_text.lower()
        
        if any(word in message_lower for word in ['schedule', 'booking', 'appointment', 'session']):
            return "I can help with scheduling! For now, I recommend using a simple calendar system. Would you like tips on managing client appointments?"
        
        elif any(word in message_lower for word in ['invoice', 'payment', 'bill', 'money']):
            return "For invoicing, I suggest creating a simple template with: Client name, services provided, amount due, and payment terms. Would you like help with payment follow-up strategies?"
        
        elif any(word in message_lower for word in ['client', 'customer']):
            return "Great question about client management! As a personal trainer, clear communication and consistent follow-up are key. What specific client situation are you dealing with?"
        
        else:
            return "Hi! I'm your AI assistant for personal training business. I can help with scheduling, invoicing, client management, and more. What would you like assistance with?"

def send_whatsapp_message(phone_number, message_text):
    """Send message back to WhatsApp"""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("Missing ACCESS_TOKEN or PHONE_NUMBER_ID")
        return
    
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'messaging_product': 'whatsapp',
        'to': phone_number,
        'text': {'body': message_text}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"WhatsApp API response: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
        return None

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'claude_api': 'connected' if ANTHROPIC_API_KEY else 'not configured',
        'whatsapp_api': 'configured' if ACCESS_TOKEN and PHONE_NUMBER_ID else 'not configured',
        'version': 'minimal'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
