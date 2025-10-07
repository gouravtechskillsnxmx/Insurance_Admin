# app/leads_api.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from db import SessionLocal, Lead, Reminder
import pandas as pd
from datetime import datetime

router = APIRouter(prefix="/leads")

class LeadCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    policy_id: Optional[str] = None
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    policy_id: Optional[str] = None
    notes: Optional[str] = None

@router.post("/", response_model=dict)
def create_lead(l: LeadCreate):
    db = SessionLocal()
    lead = Lead(name=l.name, phone=l.phone, email=l.email, policy_id=l.policy_id, notes=l.notes)
    db.add(lead); db.commit(); db.refresh(lead); db.close()
    return {"lead_id": lead.id}

@router.get("/", response_model=List[dict])
def list_leads(skip: int = 0, limit: int = 100):
    db = SessionLocal()
    leads = db.query(Lead).offset(skip).limit(limit).all()
    out = [{"id": r.id, "name": r.name, "phone": r.phone, "email": r.email, "policy_id": r.policy_id, "notes": r.notes} for r in leads]
    db.close()
    return out

@router.put("/{lead_id}", response_model=dict)
def update_lead(lead_id: int, payload: LeadUpdate):
    db = SessionLocal()
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        db.close()
        raise HTTPException(status_code=404, detail="Lead not found")
    for k, v in payload.dict(exclude_none=True).items():
        setattr(lead, k, v)
    db.commit(); db.refresh(lead); db.close()
    return {"ok": True, "lead": {"id": lead.id, "name": lead.name, "phone": lead.phone, "email": lead.email, "policy_id": lead.policy_id, "notes": lead.notes}}

@router.delete("/{lead_id}", response_model=dict)
def delete_lead(lead_id: int):
    db = SessionLocal()
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        db.close()
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead); db.commit(); db.close()
    return {"ok": True}

@router.post("/bulk_upload", response_model=dict)
async def bulk_upload(file: UploadFile = File(...)):
    """
    Accept CSV or Excel file with columns:
    name, phone, email (optional), policy_id (optional), notes (optional), due_date (optional ISO)
    If due_date provided, schedule a Reminder row.
    """
    ext = (file.filename or "").lower()
    contents = await file.read()
    try:
        if ext.endswith(".csv"):
            df = pd.read_csv(pd.io.common.BytesIO(contents))
        elif ext.endswith((".xls", ".xlsx")):
            df = pd.read_excel(pd.io.common.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    required = ["name", "phone"]
    for c in required:
        if c not in df.columns.str.lower().tolist() and c not in df.columns.tolist():
            raise HTTPException(status_code=400, detail=f"File missing required column: {c}")

    inserted = 0
    reminders_created = 0
    db = SessionLocal()
    # normalize columns by lowercasing
    df.columns = [c.strip() for c in df.columns]
    for _, row in df.iterrows():
        name = row.get("name") or row.get("Name")
        phone = row.get("phone") or row.get("Phone")
        email = row.get("email") or row.get("Email")
        policy_id = row.get("policy_id") or row.get("Policy_ID") or row.get("policy")
        notes = row.get("notes") or row.get("Notes")
        lead = Lead(name=str(name), phone=str(phone), email=(str(email) if not pd.isna(email) else None), policy_id=(str(policy_id) if not pd.isna(policy_id) else None), notes=(str(notes) if not pd.isna(notes) else None))
        db.add(lead)
        db.flush()  # get id
        inserted += 1
        # optional due_date column (ISO or recognizable)
        due_date_val = None
        if "due_date" in row.index or "Due_Date" in row.index or "due" in row.index:
            for c in ["due_date", "Due_Date", "due"]:
                if c in row.index and not pd.isna(row[c]):
                    due_date_val = row[c]
                    break
        if due_date_val:
            try:
                # accept datetime or parse string
                if isinstance(due_date_val, str):
                    due_dt = datetime.fromisoformat(due_date_val)
                elif isinstance(due_date_val, (pd.Timestamp, datetime)):
                    due_dt = due_date_val.to_pydatetime() if hasattr(due_date_val, "to_pydatetime") else due_date_val
                else:
                    due_dt = datetime(due_date_val.year, due_date_val.month, due_date_val.day)
                rem = Reminder(lead_id=lead.id, due_date=due_dt, message=f"Premium due for {lead.name}", sent=False)
                db.add(rem)
                reminders_created += 1
            except Exception:
                # skip bad date
                pass

    db.commit()
    db.close()
    return {"inserted": inserted, "reminders_created": reminders_created}
