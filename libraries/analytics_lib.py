import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os
import base64
import re

# --- 🎨 HELPER: IMAGE LOADING ---
def get_img_as_base64(file):
    if os.path.exists(file):
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

# --- 🧠 SMART PARSER: WHATSAPP TO DATA ---
def parse_whatsapp_log(text):
    """
    Extracts Date, Venue, Scores, and Players from the standard WhatsApp paste.
    Returns a dictionary of found values.
    """
    data = {}
    
    try:
        # 1. DATE (📅 Saturday, September 16, 2023)
        date_match = re.search(r'📅\s*(.*)', text)
        if date_match:
            try:
                # Remove brackets like (Ganesh Chaturthi Cup) and parse
                dt_str = re.sub(r'\(.*?\)', '', date_match.group(1).strip()).strip()
                data['date'] = pd.to_datetime(dt_str).date()
            except:
                pass # Keep default if fail

        # 2. VENUE (🏟️ Venue: MKR Arena)
        venue_match = re.search(r'🏟️\s*(?:Venue:)?\s*(.*)', text)
        if venue_match:
            data['venue'] = venue_match.group(1).strip()

        # 3. SCORES (⚽ Score: Red 8 - 5 Blue)
        score_match = re.search(r'⚽.*Score:\s*(.*)', text, re.IGNORECASE)
        if score_match:
            score_line = score_match.group(1)
            # Find all numbers
            nums = re.findall(r'\d+', score_line)
            if len(nums) >= 2:
                # Logic: Check if "Red" or "Blue" appears first to assign scores correctly
                red_idx = score_line.lower().find('red')
                blue_idx = score_line.lower().find('blue')
                
                val1, val2 = int(nums[0]), int(nums[1])
                
                if red_idx < blue_idx: # "Red 8 - 5 Blue"
                    data['s_red'], data['s_blue'] = val1, val2
                else: # "Blue 5 - 8 Red"
                    data['s_blue'], data['s_red'] = val1, val2

        # 4. PLAYERS (🔴 Red Team: ... / 🔵 Blue Team: ...)
        # We look for the emoji and capture text until the next newline
        red_team_match = re.search(r'🔴.*?:(.*?)(?:\n|$)', text)
        if red_team_match:
            data['p_red'] = red_team_match.group(1).strip()
            
        blue_team_match = re.search(r'[🔵🟢].*?:(.*?)(?:\n|$)', text)
        if blue_team_match:
            data['p_blue'] = blue_team_match.group(1).strip()

    except Exception as e:
        st.error(f"Parser Error: {e}")
    
    return data

# --- 📥 DATA LOADING (SECURE) ---
def load_data_secure():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Load Official Roster
        df_players = conn.read(worksheet="Sheet1", ttl=0)
        official_names = set([str(n).strip() for n in df_players['Name'].dropna().unique().tolist()])
        # Load Match History
        df_matches = conn.read(worksheet="Match_History", ttl=0)
        return conn, official_names, df_matches
    except Exception as e:
        return None, set(), pd.DataFrame()

# --- 🧠 STATS ENGINE ---
def calculate_leaderboard(df_matches, official_names):
    if df_matches.empty: return pd.DataFrame()

    stats = {}
    for index, row in df_matches.iterrows():
        winner = row['Winner']
        blue_team = [x.strip() for x in str(row['Team_Blue']).split(',') if x.strip()]
        red_team = [x.strip() for x in str(row['Team_Red']).split(',') if x.strip()]

        def update(player_name, team_color):
            if player_name not in official_names: return
            if player_name not in stats: stats[player_name] = {'M': 0, 'W': 0, 'L': 0, 'D': 0, 'Form': []}
            
            p = stats[player_name]
            p['M'] += 1
            
            if winner == team_color: p['W'] += 1; res='W'
            elif winner == 'Draw': p['D'] += 1; res='D'
            else: p['L'] += 1; res='L'
            p['Form'].append(res)

        for p in blue_team: update(p, 'Blue')
        for p in red_team: update(p, 'Red')

    if not stats: return pd.DataFrame()
    
    res = pd.DataFrame.from_dict(stats, orient='index')
    res['Win %'] = ((res['W'] / res['M']) * 100).round(0).astype(int)
    icon_map = {'W': '✅', 'L': '❌', 'D': '➖'}
    res['Form (Last 5)'] = res['Form'].apply(lambda x: " ".join([icon_map.get(i, i) for i in x[-5:]]))
    
    return res.sort_values(by=['W', 'Win %'], ascending=False)

# --- 🚀 MAIN UI FUNCTION ---
def run_analytics_app():
    # --- THEME: ORANGE DNA ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@700;900&display=swap');
        .stApp { background-color: #0e1117; font-family: 'Rajdhani', sans-serif; background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%); color: #e0e0e0; }
        h1, h2, h3 { font-family: 'Rajdhani', sans-serif !important; text-transform: uppercase; color: #FF5722 !important; text-shadow: 0 0 20px rgba(255, 87, 34, 0.3); }
        div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 87, 34, 0.2); border-radius: 12px; padding: 15px; }
        div[data-testid="stMetric"] label { color: #FF5722 !important; font-weight: 800 !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 900 !important; }
        div.stButton > button { background: linear-gradient(90deg, #D84315 0%, #FF5722 100%); color: white !important; font-weight: 900 !important; border: none; height: 50px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    c1, c2 = st.columns([1, 5])
    with c2:
        st.markdown("# SMFC ANALYTICS HUB")
        st.caption("OFFICIAL MATCH RECORDS & PLAYER STATISTICS")

    # --- LOAD DATA ---
    conn, official_roster, df_matches = load_data_secure()

    # --- METRICS ---
    total_goals = 0
    if not df_matches.empty:
        total_goals = pd.to_numeric(df_matches['Score_Blue'], errors='coerce').sum() + pd.to_numeric(df_matches['Score_Red'], errors='coerce').sum()
        df_matches['Date'] = pd.to_datetime(df_matches['Date'])
        df_matches = df_matches.sort_values(by='Date', ascending=False)
        df_matches['Display_Date'] = df_matches['Date'].dt.strftime('%A, %d %b')
    
    m1, m2, m3 = st.columns(3)
    m1.metric("MATCHES PLAYED", len(df_matches))
    m2.metric("GOALS SCORED", int(total_goals))
    m3.metric("ACTIVE PLAYERS", len(official_roster))
    st.write("---")

    # --- LEADERBOARD ---
    st.markdown("### 🏆 PLAYER LEADERBOARD")
    leaderboard = calculate_leaderboard(df_matches, official_roster)
    if not leaderboard.empty:
        st.dataframe(leaderboard[['M', 'W', 'L', 'D', 'Win %', 'Form (Last 5)']], width='stretch', height=500)
    else:
        st.info("No stats available. Log a match to begin.")

    st.write("---")

    # --- ⚙️ ADMIN ZONE (HIDDEN IN EXPANDER) ---
    with st.expander("⚙️ ADMIN ZONE (Log Match Results)", expanded=False):
        st.markdown("### 📝 LOG MATCH")
        
        # Initialize Session State
        if 'form_date' not in st.session_state: st.session_state['form_date'] = datetime.today()
        if 'form_venue' not in st.session_state: st.session_state['form_venue'] = "BFC"
        if 'form_sb' not in st.session_state: st.session_state['form_sb'] = 0
        if 'form_sr' not in st.session_state: st.session_state['form_sr'] = 0
        if 'form_pb' not in st.session_state: st.session_state['form_pb'] = ""
        if 'form_pr' not in st.session_state: st.session_state['form_pr'] = ""

        # --- TABS: PASTE VS MANUAL ---
        tab_paste, tab_manual = st.tabs(["📋 WHATSAPP PASTE", "✍️ MANUAL ENTRY"])

        with tab_paste:
            st.info("Paste the WhatsApp summary here:")
            wa_text = st.text_area("WhatsApp Text", height=150, placeholder="📅 Saturday...\n⚽ Score: Red 5 - 4 Blue...")
            
            if st.button("🔮 AUTO-FILL FORM", key="btn_parse"):
                parsed = parse_whatsapp_log(wa_text)
                if parsed:
                    # Auto-fill the state variables
                    if 'date' in parsed: st.session_state['form_date'] = parsed['date']
                    if 'venue' in parsed: st.session_state['form_venue'] = parsed['venue']
                    if 's_blue' in parsed: st.session_state['form_sb'] = parsed['s_blue']
                    if 's_red' in parsed: st.session_state['form_sr'] = parsed['s_red']
                    if 'p_blue' in parsed: st.session_state['form_pb'] = parsed['p_blue']
                    if 'p_red' in parsed: st.session_state['form_pr'] = parsed['p_red']
                    st.success("✅ Parsed! Check the Manual Entry tab to verify.")
                else:
                    st.warning("⚠️ Could not read data. Try manual entry.")

        with tab_manual:
            with st.form("final_save_form"):
                c1, c2 = st.columns(2)
                # Link widgets to session_state so they get filled
                date_in = c1.date_input("Date", key="form_date")
                venue = c2.text_input("Venue", key="form_venue")
                
                col_b, col_r = st.columns(2)
                with col_b:
                    st.markdown("#### 🔵 BLUE TEAM")
                    s_blue = st.number_input("Goals", min_value=0, key="form_sb")
                    p_blue = st.text_area("Players", height=80, key="form_pb")
                with col_r:
                    st.markdown("#### 🔴 RED TEAM")
                    s_red = st.number_input("Goals", min_value=0, key="form_sr")
                    p_red = st.text_area("Players", height=80, key="form_pr")
                    
                st.write("---")
                password = st.text_input("🔑 ADMIN PASSWORD", type="password")
                
                if st.form_submit_button("💾 SAVE RECORD"):
                    if password == st.secrets["passwords"]["admin"]:
                        if s_blue > s_red: winner = "Blue"
                        elif s_red > s_blue: winner = "Red"
                        else: winner = "Draw"
                        
                        new_row = pd.DataFrame([{
                            "Date": date_in.strftime("%Y-%m-%d"),
                            "Venue": venue,
                            "Team_Blue": p_blue,
                            "Team_Red": p_red,
                            "Score_Blue": s_blue,
                            "Score_Red": s_red,
                            "Winner": winner
                        }])
                        
                        try:
                            updated = pd.concat([df_matches.drop(columns=['Display_Date'], errors='ignore'), new_row], ignore_index=True)
                            conn.update(worksheet="Match_History", data=updated)
                            st.success("✅ Saved!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("❌ Wrong Password")