import streamlit as st
import dateparser
from ics import Calendar, Event
from github import Github
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Shift Logger", page_icon="📅")
st.title("🎙️ Voice Shift Logger")

# Load secrets
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "my_shifts.ics"
except Exception:
    st.error("Please set up GITHUB_TOKEN and REPO_NAME in Streamlit Secrets!")
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

# --- UI ---
st.write("Tap the box and use your keyboard's **Voice Mic**.")
voice_input = st.text_input("Example: 'Morning shift tomorrow at 8am'", key="input")

if st.button("Add to Calendar"):
    if voice_input:
        with st.spinner("Syncing with GitHub..."):
            dt = dateparser.parse(voice_input)
            if dt:
                cal, sha = get_calendar_from_github()
                event = Event(name="Work Shift", begin=dt)
                cal.events.add(event)
                push_to_github(cal, sha)
                st.success(f"✅ Added: {dt.strftime('%A, %b %d at %I:%M %p')}")
            else:
                st.error("Couldn't understand the date. Try 'Monday 8am'.")

# --- SYNC INSTRUCTIONS ---
st.divider()
st.subheader("🔗 How to Sync to Google/Outlook")
st.write("To make the calendar update automatically, use the **Raw** URL from GitHub.")

# Generate the Raw URL (Note: Private repos require a token in the URL for external apps)
# For simplicity, if you make the REPO 'Public', this link works instantly:
raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FILE_PATH}"
st.info("Copy this link into your Calendar settings:")
st.code(raw_url)

st.warning("⚠️ **Note:** If your repo is Private, Google/Outlook cannot see this link. "
           "For the easiest sync, set your GitHub Repository to **Public** in the repo settings.")
