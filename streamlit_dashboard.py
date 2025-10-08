# streamlit_dashboard.py
import streamlit as st
import requests, datetime, io, pandas as pd

st.set_page_config(layout="wide")
API_BASE = st.text_input("API base URL", ""https://insurance-admin-drg8.onrender.com")

st.title("InsureAI Desk — Dashboard")

# ---- Leads panel ----
st.header("Leads")
col1, col2 = st.columns([2,1])
with col1:
    if st.button("Refresh leads"):
        st.rerun()
    # fetch and show leads
    try:
        resp = requests.get(f"{API_BASE}/leads")
        leads = resp.json()
        df_leads = pd.DataFrame(leads)
        st.dataframe(df_leads)
    except Exception as e:
        st.error(f"Could not fetch leads: {e}")
with col2:
    st.subheader("Bulk upload")
    uploaded = st.file_uploader("Upload CSV / Excel", type=["csv","xls","xlsx"])
    if uploaded:
        st.write("Preview:")
        try:
            if uploaded.name.endswith(".csv"):
                preview_df = pd.read_csv(uploaded)
            else:
                preview_df = pd.read_excel(uploaded)
            st.dataframe(preview_df.head())
            if st.button("Upload file to backend"):
                # send file to API
                files = {"file": (uploaded.name, uploaded.getvalue())}
                res = requests.post(f"{API_BASE}/leads/bulk_upload", files=files)
                st.success(res.json())
        except Exception as e:
            st.error(f"Error reading file: {e}")

st.markdown("---")

# ---- Edit single lead ----
st.header("Edit Lead")
lead_id = st.number_input("Lead id", min_value=1, step=1, value=1)
if st.button("Load lead"):
    try:
        r = requests.get(f"{API_BASE}/leads")
        j = r.json()
        match = next((x for x in j if x["id"]==lead_id), None)
        if not match:
            st.warning("Lead not found in list")
        else:
            st.session_state["edit_lead"] = match
    except Exception as e:
        st.error(e)

if "edit_lead" in st.session_state:
    lead = st.session_state["edit_lead"]
    name = st.text_input("Name", lead.get("name"))
    phone = st.text_input("Phone", lead.get("phone"))
    email = st.text_input("Email", lead.get("email") or "")
    policy_id = st.text_input("Policy ID", lead.get("policy_id") or "")
    notes = st.text_area("Notes", lead.get("notes") or "")
    if st.button("Save lead"):
        payload = {"name": name, "phone": phone, "email": email, "policy_id": policy_id, "notes": notes}
        res = requests.put(f"{API_BASE}/leads/{lead['id']}", json=payload)
        st.success(res.json())

st.markdown("---")

# ---- Reminders panel ----
st.header("Reminders (Scheduled Calls)")
try:
    r = requests.get(f"{API_BASE}/reminders")
    reminders = r.json()
    df_rem = pd.DataFrame(reminders)
    if not df_rem.empty:
        df_rem["due_date_local"] = pd.to_datetime(df_rem["due_date"], format='mixed', errors='coerce').dt.tz_localize(None)
    st.dataframe(df_rem)
except Exception as e:
    st.error(f"Could not fetch reminders: {e}")

st.subheader("Edit reminder")
reminder_id = st.number_input("Reminder id", min_value=1, step=1, value=1, key="remid")
if st.button("Load reminder"):
    try:
        rr = requests.get(f"{API_BASE}/reminders")
        match = next((x for x in rr.json() if x["id"]==reminder_id), None)
        if not match:
            st.warning("Reminder not found")
        else:
            st.session_state["edit_reminder"] = match
    except Exception as e:
        st.error(e)

if "edit_reminder" in st.session_state:
    rem = st.session_state["edit_reminder"]
    new_due = st.date_input("Due date", pd.to_datetime(rem["due_date"]).date())
    new_time = st.time_input("Time", pd.to_datetime(rem["due_date"]).time())
    new_msg = st.text_area("Message", rem["message"])
    sent_flag = st.checkbox("Sent", rem["sent"])
    if st.button("Save reminder"):
        dt = datetime.datetime.combine(new_due, new_time)
        payload = {"due_date": dt.isoformat(), "message": new_msg, "sent": sent_flag}
        res = requests.put(f"{API_BASE}/reminders/{rem['id']}", json=payload)
        st.success(res.json())

st.markdown("---")
st.write("Tip: create a lead first (via Create Lead or bulk upload), note its id, then create reminders by scheduling via the API or the Crew scheduler endpoint.")
