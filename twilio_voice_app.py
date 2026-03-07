#!/usr/bin/env python3
"""
Clav Voice API - Twilio Backend (FIXED VERSION)
Properly handles audio transcription using Whisper
"""

from flask import Flask, request, Response
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import subprocess
import tempfile
from base64 import b64encode

# Load environment variables
load_dotenv()

# Twilio Credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Twilio Auth
TWILIO_AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Conversation memory
conversation_history = {}

def download_and_transcribe_audio(recording_url):
    """Download Twilio recording and transcribe using Whisper"""
    try:
        # Download audio file with Twilio auth
        response = requests.get(recording_url + ".wav", auth=TWILIO_AUTH, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to download audio: {response.status_code}")
            return None
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        print(f"Downloaded audio to {tmp_path}, size: {len(response.content)} bytes")
        
        # Transcribe using Whisper
        try:
            result = subprocess.run(
                ["whisper", tmp_path, "--model", "tiny", "--language", "en", "--output_format", "json", "-o", "/tmp/"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            json_file = tmp_path.replace('.wav', '.json')
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    transcription = data.get('text', '').strip()
                os.remove(json_file)
                print(f"Transcribed: {transcription}")
                return transcription if transcription else None
            else:
                print(f"Transcription file not found: {json_file}")
                print(f"Whisper output: {result.stderr}")
                return None
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    except Exception as e:
        print(f"Error downloading/transcribing audio: {e}")
        return None

def get_response(user_text, call_sid):
    """Generate response based on user input"""
    
    if not user_text or user_text.strip() == "":
        return "I didn't catch that. Can you speak up and try again?"
    
    # Initialize conversation
    if call_sid not in conversation_history:
        conversation_history[call_sid] = {
            "messages": [],
            "started": datetime.now().isoformat(),
            "count": 0
        }
    
    conversation_history[call_sid]["count"] += 1
    conversation_history[call_sid]["messages"].append({
        "role": "user",
        "text": user_text
    })
    
    user_lower = user_text.lower().strip()
    count = conversation_history[call_sid]["count"]
    
    # First message responses
    if count == 1:
        if any(word in user_lower for word in ["hi", "hello", "hey"]):
            return "Hey Henry! What's up?"
        elif any(word in user_lower for word in ["contrarian", "track record"]):
            return "Want to analyze contrarian8888's picks?"
        elif any(word in user_lower for word in ["morgan stanley", "banking"]):
            return "Let's work on your investment banking strategy."
        elif any(word in user_lower for word in ["hinge", "dating"]):
            return "How's the dating automation going?"
        else:
            return f"You said: {user_text}. Tell me more."
    
    # Follow-up responses
    elif "yes" in user_lower:
        return "Great! What's your next question?"
    elif "no" in user_lower:
        return "Got it. Anything else?"
    elif any(word in user_lower for word in ["thanks", "thank you"]):
        return "Happy to help! Anything else?"
    elif any(word in user_lower for word in ["bye", "goodbye", "later"]):
        return "Catch you later, Henry!"
    else:
        return "Interesting. Tell me more about that."

@app.route("/", methods=['GET'])
def index():
    """Health check"""
    return {
        "status": "healthy",
        "app": "Clav Voice API",
        "phone": TWILIO_PHONE_NUMBER,
        "ready": True
    }

@app.route("/voice/incoming", methods=['POST'])
def incoming_call():
    """Handle incoming Twilio voice calls"""
    
    call_sid = request.values.get('CallSid', 'unknown')
    from_number = request.values.get('From', 'unknown')
    
    print(f"[{datetime.now()}] Incoming call from {from_number} (SID: {call_sid})")
    
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        response = VoiceResponse()
        response.say("Hey Henry, I'm listening. Go ahead and speak.", voice='alice')
        response.record(
            max_speech_time=30,
            action="/voice/transcribe",
            method="POST",
            speech_timeout="auto"
        )
        
        return Response(str(response), mimetype='application/xml')
    
    except Exception as e:
        print(f"Error in incoming_call: {e}")
        xml = """<?xml version="1.0" encoding="UTF-8"?>
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
    
    print(f"[{datetime.now()}] Transcribing for call {call_sid}")
    print(f"Recording URL: {recording_url}")
    
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        # Download and transcribe the audio
        user_text = None
        if recording_url:
            user_text = download_and_transcribe_audio(recording_url)
        
        if not user_text:
            user_text = "I didn't catch that."
        
        print(f"Transcribed: {user_text}")
        
        # Generate response
        response_text = get_response(user_text, call_sid)
        print(f"Response: {response_text}")
        
        # Create TwiML response
        response = VoiceResponse()
        response.say(response_text, voice='alice')
        response.record(
            max_speech_time=30,
            action="/voice/transcribe",
            method="POST",
            speech_timeout="auto"
        )
        
        return Response(str(response), mimetype='application/xml')
    
    except Exception as e:
        print(f"Error in transcribe_and_respond: {e}")
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice">Sorry, there was a technical issue. Please try again.</Say>
            <Record maxSpeechTime="30" action="/voice/transcribe" method="POST" speechTimeout="auto"/>
        </Response>"""
        return Response(xml, mimetype='application/xml')

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting Clav Voice API on port {port}")
    print(f"Twilio Phone: {TWILIO_PHONE_NUMBER}")
    app.run(host='0.0.0.0', port=port, debug=False)
