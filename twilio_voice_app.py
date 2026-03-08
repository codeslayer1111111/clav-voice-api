#!/usr/bin/env python3
"""
Clav Voice API - ULTRA SIMPLIFIED
Single endpoint handling everything
"""

from flask import Flask, request, Response
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
app = Flask(__name__)

conversation = {}

def get_response(text, call_sid):
    """Generate response"""
    if call_sid not in conversation:
        conversation[call_sid] = 0
    conversation[call_sid] += 1
    
    text_lower = (text or "").lower().strip()
    
    print(f"[{datetime.now()}] Response gen: call={call_sid}, msg={conversation[call_sid]}, text='{text}'")
    
    if conversation[call_sid] == 1:
        if any(w in text_lower for w in ["hi", "hello", "hey", "test", "hey"]):
            return "Hey Henry! The API is working live. What do you want to talk about?"
        elif "contrarian" in text_lower:
            return "Want to analyze contrarian 8888's track record?"
        elif "investing" in text_lower or "stocks" in text_lower:
            return "Let's talk about investing strategy."
        else:
            return f"You said: {text}. Tell me more."
    else:
        if "yes" in text_lower:
            return "Great! What's your next question?"
        elif "no" in text_lower:
            return "Understood. Anything else?"
        else:
            return "Got it. What else would you like to discuss?"

@app.route("/", methods=['GET'])
def health():
    return {"status": "online", "phone": TWILIO_PHONE_NUMBER}

@app.route("/voice/incoming", methods=['POST'])
def incoming():
    """Answer call and record"""
    call_sid = request.values.get('CallSid', 'unknown')
    print(f"[{datetime.now()}] INCOMING CALL: {call_sid}")
    
    try:
        from twilio.twiml.voice_response import VoiceResponse
        resp = VoiceResponse()
        resp.say("Hey Henry, the voice API is live. Speak now.", voice='alice')
        
        # Record with transcription and callback to same endpoint
        resp.record(
            max_speech_time=20,
            action="/voice/process",
            method="POST",
            transcribe=True
        )
        
        return Response(str(resp), mimetype='application/xml')
    except Exception as e:
        print(f"Error in incoming: {e}")
        return Response('<?xml version="1.0"?><Response><Say>Error</Say></Response>', mimetype='application/xml')

@app.route("/voice/process", methods=['POST'])
def process_speech():
    """Handle recorded audio + transcription"""
    call_sid = request.values.get('CallSid', 'unknown')
    
    # Try to get transcription
    transcript = request.values.get('TranscriptionText', '').strip()
    has_transcription = request.values.get('TranscriptionStatus', '').lower() == 'completed'
    recording_url = request.values.get('RecordingUrl', '')
    
    print(f"[{datetime.now()}] PROCESS: call={call_sid}")
    print(f"  TranscriptionStatus: {request.values.get('TranscriptionStatus', 'none')}")
    print(f"  TranscriptionText: '{transcript}'")
    print(f"  RecordingUrl: {recording_url}")
    print(f"  All params: {dict(request.values)}")
    
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        # Determine what user said
        user_text = ""
        if transcript:
            user_text = transcript
            print(f"  Using transcription: {user_text}")
        else:
            user_text = "I didn't catch that clearly"
            print(f"  No transcription, using fallback")
        
        # Get response
        response_text = get_response(user_text, call_sid)
        print(f"  Response: {response_text}")
        
        # Send response and loop
        resp = VoiceResponse()
        resp.say(response_text, voice='alice')
        resp.say("Speak again.", voice='alice')
        resp.record(
            max_speech_time=20,
            action="/voice/process",
            method="POST",
            transcribe=True
        )
        
        return Response(str(resp), mimetype='application/xml')
    except Exception as e:
        print(f"Error in process: {e}")
        import traceback
        traceback.print_exc()
        return Response('<?xml version="1.0"?><Response><Say>Error</Say></Response>', mimetype='application/xml')

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
