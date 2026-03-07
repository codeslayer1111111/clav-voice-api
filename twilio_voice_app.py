#!/usr/bin/env python3
"""
Clav Voice API - Twilio Backend
Handles incoming calls, transcribes audio, responds with voice
Deploy to Railway, Heroku, or similar
"""

from flask import Flask, request, Response
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twilio Credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Validate credentials
if not TWILIO_ACCOUNT_SID:
    print("ERROR: TWILIO_ACCOUNT_SID not set in environment variables")
if not TWILIO_AUTH_TOKEN:
    print("ERROR: TWILIO_AUTH_TOKEN not set in environment variables")

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Conversation memory
conversation_history = {}

def get_response(user_input, call_sid):
    """Generate a contextual response based on user input"""
    
    # Initialize conversation if new
    if call_sid not in conversation_history:
        conversation_history[call_sid] = {
            "messages": [],
            "started": datetime.now().isoformat(),
            "count": 0
        }
    
    # Increment message count
    conversation_history[call_sid]["count"] += 1
    msg_count = conversation_history[call_sid]["count"]
    
    # Store user message
    conversation_history[call_sid]["messages"].append({
        "role": "user",
        "text": user_input,
        "time": datetime.now().isoformat()
    })
    
    user_lower = user_input.lower().strip()
    
    # Response logic - first message
    if msg_count == 1:
        if any(word in user_lower for word in ["hi", "hello", "hey"]):
            response = "Hey Henry! Good to hear from you. What's on your mind today?"
        elif any(word in user_lower for word in ["contrarian", "track record", "backtest"]):
            response = "Want to talk about contrarian8888's performance? I've got the data."
        elif any(word in user_lower for word in ["morgan stanley", "networking", "banking"]):
            response = "Let's work on your Morgan Stanley strategy. What do you want to focus on?"
        elif any(word in user_lower for word in ["hinge", "dating"]):
            response = "How's the Hinge automation going? Any updates?"
        else:
            response = f"You said: {user_input}. What do you want to discuss?"
    
    # Follow-up responses
    elif "yes" in user_lower or "yeah" in user_lower:
        response = "Great. What would you like to know?"
    
    elif "no" in user_lower or "nope" in user_lower:
        response = "Understood. Anything else I can help with?"
    
    elif any(word in user_lower for word in ["thanks", "thank you", "thanks buddy"]):
        response = "Anytime! Anything else?"
    
    elif any(word in user_lower for word in ["bye", "goodbye", "talk later", "see you"]):
        response = "Catch you later, Henry. Talk soon!"
    
    else:
        # Generic echo response
        response = f"Interesting. Tell me more about that."
    
    # Store response
    conversation_history[call_sid]["messages"].append({
        "role": "assistant",
        "text": response,
        "time": datetime.now().isoformat()
    })
    
    return response

@app.route("/", methods=['GET'])
def index():
    """Health check"""
    return {
        "status": "healthy",
        "app": "Clav Voice API",
        "phone": TWILIO_PHONE_NUMBER,
        "ready": True,
        "timestamp": datetime.now().isoformat()
    }

@app.route("/voice/incoming", methods=['GET', 'POST'])
def incoming_call():
    """Handle incoming Twilio voice calls"""
    
    call_sid = request.values.get('CallSid', 'unknown')
    from_number = request.values.get('From', 'unknown')
    
    print(f"[{datetime.now()}] Incoming call from {from_number} (SID: {call_sid})")
    
    try:
        # Import here to avoid issues on non-audio systems
        from twilio.twiml.voice_response import VoiceResponse
        
        response = VoiceResponse()
        
        # Greet the caller
        response.say("Hey Henry, I'm listening. Go ahead and speak.", voice='alice')
        
        # Record caller's voice
        response.record(
            max_speech_time=30,
            action="/voice/transcribe",
            method="POST",
            speech_timeout="auto"
        )
        
        return Response(str(response), mimetype='application/xml')
    
    except Exception as e:
        print(f"Error in incoming_call: {e}")
        # Fallback XML response
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice">Hey Henry, I am listening. Go ahead and speak.</Say>
            <Record maxSpeechTime="30" action="/voice/transcribe" method="POST" speechTimeout="auto"/>
        </Response>"""
        return Response(xml, mimetype='application/xml')

@app.route("/voice/transcribe", methods=['POST'])
def transcribe_and_respond():
    """Transcribe recorded audio and generate response"""
    
    call_sid = request.values.get('CallSid', 'unknown')
    recording_url = request.values.get('RecordingUrl', '')
    speech_result = request.values.get('SpeechResult', '')
    
    print(f"[{datetime.now()}] Processing for call {call_sid}")
    
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        # Twilio provides speech_result if speech recognition is enabled
        # Otherwise we'd need to download and transcribe, but that's complex on cloud
        user_text = speech_result if speech_result else "I didn't catch that. Can you repeat?"
        
        if user_text and user_text != "I didn't catch that. Can you repeat?":
            print(f"Transcribed: {user_text}")
        
        # Generate response
        response_text = get_response(user_text, call_sid)
        print(f"Response: {response_text}")
        
        # Create TwiML response
        response = VoiceResponse()
        response.say(response_text, voice='alice')
        
        # Ask for next input
        response.record(
            max_speech_time=30,
            action="/voice/transcribe",
            method="POST",
            speech_timeout="auto"
        )
        
        return Response(str(response), mimetype='application/xml')
    
    except Exception as e:
        print(f"Error in transcribe_and_respond: {e}")
        # Fallback response
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice">Sorry, there was a technical issue. Please try again.</Say>
            <Record maxSpeechTime="30" action="/voice/transcribe" method="POST" speechTimeout="auto"/>
        </Response>"""
        return Response(xml, mimetype='application/xml')

@app.route("/health", methods=['GET'])
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting Clav Voice API on port {port}")
    print(f"Twilio Phone: {TWILIO_PHONE_NUMBER}")
    app.run(host='0.0.0.0', port=port, debug=False)
