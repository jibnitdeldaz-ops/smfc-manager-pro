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
    Parses raw WhatsApp text to extract match details.
    """
    data = {}
    try:
        # 1. VENUE (Look for 🏟️)
        venue_match = re.search(r'🏟️\s*(.*)', text)
        if venue_match:
            data['venue'] = venue_match.group(1).strip()
        else:
            data['venue'] = "BFC" # Default

        # 2. SCORE (Look for "Score: Red 5-4 Blue" or similar)
        # We look for digits around a hyphen or "vs"
        score_match = re.search(r'Score.*?:.*?(\d+)\s*[-v]\s*(\d+)', text, re.IGNORECASE)
        if score_match:
            # We assume standard format is often Red first, but let's check text
            # If text says "Red 5-4 Blue", val1=Red. If "Blue 5-4 Red", val1=Blue.
            val1 = int(score_match.group(1))
            val2 = int(score_match.group(2))
            
            # Simple heuristic: find 'red' and 'blue' positions in the score line
            line_context = text[max(0, score_match.start()-20):score_match.end()+20].lower()
            red_idx = line_context.find('red')
            blue_idx = line_context.find('blue')
            
            if red_idx < blue_idx and red_idx != -1: # Red mentioned first
                data['s_red'] = val1
                data['s_blue'] = val2
            elif blue_idx < red_idx and blue_idx != -1: # Blue mentioned first
                data['s_blue'] = val1
                data['s_red'] = val2
            else:
                # Default fallback if colors not found nearby: Assume Red - Blue
                data['s_red'] = val1
                data['s_blue'] = val2

        # 3. PLAYERS
        # Strategy: Split text into "Red Section" and "Blue Section"
        # We look for "Red:" and "Blue:" keywords
        
        # Normalize text
        clean_text = text.replace('*', '') # Remove bolding asterisks
        
        # Find start indices
        r_start = re.search(r'Red:', clean_text, re.IGNORECASE)
        b_start = re.search(r'Blue:', clean_text, re.IGNORECASE)
        
        p_red = []
        p_blue = []

        if r_start and b_start:
            # Determine which comes first
            if r_start.start() < b_start.start():
                # Red is first block
                red_block = clean_text[r_start.end():b_start.start()]
                blue_block = clean_text[b_start.end():]
            else:
                # Blue is first block
                blue_block = clean_text[b_start.end():r_start.start()]
                red_block = clean_text[r_start.end():]

            # Helper to clean names
            def extract_names(block):
                names = []
                for line in block.split('\n'):
                    # Remove emojis, numbers, brackets
                    # Keep only letters and spaces
                    line = re.sub(r'[✅☑️\d\(\)@]', '', line) 
                    line = line.replace('Fine', '').replace(':', '').strip()
                    if len(line) > 2: # Ignore short garbage
                        names.append(line)
                return ", ".join(names)

            data['p_red'] = extract_names(red_block)
            data['p_blue'] = extract_names(blue_block)

    except Exception as e:
        print(f"Parser Error: {e}")
    
    return data

# --- 📥 DATA LOADING (SECURE) ---
def load_data_secure():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_players = conn.read(worksheet="Sheet1", ttl=0)
        official_names = set([str(n).strip() for n in df_players['Name'].dropna().unique().tolist()])
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
    # --- THEME ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@700;900&display=swap');
        .stApp { background-color: #0e1117; font-family: 'Rajdhani', sans-serif; background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%); color: #e0e0e0; }
        h1, h2, h3 { font-family: 'Rajdhani', sans-serif !important; text-transform: uppercase; color: #FF5722 !important; text-shadow: 0 0 20px rgba(255, 87, 34, 0.3); }
        div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 87, 34, 0.2); border-radius: 12px; padding: 15px; }
        div[data-testid="stMetric"] label { color: #FF5722 !important; font-weight: 800 !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 900 !important; }
        div.stButton > button { background: linear-gradient(90deg, #D84315 0%, #FF5722 100%); color: white !important; font-weight: 900 !important; border: none; height: 50px; text-transform: uppercase; }
        /* Expander Styling */
        .streamlit-expanderHeader { font-family: 'Rajdhani', sans-serif; font-weight: bold; color: #FF5722 !important; font-size: 18px; }
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

    # --- ⚙️ HIDDEN ADMIN ZONE ---
    # This matches your request: Hidden by default, expands when clicked
    with st.expander("⚙️ ADMIN ZONE (Log Match Results)", expanded=False):
        
        # Initialize Session State for Auto-Fill
        if 'form_venue' not in st.session_state: st.session_state['form_venue'] = "BFC"
        if 'form_sb' not in st.session_state: st.session_state['form_sb'] = 0
        if 'form_sr' not in st.session_state: st.session_state['form_sr'] = 0
        if 'form_pb' not in st.session_state: st.session_state['form_pb'] = ""
        if 'form_pr' not in st.session_state: st.session_state['form_pr'] = ""

        # --- TWO TABS ---
        tab_paste, tab_manual = st.tabs(["📋 WHATSAPP PASTE", "✍️ MANUAL ENTRY"])

        # TAB 1: PASTE
        with tab_paste:
            st.info("Paste the full WhatsApp match summary here:")
            wa_text = st.text_area("WhatsApp Chat", height=200, placeholder="Saturday Football\n🏟️ BFC\nScore: Red 5-4 Blue...")
            
            if st.button("🔮 PARSE & FILL FORM", key="btn_parse"):
                parsed = parse_whatsapp_log(wa_text)
                if parsed:
                    # Update State Variables
                    if 'venue' in parsed: st.session_state['form_venue'] = parsed['venue']
                    if 's_blue' in parsed: st.session_state['form_sb'] = parsed['s_blue']
                    if 's_red' in parsed: st.session_state['form_sr'] = parsed['s_red']
                    if 'p_blue' in parsed: st.session_state['form_pb'] = parsed['p_blue']
                    if 'p_red' in parsed: st.session_state['form_pr'] = parsed['p_red']
                    
                    st.success("✅ Data Parsed! Switch to 'Manual Entry' tab to verify and Save.")
                else:
                    st.warning("⚠️ Parser couldn't find data. Please enter manually.")

        # TAB 2: MANUAL / SAVE
        with tab_manual:
            with st.form("final_save_form"):
                c1, c2 = st.columns(2)
                date_in = c1.date_input("Date", datetime.today())
                venue = c2.text_input("Venue", key="form_venue")
                
                col_b, col_r = st.columns(2)
                with col_b:
                    st.markdown("#### 🔵 BLUE TEAM")
                    s_blue = st.number_input("Goals", min_value=0, key="form_sb")
                    p_blue = st.text_area("Players", height=100, key="form_pb")
                with col_r:
                    st.markdown("#### 🔴 RED TEAM")
                    s_red = st.number_input("Goals", min_value=0, key="form_sr")
                    p_red = st.text_area("Players", height=100, key="form_pr")
                    
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
                            st.success("✅ Saved Successfully! Refreshing...")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("❌ Wrong Password")