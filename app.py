import streamlit as st
import dateparser
from ics import Calendar, Event
from github import Github
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Shift Logger", page_icon="📅")
st.title("🎙️ Voice Shift Logger")

try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "shift_data_secret_7x9z2.ics" 
except Exception:
    st.error("Missing Secrets in Streamlit Settings!")
    st.stop()

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

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

# --- SMART PARSER ---
def parse_shift_text(text):
    text = text.lower()
    start_dt, end_dt = None, None
    
    # Check if user said "to" or "-" (e.g., "8am to 4pm")
    if " to " in text:
        parts = text.split(" to ")
    elif "-" in text:
        parts = text.split("-")
    else:
        # Single time mentioned
        return dateparser.parse(text), None

    start_str = parts[0].replace("from", "").strip()
    end_str = parts[1].strip()

    start_dt = dateparser.parse(start_str)
    end_dt = dateparser.parse(end_str, settings={'RELATIVE_BASE': start_dt}) if start_dt else dateparser.parse(end_str)

    # If end_dt is before start_dt (e.g., 11pm to 7am), it's likely the next day
    if start_dt and end_dt and end_dt < start_dt:
        from datetime import timedelta
        end_dt += timedelta(days=1)

    return start_dt, end_dt

# --- USER INTERFACE ---
voice_input = st.text_input("Speak/Type your shift:", placeholder="e.g. Today 2:15pm to 7:30pm", key="input")

if st.button("🚀 Add Shift"):
    if voice_input:
        with st.spinner("Processing..."):
            start, end = parse_shift_text(voice_input)
            
            if start:
                cal, sha = get_calendar_from_github()
                event = Event(name="Work Shift", begin=start)
                if end:
                    event.end = end
                
                cal.events.add(event)
                push_to_github(cal, sha)
                
                success_msg = f"✅ Added: {start.strftime('%b %d, %I:%M %p')}"
                if end:
                    success_msg += f" to {end.strftime('%I:%M %p')}"
                st.success(success_msg)
            else:
                st.error("Could not understand the time. Try 'Monday 8am to 4pm'.")

# --- SYNC SECTION ---
st.divider()
st.subheader("🔗 Outlook/Google Sync Link")
st.info("Copy the URL below. In Outlook, go to 'Add Calendar' -> 'Subscribe from Web' and paste it.")

# GENERATE THE CORRECT LINK
# Note: Ensure your GitHub Repo is PUBLIC for this link to work in Outlook!
raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FILE_PATH}"
st.code(raw_url)
