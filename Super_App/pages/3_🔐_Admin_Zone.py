import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Connection Test", layout="wide")

st.title("🔌 Connection Diagnostic")

# 1. Initialize Connection
try:
    # conn = st.connection("gsheets", type=GSheetsConnection) 
    # Using Direct CSV method now for reliability
    st.write("✅ Connection Strategy: Direct CSV Export (Public Sheet)")
except Exception as e:
    st.error(f"❌ Failed: {e}")
    st.stop()

# 2. Try Reading Sheet1 (The Player List)
st.write("---")
st.write("📂 **Attempting to read 'Sheet1' (Player List)...**")

try:
    # We use the name "Sheet1" -> GID 0
    sheet_id = "1-ShO5kfDdPH4FxSX-S9tyUNeyLAIOHi44NePaKff7Lw"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    df_players = pd.read_csv(url)
    st.success(f"✅ Success! Read {len(df_players)} rows from Sheet1 (Public CSV).")
    st.dataframe(df_players.head(3))
except Exception as e:
    st.error("❌ Failed to read Sheet1.")
    st.code(str(e))

# 3. Try Reading Tab 2 (The Log)
st.write("---")
st.write("📂 **Attempting to read Tab #2 (Index 1)...**")

try:
    # Tab 2 (Log) - Assuming GID from user link or just skipping
    # Attempting to read GID from user provided link: 654281007
    sheet_id = "1-ShO5kfDdPH4FxSX-S9tyUNeyLAIOHi44NePaKff7Lw"
    url_tab2 = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=654281007"
    df_log = pd.read_csv(url_tab2)
    st.success(f"✅ Success! Read {len(df_log)} rows from Tab 2 (GID 654281007).")
    st.dataframe(df_log.head(3))
except Exception as e:
    st.warning("⚠️ Could not read Tab 2 (Check GID).")
    st.code(str(e))