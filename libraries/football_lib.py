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

# --- 🧮 HELPER FUNCTIONS ---
def extract_whatsapp_players(text):
    text = re.sub(r'[\u200b\u2060\ufeff\xa0]', ' ', text)
    matches = re.findall(r'(?:^|\n)\s*\d+[\.\)]\s*([^\n\r]+)', text)
    return [m.strip() for m in matches if len(m.strip()) > 1]

def clean_player_name(text):
    text = re.sub(r'\s*\([tT]\)', '', text)
    text = re.sub(r'\s*[\(\[\{（].*?[\)\]\}）]', '', text)
    text = re.sub(r'\s+[-–].*$', '', text)
    text = re.sub(r'\s+[tTgG]$', '', text)
    text = re.sub(r'\s+(?:tentative|late|maybe|confirm|guest|paid)\b.*$', '', text, flags=re.IGNORECASE)
    return text.strip()

def get_guests_list():
    raw = st.session_state.get('guest_input_val', '')
    return [g.strip() for g in raw.split(',') if g.strip()]

def get_counts():
    smfc_count = 0
    if hasattr(st.session_state, 'master_db') and isinstance(st.session_state.master_db, pd.DataFrame):
        if 'Selected' in st.session_state.master_db.columns:
            smfc_count = st.session_state.master_db['Selected'].fillna(False).astype(bool).sum()
    guest_count = len(get_guests_list())
    return smfc_count, guest_count, smfc_count + guest_count

def toggle_selection(idx):
    if 'Selected' in st.session_state.master_db.columns:
        current_val = bool(st.session_state.master_db.at[idx, 'Selected'])
        st.session_state.master_db.at[idx, 'Selected'] = not current_val
        if 'ui_version' not in st.session_state: st.session_state.ui_version = 0
        st.session_state.ui_version += 1

# --- 🧠 ANALYTICS & PARSING ---
def parse_match_log(text):
    data = {
        "Date": datetime.today().strftime('%Y-%m-%d'),
        "Time": "00:00", "Venue": "BFC",
        "Score_Blue": 0, "Score_Red": 0, "Winner": "Draw",
        "Team_Blue": "", "Team_Red": ""
    }
    try:
        date_match = re.search(r'Date:\s*(.*)', text, re.IGNORECASE)
        if date_match: 
            raw_date = date_match.group(1).strip()
            try:
                if ',' in raw_date: clean_date_str = raw_date.split(',', 1)[1].strip()
                else: clean_date_str = raw_date
                dt_obj = datetime.strptime(clean_date_str, "%d %b")
                dt_obj = dt_obj.replace(year=datetime.now().year)
                data['Date'] = dt_obj.strftime("%Y-%m-%d")
            except: data['Date'] = raw_date
        
        time_match = re.search(r'Time:\s*(.*)', text, re.IGNORECASE)
        if time_match: data['Time'] = time_match.group(1).strip()
        venue_match = re.search(r'(?:Ground|Venue):\s*(.*)', text, re.IGNORECASE)
        if venue_match: data['Venue'] = venue_match.group(1).strip()
        
        score_match = re.search(r'Score:.*?Blue\s*(\d+)\s*[-v]\s*(\d+)\s*Red', text, re.IGNORECASE)
        if score_match:
            data['Score_Blue'] = int(score_match.group(1))
            data['Score_Red'] = int(score_match.group(2))
            if data['Score_Blue'] > data['Score_Red']: data['Winner'] = "Blue"
            elif data['Score_Red'] > data['Score_Blue']: data['Winner'] = "Red"
            else: data['Winner'] = "Draw"

        clean_text = text.replace('*', '')
        blue_start = re.search(r'🔵.*?BLUE TEAM', clean_text, re.IGNORECASE)
        red_start = re.search(r'🔴.*?RED TEAM', clean_text, re.IGNORECASE)
        if blue_start and red_start:
            if blue_start.start() < red_start.start():
                blue_block = clean_text[blue_start.end():red_start.start()]
                red_block = clean_text[red_start.end():]
            else:
                red_block = clean_text[red_start.end():blue_start.start()]
                blue_block = clean_text[blue_start.end():]
            def get_names(block):
                names = []
                for line in block.split('\n'):
                    line = line.strip()
                    if len(line) > 2 and not line.lower().startswith("we had") and not any(char.isdigit() for char in line):
                        names.append(clean_player_name(line))
                return ", ".join(names)
            data['Team_Blue'] = get_names(blue_block)
            data['Team_Red'] = get_names(red_block)
    except Exception as e: print(f"Parsing Error: {e}")
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
    res['Win %'] = ((res['W'] / res['M']) * 100).fillna(0).round(0).astype(int)
    res = res[res['M'] >= 2]
    res = res.sort_values(by=['Win %', 'W'], ascending=[False, False])
    res['Rank'] = range(1, len(res) + 1)
    
    icon_map = {'W': '✅', 'L': '❌', 'D': '➖'}
    res['Form_Icons'] = res['Form'].apply(lambda x: " ".join([icon_map.get(i, i) for i in x[-5:]]))
    
    return res

def calculate_player_score(row):
    stats = {
        'PAC': row.get('PAC', 70), 'SHO': row.get('SHO', 70),
        'PAS': row.get('PAS', 70), 'DRI': row.get('DRI', 70),
        'DEF': row.get('DEF', 70), 'PHY': row.get('PHY', 70)
    }
    for k, v in stats.items():
        try: stats[k] = float(v)
        except: stats[k] = 70.0

    pos = row.get('Position', 'MID')
    if pos == 'FWD': weighted_avg = (stats['SHO']*0.25 + stats['DRI']*0.2 + stats['PAC']*0.2 + stats['PAS']*0.15 + stats['PHY']*0.1 + stats['DEF']*0.1)
    elif pos == 'DEF': weighted_avg = (stats['DEF']*0.35 + stats['PHY']*0.25 + stats['PAC']*0.15 + stats['PAS']*0.15 + stats['DRI']*0.05 + stats['SHO']*0.05)
    else: weighted_avg = (stats['PAS']*0.25 + stats['DRI']*0.2 + stats['DEF']*0.15 + stats['SHO']*0.15 + stats['PAC']*0.15 + stats['PHY']*0.1)
    try: star_r = float(row.get('StarRating', 3))
    except: star_r = 3.0
    star_score = 45 + (star_r * 10)
    return round((weighted_avg * 0.6) + (star_score * 0.4), 1)

def load_data():
    conn = None
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Sheet1", ttl=0, show_spinner=False)
        if df is None or df.empty: raise ValueError("Sheet1 returned empty data")
        if 'Selected' not in df.columns: df['Selected'] = False
        else: df['Selected'] = df['Selected'].fillna(False).astype(bool)
        try: df_matches = conn.read(worksheet="Match_History", ttl=0, show_spinner=False)
        except: df_matches = pd.DataFrame()
        return conn, df, df_matches
    except Exception as e:
        dummy_df = pd.DataFrame(columns=["Name", "Position", "Selected", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY", "StarRating"])
        return conn, dummy_df, pd.DataFrame()

# --- 📌 PRESETS ---
formation_presets = {
    "9 vs 9": {"limit": 9, "RED_COORDS": [(10, 20), (10, 50), (10, 80), (30, 15), (30, 38), (30, 62), (30, 85), (45, 35), (45, 65)], "BLUE_COORDS": [(90, 20), (90, 50), (90, 80), (70, 15), (70, 38), (70, 62), (70, 85), (55, 35), (55, 65)]},
    "7 vs 7": {"limit": 7, "RED_COORDS": [(10, 30), (10, 70), (30, 20), (30, 50), (30, 80), (45, 35), (45, 65)], "BLUE_COORDS": [(90, 30), (90, 70), (70, 20), (70, 50), (70, 80), (55, 35), (55, 65)]},
    "6 vs 6": {"limit": 6, "RED_COORDS": [(10, 30), (10, 70), (30, 30), (30, 70), (45, 35), (45, 65)], "BLUE_COORDS": [(90, 30), (90, 70), (70, 30), (70, 70), (55, 35), (55, 65)]},
    "5 vs 5": {"limit": 5, "RED_COORDS": [(10, 30), (10, 70), (30, 50), (45, 30), (45, 70)], "BLUE_COORDS": [(90, 30), (90, 70), (70, 50), (55, 30), (55, 70)]}
}

# --- 🚀 MAIN APP ---
def run_football_app():
    if 'ui_version' not in st.session_state: st.session_state.ui_version = 0
    if 'checklist_version' not in st.session_state: st.session_state.checklist_version = 0
    if 'parsed_match_data' not in st.session_state: st.session_state.parsed_match_data = None
    if 'position_changes' not in st.session_state: st.session_state.position_changes = []
    if 'transfer_log' not in st.session_state: st.session_state.transfer_log = []
    if 'match_squad' not in st.session_state: st.session_state.match_squad = pd.DataFrame()
    if 'guest_input_val' not in st.session_state: st.session_state.guest_input_val = ""

    # --- GLOBAL CSS ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@700;900&family=Courier+Prime:wght@700&display=swap');
        .stApp { background-color: #0e1117; font-family: 'Rajdhani', sans-serif; background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%); color: #e0e0e0; }
        
        .neon-white { color: #ffffff; text-shadow: 0 0 5px #ffffff, 0 0 10px #ffffff; font-weight: 800; text-transform: uppercase; }
        .neon-red { color: #ff4b4b; text-shadow: 0 0 5px #ff4b4b, 0 0 10px #ff4b4b; font-weight: 800; text-transform: uppercase; }
        .neon-blue { color: #1c83e1; text-shadow: 0 0 5px #1c83e1, 0 0 10px #1c83e1; font-weight: 800; text-transform: uppercase; }
        
        /* MATCH HISTORY COLORS */
        .neon-gold { color: #FFD700; text-shadow: 0 0 5px #FFD700; font-weight: 900; font-size: 14px; }
        .dull-grey { color: #666; font-weight: 600; opacity: 0.7; font-size: 13px; }
        .draw-text { color: #ccc; font-weight: 700; font-size: 13px; }

        input[type="text"], input[type="number"], textarea, div[data-baseweb="input"] { background-color: #ffffff !important; color: #000000 !important; border-radius: 5px !important; }
        div[data-baseweb="base-input"] input { color: #000000 !important; -webkit-text-fill-color: #000000 !important; font-weight: bold !important; }
        div[data-baseweb="select"] div { background-color: #ffffff !important; color: #000000 !important; }
        div[data-testid="stWidgetLabel"] p { color: #ffffff !important; text-shadow: 0 0 8px rgba(255,255,255,0.8) !important; font-weight: 800 !important; text-transform: uppercase; font-size: 14px !important; }
        
        /* METRICS */
        [data-testid="stMetricLabel"] { color: #ffffff !important; font-weight: bold !important; text-shadow: 0 0 5px rgba(255,255,255,0.5); }
        [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 900 !important; text-shadow: 0 0 10px rgba(255,255,255,0.7); }
        
        .badge-box { display: flex; gap: 5px; }
        .badge-smfc, .badge-guest { background:#111; padding:5px 10px; border-radius:6px; border:1px solid #444; color:white; font-weight:bold; }
        .badge-total { background:linear-gradient(45deg, #FF5722, #FF8A65); padding:5px 10px; border-radius:6px; color:white; font-weight:bold; box-shadow: 0 0 10px rgba(255,87,34,0.4); }
        
        /* ANALYTICS CARDS */
        .lb-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
            border: 1px solid rgba(255,255,255,0.1);
            border-left: 4px solid #FF5722;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: transform 0.2s;
        }
        .lb-card:hover { transform: translateX(5px); background: rgba(255,255,255,0.08); }
        .lb-rank { font-size: 24px; font-weight: 900; color: #FF5722; width: 40px; }
        .lb-info { flex-grow: 1; padding-left: 10px; }
        .lb-name { font-size: 18px; font-weight: 800; color: #fff; text-transform: uppercase; }
        .lb-stats { font-size: 12px; color: #bbb; margin-top: 2px; }
        .lb-form { font-size: 14px; margin-right: 15px; letter-spacing: 2px; }
        .lb-winrate { font-size: 22px; font-weight: 900; color: #00E676; text-shadow: 0 0 10px rgba(0, 230, 118, 0.4); }
        
        /* --- NEW MATCH HISTORY CARD STYLE --- */
        .match-card {
            background: rgba(20, 20, 20, 0.8);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            display: flex;
            align-items: stretch;
            transition: all 0.3s ease;
        }
        .mc-left { flex: 1; padding-right: 15px; display: flex; flex-direction: column; justify-content: center; }
        .mc-right { flex: 2; padding-left: 20px; border-left: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; justify-content: center; gap: 6px; }
        
        .mc-date { font-size: 11px; color: #888; font-weight: bold; margin-bottom: 4px; text-transform: uppercase; }
        .mc-score { font-size: 22px; font-family: 'Orbitron', sans-serif; letter-spacing: 1px; color: white; }
        .mc-score-blue { color: #1c83e1; }
        .mc-score-red { color: #ff4b4b; }
        .mc-score-draw { color: #fff; }

        .player-card { background: linear-gradient(90deg, #1a1f26, #121212); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; }
        .kit-red { border-left: 4px solid #ff4b4b; }
        .kit-blue { border-left: 4px solid #1c83e1; }
        .card-name { font-size: 14px; font-weight: 700; color: white !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }
        .pos-badge { font-size: 10px; font-weight: 900; background: rgba(255,255,255,0.1); padding: 2px 5px; border-radius: 4px; color: #ccc; text-transform: uppercase; }
        .spotlight-box { background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%); border-radius: 10px; padding: 15px; text-align: center; height: 100%; border: 1px solid rgba(255,255,255,0.1); }
        .sp-value { font-size: 32px; font-weight: 900; color: #ffffff; margin: 5px 0; text-shadow: 0 0 15px rgba(255,255,255,0.9), 0 0 30px rgba(255,255,255,0.5); }
        .sp-title { font-size: 16px; font-weight: 900; color: #ffffff; text-transform: uppercase; letter-spacing: 1px; text-shadow: 0 0 10px rgba(255,255,255,0.7); margin-bottom: 10px; }
        .sp-name { color: #ffffff; font-size: 20px; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 10px rgba(255,255,255,0.7); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .change-log-item { color: #00E676; font-size: 13px; font-family: monospace; border-left: 2px solid #00E676; padding-left: 8px; margin-bottom: 4px; }
        div.stButton > button { background: linear-gradient(90deg, #D84315 0%, #FF5722 100%) !important; color: white !important; font-weight: 900 !important; border: none !important; height: 55px; font-size: 20px !important; text-transform: uppercase; width: 100%; box-shadow: 0 4px 15px rgba(216, 67, 21, 0.4); }
    </style>
    """, unsafe_allow_html=True)

    if 'master_db' not in st.session_state or (isinstance(st.session_state.master_db, pd.DataFrame) and st.session_state.master_db.empty):
        conn, df_p, df_m = load_data()
        st.session_state.conn = conn; st.session_state.master_db = df_p; st.session_state.match_db = df_m
    else:
        if 'conn' not in st.session_state: conn, df_p, df_m = load_data(); st.session_state.conn = conn

    st.markdown("<h1 style='text-align:center; font-family:Rajdhani; font-size: 3.5rem; background: -webkit-linear-gradient(45deg, #D84315, #FF5722); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>SMFC MANAGER PRO</h1>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh Data"): 
        st.session_state.pop('master_db', None)
        st.session_state.ui_version += 1
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["MATCH LOBBY", "TACTICAL BOARD", "ANALYTICS", "DATABASE"])

    with tab1:
        smfc_n, guest_n, total_n = get_counts()
        st.markdown(f"""<div class="section-box"><div style="display:flex; justify-content:space-between; align-items:center;"><div style="color:#FF5722; font-weight:bold; font-size:20px; font-family:Rajdhani;">PLAYER POOL</div><div class="badge-box"><div class="badge-smfc">{smfc_n} SMFC</div><div class="badge-guest">{guest_n} GUEST</div><div class="badge-total">{total_n} TOTAL</div></div></div>""", unsafe_allow_html=True)
        
        with st.expander("📋 PASTE FROM WHATSAPP", expanded=True):
            whatsapp_text = st.text_area("List:", height=150, label_visibility="collapsed", placeholder="Paste list here...")
            if st.button("Select Players", key="btn_select"):
                if 'Selected' in st.session_state.master_db.columns:
                    st.session_state.master_db['Selected'] = False 
                    new_guests = []
                    found_count = 0
                    raw_lines = extract_whatsapp_players(whatsapp_text)
                    for line in raw_lines:
                        match = False
                        clean_input = clean_player_name(line).lower()
                        for idx, row in st.session_state.master_db.iterrows():
                            db_name = clean_player_name(str(row['Name'])).lower()
                            if db_name == clean_input:
                                st.session_state.master_db.at[idx, 'Selected'] = True; match = True; found_count += 1; break
                        if not match: new_guests.append(clean_player_name(line))
                    current = get_guests_list()
                    for g in new_guests:
                        if g not in current: current.append(g)
                    st.session_state.guest_input_val = ", ".join(current)
                    st.session_state.ui_version += 1
                    st.toast(f"✅ Found {found_count} players. {len(new_guests)} guests added!"); st.rerun()
                else: st.error("DB Offline")

        pos_tabs = st.tabs(["ALL", "FWD", "MID", "DEF"])
        def render_checklist(df_s, t_n):
            if df_s.empty or 'Name' not in df_s.columns: return
            df_s = df_s.sort_values("Name")
            cols = st.columns(3) 
            for i, (idx, row) in enumerate(df_s.iterrows()):
                key_id = f"chk_{idx}_{t_n}_v{st.session_state.ui_version}"
                cols[i % 3].checkbox(f"{row['Name']}", value=bool(row.get('Selected', False)), key=key_id, on_change=toggle_selection, args=(idx,))
        
        with pos_tabs[0]: render_checklist(st.session_state.master_db, "all")
        with pos_tabs[1]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'FWD'], "fwd")
        with pos_tabs[2]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'MID'], "mid")
        with pos_tabs[3]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'DEF'], "def")
        st.write(""); st.text_input("Guests (Comma separated)", key="guest_input_val"); st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("⚙️ MATCH SETTINGS (Date, Time, Venue)", expanded=False):
            c1, c2 = st.columns(2)
            match_date = c1.date_input("Match Date", datetime.today(), key="match_date_input")
            match_time = c1.time_input("Kickoff", datetime.now().time(), key="match_time_input")
            venue_opt = c2.selectbox("Venue", ["BFC", "GoatArena", "SportZ", "Other"], key="venue_select")
            venue = c2.text_input("Venue Name", "Ground", key="venue_text") if venue_opt == "Other" else venue_opt
            duration = c2.slider("Duration (Mins)", 60, 120, 90, 30, key="duration_slider")
            st.session_state.match_format = st.selectbox("Format", ["9 vs 9", "7 vs 7", "6 vs 6", "5 vs 5"], key="fmt_select")

        guests = get_guests_list()
        if guests:
            st.write("---"); st.markdown("<h3 style='color:#FFD700; text-align:center; margin-bottom: 15px;'>GUEST SQUAD SETUP</h3>", unsafe_allow_html=True)
            for g_name in guests:
                c_name, c_pos, c_lvl = st.columns([3.5, 2, 2.5])
                with c_name: st.markdown(f"<div class='guest-row-label'>{g_name}</div>", unsafe_allow_html=True)
                with c_pos: st.selectbox("Pos", ["FWD", "MID", "DEF", "GK"], key=f"g_pos_{g_name}", label_visibility="collapsed")
                with c_lvl: st.selectbox("Lvl", ["⭐⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐", "⭐"], index=2, key=f"g_lvl_{g_name}", label_visibility="collapsed")
            st.write("---")

        with st.expander("🛠️ EDIT POSITIONS (Session Only)", expanded=False):
            selected_players = st.session_state.master_db[st.session_state.master_db['Selected'] == True]
            if not selected_players.empty:
                c_p_sel, c_p_pos, c_p_btn = st.columns([3.5, 2, 2.5])
                with c_p_sel:
                    p_opts = [f"{row['Name']} ({row['Position']})" for _, row in selected_players.iterrows()]
                    p_to_edit_str = st.selectbox("Select Player", p_opts, key="edit_pos_player")
                with c_p_pos: new_pos = st.selectbox("New Position", ["FWD", "MID", "DEF", "GK"], key="edit_pos_new")
                with c_p_btn:
                    st.write(""); st.write("")
                    if st.button("UPDATE POS", key="btn_update_pos"):
                        p_name_clean = p_to_edit_str.rsplit(" (", 1)[0]
                        idx = st.session_state.master_db[st.session_state.master_db['Name'] == p_name_clean].index[0]
                        old_pos = st.session_state.master_db.at[idx, 'Position']
                        st.session_state.master_db.at[idx, 'Position'] = new_pos
                        st.session_state.master_db.at[idx, 'Selected'] = True 
                        st.session_state.ui_version += 1
                        st.session_state.position_changes.append(f"{p_name_clean}: {old_pos} → {new_pos}")
                        st.rerun()
                if st.session_state.position_changes:
                    st.write(""); 
                    for change in st.session_state.position_changes: st.markdown(f"<div class='change-log-item'>{change}</div>", unsafe_allow_html=True)
            else: st.info("Select players first.")

        st.write(""); 
        if st.button("⚡ GENERATE SQUAD"):
            if 'Selected' in st.session_state.master_db.columns:
                active = st.session_state.master_db[st.session_state.master_db['Selected'] == True].copy()
                guest_rows = []
                star_map = {"⭐": 1, "⭐⭐": 2, "⭐⭐⭐": 3, "⭐⭐⭐⭐": 4, "⭐⭐⭐⭐⭐": 5}
                for g in get_guests_list():
                    chosen_pos = st.session_state.get(f"g_pos_{g}", "MID")
                    chosen_stars = st.session_state.get(f"g_lvl_{g}", "⭐⭐⭐")
                    rating_val = star_map.get(chosen_stars, 3)
                    guest_rows.append({"Name": g, "Position": chosen_pos, "StarRating": rating_val, "PAC":70,"SHO":70,"PAS":70,"DRI":70,"DEF":70,"PHY":70})
                if guest_rows: active = pd.concat([active, pd.DataFrame(guest_rows)], ignore_index=True)
                
                if not active.empty:
                    active['Power'] = active.apply(calculate_player_score, axis=1)
                    active = active.sort_values(['Position', 'Power'], ascending=[True, False])
                    gks = active[active['Position'] == 'GK'].sort_values('Power', ascending=False)
                    defs = active[active['Position'] == 'DEF'].sort_values('Power', ascending=False)
                    mids = active[active['Position'] == 'MID'].sort_values('Power', ascending=False)
                    fwds = active[active['Position'] == 'FWD'].sort_values('Power', ascending=False)
                    red_team, blue_team = [], []; red_score, blue_score = 0, 0
                    turn = 0 
                    def draft_players(pool):
                        nonlocal turn, red_score, blue_score
                        for _, p in pool.iterrows():
                            if len(red_team) > len(blue_team) + 1: turn = 1
                            elif len(blue_team) > len(red_team) + 1: turn = 0
                            if turn == 0: red_team.append(p); red_score += p['Power']; turn = 1
                            else: blue_team.append(p); blue_score += p['Power']; turn = 0
                    draft_players(gks); draft_players(defs); draft_players(mids); draft_players(fwds)
                    df_red = pd.DataFrame(red_team); df_red['Team'] = 'Red'
                    df_blue = pd.DataFrame(blue_team); df_blue['Team'] = 'Blue'
                    st.session_state.match_squad = pd.concat([df_red, df_blue], ignore_index=True)
                    st.session_state.red_ovr = int(df_red['Power'].mean()) if not df_red.empty else 0
                    st.session_state.blue_ovr = int(df_blue['Power'].mean()) if not df_blue.empty else 0
                    st.rerun()
            else: st.error("Database offline.")

        if not st.session_state.match_squad.empty:
            pos_map = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
            st.session_state.match_squad['Pos_Ord'] = st.session_state.match_squad['Position'].map(pos_map).fillna(4)
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"].sort_values('Pos_Ord')
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"].sort_values('Pos_Ord')
            r_ovr = st.session_state.get('red_ovr', 0); b_ovr = st.session_state.get('blue_ovr', 0)
            red_html = ""; blue_html = ""
            for _, p in reds.iterrows(): red_html += f"<div class='player-card kit-red'><span class='card-name'>{p['Name']}</span><span class='pos-badge'>{p['Position']}</span></div>"
            for _, p in blues.iterrows(): blue_html += f"<div class='player-card kit-blue'><span class='card-name'>{p['Name']}</span><span class='pos-badge'>{p['Position']}</span></div>"
            st.markdown(f"""
            <div class="section-box">
                <div style="color:#FF5722; font-weight:bold; font-size:18px; margin-bottom: 10px;">LINEUPS</div>
                <div style="display: flex; gap: 8px;">
                    <div style="flex: 1; min-width: 0;"><h4 style='color:#ff4b4b; text-align:center; margin:0 0 5px 0; font-size:16px;'>RED <span style='font-size:12px; color:#aaa;'>({r_ovr})</span></h4>{red_html}</div>
                    <div style="width: 1px; background: rgba(255,255,255,0.1);"></div>
                    <div style="flex: 1; min-width: 0;"><h4 style='color:#1c83e1; text-align:center; margin:0 0 5px 0; font-size:16px;'>BLUE <span style='font-size:12px; color:#aaa;'>({b_ovr})</span></h4>{blue_html}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            dt_match = datetime.combine(match_date, match_time)
            dt_end = dt_match + timedelta(minutes=duration)
            str_date = dt_match.strftime('%A, %d %b'); str_time = f"{dt_match.strftime('%I:%M %p')} - {dt_end.strftime('%I:%M %p')}"
            r_list = "\n".join([p['Name'] for p in reds.to_dict('records')]); b_list = "\n".join([p['Name'] for p in blues.to_dict('records')])
            summary = f"Date: {str_date}\nTime: {str_time}\nGround: {venue}\nScore: Blue 0-0 Red\nCost per player: *\nGpay: *\nLateFee: 50\n\n🔵 *BLUE TEAM* ({b_ovr})\n{b_list}\n\n🔴 *RED TEAM* ({r_ovr})\n{r_list}"
            components.html(f"""<textarea id="text_to_copy_v2" style="position:absolute; left:-9999px;">{summary}</textarea><button onclick="var c=document.getElementById('text_to_copy_v2');c.select();document.execCommand('copy');this.innerText='✅ COPIED!';" style="background:linear-gradient(90deg, #FF5722, #FF8A65); color:white; font-weight:800; padding:15px 0; border:none; border-radius:8px; width:100%; cursor:pointer; font-size:16px; margin-top:10px;">📋 COPY TEAM LIST</button>""", height=70)
            
            st.write("---"); st.markdown("<h3 style='text-align:center; color:#FF5722;'>TRANSFER WINDOW</h3>", unsafe_allow_html=True)
            col_tr_red, col_btn, col_tr_blue = st.columns([4, 1, 4])
            red_opts = [f"{r['Name']} ({r['Position']})" for _, r in reds.iterrows()]; blue_opts = [f"{r['Name']} ({r['Position']})" for _, r in blues.iterrows()]
            with col_tr_red: s_red_str = st.selectbox("Select Red", red_opts, key="sel_red", label_visibility="collapsed")
            with col_tr_blue: s_blue_str = st.selectbox("Select Blue", blue_opts, key="sel_blue", label_visibility="collapsed")
            with col_btn:
                st.write(""); st.write("")
                if st.button("↔️", key="swap_btn"):
                    s_red = s_red_str.rsplit(" (", 1)[0]; s_blue = s_blue_str.rsplit(" (", 1)[0]
                    idx_r = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_red].index[0]
                    idx_b = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_blue].index[0]
                    st.session_state.match_squad.at[idx_r, "Team"] = "Blue"; st.session_state.match_squad.at[idx_b, "Team"] = "Red"
                    st.session_state.transfer_log.append(f"{s_red} (RED) ↔ {s_blue} (BLUE)")
                    r_p = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
                    b_p = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
                    st.session_state.red_ovr = int(r_p['Power'].mean()); st.session_state.blue_ovr = int(b_p['Power'].mean())
                    st.rerun()
            if st.session_state.transfer_log:
                st.write(""); 
                for log in st.session_state.transfer_log: st.markdown(f"<div class='change-log-item'>{log}</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        if not st.session_state.match_squad.empty:
            c_pitch, c_subs = st.columns([3, 1])
            with c_pitch:
                pitch = Pitch(pitch_type='custom', pitch_length=100, pitch_width=100, pitch_color='#43a047', line_color='white')
                fig, ax = pitch.draw(figsize=(10, 8))
                def draw_player(player_name, x, y, color):
                    pitch.scatter(x, y, s=600, marker='h', c=color, edgecolors='white', linewidth=2, ax=ax, zorder=2)
                    ax.text(x, y-4, player_name, color='black', ha='center', fontsize=10, fontweight='bold', bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", lw=1), zorder=3)
                fmt = st.session_state.get('match_format', '9 vs 9')
                coords_map = formation_presets.get(fmt, formation_presets['9 vs 9'])
                reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"].sort_values('Pos_Ord')
                blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"].sort_values('Pos_Ord')
                r_spots = coords_map.get("RED_COORDS", []); b_spots = coords_map.get("BLUE_COORDS", [])
                subs_r = []
                for i, row in enumerate(reds.itertuples()):
                    if i < len(r_spots): draw_player(row.Name, r_spots[i][0], r_spots[i][1], '#ff4b4b')
                    else: subs_r.append(row.Name)
                subs_b = []
                for i, row in enumerate(blues.itertuples()):
                    if i < len(b_spots): draw_player(row.Name, b_spots[i][0], b_spots[i][1], '#1c83e1')
                    else: subs_b.append(row.Name)
                st.pyplot(fig)
            with c_subs:
                st.markdown("<h4 style='color:#FF5722; text-align:center; border-bottom:2px solid #FF5722;'>SUBSTITUTES</h4>", unsafe_allow_html=True)
                if subs_r:
                    st.markdown("<div style='color:#ff4b4b; font-weight:bold;'>🔴 RED SUBS</div>", unsafe_allow_html=True)
                    for s in subs_r: st.markdown(f"- {s}")
                if subs_b:
                    st.markdown("<div style='color:#1c83e1; font-weight:bold; margin-top:10px;'>🔵 BLUE SUBS</div>", unsafe_allow_html=True)
                    for s in subs_b: st.markdown(f"- {s}")
                if not subs_r and not subs_b: st.info("No Subs")
                
                # Side-by-Side on Tact Board too
                red_html = ""; blue_html = ""
                for _, p in reds.iterrows(): red_html += f"<div class='player-card kit-red' style='padding: 4px 8px;'><span class='card-name' style='font-size:12px;'>{p['Name']}</span></div>"
                for _, p in blues.iterrows(): blue_html += f"<div class='player-card kit-blue' style='padding: 4px 8px;'><span class='card-name' style='font-size:12px;'>{p['Name']}</span></div>"
                st.write("---")
                st.markdown(f"""
                <div style="display: flex; gap: 5px; margin-top: 10px;">
                    <div style="flex: 1; min-width: 0;"><h6 style='color:#ff4b4b; text-align:center; margin:0 0 5px 0;'>RED ({r_ovr})</h6>{red_html}</div>
                    <div style="flex: 1; min-width: 0;"><h6 style='color:#1c83e1; text-align:center; margin:0 0 5px 0;'>BLUE ({b_ovr})</h6>{blue_html}</div>
                </div>
                """, unsafe_allow_html=True)

        else: st.info("Generate Squad First")

    with tab3:
        if 'match_db' in st.session_state and not st.session_state.match_db.empty:
            df_m = st.session_state.match_db
            official_names = set(st.session_state.master_db['Name'].unique()) if 'Name' in st.session_state.master_db.columns else set()
            total_goals = pd.to_numeric(df_m['Score_Blue'], errors='coerce').sum() + pd.to_numeric(df_m['Score_Red'], errors='coerce').sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("MATCHES", len(df_m)); c2.metric("GOALS", int(total_goals)); c3.metric("PLAYERS", len(official_names))
            lb = calculate_leaderboard(df_m, official_names)
            
            # --- LEADERBOARD CARDS ---
            if not lb.empty:
                # Spotlight Top 3 (Simplified for brevity, standard card loop below)
                max_m = lb['M'].max(); names_m = ", ".join(lb[lb['M'] == max_m].index.tolist())
                top_player = lb.iloc[0]; val_w = f"{top_player['Win %']}%"; name_w = lb.index[0]
                max_l = lb['L'].max(); names_l = ", ".join(lb[lb['L'] == max_l].index.tolist())
                sp1, sp2, sp3 = st.columns(3)
                with sp1: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #00C9FF;'><div class='sp-value'>{max_m}</div><div class='sp-title'>COMMITMENT KING</div><div class='sp-name'>{names_m}</div></div>", unsafe_allow_html=True)
                with sp2: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #FFD700;'><div class='sp-value'>{val_w}</div><div class='sp-title'>STAR PLAYER</div><div class='sp-name'>{name_w}</div></div>", unsafe_allow_html=True)
                with sp3: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #ff4b4b;'><div class='sp-value'>{max_l}</div><div class='sp-title'>MOST LOSSES</div><div class='sp-name'>{names_l}</div></div>", unsafe_allow_html=True)
                
                st.write("---")
                
                for p, r in lb.iterrows(): 
                    st.markdown(f"""
                    <div class='lb-card'>
                        <div class='lb-rank'>#{r['Rank']}</div>
                        <div class='lb-info'>
                            <div class='lb-name'>{p}</div>
                            <div class='lb-stats'>{r['M']} Matches • {r['W']} Wins</div>
                        </div>
                        <div class='lb-form'>{r['Form_Icons']}</div>
                        <div class='lb-winrate'>{r['Win %']}%</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # --- MATCH HISTORY VISUALS ---
            st.write("---")
            st.markdown("<h4 class='neon-white'>RECENT MATCHES</h4>", unsafe_allow_html=True)
            history = df_m.sort_values('Date', ascending=False).head(10)
            
            for _, row in history.iterrows():
                # Logic for Gold/Grey coloring & Border
                score_b = int(row['Score_Blue'])
                score_r = int(row['Score_Red'])
                
                b_cls, r_cls = "mc-score-draw", "mc-score-draw"
                border_color = "#555" # Default Grey for Draw
                
                win_text, lose_text = "", ""
                win_team_cls, lose_team_cls = "", ""
                
                # Logic to determine Winner/Loser lists
                if row['Winner'] == "Blue":
                    b_cls, r_cls = "mc-score-blue", "mc-score-red" # Blue highlight
                    border_color = "#1c83e1" # Blue Border
                    
                    # Winner = Blue Team, Loser = Red Team
                    win_text = row['Team_Blue']
                    lose_text = row['Team_Red']
                    win_team_cls = "neon-gold"
                    lose_team_cls = "dull-grey"
                    
                elif row['Winner'] == "Red":
                    b_cls, r_cls = "mc-score-blue", "mc-score-red"
                    border_color = "#ff4b4b" # Red Border
                    
                    # Winner = Red Team, Loser = Blue Team
                    win_text = row['Team_Red']
                    lose_text = row['Team_Blue']
                    win_team_cls = "neon-gold"
                    lose_team_cls = "dull-grey"
                else:
                    # Draw
                    win_text = row['Team_Blue']
                    lose_text = row['Team_Red']
                    win_team_cls = "draw-text"
                    lose_team_cls = "draw-text"

                # Render Card with Layout
                st.markdown(f"""
                <div class='match-card' style='border-left: 4px solid {border_color};'>
                    <div class='mc-left'>
                        <div class='mc-date'>{row['Date']} | {row['Venue']}</div>
                        <div class='mc-score'>
                            <span class='{b_cls}'>BLUE {score_b}</span> 
                            <span style='color:#888; margin:0 5px;'>-</span>
                            <span class='{r_cls}'>{score_r} RED</span>
                        </div>
                    </div>
                    <div class='mc-right'>
                        <div class='{win_team_cls}'>{win_text}</div>
                        <div class='{lose_team_cls}'>{lose_text}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # --- TAB 3 LOG MATCH UPDATE ---
            with st.expander("⚙️ LOG MATCH"):
                # Updated text area label to specific neon-white instruction
                wa_txt = st.text_area("Paste the final full result with scoreline and team split")
                if st.button("Parse"):
                    parsed = parse_match_log(wa_txt)
                    st.session_state.parsed_match_data = parsed
                    st.toast("Match Parsed!")
                
                if st.session_state.parsed_match_data:
                    pm = st.session_state.parsed_match_data
                    
                    # Main heading (Neon White)
                    st.markdown("<div class='neon-white' style='margin-bottom:15px;'>MATCH DETAILS (Auto-Filled)</div>", unsafe_allow_html=True)

                    c_d, c_t, c_v = st.columns(3)
                    # Standard labels pick up neon-white CSS
                    new_date = c_d.text_input("Date (YYYY-MM-DD)", pm['Date'])
                    new_time = c_t.text_input("Time", pm['Time'])
                    new_venue = c_v.text_input("Venue", pm['Venue'])
                    
                    c_s1, c_s2 = st.columns(2)
                    with c_s1:
                        st.markdown("<div class='neon-blue'>BLUE SCORE</div>", unsafe_allow_html=True)
                        new_score_b = st.number_input("Blue Score", value=pm['Score_Blue'], label_visibility="collapsed")
                    with c_s2:
                        st.markdown("<div class='neon-red'>RED SCORE</div>", unsafe_allow_html=True)
                        new_score_r = st.number_input("Red Score", value=pm['Score_Red'], label_visibility="collapsed")
                    
                    st.markdown("<div class='neon-blue' style='margin-top:10px;'>BLUE TEAM LIST</div>", unsafe_allow_html=True)
                    new_blue = st.text_area("Blue Team", pm['Team_Blue'], label_visibility="collapsed")

                    st.markdown("<div class='neon-red' style='margin-top:10px;'>RED TEAM LIST</div>", unsafe_allow_html=True)
                    new_red = st.text_area("Red Team", pm['Team_Red'], label_visibility="collapsed")
                    
                    save_pass = st.text_input("Admin Password", type="password")
                    if st.button("💾 SAVE MATCH TO DB"):
                        try:
                            admin_pw = st.secrets["passwords"]["admin"]
                        except:
                            admin_pw = "1234"
                            
                        if save_pass == admin_pw:
                            new_row = pd.DataFrame([{
                                "Date": new_date,
                                "Score_Blue": new_score_b,
                                "Score_Red": new_score_r,
                                "Winner": "Blue" if new_score_b > new_score_r else ("Red" if new_score_r > new_score_b else "Draw"),
                                "Team_Blue": new_blue,
                                "Team_Red": new_red,
                                "Time": "", "Venue": new_venue, "Cost": "", "Gpay": "", "LateFee": ""
                            }])
                            try:
                                updated_df = pd.concat([st.session_state.match_db, new_row], ignore_index=True)
                                conn = st.session_state.conn
                                conn.update(worksheet="Match_History", data=updated_df)
                                st.session_state.match_db = updated_df
                                st.success("Match Saved Successfully! (Check Google Sheet)")
                            except Exception as e:
                                st.error(f"Failed to save: {e}")
                        else:
                            st.error("Wrong Password")

    with tab4:
        try:
            admin_pw = st.secrets["passwords"]["admin"]
        except (FileNotFoundError, KeyError):
            st.error("🚫 Security Config Missing. Please set up .streamlit/secrets.toml")
            st.stop()

        if st.text_input("Enter Admin Password", type="password", key="db_pass_input") == admin_pw: 
            st.success("✅ Access Granted")
            st.dataframe(st.session_state.master_db, use_container_width=True)
        else:
            st.info("🔒 Enter password to view raw database.")