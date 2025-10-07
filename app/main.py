# app/main.py
import os
from fastapi import FastAPI, UploadFile, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timedelta
from .db import init_db, SessionLocal, Lead
from .agents import policy_expert_answer, advisor_recommendation, schedule_premium_reminder, send_premium_call
from apscheduler.schedulers.background import BackgroundScheduler

init_db()
app = FastAPI(title="InsureAI Desk Orchestrator")

# Simple in-memory scheduler (for demo). Use Celery for prod.
scheduler = BackgroundScheduler()
scheduler.start()

class LeadCreate(BaseModel):
    name: str
    phone: str
    email: str = None

@app.post("/leads")
def create_lead(l: LeadCreate):
    db = SessionLocal()
    lead = Lead(name=l.name, phone=l.phone, email=l.email)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    db.close()
    return {"lead_id": lead.id}

@app.post("/ingest_policy")
async def ingest_policy(file: UploadFile):
    """
    Save file, parse (simplified), chunk, create embeddings (call create_embeddings_and_store).
    For brevity this demo will just read text and add as single doc.
    """
    content = await file.read()
    text = content.decode(errors="ignore")
    # TODO: chunk & create embeddings
    from .embeddings_rag import create_embeddings_and_store
    docs = [{"id": file.filename, "text": text, "meta": {"filename": file.filename}}]
    create_embeddings_and_store("policies", docs)
    return {"status": "ok", "ingested_file": file.filename}

class QARequest(BaseModel):
    lead_id: int
    question: str

@app.post("/ask")
def ask_question(q: QARequest):
    # fetch lead data
    db = SessionLocal()
    lead = db.query(Lead).filter(Lead.id == q.lead_id).first()
    db.close()
    lead_ctx = {"name": lead.name, "phone": lead.phone}
    answer = policy_expert_answer("policies", q.question, lead_ctx)
    return {"answer": answer}

class ReminderReq(BaseModel):
    lead_id: int
    days_before: int = 3
    custom_message: str = None
    due_date: datetime

@app.post("/schedule_reminder")
def schedule_reminder(req: ReminderReq, background_tasks: BackgroundTasks):
    """
    Create reminder and schedule APS job to call at (due_date - days_before).
    """
    # build default message
    db = SessionLocal()
    lead = db.query(Lead).filter(Lead.id == req.lead_id).first()
    db.close()
    default_msg = req.custom_message or f"Hello {lead.name}. This is a reminder that your premium for policy {lead.policy_id or 'your policy'} is due on {req.due_date.date()}. Please contact your agent to pay."
    reminder = schedule_premium_reminder(req.lead_id, req.due_date, default_msg)
    # schedule a job
    call_time = req.due_date - timedelta(days=req.days_before)
    def job_call(lead_phone=lead.phone, message=default_msg, reminder_id=reminder.id):
        sid = send_premium_call(lead_phone, message)
        # update DB reminder as sent
        from .db import SessionLocal, Reminder
        s = SessionLocal()
        r = s.query(Reminder).filter(Reminder.id == reminder_id).first()
        if r:
            r.sent = True
            s.commit()
        s.close()
        print("Call placed:", sid)
    scheduler.add_job(job_call, 'date', run_date=call_time, id=f"reminder_{reminder.id}")
    return {"status": "scheduled", "run_at": str(call_time), "reminder_id": reminder.id}
