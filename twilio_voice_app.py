#!/usr/bin/env python3
"""
Clav Voice API - Twilio Backend (SIMPLIFIED)
Uses Twilio's built-in speech recognition (no Whisper needed)
"""

from flask import Flask, request, Response
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twilio Credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

app = Flask(__name__)

# Simple conversation memory
conversation_history = {}

def get_response(user_text, call_sid):
    """Generate response based on what the user said"""
    
    if not user_text or user_text.strip() == "":
        return "I didn't catch that. Can you speak up?"
    
    # Initialize conversation
    if call_sid not in conversation_history:
        conversation_history[call_sid] = {"count": 0}
    
    conversation_history[call_sid]["count"] += 1
    count = conversation_history[call_sid]["count"]
    
    user_lower = user_text.lower().strip()
    
    # Smart responses based on what they say
    if count == 1:
        # First message
        if any(w in user_lower for w in ["hi", "hello", "hey", "test"]):
            return "Hey Henry! The voice API is working! What's up?"
        elif any(w in user_lower for w in ["contrarian", "track record", "backtest"]):
            return "Want to dive into contrarian8888's track record?"
        elif any(w in user_lower for w in ["morgan stanley", "banking", "investing"]):
            return "Let's work on your investment strategy."
        elif any(w in user_lower for w in ["hinge", "dating", "girls"]):
            return "How's the dating app automation going?"
        else:
            return f"You said: {user_text}. What else?"
    else:
        # Follow-up messages
        if "yes" in user_lower:
            return "Great! Tell me more."
        elif "no" in user_lower:
            return "Got it. What else can I help with?"
        elif any(w in user_lower for w in ["thanks", "thank you"]):
            return "Happy to help!"
        elif any(w in user_lower for w in ["bye", "goodbye"]):
            return "Catch you later!"
        else:
            return f"You said: {user_text}. Anything else?"

@app.route("/", methods=['GET'])
def index():
    """Health check"""
    return {
        "status": "online",
        "app": "Clav Voice API",
        "phone": TWILIO_PHONE_NUMBER
    }

@app.route("/voice/incoming", methods=['POST'])
def incoming_call():
    """Handle incoming call - greet and ask for speech"""
    
    call_sid = request.values.get('CallSid', 'unknown')
    from_number = request.values.get('From', 'unknown')
    
    print(f"[{datetime.now()}] Call from {from_number} (SID: {call_sid})")
    
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        response = VoiceResponse()
        
        # Greet
        response.say("Hey Henry! The voice API is live. Speak naturally and I'll respond.", voice='alice')
        
        # Gather speech with Twilio's built-in recognition
        # This is KEY: speechTimeout="auto" lets Twilio auto-detect end of speech
        # numDigits="0" means don't listen for DTMF tones, just speech
        with response.gather(
            num_digits=0,  # Speech only, no tone listening
            action="/voice/respond",  # Route to response endpoint
            method="POST",
            speech_timeout="auto",  # Auto-detect speech end
            language="en-US",  # English US
            max_speech_time=30  # Max 30 seconds
        ) as gather:
            gather.say("Go ahead.", voice='alice')
        
        return Response(str(response), mimetype='application/xml')
    
    except Exception as e:
        print(f"Error in incoming_call: {e}")
        # Fallback
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice">Hey Henry! Speak naturally.</Say>
            <Gather numDigits="0" action="/voice/respond" method="POST" speechTimeout="auto" language="en-US" maxSpeechTime="30">
                <Say voice="alice">Go ahead.</Say>
            </Gather>
        </Response>"""
        return Response(xml, mimetype='application/xml')

@app.route("/voice/respond", methods=['POST'])
def respond_to_speech():
    """Get the transcribed speech from Twilio and respond"""
    
    call_sid = request.values.get('CallSid', 'unknown')
    
    # THIS is key: Twilio provides SpeechResult after gathering speech
    speech_result = request.values.get('SpeechResult', '').strip()
    confidence = request.values.get('Confidence', '0')
    
    print(f"[{datetime.now()}] Speech from {call_sid}")
    print(f"  Text: {speech_result}")
    print(f"  Confidence: {confidence}")
    
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        # Get response to what they said
        response_text = get_response(speech_result, call_sid)
        
        print(f"  Response: {response_text}")
        
        # Create response with TwiML
        response = VoiceResponse()
        response.say(response_text, voice='alice')
        
        # Loop back - ask for next input
        with response.gather(
            num_digits=0,
            action="/voice/respond",
            method="POST",
            speech_timeout="auto",
            language="en-US",
            max_speech_time=30
        ) as gather:
            gather.say("Go ahead.", voice='alice')
        
        return Response(str(response), mimetype='application/xml')
    
    except Exception as e:
        print(f"Error in respond_to_speech: {e}")
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice">Sorry, technical issue. Speak again.</Say>
            <Gather numDigits="0" action="/voice/respond" method="POST" speechTimeout="auto" language="en-US" maxSpeechTime="30">
                <Say voice="alice">Go ahead.</Say>
            </Gather>
        </Response>"""
        return Response(xml, mimetype='application/xml')

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting Clav Voice API on port {port}")
    print(f"Twilio Phone: {TWILIO_PHONE_NUMBER}")
    print(f"Using Twilio's built-in speech recognition")
    app.run(host='0.0.0.0', port=port, debug=False)
