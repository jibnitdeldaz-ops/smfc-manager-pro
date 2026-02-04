import streamlit as st
import sys
import os

# --- 🔧 PERISCOPE FIX: Add Project Root to Path ---
# This looks 2 levels up to find the 'libraries' folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the football app logic
from libraries.football_lib import run_football_app

# Set Page Config (Single time setup)
st.set_page_config(page_title="SMFC Manager", page_icon="⚽", layout="wide")

# Run the App
run_football_app()