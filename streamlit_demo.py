import streamlit as st
import requests, datetime, time

st.set_page_config(page_title="InsureAI Desk Demo", layout="centered")
st.title("📞 InsureAI Desk - Reminder Scheduler Demo (TTS Enabled)")

API_URL = st.text_input("API URL", "http://localhost:8000/crew/schedule_reminder")
LEADS_URL = st.text_input("Leads API URL", "http://localhost:8000/leads")
name = st.text_input("Lead name", "Test User")
phone = st.text_input("Phone (E.164)", "+15555555555")
policy_id = st.text_input("Policy ID", "POL123")
if st.button("Create Lead"):
    payload = {"name": name, "phone": phone, "policy_id": policy_id}
    try:
        r = requests.post(LEADS_URL, json=payload)
        st.success(r.json())
    except Exception as e:
        st.error(str(e))

st.markdown("---")
lead_id = st.number_input("Lead ID (from created lead)", 1, step=1)
due_date = st.date_input("Due Date", datetime.date.today())
due_time = st.time_input("Time",  datetime.time(20, 51))#(datetime.datetime.utcnow()+datetime.timedelta(minutes=1)).time())
prefer_tts = st.selectbox("Preferred TTS Engine", ["polly", "gcloud", "say"])
custom_message = st.text_area("Custom Message (optional)", placeholder="Enter custom reminder text...")

if st.button("Schedule Reminder"):
    due_datetime = datetime.datetime.combine(due_date, due_time)
    payload = {
        "lead_id": int(lead_id),
        "due_date": due_datetime.isoformat(),
        "days_before": 0,
        "custom_message": custom_message if custom_message else None,
        "prefer_tts": prefer_tts
    }
    st.write("Sending:", payload)
    try:
        res = requests.post(API_URL, json=payload)
        st.success(f"Response: {res.json()}")
    except Exception as e:
        st.error(f"Error: {e}")
