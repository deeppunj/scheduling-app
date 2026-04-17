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

try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "shift_data_secret_7x9z2.ics" # Use your secret name here
except Exception:
    st.error("Missing Secrets! Check GITHUB_TOKEN and REPO_NAME in Streamlit Settings.")
    st.stop()

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# --- GITHUB HELPERS ---
def get_calendar_from_github():
    try:
        file_content = repo.get_contents(FILE_PATH)
        return Calendar(file_content.decoded_content.decode()), file_content.sha
    except:
        return Calendar(), None

def push_to_github(calendar, sha, message="Update shifts"):
    content = "".join(calendar.serialize_iter())
    if sha:
        repo.update_file(FILE_PATH, message, content, sha)
    else:
        repo.create_file(FILE_PATH, message, content)

def delete_event(event_to_remove):
    cal, sha = get_calendar_from_github()
    # Find the matching event by comparing start times (unique enough for shifts)
    new_events = set()
    for e in cal.events:
        if e.begin != event_to_remove.begin:
            new_events.add(e)
    cal.events = new_events
    push_to_github(cal, sha, "Deleted a shift")
    st.toast("Shift deleted successfully!", icon="🗑️")

# --- PARSER ---
def parse_shift_text(text):
    text = text.lower().replace("from", "").strip()
    settings = {'TIMEZONE': 'Europe/Brussels', 'TO_TIMEZONE': 'Europe/Brussels', 
                'RETURN_AS_TIMEZONE_AWARE': True, 'PREFER_DATES_FROM': 'future'}
    if " to " in text:
        parts = text.split(" to ")
    elif "-" in text:
        parts = text.split("-")
    else:
        return dateparser.parse(text, settings=settings), None

    start = dateparser.parse(parts[0].strip(), settings=settings)
    if start: settings['RELATIVE_BASE'] = start.replace(tzinfo=None)
    end = dateparser.parse(parts[1].strip(), settings=settings)
    if start and end and end < start: end += timedelta(days=1)
    return start, end

# --- APP LAYOUT ---
st.title("🇧🇪 Shift Manager (Belgium)")
col_left, col_right = st.columns([1, 1.5], gap="large")

# --- LEFT: ADDING SHIFTS ---
with col_left:
    st.subheader("➕ Log New Shift")
    voice_input = st.text_input("Say/Type shift:", placeholder="Today 2:15pm to 7:30pm", key="voice_in")
    
    if st.button("🚀 Add to Calendar", use_container_width=True):
        if voice_input:
            start, end = parse_shift_text(voice_input)
            if start:
                cal, sha = get_calendar_from_github()
                event = Event(name="Work Shift", begin=start, end=end if end else start + timedelta(hours=8))
                cal.events.add(event)
                push_to_github(cal, sha, "Added a shift")
                st.success("Shift Added!")
                st.rerun()

    st.divider()
    st.subheader("🔗 Syncing")
    raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FILE_PATH}"
    st.code(raw_url, language="text")
    st.caption("Paste this into ICSx5 or Outlook.")

# --- RIGHT: MANAGING SHIFTS ---
with col_right:
    cal_obj, current_sha = get_calendar_from_github()
    
    # Setup for Table and Calendar
    calendar_events = []
    display_data = []
    
    # Sort events by date (newest first)
    sorted_events = sorted(cal_obj.events, key=lambda x: x.begin, reverse=True)

    tab_cal, tab_list = st.tabs(["📅 Calendar View", "📋 Manage List"])

    with tab_cal:
        for e in sorted_events:
            b_start = e.begin.datetime.astimezone(BELGIUM_TZ)
            b_end = e.end.datetime.astimezone(BELGIUM_TZ)
            calendar_events.append({
                "title": f"Shift {b_start.strftime('%H:%M')}",
                "start": b_start.isoformat(),
                "end": b_end.isoformat(),
                "color": "#3D9DF3"
            })
        calendar(events=calendar_events, options={"initialView": "dayGridMonth", "timeZone": "Europe/Brussels"})

    with tab_list:
        st.subheader("Your Registered Shifts")
        if not sorted_events:
            st.write("No shifts found.")
        else:
            for i, e in enumerate(sorted_events):
                b_start = e.begin.datetime.astimezone(BELGIUM_TZ)
                b_end = e.end.datetime.astimezone(BELGIUM_TZ)
                
                # Create a row with info and a delete button
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"**{b_start.strftime('%d %b (%a)')}**")
                c2.write(f"{b_start.strftime('%H:%M')} - {b_end.strftime('%H:%M')}")
                
                # Each delete button needs a unique key
                if c3.button("🗑️", key=f"del_{i}"):
                    delete_event(e)
                    st.rerun()
                st.divider()
