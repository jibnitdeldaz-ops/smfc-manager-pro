import streamlit as st
import sys
import os

# --- 🔧 PERISCOPE FIX: Add Project Root to Path ---
# This tells Python: "Look 2 levels up (../../) to find the 'libraries' folder"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Now we can import from the shared 'libraries' folder!
from libraries.analytics_lib import run_analytics_app

# Set config immediately
st.set_page_config(page_title="SMFC Analytics", page_icon="📊", layout="wide")

# Run the app from the library
run_analytics_app()