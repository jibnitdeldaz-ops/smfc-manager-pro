import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Connection Test", layout="wide")

st.title("🔌 Connection Diagnostic")

# 1. Initialize Connection
try:
    conn = st.connection("gsheets", type=GSheetsConnection) 
    st.write("✅ Connection Strategy: GSheetsConnection (Service Account)")
except Exception as e:
    st.error(f"❌ Failed: {e}")
    st.stop()

# 2. Try Reading Sheet1 (The Player List)
st.write("---")
st.write("📂 **Attempting to read 'Sheet1' (Player List)...**")

try:
    # We use the name "Sheet1" -> GSheetsConnection
    df_players = conn.read(worksheet="Sheet1", ttl=0)
    st.success(f"✅ Success! Read {len(df_players)} rows from Sheet1 (Service Account).")
    st.dataframe(df_players.head(3))
except Exception as e:
    st.error("❌ Failed to read Sheet1.")
    st.code(str(e))

# 3. Try Reading Tab 2 (The Log)
st.write("---")
st.write("📂 **Attempting to read Tab #2 (Index 1)...**")

try:
    # Tab 2 (Log)
    # Using index 1 (Tab #2)
    df_log = conn.read(worksheet=1, ttl=0)
    st.success(f"✅ Success! Read {len(df_log)} rows from Tab 2.")
    st.dataframe(df_log.head(3))
except Exception as e:
    st.warning("⚠️ Could not read Tab 2.")
    st.code(str(e))