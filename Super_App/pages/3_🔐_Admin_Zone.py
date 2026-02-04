import streamlit as st
import pandas as pd
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Admin Zone", page_icon="🔐", layout="wide")

# --- 🔐 SECURITY ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    password = st.text_input("Enter Admin Password", type="password")
    if st.button("Unlock System"):
        if password == st.secrets["passwords"]["admin"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("⛔ Access Denied")

if not st.session_state.authenticated:
    st.title("🔐 Restricted Access")
    check_password()
    st.stop()

# --- 🕵️‍♂️ DEBUG CONNECTION TEST ---
st.title("🛡️ Match Logger (Debug Mode)")

conn = st.connection("gsheets", type=GSheetsConnection)

st.write("1️⃣ Attempting to connect to file...")

# TEST 1: Read Sheet1 (Player List) - verifying file access
# We know this works for the other app, so it SHOULD work here.
st.info("Reading Sheet1 (Players)...")
players_df = conn.read(worksheet="Sheet1", usecols=[0], ttl=0)
st.success(f"✅ Sheet1 Found! Loaded {len(players_df)} rows.")

# TEST 2: Read Match_History - verifying tab access
st.info("Reading Match_History tab...")

# ⚠️ NO TRY/EXCEPT BLOCK HERE!
# If this fails, we WANT to see the big red error box.
history_df = conn.read(worksheet="Match_History", ttl=0)

st.success(f"✅ Match_History Found! Loaded {len(history_df)} rows.")
st.dataframe(history_df)

# --- IF WE GET HERE, IT WORKS! ---
# (Rest of the manual entry form code would go here, 
# but let's just fix the connection first).