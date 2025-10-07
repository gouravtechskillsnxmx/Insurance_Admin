import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from db import init_db
from agents import SchedulerAgent
from leads_api import router as leads_router
from db import init_db as initdb
# at very top of app/main_crewai.py (or main entry)
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from reminders_api import router as reminders_router

init_db()
app = FastAPI(title="InsureAI Desk - CrewAI Orchestrator")
app.include_router(leads_router)
app.include_router(reminders_router)

# existing /crew/schedule_reminder endpoint...
# (keep your endpoint that triggers SchedulerAgent; unchanged)


class ScheduleReq(BaseModel):
    lead_id: int
    due_date: datetime
    days_before: int = 3
    custom_message: str = None
    prefer_tts: str = "polly"

@app.post("/crew/schedule_reminder")
async def crew_schedule(req: ScheduleReq, background_tasks: BackgroundTasks):
    payload = req.dict()
    def run_job():
        agent = SchedulerAgent()
        res = agent.run(payload['lead_id'], datetime.fromisoformat(payload['due_date']) if isinstance(payload['due_date'], str) else payload['due_date'], payload.get('days_before',3), payload.get('custom_message'), payload.get('prefer_tts','polly'))
        print('SchedulerAgent result:', res)
    background_tasks.add_task(run_job)
    return {"status":"scheduled_in_crew","lead_id": req.lead_id}
