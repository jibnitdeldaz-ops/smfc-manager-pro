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

# --- 🧠 PARSER FUNCTION (The Magic Logic) ---
def parse_whatsapp_text(text):
    data = {}
    
    # 1. CLEANUP: Remove "✅" and extra spaces
    text = text.replace("✅", "").replace("*", "")
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    try:
        # 2. EXTRACT VENUE & TIME (Assumes format "BFC: 7:30 AM")
        for line in lines:
            if ":" in line and ("AM" in line or "PM" in line) and "Score" not in line:
                data['Venue'] = line.split(":")[0].strip()
                break
        
        # 3. EXTRACT SCORE (Assumes format "Score: Blue 5-7 Red")
        for line in lines:
            if "Score:" in line:
                # Find all numbers in the string
                scores = re.findall(r'\d+', line)
                if len(scores) >= 2:
                    data['Score_Blue'] = int(scores[0])
                    data['Score_Red'] = int(scores[1])
                break

        # 4. EXTRACT COST (Assumes format "Cost per player: ... = 241.8")
        for line in lines:
            if "Cost" in line:
                # Look for the number after the "=" sign first
                if "=" in line:
                    cost_part = line.split("=")[-1].strip()
                    data['Cost'] = float(re.findall(r"[\d\.]+", cost_part)[0])
                else:
                    # Fallback: look for the last number in line
                    data['Cost'] = float(re.findall(r"[\d\.]+", line)[-1])
                break

        # 5. EXTRACT PLAYERS
        # We split the big text block by "Blue:" and "Red:" keywords
        # This is a bit tricky, but robust for the format you showed
        blue_players = []
        red_players = []
        
        # Find where the lists start
        blue_idx = -1
        red_idx = -1
        
        for i, line in enumerate(lines):
            if "Blue:" in line: blue_idx = i
            if "Red:" in line: red_idx = i
            
        # If we found markers, grab names between them
        if blue_idx != -1 and red_idx != -1:
            # Assuming Blue comes before Red usually, but let's handle order
            first_idx, first_list = (blue_idx, blue_players) if blue_idx < red_idx else (red_idx, red_players)
            second_idx, second_list = (red_idx, red_players) if blue_idx < red_idx else (blue_idx, blue_players)
            
            # Read from First Marker to Second Marker
            for i in range(first_idx + 1, second_idx):
                name = lines[i].strip()
                if name and ":" not in name: # Avoid reading "Gpay:" as a name
                    first_list.append(name)
            
            # Read from Second Marker to End
            for i in range(second_idx + 1, len(lines)):
                name = lines[i].strip()
                if name:
                    second_list.append(name)

        data['Blue_Players'] = blue_players
        data['Red_Players'] = red_players
        
        return data

    except Exception as e:
        st.error(f"Error parsing text: {e}")
        return None

# --- 🔓 ADMIN DASHBOARD ---
st.title("🛡️ Match Logger")
st.caption("Paste the WhatsApp summary to auto-fill the database.")

conn = st.connection("gsheets", type=GSheetsConnection)
try:
    history_df = conn.read(worksheet="1", ttl=0)
except:
    st.error("⚠️ 'Log' tab not found in Google Sheets.")
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
        # Auto-fill form values if parser worked, otherwise defaults
        d_venue = parsed_data.get('Venue', 'BFC')
        d_cost = parsed_data.get('Cost', 0.0)
        d_s_blue = parsed_data.get('Score_Blue', 0)
        d_s_red = parsed_data.get('Score_Red', 0)
        d_p_blue = parsed_data.get('Blue_Players', [])
        d_p_red = parsed_data.get('Red_Players', [])

        # DATE (Manual selection is safer than parsing dates usually)
        date_played = st.date_input("Date Played", datetime.now())
        
        c1, c2 = st.columns(2)
        venue = c1.text_input("Venue", value=d_venue)
        cost = c2.number_input("Cost per Player (₹)", value=d_cost)
        
        st.markdown("---")
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("🟦 **BLUE TEAM**")
            score_blue = st.number_input("Blue Score", value=d_s_blue)
            # Join list to string for editing, then split back for saving if needed
            players_blue = st.text_area("Blue Players (Edit if needed)", value="\n".join(d_p_blue), height=150)
            
        with c4:
            st.markdown("🟥 **RED TEAM**")
            score_red = st.number_input("Red Score", value=d_s_red)
            players_red = st.text_area("Red Players (Edit if needed)", value="\n".join(d_p_red), height=150)

        submitted = st.form_submit_button("💾 Save to Database")

        if submitted:
            # 1. Clean up player lists (convert back to comma-string)
            p_blue_clean = [p.strip() for p in players_blue.split('\n') if p.strip()]
            p_red_clean = [p.strip() for p in players_red.split('\n') if p.strip()]
            
            str_blue = ", ".join(p_blue_clean)
            str_red = ", ".join(p_red_clean)
            
            # 2. Determine Winner
            if score_blue > score_red: winner = "Blue"
            elif score_red > score_blue: winner = "Red"
            else: winner = "Draw"

            # 3. Create Row
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
            
            # 4. DUPLICATE CHECK (Prevent double pasting)
            # We check if a match on this Date with these exact Scores exists
            is_dup = False
            if not history_df.empty:
                # Check for same date AND same scores
                # (You can make this stricter by checking venue too)
                mask = (history_df['Date'] == new_row['Date'].iloc[0]) & \
                       (history_df['Score_Blue'] == score_blue) & \
                       (history_df['Score_Red'] == score_red)
                if not history_df[mask].empty:
                    is_dup = True
            
            if is_dup:
                st.error("⚠️ DUPLICATE! This match seems to be already saved.")
            else:
                updated_df = pd.concat([history_df, new_row], ignore_index=True)
                conn.update(worksheet="1", data=updated_df)
                st.success("✅ Match Saved Successfully!")
                st.rerun()

# --- 📊 MINI LOG (To see what's inside) ---
st.markdown("---")
st.subheader("📚 Recent Database Entries")
st.dataframe(history_df.tail(3), use_container_width=True)