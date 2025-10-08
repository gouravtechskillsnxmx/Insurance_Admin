import os, json
from datetime import datetime, timedelta
import openai
from .db import SessionLocal, Lead, Reminder
from .twilio_client import place_tts_call
try:
    from polly_s3 import synthesize_speech_to_s3
except Exception:
    synthesize_speech_to_s3 = None
try:
    from gcloud_tts import synthesize_gcloud_tts_to_s3
except Exception:
    synthesize_gcloud_tts_to_s3 = None

openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def superego_check(message: str):
    prompt = f"Check this outbound insurance reminder for compliance. Remove marketing claims or guarantees. Return JSON like {{'ok': true, 'message': '<cleaned>'}} or {{'ok': false, 'reason': '...'}}\nMessage:\n{message}"
    try:
        resp = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=[{'role':'user','content':prompt}], max_tokens=200)
        out = resp['choices'][0]['message']['content'].strip()
        parsed = json.loads(out)
        return parsed
    except Exception as e:
        # fallback: quick heuristic safe-clean (strip promotional phrases)
        cleaned = message.replace('best', '').replace('guarantee', '').strip()
        return {'ok': True, 'message': cleaned}

class SchedulerAgent:
    def __init__(self):
        pass

    def run(self, lead_id: int, due_date: datetime, days_before: int = 3, custom_message: str = None, prefer_tts: str = 'polly'):
        db = SessionLocal()
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {'status':'error','reason':'lead_not_found'}
        if not custom_message:
            message = f"Hello {lead.name}. Reminder: your premium for policy {lead.policy_id or 'your policy'} is due on {due_date.date()}. Please contact your agent to pay."
        else:
            message = custom_message
        check = superego_check(message)
        if not check.get('ok'):
            return {'status':'blocked','reason':check.get('reason')}
        cleaned = check.get('message')
        # persist reminder
        r = Reminder(lead_id=lead.id, due_date=due_date, message=cleaned, sent=False)
        db.add(r); db.commit(); db.refresh(r)
        # choose TTS provider
        play_url = None
        provider_used = None
        if prefer_tts == 'polly' and synthesize_speech_to_s3:
            try:
                play_url = synthesize_speech_to_s3(cleaned)
                provider_used = 'polly'
            except Exception as e:
                play_url = None
        if (not play_url) and prefer_tts in ('polly','gcloud') and synthesize_gcloud_tts_to_s3:
            try:
                play_url = synthesize_gcloud_tts_to_s3(cleaned)
                provider_used = 'gcloud'
            except Exception as e:
                play_url = None
        # fallback to Twilio Say
        sid = None
        try:
            if play_url:
                sid = place_tts_call(lead.phone, play_url=play_url)
            else:
                sid = place_tts_call(lead.phone, message=cleaned)
            r.sent = True; db.commit()
            return {'status':'called','call_sid':sid,'provider':provider_used,'played_url':play_url}
        except Exception as e:
            return {'status':'failed','error':str(e)}
