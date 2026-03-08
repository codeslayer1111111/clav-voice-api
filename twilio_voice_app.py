#!/usr/bin/env python3
"""
Clav Voice API - WITH CLAUDE AI
Actually answers questions, not just generic responses
"""

from flask import Flask, request, Response
import os
from datetime import datetime
from dotenv import load_dotenv
import anthropic

load_dotenv()

TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

app = Flask(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

conversation = {}

def get_smart_response(text, call_sid):
    """Use Claude to generate intelligent responses"""
    
    if call_sid not in conversation:
        conversation[call_sid] = []
    
    # Add user message to conversation history
    conversation[call_sid].append({
        "role": "user",
        "content": text
    })
    
    try:
        # Call Claude with conversation history
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            system="You are Henry's personal AI assistant named Clav. You're sharp, efficient, and helpful. Keep responses brief and natural for phone calls (1-2 sentences max). Answer questions directly and conversationally.",
            messages=conversation[call_sid]
        )
        
        assistant_message = response.content[0].text
        
        # Add assistant response to history
        conversation[call_sid].append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Keep conversation history limited to last 10 messages
        if len(conversation[call_sid]) > 20:
            conversation[call_sid] = conversation[call_sid][-20:]
        
        return assistant_message
    
    except Exception as e:
        print(f"Claude error: {e}")
        return "Sorry, I had a technical issue. Can you repeat that?"

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
        resp.say("Hey Henry, I'm Clav. Your personal voice assistant is live. Go ahead and ask me anything.", voice='alice')
        
        # Record with transcription
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
    
    # Get transcription
    transcript = request.values.get('TranscriptionText', '').strip()
    
    print(f"[{datetime.now()}] PROCESS: call={call_sid}")
    print(f"  User said: '{transcript}'")
    
    try:
        from twilio.twiml.voice_response import VoiceResponse
        
        if not transcript or transcript == "":
            response_text = "I didn't catch that. Can you speak up?"
        else:
            # Use Claude to generate smart response
            response_text = get_smart_response(transcript, call_sid)
            print(f"  Clav response: {response_text}")
        
        # Send response and loop
        resp = VoiceResponse()
        resp.say(response_text, voice='alice')
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
        return Response('<?xml version="1.0"?><Response><Say>Error processing</Say></Response>', mimetype='application/xml')

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
