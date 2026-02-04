import streamlit as st
import pandas as pd
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- ⚙️ PAGE CONFIG ---
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

# --- 🧠 PARSER FUNCTION ---
def parse_whatsapp_text(text):
    data = {}
    text = text.replace("✅", "").replace("*", "")
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    try:
        # Venue
        for line in lines:
            if ":" in line and ("AM" in line or "PM" in line) and "Score" not in line:
                data['Venue'] = line.split(":")[0].strip()
                break
        
        # Score
        for line in lines:
            if "Score:" in line:
                scores = re.findall(r'\d+', line)
                if len(scores) >= 2:
                    data['Score_Blue'] = int(scores[0])
                    data['Score_Red'] = int(scores[1])
                break

        # Cost
        for line in lines:
            if "Cost" in line:
                if "=" in line:
                    cost_part = line.split("=")[-1].strip()
                    data['Cost'] = float(re.findall(r"[\d\.]+", cost_part)[0])
                else:
                    data['Cost'] = float(re.findall(r"[\d\.]+", line)[-1])
                break

        # Players
        blue_players = []
        red_players = []
        blue_idx, red_idx = -1, -1
        
        for i, line in enumerate(lines):
            if "Blue:" in line: blue_idx = i
            if "Red:" in line: red_idx = i
            
        if blue_idx != -1 and red_idx != -1:
            first_idx, first_list = (blue_idx, blue_players) if blue_idx < red_idx else (red_idx, red_players)
            second_idx, second_list = (red_idx, red_players) if blue_idx < red_idx else (blue_idx, blue_players)
            
            for i in range(first_idx + 1, second_idx):
                name = lines[i].strip()
                if name and ":" not in name: first_list.append(name)
            
            for i in range(second_idx + 1, len(lines)):
                name = lines[i].strip()
                if name: second_list.append(name)

        data['Blue_Players'] = blue_players
        data['Red_Players'] = red_players
        return data

    except Exception:
        return None

# --- 🔓 ADMIN DASHBOARD ---
st.title("🛡️ Match Logger")

conn = st.connection("gsheets", type=GSheetsConnection)

# 🟢 THE FIX: Use Index 1 (Integer) for the second tab
try:
    history_df = conn.read(worksheet=1, ttl=0)
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# --- 📝 INPUT SECTION ---
col_paste, col_preview = st.columns([1, 1])

with col_paste:
    st.subheader("1. Paste WhatsApp Text")
    raw_text = st.text_area("Paste here...", height=300)
    parsed_data = {}
    if raw_text:
        parsed_data = parse_whatsapp_text(raw_text)
        if parsed_data:
            st.success("✅ Text Processed!")

with col_preview:
    st.subheader("2. Verify Data")
    with st.form("save_match"):
        d_venue = parsed_data.get('Venue', 'BFC')
        d_cost = parsed_data.get('Cost', 0.0)
        d_s_blue = parsed_data.get('Score_Blue', 0)
        d_s_red = parsed_data.get('Score_Red', 0)
        d_p_blue = parsed_data.get('Blue_Players', [])
        d_p_red = parsed_data.get('Red_Players', [])

        date_played = st.date_input("Date Played", datetime.now())
        
        c1, c2 = st.columns(2)
        venue = c1.text_input("Venue", value=d_venue)
        cost = c2.number_input("Cost per Player (₹)", value=d_cost)
        
        st.markdown("---")
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("🟦 **BLUE TEAM**")
            score_blue = st.number_input("Blue Score", value=d_s_blue)
            players_blue = st.text_area("Blue Players", value="\n".join(d_p_blue), height=150)
            
        with c4:
            st.markdown("🟥 **RED TEAM**")
            score_red = st.number_input("Red Score", value=d_s_red)
            players_red = st.text_area("Red Players", value="\n".join(d_p_red), height=150)

        submitted = st.form_submit_button("💾 Save to Database")

        if submitted:
            p_blue_clean = [p.strip() for p in players_blue.split('\n') if p.strip()]
            p_red_clean = [p.strip() for p in players_red.split('\n') if p.strip()]
            str_blue = ", ".join(p_blue_clean)
            str_red = ", ".join(p_red_clean)
            
            if score_blue > score_red: winner = "Blue"
            elif score_red > score_blue: winner = "Red"
            else: winner = "Draw"

            new_row = pd.DataFrame([{
                "Date": date_played.strftime("%Y-%m-%d"),
                "Venue": venue,
                "Team_Blue": str_blue,
                "Team_Red": str_red,
                "Score_Blue": score_blue,
                "Score_Red": score_red,
                "Cost": cost,
                "Winner": winner
            }])
            
            updated_df = pd.concat([history_df, new_row], ignore_index=True)
            
            # 🟢 THE FIX: Use Index 1 here too
            conn.update(worksheet=1, data=updated_df)
            
            st.success("✅ Match Saved Successfully!")
            st.rerun()