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
    text = text.replace('\u200b', '').replace('\u2060', '').replace('\ufeff', '')
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
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

# --- 📥 DATA LOADING (ROBUST VERSION) ---
def load_data():
    conn = None
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Sheet1", ttl=0)
        
        if df is None or df.empty:
             raise ValueError("Sheet1 returned empty data")
             
        if 'Selected' not in df.columns: df['Selected'] = False
        
        try:
            df_matches = conn.read(worksheet="Match_History", ttl=0)
        except:
            df_matches = pd.DataFrame()
            
        return conn, df, df_matches

    except Exception as e:
        # Fallback to prevent crash
        dummy_df = pd.DataFrame(columns=["Name", "Position", "Selected", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY"])
        return conn, dummy_df, pd.DataFrame()

# --- 📌 PRESETS ---
formation_presets = {
    "9 vs 9": {"limit": 9, "DEF_R": [(20,20),(20,50),(20,80)], "MID_R": [(35,15),(35,38),(35,62),(35,85)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,20),(80,50),(80,80)], "MID_B": [(65,15),(65,38),(65,62),(65,85)], "FWD_B": [(55,35),(55,65)]},
    "7 vs 7": {"limit": 7, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,20),(35,50),(35,80)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,20),(65,50),(65,80)], "FWD_B": [(55,35),(55,65)]},
    "6 vs 6": {"limit": 6, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,30),(35,70)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,30),(65,70)], "FWD_B": [(55,35),(55,65)]},
    "5 vs 5": {"limit": 5, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,30),(35,70)], "FWD_R": [(45,50)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,30),(65,70)], "FWD_B": [(55,50)]}
}

# --- 🚀 MAIN APP ---
def run_football_app():
    # CSS
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@700;900&family=Courier+Prime:wght@700&display=swap');
        .stApp { background-color: #0e1117; font-family: 'Rajdhani', sans-serif; background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%); }
        .section-box { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .player-card { background: linear-gradient(90deg, #1a1f26, #121212); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 8px; margin-bottom: 6px; display: flex; align-items: center; }
        .kit-red { border-left: 4px solid #ff4b4b; }
        .kit-blue { border-left: 4px solid #1c83e1; }
        .spotlight-box { background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%); border-radius: 10px; padding: 15px; text-align: center; height: 100%; border: 1px solid rgba(255,255,255,0.1); }
        .sp-value { font-size: 24px; font-weight: 900; color: #fff; margin: 5px 0; }
        .lb-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid #FF5722; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; }
        .lb-winrate { font-size: 20px; font-weight: 900; color: #00E676; text-align: right; }
        .card-name { font-size: 15px; font-weight: 700; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

    # SESSION STATE
    if 'master_db' not in st.session_state or (isinstance(st.session_state.master_db, pd.DataFrame) and st.session_state.master_db.empty):
        conn, df_p, df_m = load_data()
        st.session_state.conn = conn
        st.session_state.master_db = df_p
        st.session_state.match_db = df_m
    else:
        if 'conn' not in st.session_state:
             conn, df_p, df_m = load_data()
             st.session_state.conn = conn

    if 'match_squad' not in st.session_state: st.session_state.match_squad = pd.DataFrame()
    if 'guest_input_val' not in st.session_state: st.session_state.guest_input_val = ""

    # HEADER
    st.markdown("<h1 style='text-align:center; color:#FF5722;'>SMFC MANAGER PRO</h1>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh Data"):
        st.session_state.pop('master_db', None)
        st.rerun()

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["MATCH LOBBY", "TACTICAL BOARD", "ANALYTICS", "DATABASE"])

    # TAB 1: LOBBY
    with tab1:
        smfc_n, guest_n, total_n = get_counts()
        st.markdown(f"""<div class='section-box' style='text-align:center; font-size:20px; font-weight:bold; color:white;'>PLAYER POOL: <span style='color:#FF5722'>{total_n}</span></div>""", unsafe_allow_html=True)
        
        with st.expander("📋 PASTE FROM WHATSAPP", expanded=True):
            whatsapp_text = st.text_area("List:", height=100, label_visibility="collapsed")
            if st.button("Select Players"):
                if 'Selected' in st.session_state.master_db.columns:
                    st.session_state.master_db['Selected'] = False
                    new_guests = []
                    for line in whatsapp_text.split('\n'):
                        if not re.match(r'^\d+', line.strip()): continue
                        clean_name = clean_whatsapp_name(line)
                        if len(clean_name) < 2: continue
                        match = False
                        for idx, row in st.session_state.master_db.iterrows():
                            if clean_whatsapp_name(str(row['Name'])).lower() == clean_name.lower():
                                st.session_state.master_db.at[idx, 'Selected'] = True
                                match = True; break
                        if not match: new_guests.append(clean_name)
                    st.session_state.guest_input_val = ", ".join(list(set(get_guests_list() + new_guests)))
                    st.rerun()
                else: st.error("DB Offline")

        st.text_input("Guests", key="guest_input_val")
        
        # CHECKLIST
        cols = st.columns(3)
        if 'Name' in st.session_state.master_db.columns:
            for i, (idx, row) in enumerate(st.session_state.master_db.sort_values("Name").iterrows()):
                cols[i%3].checkbox(f"{row['Name']}", value=bool(row.get('Selected', False)), key=f"chk_{row['Name']}", on_change=toggle_selection, args=(row['Name'],))

        # --- MATCH SETTINGS ---
        with st.expander("⚙️ MATCH SETTINGS"):
            c1, c2 = st.columns(2)
            match_date = c1.date_input("Date")
            venue_opt = c2.selectbox("Venue", ["BFC", "SportZ", "Other"])
            venue = st.text_input("Venue Name") if venue_opt == "Other" else venue_opt
            st.session_state.match_format = st.selectbox("Format", ["9 vs 9", "7 vs 7", "6 vs 6"])

        if st.button("⚡ GENERATE SQUAD"):
            if 'Selected' in st.session_state.master_db.columns:
                active = st.session_state.master_db[st.session_state.master_db['Selected'] == True].copy()
                for g in get_guests_list(): active = pd.concat([active, pd.DataFrame([{"Name": g, "Position": "MID", "PAC":70,"SHO":70,"PAS":70,"DRI":70,"DEF":70,"PHY":70}])], ignore_index=True)
                if not active.empty:
                    active['OVR'] = active[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
                    active['Sort_OVR'] = active['OVR'] + np.random.uniform(-3.0, 3.0, size=len(active))
                    active = active.sort_values('Sort_OVR', ascending=False).reset_index(drop=True)
                    active['Team'] = ["Red" if i % 4 in [0, 3] else "Blue" for i in range(len(active))]
                    st.session_state.match_squad = active
                    st.rerun()
            else: st.error("Database offline.")

        # --- PREVIEW & COPY ---
        if not st.session_state.match_squad.empty:
            st.markdown('<div class="section-box"><div style="color:#FF5722; font-weight:bold;">LINEUPS</div>', unsafe_allow_html=True)
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            
            c1, c2 = st.columns(2)
            with c1: 
                st.markdown("#### 🔴 RED")
                for _, p in reds.iterrows(): st.markdown(f"<div class='player-card kit-red'><span class='card-name'>{p['Name']}</span></div>", unsafe_allow_html=True)
            with c2: 
                st.markdown("#### 🔵 BLUE")
                for _, p in blues.iterrows(): st.markdown(f"<div class='player-card kit-blue'><span class='card-name'>{p['Name']}</span></div>", unsafe_allow_html=True)
            
            # COPY BUTTON LOGIC
            r_list = "\n".join([p['Name'] for p in reds.to_dict('records')])
            b_list = "\n".join([p['Name'] for p in blues.to_dict('records')])
            summary = f"Date: {match_date}\nVenue: {venue}\n\n🔵 *BLUE TEAM*\n{b_list}\n\n🔴 *RED TEAM*\n{r_list}"
            
            components.html(
                f"""
                <textarea id="text_to_copy" style="position:absolute; left:-9999px;">{summary}</textarea>
                <button onclick="var c=document.getElementById('text_to_copy');c.select();document.execCommand('copy');this.innerText='✅ COPIED!';" style="background:linear-gradient(90deg, #FF5722, #FF8A65); color:white; font-weight:800; padding:10px 0; border:none; border-radius:8px; width:100%; cursor:pointer;">📋 COPY TEAM LIST</button>
                """, height=50
            )

            # PLAYER TRANSFER WINDOW
            st.write("---")
            st.markdown("### ↔️ TRANSFER WINDOW")
            col_tr_red, col_btn, col_tr_blue = st.columns([4, 1, 4])
            with col_tr_red:
                s_red = st.selectbox("From Red", reds["Name"], key="sel_red")
            with col_tr_blue:
                s_blue = st.selectbox("From Blue", blues["Name"], key="sel_blue")
            with col_btn:
                st.write("")
                if st.button("Swap"):
                    idx_r = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_red].index[0]
                    idx_b = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_blue].index[0]
                    st.session_state.match_squad.at[idx_r, "Team"] = "Blue"
                    st.session_state.match_squad.at[idx_b, "Team"] = "Red"
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # TAB 2: TACTICS
    with tab2:
        if not st.session_state.match_squad.empty:
            pitch = Pitch(pitch_type='custom', pitch_length=100, pitch_width=100, pitch_color='#43a047', line_color='white')
            fig, ax = pitch.draw(figsize=(10, 6))
            
            # Drawing Logic
            def draw_player(player, x, y, color):
                pitch.scatter(x, y, s=500, c=color, edgecolors='white', ax=ax, zorder=2)
                ax.text(x, y-4, player["Name"], color='black', ha='center', fontsize=9, fontweight='bold', bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", lw=1), zorder=3)

            fmt = st.session_state.get('match_format', '9 vs 9')
            coords = formation_presets.get(fmt, formation_presets['9 vs 9'])
            
            # REDS
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            assigned_r = {"DEF":[], "MID":[], "FWD":[]}
            rem_r = []
            for _, p in reds.iterrows():
                pos = p["Position"] if p["Position"] in assigned_r else "MID"
                if len(assigned_r[pos]) < len(coords.get(f"{pos}_R", [])): assigned_r[pos].append(p)
                else: rem_r.append(p)
            for role, players in assigned_r.items():
                for i, p in enumerate(players):
                    x, y = coords[f"{role}_R"][i]
                    draw_player(p, x, y, '#ff4b4b')

            # BLUES
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            assigned_b = {"DEF":[], "MID":[], "FWD":[]}
            rem_b = []
            for _, p in blues.iterrows():
                pos = p["Position"] if p["Position"] in assigned_b else "MID"
                if len(assigned_b[pos]) < len(coords.get(f"{pos}_B", [])): assigned_b[pos].append(p)
                else: rem_b.append(p)
            for role, players in assigned_b.items():
                for i, p in enumerate(players):
                    x, y = coords[f"{role}_B"][i]
                    draw_player(p, x, y, '#1c83e1')

            st.pyplot(fig)
        else: st.info("Generate Squad First")

    # TAB 3: ANALYTICS
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
                with sp1: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #00C9FF;'><div class='sp-value'>{max_m}</div><div>COMMITMENT KING</div><div style='color:#FF5722'>{names_m}</div></div>", unsafe_allow_html=True)
                with sp2: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #FFD700;'><div class='sp-value'>{val_w}</div><div>STAR PLAYER</div><div style='color:#FF5722'>{name_w}</div></div>", unsafe_allow_html=True)
                with sp3: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #ff4b4b;'><div class='sp-value'>{max_l}</div><div>MOST LOSSES</div><div style='color:#FF5722'>{names_l}</div></div>", unsafe_allow_html=True)
                
                st.write("---")
                for p, r in lb.iterrows():
                     st.markdown(f"<div class='lb-card'><div style='font-size:20px; font-weight:900; color:#FF5722'>#{r['Rank']}</div><div><span style='font-size:18px; font-weight:800; color:#fff'>{p}</span><br><span style='font-size:13px; color:#888'>{r['M']} Matches • {r['W']} Wins</span></div><div class='lb-winrate'>{r['Win %']}%</div></div>", unsafe_allow_html=True)
            
            with st.expander("⚙️ LOG MATCH"):
                wa_txt = st.text_area("Paste WhatsApp Chat")
                if st.button("Parse"):
                    parsed = parse_whatsapp_log(wa_txt)
                    if parsed: st.success(f"Parsed: {parsed}")
                    else: st.warning("Failed to parse")

    # TAB 4: DB
    with tab4:
        if st.text_input("Password", type="password") == "1234":
            st.dataframe(st.session_state.master_db)