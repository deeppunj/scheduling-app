import streamlit as st
import dateparser
from ics import Calendar, Event
from datetime import datetime
import os

st.set_page_config(page_title="Shift Logger", page_icon="📅")
st.title("🎙️ Voice Shift Logger")

# File to store the calendar
ICS_FILE = "my_shifts.ics"

def get_calendar():
    if os.path.exists(ICS_FILE):
        with open(ICS_FILE, "r") as f:
            return Calendar(f.read())
    return Calendar()

def save_calendar(cal):
    with open(ICS_FILE, "w") as f:
        f.writelines(cal.serialize_iter())

# UI Input
st.write("Tap the box below and use your keyboard's **Voice Mic** to say your shift.")
voice_input = st.text_input("Example: 'Next Wednesday at 2pm'", key="input")

if st.button("Add to Calendar"):
    if voice_input:
        dt = dateparser.parse(voice_input)
        if dt:
            cal = get_calendar()
            event = Event(name="Work Shift", begin=dt)
            cal.events.add(event)
            save_calendar(cal)
            st.success(f"Added: {dt.strftime('%A, %b %d at %I:%M %p')}")
        else:
            st.error("Could not understand that date. Try being more specific!")

# Provide the public link for Syncing
st.divider()
st.subheader("🔗 Sync Link")
st.info("Copy this URL into Google/Outlook Calendar settings:")
# This will be your app's URL + /raw
st.code("https://your-app-name.streamlit.app/raw")