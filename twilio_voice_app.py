#!/usr/bin/env python3
"""
Clav Voice API - SIMPLIFIED VERSION
Using Twilio Record + transcription callback
"""

from flask import Flask, request, Response
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

app = Flask(__name__)

conversation = {}

def get_response(text, call_sid):
    """Simple response logic"""
    if call_sid not in conversation:
        conversation[call_sid] = 0
    conversation[call_sid] += 1
    
    text_lower = (text or "").lower()
    
    # Just echo back what they said
    if conversation[call_sid] == 1:
        if any(w in text_lower for w in ["hi", "hello", "hey", "test"]):
            return "Hey Henry! Voice API is working. What do you want to talk about?"
        elif "contrarian" in text_lower:
            return "Want to analyze contrarian8888?"
        elif "bye" in text_lower:
            return "Talk later!"
        else:
            return f"You said {text}. Tell me more."
    else:
        if "yes" in text_lower:
            return "Great! What else?"
        elif "no" in text_lower:
            return "Got it. Next question?"
        elif "bye" in text_lower:
            return "Goodbye!"
        else:
            return "Anything else?"

@app.route("/", methods=['GET'])
def index():
    return {"status": "ok", "phone": TWILIO_PHONE_NUMBER}

@app.route("/voice/incoming", methods=['POST'])
def incoming():
    """Initial greeting and record"""
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        resp = VoiceResponse()
        resp.say("Hey Henry, voice API is live. Speak now.", voice='alice')
        
        # Just use Record + transcription callback
        resp.record(
            max_speech_time=20,
            transcribe=True,
            transcribe_callback="/voice/transcribed",
            action="/voice/next",  # Fallback if transcription fails
            method="POST"
        )
        
        return Response(str(resp), mimetype='application/xml')
    except Exception as e:
        print(f"Error: {e}")
        return Response('<?xml version="1.0"?><Response><Say>Error</Say></Response>', mimetype='application/xml')

@app.route("/voice/transcribed", methods=['POST'])
def transcribed():
    """Handle transcribed result from Twilio"""
    try:
        call_sid = request.values.get('CallSid', '')
        transcript = request.values.get('TranscriptionText', '').strip()
        
        print(f"[{datetime.now()}] Transcribed from {call_sid}: {transcript}")
        
        from twilio.twiml.voice_response import VoiceResponse
        
        response_text = get_response(transcript, call_sid)
        
        resp = VoiceResponse()
        resp.say(response_text, voice='alice')
        resp.record(
            max_speech_time=20,
            transcribe=True,
            transcribe_callback="/voice/transcribed",
            action="/voice/next",
            method="POST"
        )
        
        return Response(str(resp), mimetype='application/xml')
    except Exception as e:
        print(f"Transcribed error: {e}")
        return Response('<?xml version="1.0"?><Response><Say>Error processing</Say></Response>', mimetype='application/xml')

@app.route("/voice/next", methods=['POST'])
def next_recording():
    """Fallback if transcription doesn't work"""
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        resp = VoiceResponse()
        resp.say("Speak again", voice='alice')
        resp.record(
            max_speech_time=20,
            transcribe=True,
            transcribe_callback="/voice/transcribed",
            action="/voice/next",
            method="POST"
        )
        
        return Response(str(resp), mimetype='application/xml')
    except Exception as e:
        print(f"Next error: {e}")
        return Response('<?xml version="1.0"?><Response><Say>Error</Say></Response>', mimetype='application/xml')

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
