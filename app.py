import streamlit as st
import dateparser
from ics import Calendar, Event
from github import Github
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Shift Logger", page_icon="📅")
st.title("🎙️ Voice Shift Logger")

# 1. Load your secret keys from Streamlit Settings
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    
    # This is your "Secret" filename for privacy
    FILE_PATH = "shift_data_secret_7x9z2.ics" 
    
except Exception:
    st.error("Missing Secrets! Go to Streamlit Settings > Secrets and add GITHUB_TOKEN and REPO_NAME.")
    st.stop()

# 2. Connect to GitHub
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

def get_calendar_from_github():
    try:
        file_content = repo.get_contents(FILE_PATH)
        return Calendar(file_content.decoded_content.decode()), file_content.sha
    except:
        # If the file doesn't exist yet, start a fresh calendar
        return Calendar(), None

def push_to_github(calendar, sha):
    content = "".join(calendar.serialize_iter())
    if sha:
        repo.update_file(FILE_PATH, "Update shifts", content, sha)
    else:
        repo.create_file(FILE_PATH, "Initial shift commit", content)

# --- USER INTERFACE ---
st.write("Tap the box and use your keyboard's **Voice Mic** to log a shift.")
voice_input = st.text_input("Example: 'Next Friday at 2pm'", key="input")

if st.button("Add to Calendar"):
    if voice_input:
        with st.spinner("Saving to GitHub..."):
            dt = dateparser.parse(voice_input)
            if dt:
                cal, sha = get_calendar_from_github()
                event = Event(name="Work Shift", begin=dt)
                cal.events.add(event)
                push_to_github(cal, sha)
                st.success(f"✅ Saved! Shift added for {dt.strftime('%A, %b %d at %I:%M %p')}")
            else:
                st.error("I didn't catch that date. Try saying something like 'Monday 8am'.")

# --- SYNC SECTION ---
st.divider()
st.subheader("🔗 Calendar Sync Link")
st.write("Copy this link and paste it into Google Calendar (Add by URL) or Outlook (Subscribe from Web):")

raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FILE_PATH}"
st.code(raw_url)

st.info("💡 Reminder: Make sure your GitHub Repository is set to 'Public' so your calendar app can read this file.")
