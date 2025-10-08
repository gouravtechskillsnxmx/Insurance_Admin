# app/reminders_api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from .db import SessionLocal, Reminder
from datetime import datetime

router = APIRouter(prefix="/reminders")

class ReminderUpdate(BaseModel):
    due_date: datetime = None
    message: str = None
    sent: bool = None

@router.get("/", response_model=List[dict])
def list_reminders(skip: int = 0, limit: int = 100):
    db = SessionLocal()
    rems = db.query(Reminder).offset(skip).limit(limit).all()
    out = [{"id": r.id, "lead_id": r.lead_id, "due_date": r.due_date.isoformat(), "message": r.message, "sent": r.sent} for r in rems]
    db.close()
    return out

@router.put("/{reminder_id}", response_model=dict)
def update_reminder(reminder_id: int, payload: ReminderUpdate):
    db = SessionLocal()
    r = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Reminder not found")
    data = payload.dict(exclude_none=True)
    if "due_date" in data:
        r.due_date = data["due_date"]
    if "message" in data:
        r.message = data["message"]
    if "sent" in data:
        r.sent = data["sent"]
    db.commit(); db.refresh(r); db.close()
    return {"ok": True, "reminder": {"id": r.id, "lead_id": r.lead_id, "due_date": r.due_date.isoformat(), "message": r.message, "sent": r.sent}}

@router.delete("/{reminder_id}", response_model=dict)
def delete_reminder(reminder_id: int):
    db = SessionLocal()
    r = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not r:
        db.close()
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.delete(r); db.commit(); db.close()
    return {"ok": True}
