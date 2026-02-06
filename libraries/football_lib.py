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
def get_img_as_base64(file):
    if os.path.exists(file):
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

def clean_whatsapp_name(text):
    text = re.sub(r'[\u200b\u2060\ufeff\xa0]', '', text)
    text = re.sub(r'^[\d\.\)\-\s]+', '', text)
    return text.strip()

def get_guests_list():
    raw = st.session_state.get('guest_input_val', '')
    return [g.strip() for g in raw.split(',') if g.strip()]

def get_counts():
    smfc_count = 0
    if hasattr(st.session_state, 'master_db') and isinstance(st.session_state.master_db, pd.DataFrame):
        if 'Selected' in st.session_state.master_db.columns:
            smfc_count = st.session_state.master_db['Selected'].sum()
    guest_count = len(get_guests_list())
    return smfc_count, guest_count, smfc_count + guest_count

def toggle_selection(player_name):
    if 'Selected' in st.session_state.master_db.columns:
        idx = st.session_state.master_db[st.session_state.master_db['Name'] == player_name].index[0]
        current_val = st.session_state.master_db.at[idx, 'Selected']
        st.session_state.master_db.at[idx, 'Selected'] = not current_val
        for key in list(st.session_state.keys()):
            if key.startswith(f"chk_{player_name}_"):
                del st.session_state[key]

# --- 🧠 ANALYTICS HELPERS ---
def parse_whatsapp_log(text):
    data = {}
    try:
        venue_match = re.search(r'🏟️\s*(.*)', text)
        data['venue'] = venue_match.group(1).strip() if venue_match else "BFC"
        score_match = re.search(r'Score.*?:.*?(\d+)\s*[-v]\s*(\d+)', text, re.IGNORECASE)
        if score_match:
            val1, val2 = int(score_match.group(1)), int(score_match.group(2))
            line_context = text[max(0, score_match.start()-20):score_match.end()+20].lower()
            if line_context.find('red') < line_context.find('blue'):
                data['s_red'], data['s_blue'] = val1, val2
            else:
                data['s_blue'], data['s_red'] = val1, val2
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
    res = res[res['M'] >= 2]
    res = res.sort_values(by=['Win %', 'W'], ascending=[False, False])
    res['Rank'] = range(1, len(res) + 1)
    icon_map = {'W': '✅', 'L': '❌', 'D': '➖'}
    res['Form (Last 5)'] = res['Form'].apply(lambda x: " ".join([icon_map.get(i, i) for i in x[-5:]]))
    return res

# --- 📥 DATA LOADING ---
def load_data():
    conn = None
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df is None or df.empty: raise ValueError("Sheet1 returned empty data")
        if 'Selected' not in df.columns: df['Selected'] = False
        try: df_matches = conn.read(worksheet="Match_History", ttl=0)
        except: df_matches = pd.DataFrame()
        return conn, df, df_matches
    except Exception as e:
        dummy_df = pd.DataFrame(columns=["Name", "Position", "Selected", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY"])
        return conn, dummy_df, pd.DataFrame()

# --- 📌 PRESETS (3-4-2) ---
formation_presets = {
    "9 vs 9": {"limit": 9, "RED_COORDS": [(15, 20), (15, 50), (15, 80), (35, 15), (35, 38), (35, 62), (35, 85), (55, 35), (55, 65)], "BLUE_COORDS": [(85, 20), (85, 50), (85, 80), (65, 15), (65, 38), (65, 62), (65, 85), (45, 35), (45, 65)]},
    "7 vs 7": {"limit": 7, "RED_COORDS": [(15, 30), (15, 70), (35, 20), (35, 50), (35, 80), (55, 35), (55, 65)], "BLUE_COORDS": [(85, 30), (85, 70), (65, 20), (65, 50), (65, 80), (45, 35), (45, 65)]},
    "6 vs 6": {"limit": 6, "RED_COORDS": [(15, 30), (15, 70), (35, 30), (35, 70), (55, 35), (55, 65)], "BLUE_COORDS": [(85, 30), (85, 70), (65, 30), (65, 70), (45, 35), (45, 65)]},
    "5 vs 5": {"limit": 5, "RED_COORDS": [(15, 30), (15, 70), (35, 50), (50, 30), (50, 70)], "BLUE_COORDS": [(85, 30), (85, 70), (65, 50), (50, 30), (50, 70)]}
}

# --- 🚀 MAIN APP ---
def run_football_app():
    # --- CSS ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@700;900&family=Courier+Prime:wght@700&display=swap');
        .stApp { background-color: #0e1117; font-family: 'Rajdhani', sans-serif; background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%); color: #e0e0e0; }
        input { color: #ffffff !important; }
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="base-input"] { background-color: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; }
        textarea { background-color: #ffffff !important; color: #000000 !important; font-weight: bold !important; border-radius: 8px !important; }
        div[data-baseweb="textarea"] > div { background-color: #ffffff !important; border: 1px solid #ccc !important; }
        div[data-testid="stWidgetLabel"] p { color: #ffffff !important; font-weight: 800 !important; text-transform: uppercase; text-shadow: 0 0 8px rgba(255,255,255,0.6); font-size: 14px !important; }
        [data-testid="stMetricLabel"] { color: #ffffff !important; font-weight: bold !important; text-shadow: 0 0 5px rgba(255,255,255,0.5); }
        [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 900 !important; text-shadow: 0 0 10px rgba(255,255,255,0.7); }
        .badge-box { display: flex; gap: 5px; }
        .badge-smfc, .badge-guest { background:#111; padding:5px 10px; border-radius:6px; border:1px solid #444; color:white; font-weight:bold; }
        .badge-total { background:linear-gradient(45deg, #FF5722, #FF8A65); padding:5px 10px; border-radius:6px; color:white; font-weight:bold; box-shadow: 0 0 10px rgba(255,87,34,0.4); }
        div.stButton > button { background: linear-gradient(90deg, #D84315 0%, #FF5722 100%) !important; color: white !important; font-weight: 900 !important; border: none !important; height: 55px; font-size: 20px !important; text-transform: uppercase; width: 100%; box-shadow: 0 4px 15px rgba(216, 67, 21, 0.4); }
        .section-box { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        
        /* UPDATED PLAYER CARD - SPACE BETWEEN NAME & POS */
        .player-card { 
            background: linear-gradient(90deg, #1a1f26, #121212); 
            border: 1px solid rgba(255,255,255,0.1); 
            border-radius: 8px; 
            padding: 8px 12px; 
            margin-bottom: 6px; 
            display: flex; 
            align-items: center; 
            justify-content: space-between; /* Pushes Pos to right */
        }
        .kit-red { border-left: 4px solid #ff4b4b; }
        .kit-blue { border-left: 4px solid #1c83e1; }
        .card-name { font-size: 15px; font-weight: 700; color: white !important; }
        
        /* POS BADGE STYLE */
        .pos-badge {
            font-size: 11px;
            font-weight: 900;
            background: rgba(255,255,255,0.1);
            padding: 2px 6px;
            border-radius: 4px;
            color: #ccc;
            text-transform: uppercase;
        }

        .spotlight-box { background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%); border-radius: 10px; padding: 15px; text-align: center; height: 100%; border: 1px solid rgba(255,255,255,0.1); }
        .sp-value { font-size: 32px; font-weight: 900; color: #ffffff; margin: 5px 0; text-shadow: 0 0 15px rgba(255,255,255,0.9), 0 0 30px rgba(255,255,255,0.5); }
        .sp-title { font-size: 16px; font-weight: 900; color: #ffffff; text-transform: uppercase; letter-spacing: 1px; text-shadow: 0 0 10px rgba(255,255,255,0.7); margin-bottom: 10px; }
        .sp-name { color: #ffffff; font-size: 20px; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 10px rgba(255,255,255,0.7); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .lb-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid #FF5722; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; }
        .lb-winrate { font-size: 20px; font-weight: 900; color: #00E676; text-align: right; }
        .guest-row-label { color: #FFD700; font-weight: 800; font-size: 15px; text-transform: uppercase; text-shadow: 0 0 5px rgba(255, 215, 0, 0.5); display: flex; align-items: center; height: 100%; padding-top: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    </style>
    """, unsafe_allow_html=True)

    if 'master_db' not in st.session_state or (isinstance(st.session_state.master_db, pd.DataFrame) and st.session_state.master_db.empty):
        conn, df_p, df_m = load_data()
        st.session_state.conn = conn; st.session_state.master_db = df_p; st.session_state.match_db = df_m
    else:
        if 'conn' not in st.session_state: conn, df_p, df_m = load_data(); st.session_state.conn = conn

    if 'match_squad' not in st.session_state: st.session_state.match_squad = pd.DataFrame()
    if 'guest_input_val' not in st.session_state: st.session_state.guest_input_val = ""

    st.markdown("<h1 style='text-align:center; font-family:Rajdhani; font-size: 3.5rem; background: -webkit-linear-gradient(45deg, #D84315, #FF5722); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>SMFC MANAGER PRO</h1>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh Data"): st.session_state.pop('master_db', None); st.rerun()

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
                    lines = whatsapp_text.split('\n')
                    for line in lines:
                        if not re.match(r'^\d', line.strip()): continue 
                        clean_line = clean_whatsapp_name(line)
                        if len(clean_line) < 2: continue
                        match = False
                        for idx, row in st.session_state.master_db.iterrows():
                            if str(row['Name']).strip().lower() == clean_line.lower():
                                st.session_state.master_db.at[idx, 'Selected'] = True; match = True; found_count += 1; break
                        if not match: new_guests.append(clean_line)
                    current = get_guests_list()
                    for g in new_guests:
                        if g not in current: current.append(g)
                    st.session_state.guest_input_val = ", ".join(current)
                    for key in list(st.session_state.keys()):
                        if key.startswith("chk_"): del st.session_state[key]
                    st.toast(f"✅ Found {found_count} players. Guest list updated!")
                    st.rerun()
                else: st.error("DB Offline")

        pos_tabs = st.tabs(["ALL", "FWD", "MID", "DEF"])
        def render_checklist(df_s, t_n):
            if df_s.empty or 'Name' not in df_s.columns: return
            df_s = df_s.sort_values("Name")
            cols = st.columns(3) 
            for i, (idx, row) in enumerate(df_s.iterrows()):
                cols[i % 3].checkbox(f"{row['Name']}", value=bool(row.get('Selected', False)), key=f"chk_{row['Name']}_{t_n}", on_change=toggle_selection, args=(row['Name'],))
        
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
            st.write("---")
            st.markdown("<h3 style='color:#FFD700; text-align:center; margin-bottom: 15px;'>GUEST SQUAD SETUP</h3>", unsafe_allow_html=True)
            for g_name in guests:
                c_name, c_pos, c_lvl = st.columns([3, 2, 3])
                with c_name: st.markdown(f"<div class='guest-row-label'>{g_name}</div>", unsafe_allow_html=True)
                with c_pos: st.selectbox("Pos", ["FWD", "MID", "DEF", "GK"], key=f"g_pos_{g_name}", label_visibility="collapsed")
                with c_lvl: st.selectbox("Lvl", ["⭐⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐", "⭐"], index=2, key=f"g_lvl_{g_name}", label_visibility="collapsed")
            st.write("---")

        st.write(""); 
        if st.button("⚡ GENERATE SQUAD"):
            if 'Selected' in st.session_state.master_db.columns:
                active = st.session_state.master_db[st.session_state.master_db['Selected'] == True].copy()
                guest_rows = []
                star_map = {"⭐": 50, "⭐⭐": 60, "⭐⭐⭐": 70, "⭐⭐⭐⭐": 80, "⭐⭐⭐⭐⭐": 90}
                for g in get_guests_list():
                    chosen_pos = st.session_state.get(f"g_pos_{g}", "MID")
                    chosen_stars = st.session_state.get(f"g_lvl_{g}", "⭐⭐⭐")
                    rating = star_map.get(chosen_stars, 70)
                    guest_rows.append({"Name": g, "Position": chosen_pos, "PAC": rating, "SHO": rating, "PAS": rating, "DRI": rating, "DEF": rating, "PHY": rating})
                if guest_rows: active = pd.concat([active, pd.DataFrame(guest_rows)], ignore_index=True)
                if not active.empty:
                    active['OVR'] = active[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
                    active['Sort_OVR'] = active['OVR'] + np.random.uniform(-3.0, 3.0, size=len(active))
                    active = active.sort_values('Sort_OVR', ascending=False).reset_index(drop=True)
                    active['Team'] = ["Red" if i % 4 in [0, 3] else "Blue" for i in range(len(active))]
                    st.session_state.match_squad = active
                    st.rerun()
            else: st.error("Database offline.")

        if not st.session_state.match_squad.empty:
            # --- SORTED LINEUPS LOGIC ---
            pos_map = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
            st.session_state.match_squad['Pos_Ord'] = st.session_state.match_squad['Position'].map(pos_map).fillna(4)
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"].sort_values('Pos_Ord')
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"].sort_values('Pos_Ord')

            st.markdown('<div class="section-box"><div style="color:#FF5722; font-weight:bold; font-size:18px;">LINEUPS</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: 
                st.markdown("<h4 style='color:#ff4b4b; text-align:center'>RED TEAM</h4>", unsafe_allow_html=True)
                for _, p in reds.iterrows(): 
                    st.markdown(f"<div class='player-card kit-red'><span class='card-name'>{p['Name']}</span><span class='pos-badge'>{p['Position']}</span></div>", unsafe_allow_html=True)
            with c2: 
                st.markdown("<h4 style='color:#1c83e1; text-align:center'>BLUE TEAM</h4>", unsafe_allow_html=True)
                for _, p in blues.iterrows(): 
                    st.markdown(f"<div class='player-card kit-blue'><span class='card-name'>{p['Name']}</span><span class='pos-badge'>{p['Position']}</span></div>", unsafe_allow_html=True)
            
            r_list = "\n".join([p['Name'] for p in reds.to_dict('records')]); b_list = "\n".join([p['Name'] for p in blues.to_dict('records')])
            summary = f"Date: {match_date.strftime('%d %b')} | {match_time.strftime('%I:%M %p')}\nVenue: {venue}\n\n🔵 *BLUE TEAM*\n{b_list}\n\n🔴 *RED TEAM*\n{r_list}"
            components.html(f"""<textarea id="text_to_copy" style="position:absolute; left:-9999px;">{summary}</textarea><button onclick="var c=document.getElementById('text_to_copy');c.select();document.execCommand('copy');this.innerText='✅ COPIED!';" style="background:linear-gradient(90deg, #FF5722, #FF8A65); color:white; font-weight:800; padding:15px 0; border:none; border-radius:8px; width:100%; cursor:pointer; font-size:16px; margin-top:10px;">📋 COPY TEAM LIST</button>""", height=70)

            st.write("---"); st.markdown("<h3 style='text-align:center; color:#FF5722;'>TRANSFER WINDOW</h3>", unsafe_allow_html=True)
            col_tr_red, col_btn, col_tr_blue = st.columns([4, 1, 4])
            with col_tr_red:
                st.markdown(f"<div style='border:2px solid #ff4b4b; border-radius:10px; padding:10px; text-align:center; color:#ff4b4b; font-weight:bold;'>🔴 FROM RED</div>", unsafe_allow_html=True)
                s_red = st.selectbox("Select Red", reds["Name"], key="sel_red", label_visibility="collapsed")
            with col_tr_blue:
                st.markdown(f"<div style='border:2px solid #1c83e1; border-radius:10px; padding:10px; text-align:center; color:#1c83e1; font-weight:bold;'>🔵 FROM BLUE</div>", unsafe_allow_html=True)
                s_blue = st.selectbox("Select Blue", blues["Name"], key="sel_blue", label_visibility="collapsed")
            with col_btn:
                st.write(""); st.write("")
                if st.button("↔️", key="swap_btn"):
                    idx_r = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_red].index[0]
                    idx_b = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_blue].index[0]
                    st.session_state.match_squad.at[idx_r, "Team"] = "Blue"; st.session_state.match_squad.at[idx_b, "Team"] = "Red"; st.rerun()
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
                # SORT for Force Fill logic: GK -> FWD -> MID -> DEF (Fill important spots first? Or DEF first?)
                # Actually for Force Fill, if we want to fill 3 DEF spots, we should put DEFs first.
                # Let's sort by position priority: DEF -> MID -> FWD
                fill_map = {"DEF": 0, "MID": 1, "FWD": 2, "GK": 3}
                st.session_state.match_squad['Fill_Ord'] = st.session_state.match_squad['Position'].map(fill_map).fillna(4)
                
                reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"].sort_values('Fill_Ord')
                blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"].sort_values('Fill_Ord')
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
        else: st.info("Generate Squad First")

    with tab3:
        if 'match_db' in st.session_state and not st.session_state.match_db.empty:
            df_m = st.session_state.match_db
            official_names = set(st.session_state.master_db['Name'].unique()) if 'Name' in st.session_state.master_db.columns else set()
            total_goals = pd.to_numeric(df_m['Score_Blue'], errors='coerce').sum() + pd.to_numeric(df_m['Score_Red'], errors='coerce').sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("MATCHES", len(df_m)); c2.metric("GOALS", int(total_goals)); c3.metric("PLAYERS", len(official_names))
            lb = calculate_leaderboard(df_m, official_names)
            if not lb.empty:
                max_m = lb['M'].max(); names_m = ", ".join(lb[lb['M'] == max_m].index.tolist())
                top_player = lb.iloc[0]; val_w = f"{top_player['Win %']}%"; name_w = lb.index[0]
                max_l = lb['L'].max(); names_l = ", ".join(lb[lb['L'] == max_l].index.tolist())
                sp1, sp2, sp3 = st.columns(3)
                with sp1: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #00C9FF;'><div class='sp-value'>{max_m}</div><div class='sp-title'>COMMITMENT KING</div><div class='sp-name'>{names_m}</div></div>", unsafe_allow_html=True)
                with sp2: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #FFD700;'><div class='sp-value'>{val_w}</div><div class='sp-title'>STAR PLAYER</div><div class='sp-name'>{name_w}</div></div>", unsafe_allow_html=True)
                with sp3: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #ff4b4b;'><div class='sp-value'>{max_l}</div><div class='sp-title'>MOST LOSSES</div><div class='sp-name'>{names_l}</div></div>", unsafe_allow_html=True)
                st.write("---")
                for p, r in lb.iterrows(): st.markdown(f"<div class='lb-card'><div style='font-size:20px; font-weight:900; color:#FF5722'>#{r['Rank']}</div><div><span style='font-size:18px; font-weight:800; color:#fff'>{p}</span><br><span style='font-size:13px; color:#888'>{r['M']} Matches • {r['W']} Wins</span></div><div class='lb-winrate'>{r['Win %']}%</div></div>", unsafe_allow_html=True)
            with st.expander("⚙️ LOG MATCH"):
                wa_txt = st.text_area("Paste WhatsApp Chat")
                if st.button("Parse"):
                    parsed = parse_whatsapp_log(wa_txt)
                    if parsed: st.success(f"Parsed: {parsed}")
                    else: st.warning("Failed to parse")
    with tab4:
        if st.text_input("Password", type="password") == "1234": st.dataframe(st.session_state.master_db)