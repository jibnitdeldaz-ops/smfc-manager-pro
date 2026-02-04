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

# --- 📥 DATA LOADING (THE BOUNCER LOGIC) ---
def load_data_secure():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. Load Official Roster (The VIP List)
        df_players = conn.read(worksheet="Sheet1", ttl=0)
        # Create a set of "Cleaned" names for strict checking
        official_names = set([str(n).strip() for n in df_players['Name'].dropna().unique().tolist()])
        
        # 2. Load Match History
        df_matches = conn.read(worksheet="Match_History", ttl=0)
        
        return conn, official_names, df_matches
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None, set(), pd.DataFrame()

# --- 🧠 STATS ENGINE ---
def calculate_leaderboard(df_matches, official_names):
    if df_matches.empty:
        return pd.DataFrame()

    stats = {}

    for index, row in df_matches.iterrows():
        winner = row['Winner'] # Red, Blue, Draw
        
        # Parse Lists
        blue_team = [x.strip() for x in str(row['Team_Blue']).split(',') if x.strip()]
        red_team = [x.strip() for x in str(row['Team_Red']).split(',') if x.strip()]

        # --- INTERNAL FUNCTION TO UPDATE ONE PLAYER ---
        def update(player_name, team_color):
            # 🛑 THE BOUNCER: Strictly ignore guests
            if player_name not in official_names:
                return

            if player_name not in stats:
                stats[player_name] = {'M': 0, 'W': 0, 'L': 0, 'D': 0, 'Form': []}
            
            p_stat = stats[player_name]
            p_stat['M'] += 1
            
            result = 'L'
            if winner == team_color:
                p_stat['W'] += 1
                result = 'W'
            elif winner == 'Draw':
                p_stat['D'] += 1
                result = 'D'
            else:
                p_stat['L'] += 1
            
            p_stat['Form'].append(result)

        # Process Teams
        for p in blue_team: update(p, 'Blue')
        for p in red_team: update(p, 'Red')

    # Convert to DataFrame
    if not stats: return pd.DataFrame()
    
    res = pd.DataFrame.from_dict(stats, orient='index')
    
    # Calc %
    res['Win %'] = ((res['W'] / res['M']) * 100).round(0).astype(int)
    
    # Form Icons
    icon_map = {'W': '✅', 'L': '❌', 'D': '➖'}
    res['Form (Last 5)'] = res['Form'].apply(lambda x: " ".join([icon_map.get(i, i) for i in x[-5:]]))
    
    return res.sort_values(by=['W', 'Win %'], ascending=False)

# --- 🚀 MAIN UI FUNCTION ---
def run_analytics_app():
    # --- 1. APPLY SHARED THEME (SMFC ORANGE DNA) ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@700;900&display=swap');

        /* BACKGROUND */
        .stApp {
            background-color: #0e1117;
            font-family: 'Rajdhani', sans-serif;
            background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%);
            color: #e0e0e0;
        }

        /* HEADERS (ORANGE THEME) */
        h1, h2, h3 {
            font-family: 'Rajdhani', sans-serif !important;
            text-transform: uppercase;
            color: #FF5722 !important; /* SMFC Orange */
            text-shadow: 0 0 20px rgba(255, 87, 34, 0.3);
        }

        /* METRIC CARDS (FIXED VISIBILITY) */
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 87, 34, 0.2); /* Subtle Orange Border */
            border-radius: 12px;
            padding: 15px;
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 0 20px rgba(255, 87, 34, 0.3);
            border-color: #FF5722;
        }
        /* The Label (e.g., "MATCHES PLAYED") */
        div[data-testid="stMetric"] label { 
            color: #FF5722 !important; 
            font-weight: 800 !important;
            letter-spacing: 1px;
        }
        /* The Value (e.g., "12") */
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: #ffffff !important; /* Bright White */
            font-weight: 900 !important;
        }

        /* CONTAINERS */
        .section-box {
            background: rgba(255, 255, 255, 0.03); 
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px; 
            padding: 20px; 
            margin-bottom: 20px;
        }

        /* BUTTONS (ORANGE GRADIENT) */
        div.stButton > button {
            background: linear-gradient(90deg, #D84315 0%, #FF5722 100%);
            color: white !important;
            font-weight: 900 !important;
            border: none;
            height: 50px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- 2. HEADER ---
    c1, c2 = st.columns([1, 5])
    with c1:
        # Try to find logo in parent images folder or current folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        logo_path = os.path.join(project_root, "images", "logo.png")
        
        if os.path.exists(logo_path):
            st.image(logo_path, width=80)
        else:
            st.markdown("# 📊")
    with c2:
        st.markdown("# SMFC ANALYTICS HUB")
        st.caption("OFFICIAL MATCH RECORDS & PLAYER STATISTICS")

    # --- 3. LOAD DATA ---
    conn, official_roster, df_matches = load_data_secure()

    if df_matches.empty:
        st.info("No matches logged yet.")
        return

    # Clean Dates
    if 'Date' in df_matches.columns:
        df_matches['Date'] = pd.to_datetime(df_matches['Date'])
        df_matches = df_matches.sort_values(by='Date', ascending=False)
        df_matches['Display_Date'] = df_matches['Date'].dt.strftime('%A, %d %b')

    # --- 4. HERO METRICS (REMOVED SEASON, FIXED COLORS) ---
    total_goals = pd.to_numeric(df_matches['Score_Blue'], errors='coerce').sum() + \
                  pd.to_numeric(df_matches['Score_Red'], errors='coerce').sum()
    
    # Changed to 3 columns
    m1, m2, m3 = st.columns(3)
    m1.metric("MATCHES PLAYED", len(df_matches))
    m2.metric("GOALS SCORED", int(total_goals))
    m3.metric("ACTIVE PLAYERS", len(official_roster))

    st.write("---")

    # --- 5. LEADERBOARD ---
    st.markdown("### 🏆 PLAYER LEADERBOARD")
    leaderboard = calculate_leaderboard(df_matches, official_roster)
    
    if not leaderboard.empty:
        st.dataframe(
            leaderboard[['M', 'W', 'L', 'D', 'Win %', 'Form (Last 5)']], 
            width='stretch',
            height=500
        )
    else:
        st.warning("No official player stats found. Check player names in Match History.")

    # --- 6. MATCH HISTORY LOG ---
    st.write("---")
    with st.expander("📜 MATCH HISTORY LOG", expanded=False):
        display_cols = ['Display_Date', 'Venue', 'Winner', 'Score_Blue', 'Score_Red', 'Team_Blue', 'Team_Red']
        st.dataframe(df_matches[display_cols].head(10), width='stretch')

    # --- 7. ADMIN LOGGING SECTION ---
    st.write("---")
    st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown("### 📝 ADMIN ZONE: LOG MATCH")
    
    with st.form("admin_log"):
        c1, c2 = st.columns(2)
        date_in = c1.date_input("Date", datetime.today())
        venue = c2.selectbox("Venue", ["BFC", "MKR Arena", "Sport Z", "Turf Park"])
        
        st.write("")
        col_b, col_r = st.columns(2)
        with col_b:
            st.markdown("#### 🔵 BLUE TEAM")
            s_blue = st.number_input("Goals", 0, key="sb")
            p_blue = st.text_area("Players (Comma separated)", height=80, placeholder="Jibin, Akhil...")
        with col_r:
            st.markdown("#### 🔴 RED TEAM")
            s_red = st.number_input("Goals", 0, key="sr")
            p_red = st.text_area("Players (Comma separated)", height=80, placeholder="Melwin, Gilson...")
            
        st.write("")
        password = st.text_input("🔑 ADMIN PASSWORD", type="password")
        
        if st.form_submit_button("💾 SAVE RECORD"):
            if password == st.secrets["passwords"]["admin"]:
                winner = "Draw"
                if s_blue > s_red: winner = "Blue"
                if s_red > s_blue: winner = "Red"
                
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
                    st.success("✅ Match Saved!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("❌ Wrong Password")

    st.markdown('</div>', unsafe_allow_html=True)
    