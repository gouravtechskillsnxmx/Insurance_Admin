# streamlit_dashboard.py
import os
import streamlit as st
import requests
import datetime
import io
import pandas as pd
from typing import Optional

st.set_page_config(layout="wide", page_title="InsureAI Desk")

# API base default (use env var on Render)
DEFAULT_API = os.getenv("API_BASE", "http://localhost:8000")
API_BASE = st.text_input("API base URL", DEFAULT_API, help="API base URL for FastAPI backend (use the full https://... URL in production)")

# persist API in session_state so other actions don't overwrite it
st.session_state.setdefault("api_base", API_BASE)
if API_BASE != st.session_state["api_base"]:
    st.session_state["api_base"] = API_BASE
API = st.session_state["api_base"]

st.title("InsureAI Desk — Dashboard & Scheduler")

# -------------------------
# Helpers
# -------------------------
def iso_from_local_datetime(date_obj: datetime.date, time_obj: datetime.time) -> str:
    """
    Combine date + time (assumed local) into an aware UTC ISO string.
    This ensures the backend receives timezone-aware timestamps.
    """
    # system local tz
    local_tz = datetime.datetime.now().astimezone().tzinfo
    naive = datetime.datetime.combine(date_obj, time_obj)
    # attach local tz (best-effort)
    if naive.tzinfo is None:
        local_dt = naive.replace(tzinfo=local_tz)
    else:
        local_dt = naive
    utc_dt = local_dt.astimezone(datetime.timezone.utc)
    return utc_dt.isoformat()

def parse_iso_to_local_parts(iso_str: str) -> (datetime.date, datetime.time):
    """
    Parse an ISO string (possibly timezone-aware) and return local date and time
    suitable for Streamlit date_input/time_input.
    """
    try:
        ts = pd.to_datetime(iso_str)
    except Exception:
        # fallback: current time
        now = datetime.datetime.now()
        return now.date(), now.time().replace(microsecond=0)

    py_dt = ts.to_pydatetime()
    # convert to local tz for display
    if py_dt.tzinfo is not None:
        local_dt = py_dt.astimezone(datetime.datetime.now().astimezone().tzinfo)
    else:
        local_dt = py_dt
    return local_dt.date(), local_dt.time().replace(microsecond=0)

def reorder_lead_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Put id, name, phone, email near the front if they exist
    cols = list(df.columns)
    preferred = ["id", "name", "phone", "email", "policy_id", "notes"]
    ordered = [c for c in preferred if c in cols] + [c for c in cols if c not in preferred]
    return df[ordered]

# -------------------------
# Left column: Leads & Create Lead
# -------------------------
left, right = st.columns([2, 1])

with left:
    st.header("Leads")
    if st.button("Refresh leads"):
        st.rerun()

    try:
        resp = requests.get(f"{API}/leads", timeout=10)
        resp.raise_for_status()
        leads = resp.json()
        df_leads = pd.DataFrame(leads)
        if not df_leads.empty:
            df_leads = reorder_lead_columns(df_leads)
            st.dataframe(df_leads)
        else:
            st.info("No leads found.")
    except Exception as e:
        st.error(f"Could not fetch leads: {e}")

    st.markdown("---")
    st.subheader("Bulk upload leads (CSV / Excel)")
    uploaded = st.file_uploader("Upload CSV / Excel to add leads", type=["csv","xls","xlsx"])
    if uploaded:
        st.write("Preview:")
        try:
            if uploaded.name.endswith(".csv"):
                preview_df = pd.read_csv(uploaded)
            else:
                preview_df = pd.read_excel(uploaded)
            st.dataframe(preview_df.head())
            if st.button("Upload file to backend"):
                files = {"file": (uploaded.name, uploaded.getvalue())}
                res = requests.post(f"{API}/leads/bulk_upload", files=files, timeout=30)
                res.raise_for_status()
                st.success(res.json())
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {e}")

with right:
    st.header("Create Lead (one-off)")
    name = st.text_input("Name", "")
    phone = st.text_input("Phone (E.164)", "")
    email = st.text_input("Email", "")
    policy_id = st.text_input("Policy ID", "")
    notes = st.text_area("Notes", "")
    if st.button("Create Lead"):
        if not name.strip():
            st.error("Name is required")
        else:
            payload = {"name": name, "phone": phone or None, "email": email or None, "policy_id": policy_id or None, "notes": notes or None}
            try:
                r = requests.post(f"{API}/leads", json=payload, timeout=10)
                r.raise_for_status()
                st.success(r.json())
                # refresh list so phone (and other fields) appear
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create lead: {e}")

# -------------------------
# Edit Lead (right column below create)
# -------------------------
st.markdown("---")
st.header("Edit Lead")
lead_id_to_load = st.number_input("Lead id (to edit)", min_value=1, step=1, value=1, key="lead_edit_id")
if st.button("Load lead", key="load_lead"):
    try:
        r = requests.get(f"{API}/leads", timeout=10)
        r.raise_for_status()
        j = r.json()
        match = next((x for x in j if x.get("id") == lead_id_to_load), None)
        if not match:
            st.warning("Lead not found in list")
        else:
            st.session_state["edit_lead"] = match
            st.experimental_set_query_params()  # force redraw
            st.rerun()
    except Exception as e:
        st.error(e)

if "edit_lead" in st.session_state:
    lead = st.session_state["edit_lead"]
    edit_name = st.text_input("Name (edit)", lead.get("name") or "", key="edit_name")
    edit_phone = st.text_input("Phone (E.164) (edit)", lead.get("phone") or "", key="edit_phone")
    edit_email = st.text_input("Email (edit)", lead.get("email") or "", key="edit_email")
    edit_policy_id = st.text_input("Policy ID (edit)", lead.get("policy_id") or "", key="edit_policy_id")
    edit_notes = st.text_area("Notes (edit)", lead.get("notes") or "", key="edit_notes")
    if st.button("Save lead", key="save_lead"):
        payload = {"name": edit_name, "phone": edit_phone or None, "email": edit_email or None, "policy_id": edit_policy_id or None, "notes": edit_notes or None}
        try:
            res = requests.put(f"{API}/leads/{lead['id']}", json=payload, timeout=10)
            res.raise_for_status()
            st.success(res.json())
            # clear edit state and refresh lists
            st.session_state.pop("edit_lead", None)
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save lead: {e}")

# -------------------------
# Reminders / Scheduler area
# -------------------------
st.markdown("---")
st.header("Reminders (Scheduled Calls)")

try:
    r = requests.get(f"{API}/reminders", timeout=10)
    r.raise_for_status()
    reminders = r.json()
    df_rem = pd.DataFrame(reminders)
    if not df_rem.empty:
        # robust parsing for mixed timestamp formats
        df_rem["due_date_local"] = pd.to_datetime(df_rem["due_date"], format='mixed', errors='coerce').apply(
            lambda ts: pd.to_datetime(ts).tz_convert(datetime.datetime.now().astimezone().tzinfo) if pd.notna(ts) and getattr(ts, "tz", None) is not None else pd.to_datetime(ts)
        ).dt.tz_localize(None)
        st.dataframe(df_rem)
    else:
        st.info("No reminders found.")
except Exception as e:
    st.error(f"Could not fetch reminders: {e}")

# -------------------------
# Edit Reminder
# -------------------------
st.markdown("---")
st.subheader("Edit reminder")
reminder_id = st.number_input("Reminder id (to edit)", min_value=1, step=1, value=1, key="remid")
if st.button("Load reminder", key="load_rem"):
    try:
        rr = requests.get(f"{API}/reminders", timeout=10)
        rr.raise_for_status()
        match = next((x for x in rr.json() if x.get("id") == reminder_id), None)
        if not match:
            st.warning("Reminder not found")
        else:
            st.session_state["edit_reminder"] = match
            st.rerun()
    except Exception as e:
        st.error(e)

if "edit_reminder" in st.session_state:
    rem = st.session_state["edit_reminder"]
    # parse due_date to local date/time for inputs
    new_due_date, new_due_time = parse_iso_to_local_parts(rem.get("due_date"))
    new_due = st.date_input("Due date (edit)", new_due_date, key="rem_due_date")
    new_time = st.time_input("Time (edit)", new_due_time, key="rem_time")
    new_msg = st.text_area("Message (edit)", rem.get("message") or "", key="rem_msg")
    sent_flag = st.checkbox("Sent (edit)", rem.get("sent", False), key="rem_sent")
    if st.button("Save reminder", key="save_rem"):
        # validate message (make mandatory)
        if not new_msg or not new_msg.strip():
            st.error("Custom message is required for reminder (make sure you enter a message).")
        else:
            # convert to timezone-aware UTC ISO string
            due_iso = iso_from_local_datetime(new_due, new_time)
            payload = {"due_date": due_iso, "message": new_msg, "sent": bool(sent_flag)}
            try:
                res = requests.put(f"{API}/reminders/{rem['id']}", json=payload, timeout=10)
                res.raise_for_status()
                st.success(res.json())
                st.session_state.pop("edit_reminder", None)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save reminder: {e}")

# -------------------------
# Schedule Reminder (Crew)
# -------------------------
st.markdown("---")
st.subheader("Schedule Reminder (via Crew endpoint)")

col1, col2 = st.columns(2)
with col1:
    form_lead_id = st.number_input("Lead ID", min_value=1, step=1, value=1, key="form_lead_id")
    form_due_date = st.date_input("Due Date", datetime.date.today(), key="form_due_date")
    form_due_time = st.time_input("Time", (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).time(), key="form_due_time")
with col2:
    form_days_before = st.number_input("Days before (notify)", min_value=0, value=3, key="form_days_before")
    form_prefer_tts = st.selectbox("Preferred TTS", ["polly", "gcloud", "say"], key="form_prefer_tts")
    form_custom_message = st.text_area("Custom Message (required)", key="form_custom_message")

if st.button("Schedule Reminder (Crew)", key="schedule_crew"):
    # require custom message
    if not form_custom_message or not form_custom_message.strip():
        st.error("Custom message is required. Please enter a message to be used for the reminder.")
    else:
        due_iso = iso_from_local_datetime(form_due_date, form_due_time)
        payload = {
            "lead_id": int(form_lead_id),
            "due_date": due_iso,
            "days_before": int(form_days_before),
            "custom_message": form_custom_message,
            "prefer_tts": form_prefer_tts
        }
        st.write("Scheduling:", payload)
        try:
            res = requests.post(f"{API}/crew/schedule_reminder", json=payload, timeout=15)
            res.raise_for_status()
            st.success(res.json())
            # refresh reminders
            st.rerun()
        except Exception as e:
            st.error(f"Failed to schedule: {e}")

st.markdown("---")
st.write("Tip: set `API_BASE` to your deployed backend URL (e.g. https://insurance-admin-drg8.onrender.com) in Render environment variables.")
