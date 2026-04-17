import streamlit as st
import dateparser
import pandas as pd
import pytz
from ics import Calendar, Event
from github import Github
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- TIMEZONE CONFIG ---
# Force everything to Belgium time
BELGIUM_TZ = pytz.timezone("Europe/Brussels")

# --- APP CONFIG ---
st.set_page_config(page_title="Belgium Shift Logger", page_icon="📅", layout="wide")
st.title("🇧🇪 Voice Shift Logger (Belgium Time)")

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
    """
    Parses text specifically in the Europe/Brussels timezone.
    """
    text = text.lower().replace("from", "").strip()
    
    # Settings to tell dateparser we are in Belgium
    parse_settings = {
        'TIMEZONE': 'Europe/Brussels',
        'TO_TIMEZONE': 'Europe/Brussels',
        'RETURN_AS_TIMEZONE_AWARE': True,
        'PREFER_DATES_FROM': 'future'
    }

    if " to " in text:
        parts = text.split(" to ")
    elif "-" in text:
        parts = text.split("-")
    else:
        # Single time entry
        dt = dateparser.parse(text, settings=parse_settings)
        return dt, None

    start_dt = dateparser.parse(parts[0].strip(), settings=parse_settings)
    
    # Use the start_dt as the base for the end_dt to ensure they are on the same day
    if start_dt:
        parse_settings['RELATIVE_BASE'] = start_dt.replace(tzinfo=None)
        
    end_dt = dateparser.parse(parts[1].strip(), settings=parse_settings)
    
    # Fix for overnight shifts (e.g., 11pm to 7am)
    if start_dt and end_dt and end_dt < start_dt:
        end_dt += timedelta(days=1)
        
    return start_dt, end_dt

# --- MAIN LAYOUT ---
col_input, col_display = st.columns([1, 1.5], gap="large")

# --- LEFT COLUMN: INPUT ---
with col_input:
    st.subheader("➕ Add New Shift")
    st.info(f"Current Local Time: {datetime.now(BELGIUM_TZ).strftime('%H:%M')}")
    
    voice_input = st.text_input("Speak/Type:", placeholder="e.g. Today 14:15 to 19:30", key="input")
    
    if st.button("🚀 Log Shift", use_container_width=True):
        if voice_input:
            with st.spinner("Syncing to GitHub..."):
                start, end = parse_shift_text(voice_input)
                
                if start:
                    cal, sha = get_calendar_from_github()
                    
                    # If no end time given, default to 8 hours
                    final_end = end if end else (start + timedelta(hours=8))
                    
                    event = Event(
                        name="Work Shift",
                        begin=start,
                        end=final_end
                    )
                    
                    cal.events.add(event)
                    push_to_github(cal, sha)
                    
                    st.success(f"✅ Saved in Belgium Time!")
                    st.write(f"**Start:** {start.strftime('%A, %d %b at %H:%M')}")
                    st.write(f"**End:** {final_end.strftime('%H:%M')}")
                    st.rerun()
                else:
                    st.error("I didn't understand that date. Try 'Monday 8am to 4pm'.")

    st.divider()
    st.subheader("🔗 Outlook/Google Link")
    raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FILE_PATH}"
    st.code(raw_url)

# --- RIGHT COLUMN: DATA & CALENDAR ---
with col_display:
    cal_obj, _ = get_calendar_from_github()
    
    event_list = []
    calendar_events = []
    
    # Convert all events back to Belgium Time for the visual display
    sorted_events = sorted(cal_obj.events, key=lambda x: x.begin, reverse=True)
    
    for e in sorted_events:
        # ics library datetimes are often in UTC, we convert to Belgium
        b_start = e.begin.datetime.astimezone(BELGIUM_TZ)
        b_end = e.end.datetime.astimezone(BELGIUM_TZ)
        
        event_list.append({
            "Date": b_start.strftime("%d/%m/%Y (%a)"),
            "Shift Time": f"{b_start.strftime('%H:%M')} - {b_end.strftime('%H:%M')}"
        })
        
        calendar_events.append({
            "title": f"Shift {b_start.strftime('%H:%M')}",
            "start": b_start.isoformat(),
            "end": b_end.isoformat(),
        })

    st.subheader("📅 Your Schedule")
    # Show Graphical Calendar
    calendar(events=calendar_events, options={"initialView": "dayGridMonth", "timeZone": "Europe/Brussels"}, key="calendar")

    st.subheader("📋 Recent Entries")
    if event_list:
        st.dataframe(pd.DataFrame(event_list), use_container_width=True, hide_index=True)
    else:
        st.write("No shifts logged yet.")
