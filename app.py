import streamlit as st
import dateparser
import pandas as pd
from ics import Calendar, Event
from github import Github
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- APP CONFIG ---
st.set_page_config(page_title="Shift Logger", page_icon="📅", layout="wide")
st.title("🎙️ Voice Shift Logger & Agenda")

# Load secrets
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "shift_data_secret_7x9z2.ics" 
except Exception:
    st.error("Missing Secrets! Add GITHUB_TOKEN and REPO_NAME in Streamlit Settings.")
    st.stop()

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# --- HELPER FUNCTIONS ---
def get_calendar_from_github():
    try:
        file_content = repo.get_contents(FILE_PATH)
        return Calendar(file_content.decoded_content.decode()), file_content.sha
    except:
        return Calendar(), None

def push_to_github(calendar, sha):
    content = "".join(calendar.serialize_iter())
    if sha:
        repo.update_file(FILE_PATH, "Update shifts", content, sha)
    else:
        repo.create_file(FILE_PATH, "Initial shift commit", content)

def parse_shift_text(text):
    text = text.lower().replace("from", "").strip()
    if " to " in text:
        parts = text.split(" to ")
    elif "-" in text:
        parts = text.split("-")
    else:
        return dateparser.parse(text), None

    start_dt = dateparser.parse(parts[0].strip())
    end_dt = dateparser.parse(parts[1].strip(), settings={'RELATIVE_BASE': start_dt}) if start_dt else dateparser.parse(parts[1].strip())
    
    if start_dt and end_dt and end_dt < start_dt:
        end_dt += timedelta(days=1)
    return start_dt, end_dt

# --- MAIN LAYOUT ---
col_input, col_display = st.columns([1, 1.5], gap="large")

# --- LEFT COLUMN: INPUT ---
with col_input:
    st.subheader("➕ Add New Shift")
    st.write("Tap the box and use your **Voice Mic**.")
    voice_input = st.text_input("Example: 'Monday 20th 6am to 11:15am'", placeholder="Speak or type here...", key="input")
    
    if st.button("🚀 Log Shift", use_container_width=True):
        if voice_input:
            with st.spinner("Syncing..."):
                start, end = parse_shift_text(voice_input)
                if start:
                    cal, sha = get_calendar_from_github()
                    event = Event(name="Work Shift", begin=start, end=end if end else start + timedelta(hours=8))
                    cal.events.add(event)
                    push_to_github(cal, sha)
                    st.success(f"Added: {start.strftime('%d %b, %I:%M %p')}")
                    st.rerun() # Refresh to show new data
                else:
                    st.error("Could not parse date. Try: 'Today 2:15pm to 7:30pm'")

    st.divider()
    st.subheader("🔗 Outlook/Google Sync")
    raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FILE_PATH}"
    st.info("Paste this link into your Calendar settings:")
    st.code(raw_url)

# --- RIGHT COLUMN: DATA & CALENDAR ---
with col_display:
    cal_obj, _ = get_calendar_from_github()
    
    # Prepare data for Table and Calendar
    event_list = []
    calendar_events = []
    for e in sorted(cal_obj.events, key=lambda x: x.begin, reverse=True):
        # Data for Table
        event_list.append({
            "Date": e.begin.strftime("%A, %b %d"),
            "Time": f"{e.begin.strftime('%I:%M %p')} - {e.end.strftime('%I:%M %p')}"
        })
        # Data for Calendar Component
        calendar_events.append({
            "title": "Shift",
            "start": e.begin.isoformat(),
            "end": e.end.isoformat(),
            "color": "#3D9DF3"
        })

    # Show Graphical Calendar
    st.subheader("📅 Graphical View")
    calendar(events=calendar_events, options={"initialView": "dayGridMonth"}, key="calendar")

    # Show Data Table
    st.subheader("📋 Recent Shifts")
    if event_list:
        st.dataframe(pd.DataFrame(event_list), use_container_width=True, hide_index=True)
    else:
        st.write("No shifts found.")
