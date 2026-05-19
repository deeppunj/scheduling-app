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

# Raw Pre-defined Shifts (Mixing formats; handled gracefully below)
RAW_SHIFTS = [
    {"label": "(1) 06:00 - 11:15", "start": "06:00", "end": "11:15", "is_off": False},
    {"label": "(2) 09:00 - 14:15", "start": "09:00", "end": "14:15", "is_off": False},
    {"label": "(3) 14:15 - 19:30", "start": "14:15", "end": "19:30", "is_off": False},
    {"label": "(4) 14:45 - 20:00", "start": "14:45", "end": "20:00", "is_off": False},
    {"label": "10:00am - 3:15pm", "start": "10:00", "end": "15:15", "is_off": False},
    {"label": "7:00am - 12:15pm", "start": "07:00", "end": "12:15", "is_off": False},
    {"label": "🌴 Off", "start": "00:00", "end": "00:00", "is_off": True}
]

# Separate "Off" from active shifts, sort active shifts by start time, and recombine
active_shifts = sorted([s for s in RAW_SHIFTS if not s["is_off"]], key=lambda x: x["start"])
off_shift = [s for s in RAW_SHIFTS if s["is_off"]]
PRESET_SHIFTS = active_shifts + off_shift

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
    push_to_github(cal, sha, "Deleted an entry")
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
    voice_input = st.text_input("Voice/Text Entry:", placeholder="e.g. 'Monday 06:00 to 11:15' or 'Tomorrow 9am to 14:15'")
    
    if st.button("Add via Text", use_container_width=True):
        if not voice_input.strip():
            st.warning("Please enter some text first!")
        else:
            with st.spinner("Parsing and saving shift..."):
                try:
                    cleaned_input = voice_input.lower().replace(" to ", " ").replace("-", " ")
                    words = cleaned_input.split()
                    
                    if len(words) < 3:
                        st.error("Could not parse. Try format: '[Day/Date] [Start Time] [End Time]'")
                    else:
                        time_end_str = words[-1]
                        time_start_str = words[-2]
                        date_str = " ".join(words[:-2])
                        
                        base_date = dateparser.parse(
                            date_str, 
                            settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': datetime.now(BELGIUM_TZ).replace(tzinfo=None)}
                        )
                        
                        start_time_obj = dateparser.parse(time_start_str)
                        end_time_obj = dateparser.parse(time_end_str)
                        
                        if not base_date or not start_time_obj or not end_time_obj:
                            st.error("Failed to recognize date or times. Example: 'Next Monday 6:00 11:15'")
                        else:
                            start_dt = datetime.combine(base_date.date(), start_time_obj.time())
                            end_dt = datetime.combine(base_date.date(), end_time_obj.time())
                            
                            start_dt_loc = BELGIUM_TZ.localize(start_dt)
                            end_dt_loc = BELGIUM_TZ.localize(end_dt)
                            
                            if end_dt_loc <= start_dt_loc:
                                end_dt_loc += timedelta(days=1)
                                
                            new_event = Event(name="Work Shift", begin=start_dt_loc, end=end_dt_loc)
                            cal_obj.events.add(new_event)
                            
                            push_to_github(cal_obj, current_sha, f"Added shift via text: {voice_input}")
                            st.toast(f"Logged: {start_dt_loc.strftime('%A %d/%m')} ({start_dt_loc.strftime('%H:%M')} - {end_dt_loc.strftime('%H:%M')})", icon="✅")
                            st.rerun()
                            
                except Exception as parser_err:
                    st.error("Error processing text. Ensure format matches: 'Monday 06:00 11:15'")
    
    st.divider()
    
    # QUICK SELECT SECTION
    st.subheader("🖱️ Quick Select")
    
    if st.session_state.last_clicked_date:
        st.success(f"Selected Date: **{st.session_state.last_clicked_date}**")
        
        cols = st.columns(2)
        for i, shift in enumerate(PRESET_SHIFTS):
            if cols[i % 2].button(shift["label"], use_container_width=True, key=f"btn_{i}"):
                with st.spinner("Saving..."):
                    if shift["is_off"]:
                        # Treat "Off" as an all-day block or clear marker entry
                        start_dt = BELGIUM_TZ.localize(datetime.strptime(f"{st.session_state.last_clicked_date} 00:00", "%Y-%m-%d %H:%M"))
                        end_dt = BELGIUM_TZ.localize(datetime.strptime(f"{st.session_state.last_clicked_date} 23:59", "%Y-%m-%d %H:%M"))
                        new_event = Event(name="Off Day", begin=start_dt, end=end_dt)
                        msg = f"Marked {st.session_state.last_clicked_date} as Off Day"
                    else:
                        start_dt = BELGIUM_TZ.localize(datetime.strptime(f"{st.session_state.last_clicked_date} {shift['start']}", "%Y-%m-%d %H:%M"))
                        end_dt = BELGIUM_TZ.localize(datetime.strptime(f"{st.session_state.last_clicked_date} {shift['end']}", "%Y-%m-%d %H:%M"))
                        new_event = Event(name="Work Shift", begin=start_dt, end=end_dt)
                        msg = f"Added preset {shift['label']}"
                    
                    cal_obj.events.add(new_event)
                    push_to_github(cal_obj, current_sha, msg)
                    st.toast(f"Logged: {shift['label']}", icon="✅")
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
        
        # Color coding: Gray out off days, leave active shifts blue
        is_off_day = (e.name == "Off Day")
        event_color = "#A0A0A0" if is_off_day else "#3D9DF3"
        display_title = "🌴 Off" if is_off_day else f"{b_start.strftime('%H:%M')}"
        
        calendar_events.append({
            "title": display_title,
            "start": b_start.isoformat(),
            "end": b_end.isoformat(),
            "color": event_color
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
    
    if cal_output.get("callback") == "dateClick":
        new_date = cal_output["dateClick"]["date"].split("T")[0]
        if st.session_state.last_clicked_date != new_date:
            st.session_state.last_clicked_date = new_date
            st.rerun()

    # 3. Compact Manage List
    st.subheader("📋 Compact List")
    sorted_events = sorted(cal_obj.events, key=lambda x: x.begin, reverse=True)
    
    if not sorted_events:
        st.caption("No entries logged.")
    else:
        with st.expander("Show/Hide All Entries", expanded=True):
            for i, e in enumerate(sorted_events):
                b_start = e.begin.datetime.astimezone(BELGIUM_TZ)
                b_end = e.end.datetime.astimezone(BELGIUM_TZ)
                
                c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
                c1.markdown(f"**{b_start.strftime('%d/%m')}**")
                
                if e.name == "Off Day":
                    c2.markdown("<span style='color:gray;'>🌴 Off Day</span>", unsafe_allow_html=True)
                else:
                    c2.text(f"{b_start.strftime('%H:%M')}-{b_end.strftime('%H:%M')}")
                    
                if c3.button("🗑️", key=f"del_{i}"):
                    delete_event(e.begin)
                if i < len(sorted_events) - 1:
                    st.markdown("---")
