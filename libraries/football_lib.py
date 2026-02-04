import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import re
import os
import base64

# --- 🧮 HELPER FUNCTIONS (GLOBAL) ---

def get_img_as_base64(file):
    if os.path.exists(file):
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

def clean_whatsapp_name(text):
    text = text.replace('\u200b', '').replace('\u2060', '').replace('\ufeff', '')
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
    return text.strip()

def get_guests_list():
    raw = st.session_state.get('guest_input_val', '')
    return [g.strip() for g in raw.split(',') if g.strip()]

def get_counts():
    smfc_count = st.session_state.master_db['Selected'].sum()
    guest_count = len(get_guests_list())
    return smfc_count, guest_count, smfc_count + guest_count

def toggle_selection(player_name):
    idx = st.session_state.master_db[st.session_state.master_db['Name'] == player_name].index[0]
    current_val = st.session_state.master_db.at[idx, 'Selected']
    st.session_state.master_db.at[idx, 'Selected'] = not current_val

# --- 🧠 ANALYTICS HELPERS (Merged from Analytics Lib) ---
def parse_whatsapp_log(text):
    data = {}
    try:
        # Venue
        venue_match = re.search(r'🏟️\s*(.*)', text)
        data['venue'] = venue_match.group(1).strip() if venue_match else "BFC"
        
        # Scores
        score_match = re.search(r'Score.*?:.*?(\d+)\s*[-v]\s*(\d+)', text, re.IGNORECASE)
        if score_match:
            val1, val2 = int(score_match.group(1)), int(score_match.group(2))
            line_context = text[max(0, score_match.start()-20):score_match.end()+20].lower()
            if line_context.find('red') < line_context.find('blue'):
                data['s_red'], data['s_blue'] = val1, val2
            else:
                data['s_blue'], data['s_red'] = val1, val2

        # Players
        clean_text = text.replace('*', '')
        r_start = re.search(r'Red:', clean_text, re.IGNORECASE)
        b_start = re.search(r'Blue:', clean_text, re.IGNORECASE)
        
        if r_start and b_start:
            if r_start.start() < b_start.start():
                red_block = clean_text[r_start.end():b_start.start()]
                blue_block = clean_text[b_start.end():]
            else:
                blue_block = clean_text[b_start.end():r_start.start()]
                red_block = clean_text[r_start.end():]

            def extract_names(block):
                names = []
                for line in block.split('\n'):
                    line = re.sub(r'[✅☑️\d\(\)@]', '', line).replace('Fine', '').replace(':', '').strip()
                    if len(line) > 2: names.append(line)
                return ", ".join(names)

            data['p_red'] = extract_names(red_block)
            data['p_blue'] = extract_names(blue_block)
    except: pass
    return data

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

# --- 📥 DATA LOADING (Combined) ---
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Load Players
        df = conn.read(worksheet="Sheet1", ttl=0)
        if 'Selected' not in df.columns: df['Selected'] = False
        
        # Load Match History (Safely)
        try:
            df_matches = conn.read(worksheet="Match_History", ttl=0)
        except:
            df_matches = pd.DataFrame()
            
        return conn, df, df_matches
    except Exception as e:
        st.error(f"DATA ERROR: {e}")
        return None, pd.DataFrame(), pd.DataFrame()

# --- 📌 PRESETS ---
formation_presets = {
    "9 vs 9": {"limit": 9, "DEF_R": [(20,20),(20,50),(20,80)], "MID_R": [(35,15),(35,38),(35,62),(35,85)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,20),(80,50),(80,80)], "MID_B": [(65,15),(65,38),(65,62),(65,85)], "FWD_B": [(55,35),(55,65)]},
    "7 vs 7": {"limit": 7, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,20),(35,50),(35,80)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,20),(65,50),(65,80)], "FWD_B": [(55,35),(55,65)]},
    "6 vs 6": {"limit": 6, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,30),(35,70)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,30),(65,70)], "FWD_B": [(55,35),(55,65)]},
    "5 vs 5": {"limit": 5, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,30),(35,70)], "FWD_R": [(45,50)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,30),(65,70)], "FWD_B": [(55,50)]}
}

# --- 🚀 MAIN APPLICATION LOGIC ---
def run_football_app():
    # --- CSS ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@700;900&family=Courier+Prime:wght@700&display=swap');
        .stApp { background-color: #0e1117; font-family: 'Rajdhani', sans-serif; background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%); }
        .club-title-text { font-family: 'Rajdhani', sans-serif !important; font-weight: 900 !important; text-transform: uppercase; background: -webkit-linear-gradient(45deg, #D84315, #FF5722); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 0 30px rgba(216, 67, 21, 0.2); }
        h1, h2, h3, h4, .stMarkdown, p, span, div, label { color: #e0e0e0 !important; }
        .stTextInput label, .stSelectbox label, .stDateInput label, .stTimeInput label, .stSlider label { color: #FF5722 !important; font-size: 15px !important; font-weight: 800 !important; text-transform: uppercase; }
        div[data-baseweb="select"] > div { background-color: rgba(255,255,255,0.08) !important; color: white !important; border: 1px solid rgba(255,255,255,0.2) !important; }
        div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 87, 34, 0.2); border-radius: 12px; padding: 15px; }
        div[data-testid="stMetric"] label { color: #FF5722 !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #ffffff !important; }
        .section-box { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        div.stButton > button { background: linear-gradient(90deg, #D84315 0%, #FF5722 100%); font-family: 'Rajdhani', sans-serif; border: none; height: 55px; font-size: 18px !important; color: white !important; text-transform: uppercase; font-weight: 900 !important; width: 100%; }
        .player-card { background: linear-gradient(90deg, #1a1f26, #121212); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 8px; margin-bottom: 6px; display: flex; align-items: center; }
        .card-name { font-size: 15px; font-weight: 700; color: white !important; }
        .kit-red { border-left: 4px solid #ff4b4b; }
        .kit-blue { border-left: 4px solid #1c83e1; }
        .streamlit-expanderHeader { font-family: 'Rajdhani', sans-serif; font-weight: bold; color: #FF5722 !important; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

    # --- SESSION STATE ---
    if 'master_db' not in st.session_state or (isinstance(st.session_state.master_db, pd.DataFrame) and st.session_state.master_db.empty):
        conn, df_p, df_m = load_data()
        st.session_state.conn = conn
        st.session_state.master_db = df_p
        st.session_state.match_db = df_m
    else:
        # Just ensure connection exists
        if 'conn' not in st.session_state:
             conn, df_p, df_m = load_data()
             st.session_state.conn = conn

    if 'match_squad' not in st.session_state: st.session_state.match_squad = pd.DataFrame()
    if 'guest_input_val' not in st.session_state: st.session_state.guest_input_val = ""

    # --- HEADER ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "logo.png")
    img_html = ""
    if os.path.exists(logo_path):
        img_b64 = get_img_as_base64(logo_path)
        img_html = f'<img src="data:image/png;base64,{img_b64}" style="height: 60px; margin-right: 15px;">'
    else:
        img_html = '<span style="font-size: 50px; margin-right: 15px;">⚽</span>'

    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: center; padding-bottom: 10px;">
        {img_html}
        <div class="club-title-text" style="font-size: 3rem;">SMFC MANAGER PRO</div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.session_state.pop('master_db', None)
        st.rerun()

    # --- MAIN TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["MATCH LOBBY", "TACTICAL BOARD", "ANALYTICS", "DATABASE"])

    # --- TAB 1: MATCH LOBBY ---
    with tab1:
        smfc_n, guest_n, total_n = get_counts()
        st.markdown(f"""
        <div class="section-box">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="color:#FF5722; font-weight:bold; font-size:20px;">PLAYER POOL</div>
                <div style="display:flex; gap:5px;">
                    <div style="background:#111; padding:5px 10px; border-radius:6px; border:1px solid #444; color:white; font-weight:bold;">{smfc_n} SMFC</div>
                    <div style="background:#111; padding:5px 10px; border-radius:6px; border:1px solid #444; color:white; font-weight:bold;">{guest_n} GUEST</div>
                    <div style="background:linear-gradient(45deg, #FF5722, #FF8A65); padding:5px 10px; border-radius:6px; color:white; font-weight:bold;">{total_n} TOTAL</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📋 PASTE FROM WHATSAPP", expanded=True):
            whatsapp_text = st.text_area("List:", height=100, label_visibility="collapsed")
            if st.button("Select Players", type="secondary"):
                st.session_state.master_db['Selected'] = False
                new_guests = []
                lines = whatsapp_text.split('\n')
                for line in lines:
                    if not re.match(r'^\d+', line.strip()): continue
                    clean_name = clean_whatsapp_name(line)
                    if len(clean_name) < 2: continue
                    match_found = False
                    for idx, row in st.session_state.master_db.iterrows():
                        if clean_whatsapp_name(str(row['Name'])).lower() == clean_name.lower():
                            st.session_state.master_db.at[idx, 'Selected'] = True
                            match_found = True
                            break
                    if not match_found: new_guests.append(clean_name)
                final_guests = list(set(get_guests_list() + new_guests))
                st.session_state.guest_input_val = ", ".join(final_guests)
                st.rerun()

        st.write("")
        pos_tabs = st.tabs(["ALL", "FWD", "MID", "DEF"])
        def render_checklist(df_s, t_n):
            df_s = df_s.sort_values("Name")
            cols = st.columns(3) 
            for i, (idx, row) in enumerate(df_s.iterrows()):
                cols[i % 3].checkbox(f"{row['Name']}", value=bool(row['Selected']), key=f"chk_{row['Name']}_{t_n}", on_change=toggle_selection, args=(row['Name'],))
        
        with pos_tabs[0]: render_checklist(st.session_state.master_db, "all")
        with pos_tabs[1]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'FWD'], "fwd")
        with pos_tabs[2]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'MID'], "mid")
        with pos_tabs[3]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'DEF'], "def")
        
        st.write("")
        st.text_input("Guests", key="guest_input_val")
        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("⚙️ MATCH SETTINGS"):
            c1, c2 = st.columns(2)
            date_in = c1.date_input("Date")
            venue_in = c2.selectbox("Venue", ["BFC", "SportZ", "Other"])
            st.session_state.match_format = st.selectbox("Format", ["9 vs 9", "7 vs 7", "6 vs 6"])

        if st.button("⚡ GENERATE SQUAD"):
            active = st.session_state.master_db[st.session_state.master_db['Selected'] == True].copy()
            guests = get_guests_list()
            for g in guests: active = pd.concat([active, pd.DataFrame([{"Name": g, "Position": "MID", "PAC":70,"SHO":70,"PAS":70,"DRI":70,"DEF":70,"PHY":70}])], ignore_index=True)
            if not active.empty:
                active['OVR'] = active[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
                active['Sort_OVR'] = active['OVR'] + np.random.uniform(-3.0, 3.0, size=len(active))
                active = active.sort_values('Sort_OVR', ascending=False).reset_index(drop=True)
                active['Team'] = ["Red" if i % 4 in [0, 3] else "Blue" for i in range(len(active))]
                st.session_state.match_squad = active
                st.rerun()

        # PREVIEW
        if not st.session_state.match_squad.empty:
            st.markdown('<div class="section-box"><div style="color:#FF5722; font-weight:bold;">LINEUPS</div>', unsafe_allow_html=True)
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<h4 style='color:#ff4b4b; text-align:center'>RED TEAM</h4>", unsafe_allow_html=True)
                for _, p in reds.iterrows(): st.markdown(f"<div class='player-card kit-red'><span class='card-name'>{p['Name']}</span></div>", unsafe_allow_html=True)
            with c2:
                st.markdown("<h4 style='color:#1c83e1; text-align:center'>BLUE TEAM</h4>", unsafe_allow_html=True)
                for _, p in blues.iterrows(): st.markdown(f"<div class='player-card kit-blue'><span class='card-name'>{p['Name']}</span></div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: TACTICAL ---
    with tab2:
        if not st.session_state.match_squad.empty:
            pitch = Pitch(pitch_type='custom', pitch_length=100, pitch_width=100, pitch_color='#43a047', line_color='white')
            fig, ax = pitch.draw(figsize=(10, 6))
            # ... (Full drawing logic abbreviated for brevity, but same as before) ...
            # Reuse your existing drawing logic here
            st.pyplot(fig)
        else:
            st.info("Generate a squad first!")

    # --- TAB 3: ANALYTICS (NEW!) ---
    with tab3:
        st.markdown("### 📊 SMFC ANALYTICS HUB")
        
        # Check Data
        if 'match_db' not in st.session_state or st.session_state.match_db.empty:
            st.warning("No match history found.")
        else:
            df_m = st.session_state.match_db
            official_names = set(st.session_state.master_db['Name'].unique())
            
            # Metrics
            total_goals = pd.to_numeric(df_m['Score_Blue'], errors='coerce').sum() + pd.to_numeric(df_m['Score_Red'], errors='coerce').sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("MATCHES", len(df_m))
            c2.metric("GOALS", int(total_goals))
            c3.metric("PLAYERS", len(official_names))

            # Leaderboard
            st.write("---")
            lb = calculate_leaderboard(df_m, official_names)
            if not lb.empty:
                st.dataframe(lb[['M', 'W', 'L', 'D', 'Win %', 'Form (Last 5)']], width=1000, height=400)

            # Hidden Admin Zone
            st.write("---")
            with st.expander("⚙️ ADMIN ZONE (Log Match)"):
                t_paste, t_man = st.tabs(["📋 PASTE", "✍️ MANUAL"])
                
                # Session State for Forms
                if 'f_venue' not in st.session_state: st.session_state.f_venue = "BFC"
                if 'f_sb' not in st.session_state: st.session_state.f_sb = 0
                if 'f_sr' not in st.session_state: st.session_state.f_sr = 0
                if 'f_pb' not in st.session_state: st.session_state.f_pb = ""
                if 'f_pr' not in st.session_state: st.session_state.f_pr = ""

                with t_paste:
                    wa_txt = st.text_area("WhatsApp Chat", height=150)
                    if st.button("🔮 Parse"):
                        parsed = parse_whatsapp_log(wa_txt)
                        if parsed:
                            if 'venue' in parsed: st.session_state.f_venue = parsed['venue']
                            if 's_blue' in parsed: st.session_state.f_sb = parsed['s_blue']
                            if 's_red' in parsed: st.session_state.f_sr = parsed['s_red']
                            if 'p_blue' in parsed: st.session_state.f_pb = parsed['p_blue']
                            if 'p_red' in parsed: st.session_state.f_pr = parsed['p_red']
                            st.success("Parsed!")

                with t_man:
                    with st.form("save_match"):
                        d_in = st.date_input("Date")
                        v_in = st.text_input("Venue", key="f_venue")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("🔵 BLUE")
                            sb = st.number_input("Goals", key="f_sb")
                            pb = st.text_area("Players", key="f_pb")
                        with c2:
                            st.markdown("🔴 RED")
                            sr = st.number_input("Goals", key="f_sr")
                            pr = st.text_area("Players", key="f_pr")
                        
                        pwd = st.text_input("Password", type="password")
                        if st.form_submit_button("💾 Save"):
                            if pwd == st.secrets["passwords"]["admin"]:
                                w = "Draw"
                                if sb > sr: w = "Blue"
                                elif sr > sb: w = "Red"
                                
                                new_row = pd.DataFrame([{
                                    "Date": d_in.strftime("%Y-%m-%d"),
                                    "Venue": v_in, "Team_Blue": pb, "Team_Red": pr,
                                    "Score_Blue": sb, "Score_Red": sr, "Winner": w
                                }])
                                try:
                                    # Use the connection saved in session state
                                    updated = pd.concat([st.session_state.match_db, new_row], ignore_index=True)
                                    st.session_state.conn.update(worksheet="Match_History", data=updated)
                                    st.success("Saved!")
                                    st.cache_data.clear()
                                except Exception as e: st.error(str(e))
                            else:
                                st.error("Wrong Password")

    # --- TAB 4: DATABASE ---
    with tab4:
        if st.text_input("ENTER DB PASSCODE", type="password") == "1234":
            st.data_editor(st.session_state.master_db, use_container_width=True)