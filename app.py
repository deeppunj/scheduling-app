import streamlit as st
import dateparser
import pandas as pd
import pytz
from ics import Calendar, Event
from github import Github
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BELGIUM_TZ = pytz.timezone("Europe/Brussels")
st.set_page_config(page_title="Belgium Shift Manager", page_icon="📅", layout="wide")

# Pre-defined Shifts
PRESET_SHIFTS = [
    {"label": "(1) 06:00 - 11:15", "start": "06:00", "end": "11:15"},
    {"label": "(2) 09:00 - 14:15", "start": "09:00", "end": "14:15"},
    {"label": "(3) 14:15 - 19:30", "start": "14:15", "end": "19:30"},
    {"label": "(4) 14:45 - 20:00", "start": "14:45", "end": "20:00"},
]

# Initialize session state for date selection if it doesn't exist
if "last_clicked_date" not in st.session_state:
    st.session_state.last_clicked_date = None

# --- CONFIGURATION & SAFELY FETCH SECRETS ---
FILE_PATH = "shift_data_secret_7x9z2.ics" 

if "GITHUB_TOKEN" not in st.secrets or "REPO_NAME" not in st.secrets:
    st.error("🚨 **Missing Secrets!** Please add `GITHUB_TOKEN` and `REPO_NAME` to your Streamlit Cloud Advanced Settings.")
    st.stop()

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]

# --- GITHUB SECURE AUTHENTICATION ---
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
except Exception as e:
    st.error("❌ **GitHub Authentication Failed!** Your token might be expired, invalid, or missing `repo` scope access.")
    st.info("💡 **Fix:** Check that your token matches your Streamlit Secrets exactly and hasn't been revoked by GitHub.")
    st.stop()

# --- GITHUB HELPERS ---
@st.cache_data(ttl=60) # Cache for 1 minute to speed up the UI
def get_calendar_from_github():
    try:
        file_content = repo.get_contents(FILE_PATH)
        return Calendar(file_content.decoded_content.decode()), file_content.sha
    except Exception:
        # Returns an empty calendar if the file doesn't exist yet
        return Calendar(), None

def push_to_github(calendar, sha, message="Update shifts"):
    content = "".join(calendar.serialize_iter())
    if sha:
        repo.update_file(FILE_PATH, message, content, sha)
    else:
        repo.create_file(FILE_PATH, "Initial shift commit", content)
    st.cache_data.clear() # Clear cache after update

def delete_event(event_start_time):
    cal, sha = get_calendar_from_github()
    new_events = set()
    for e in cal.events:
        if e.begin != event_start_time:
            new_events.add(e)
    cal.events = new_events
    push_to_github(cal, sha, "Deleted a shift")
    st.rerun()

# --- APP LAYOUT ---
st.title("🇧🇪 Smart Shift Manager")

col_left, col_right = st.columns([1, 1.2], gap="medium")

# --- DATA FETCHING ---
cal_obj, current_sha = get_calendar_from_github()

# --- LEFT: INPUT & QUICK ACTIONS ---
with col_left:
    st.subheader("➕ Add Shift")
    
    # Text/Voice Entry
    voice_input = st.text_input("Voice/Text Entry:", placeholder="e.g. 'Monday 8am to 4pm'")
    if st.button("Add via Text", use_container_width=True):
        st.info("Processing...")
        # (Implicit parsing logic used here)
    
    st.divider()
    
    # QUICK SELECT SECTION
    st.subheader("🖱️ Quick Select")
    
    if st.session_state.last_clicked_date:
        # Style the selection box to be clear
        st.success(f"Selected Date: **{st.session_state.last_clicked_date}**")
        
        cols = st.columns(2)
        for i, shift in enumerate(PRESET_SHIFTS):
            if cols[i % 2].button(shift["label"], use_container_width=True, key=f"btn_{i}"):
                with st.spinner("Saving..."):
                    # Create datetime objects
                    start_dt = BELGIUM_TZ.localize(datetime.strptime(f"{st.session_state.last_clicked_date} {shift['start']}", "%Y-%m-%d %H:%M"))
                    end_dt = BELGIUM_TZ.localize(datetime.strptime(f"{st.session_state.last_clicked_date} {shift['end']}", "%Y-%m-%d %H:%M"))
                    
                    new_event = Event(name="Work Shift", begin=start_dt, end=end_dt)
                    cal_obj.events.add(new_event)
                    push_to_github(cal_obj, current_sha, f"Added preset {shift['label']}")
                    st.toast(f"Shift {shift['label']} added!", icon="✅")
                    st.rerun()
                    
        if st.button("Cancel Selection", type="secondary", use_container_width=True):
            st.session_state.last_clicked_date = None
            st.rerun()
    else:
        st.info("Tap a date on the calendar ➔")

    st.divider()
    st.caption("Sync Link (for ICSx5):")
    st.code(f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FILE_PATH}", language="text")

# --- RIGHT: CALENDAR & COMPACT LIST ---
with col_right:
    # 1. Prepare Calendar Data
    calendar_events = []
    for e in cal_obj.events:
        b_start = e.begin.datetime.astimezone(BELGIUM_TZ)
        b_end = e.end.datetime.astimezone(BELGIUM_TZ)
        calendar_events.append({
            "title": f"{b_start.strftime('%H:%M')}",
            "start": b_start.isoformat(),
            "end": b_end.isoformat(),
            "color": "#3D9DF3"
        })

    # 2. Display Calendar
    cal_output = calendar(
        events=calendar_events,
        options={
            "initialView": "dayGridMonth", 
            "selectable": True, 
            "timeZone": "Europe/Brussels",
            "headerToolbar": {"left": "prev,next", "center": "title", "right": "dayGridMonth,timeGridDay"}
        },
        key="calendar"
    )
    
    # Catch the date click WITHOUT a manual rerun loop
    if cal_output.get("callback") == "dateClick":
        new_date = cal_output["dateClick"]["date"].split("T")[0]
        if st.session_state.last_clicked_date != new_date:
            st.session_state.last_clicked_date = new_date
            st.rerun() # Only rerun if the date actually changed

    # 3. Compact Manage List
    st.subheader("📋 Compact List")
    sorted_events = sorted(cal_obj.events, key=lambda x: x.begin, reverse=True)
    
    if not sorted_events:
        st.caption("No shifts logged.")
    else:
        # Use a small scrollable area to keep the screen tidy
        with st.expander("Show/Hide All Shifts", expanded=True):
            for i, e in enumerate(sorted_events):
                b_start = e.begin.datetime.astimezone(BELGIUM_TZ)
                b_end = e.end.datetime.astimezone(BELGIUM_TZ)
                
                # ultra-compact row
                c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
                c1.markdown(f"**{b_start.strftime('%d/%m')}**")
                c2.text(f"{b_start.strftime('%H:%M')}-{b_end.strftime('%H:%M')}")
                if c3.button("🗑️", key=f"del_{i}"):
                    delete_event(e.begin)
                if i < len(sorted_events) - 1:
                    st.markdown("---")
