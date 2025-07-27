from flask import Flask, request, jsonify
import os
import requests
import hashlib
import hmac

app = Flask(__name__)

# You'll get these from Facebook
VERIFY_TOKEN = "your_verify_token_here"  # You create this
ACCESS_TOKEN = "your_access_token_here"  # Facebook gives you this

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Webhook verification"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge
    return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def handle_message():
    """Handle incoming WhatsApp messages"""
    data = request.get_json()
    
    # Log the message (for testing)
    print("Received:", data)
    
    # Extract message details
    if 'messages' in data['entry'][0]['changes'][0]['value']:
        messages = data['entry'][0]['changes'][0]['value']['messages']
        
        for message in messages:
            phone_number = message['from']
            message_text = message.get('text', {}).get('body', '')
            message_id = message['id']
            
            # For now, just echo the message back
            send_whatsapp_message(phone_number, f"I received: {message_text}")
    
    return jsonify({'status': 'success'})

def send_whatsapp_message(phone_number, message_text):
    """Send message back to WhatsApp"""
    url = f"https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID/messages"
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'messaging_product': 'whatsapp',
        'to': phone_number,
        'text': {'body': message_text}
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
