import os
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
load_dotenv()  

TW_SID = os.getenv("TWILIO_ACCOUNT_SID")
TW_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TW_FROM = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TW_SID, TW_TOKEN)

def _get_twilio_client():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise RuntimeError("Twilio credentials missing; set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
    return Client(sid, token)

def place_tts_call(to_phone, message=None, play_url=None, voice="Polly.Joanna"):
    client = _get_twilio_client()
    vr = VoiceResponse()
    if play_url:
        vr.play(play_url)
    elif message:
        vr.say(message, voice=voice)
    else:
        raise ValueError("Either message or play_url must be provided")
    return client.calls.create(to=to_phone, twiml=str(vr), from_=os.getenv("TWILIO_PHONE_NUMBER"))

