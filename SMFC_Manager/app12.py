import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection
from mplsoccer import Pitch
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import re

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="SMFC Manager Pro", layout="wide", page_icon="⚽")

# --- 🎨 THEME: "BROADCAST ULTRA" ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@600&display=swap');

    .stApp {
        background-color: #0e1117;
        font-family: 'Rajdhani', sans-serif;
    }

    /* GLOBAL TEXT */
    h1, h2, h3, h4, .stMarkdown, p, span, div, label {
        color: #e0e0e0 !important;
        text-shadow: 0 0 5px rgba(0,0,0,0.8);
    }
    
    /* INPUTS & LABELS (GOLD) */
    .stTextInput label, .stSelectbox label, .stDateInput label, .stTimeInput label, .stSlider label {
        color: #FFD700 !important;
        font-size: 14px !important;
        text-transform: uppercase;
        font-weight: bold;
    }
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px; background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 50px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent; border-radius: 30px; color: #aaa; font-weight: bold; border: none; padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #ff4b4b, #1c83e1) !important; color: white !important;
        box-shadow: 0 0 15px rgba(255, 255, 255, 0.3);
    }

    /* SECTION BOX */
    .section-box {
        background: rgba(20, 24, 30, 0.8); border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px; padding: 24px; margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .section-header {
        font-size: 18px; font-weight: bold; color: #4facfe !important;
        text-transform: uppercase; margin-bottom: 20px;
        border-bottom: 2px solid rgba(255,255,255,0.05); padding-bottom: 10px; letter-spacing: 1px;
    }

    /* COUNTER */
    .count-box {
        background: #111; border: 1px solid #333; padding: 5px 15px; border-radius: 8px;
        min-width: 70px; text-align: center;
    }
    .count-num { font-size: 24px; font-weight: bold; color: white !important; }
    .count-lbl { font-size: 10px; color: #888 !important; letter-spacing: 1px; }

    /* CARDS */
    .player-card {
        background: linear-gradient(145deg, #1a1f26, #14181d);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 10px; padding: 10px; margin-bottom: 8px;
        display: flex; align-items: center; transition: transform 0.2s;
    }
    
    .card-name { font-size: 16px; font-weight: 700; color: white !important; letter-spacing: 0.5px; }
    .card-pos { font-size: 11px; color: #888 !important; font-weight: 600; background: #222; padding: 2px 6px; border-radius: 4px; margin-top: 4px; display:inline-block;}

    .kit-red { border-left: 4px solid #ff4b4b; box-shadow: -5px 0 10px rgba(255, 75, 75, 0.1); }
    .kit-blue { border-left: 4px solid #1c83e1; box-shadow: -5px 0 10px rgba(28, 131, 225, 0.1); }
    .kit-neutral { border-left: 4px solid #ffd700; }

    /* BUTTONS */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #ff8c00 0%, #ff0080 100%);
        font-family: 'Orbitron', sans-serif; border: none; height: 65px; font-size: 24px !important;
        text-transform: uppercase; letter-spacing: 3px; border-radius: 12px;
        box-shadow: 0 0 25px rgba(255, 0, 128, 0.4); color: white !important;
    }
    div.stButton > button[kind="secondary"] {
        background: #238636; border: none; font-weight: bold; border-radius: 8px; color: white !important;
    }
    
    /* 📋 SUMMARY BOX - NUCLEAR OPTION */
    div[data-testid="stCodeBlock"] {
        background-color: #ffffff !important;
        border: 2px solid #ccc !important;
    }
    div[data-testid="stCodeBlock"] pre {
        background-color: #ffffff !important;
    }
    /* Force EVERY text element inside the code block to be black */
    div[data-testid="stCodeBlock"] code,
    div[data-testid="stCodeBlock"] span,
    div[data-testid="stCodeBlock"] div {
        color: #000000 !important;
        font-weight: 900 !important;
        font-family: monospace !important;
        text-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 📊 DATA LOAD ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = pd.read_csv(url)
    except Exception:
        df = pd.DataFrame(columns=["Name", "Position", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY"])
    
    if 'Selected' not in df.columns: df['Selected'] = False
    return df

if 'master_db' not in st.session_state:
    st.session_state.master_db = load_data()
if 'match_squad' not in st.session_state:
    st.session_state.match_squad = pd.DataFrame()
if 'guest_input_val' not in st.session_state:
    st.session_state.guest_input_val = ""

# --- 📌 PRESETS ---
formation_presets = {
    "9 vs 9": {"limit": 9, "DEF_R": [(20,20),(20,50),(20,80)], "MID_R": [(35,15),(35,38),(35,62),(35,85)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,20),(80,50),(80,80)], "MID_B": [(65,15),(65,38),(65,62),(65,85)], "FWD_B": [(55,35),(55,65)]},
    "7 vs 7": {"limit": 7, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,20),(35,50),(35,80)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,20),(65,50),(65,80)], "FWD_B": [(55,35),(55,65)]},
    "6 vs 6": {"limit": 6, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,30),(35,70)], "FWD_R": [(45,35),(45,65)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,30),(65,70)], "FWD_B": [(55,35),(55,65)]},
    "5 vs 5": {"limit": 5, "DEF_R": [(20,30),(20,70)], "MID_R": [(35,30),(35,70)], "FWD_R": [(45,50)], "DEF_B": [(80,30),(80,70)], "MID_B": [(65,30),(65,70)], "FWD_B": [(55,50)]}
}

# --- 🧮 HELPERS ---
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

def clean_whatsapp_name(text):
    text = text.replace('\u200b', '').replace('\u2060', '').replace('\ufeff', '')
    import re
    text = re.sub(r'^\d+[\.\)]\s*', '', text)
    return text.strip()

# --- 📌 APP LAYOUT ---
st.title("⚽ SMFC MANAGER PRO")
tab1, tab2, tab3 = st.tabs(["MATCH LOBBY", "TACTICAL BOARD", "DATABASE"])

with tab1:
    c1, c2 = st.columns([1.3, 1]) 
    with c1:
        smfc_n, guest_n, total_n = get_counts()
        
        st.markdown(f"""
        <div class="section-box">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div class="section-header" style="margin:0; border:none; color:white;">PLAYER POOL</div>
                <div style="display:flex; gap:10px;">
                    <div class="count-box"><div class="count-num">{smfc_n}</div><div class="count-lbl">SMFC</div></div>
                    <div class="count-box"><div class="count-num">{guest_n}</div><div class="count-lbl">GUEST</div></div>
                    <div class="count-box" style="border-color:#ff0080"><div class="count-num" style="color:#ff0080">{total_n}</div><div class="count-lbl">TOTAL</div></div>
                </div>
            </div>
            <hr style="border-color:rgba(255,255,255,0.1); margin:15px 0;">
        """, unsafe_allow_html=True)
        
        with st.expander("📋 PASTE FROM WHATSAPP", expanded=True):
            whatsapp_text = st.text_area("List:", height=80, placeholder="1. Akhil\n2. Isa...", label_visibility="collapsed")
            if st.button("Select Players", type="secondary"):
                st.session_state.master_db['Selected'] = False
                new_guests = []
                lines = whatsapp_text.split('\n')
                for line in lines:
                    import re
                    if not re.match(r'^\d+', line.strip()): continue
                    clean_name = clean_whatsapp_name(line)
                    if len(clean_name) < 2: continue
                    
                    match_found = False
                    for idx, row in st.session_state.master_db.iterrows():
                        db_name_clean = clean_whatsapp_name(str(row['Name']))
                        if db_name_clean.lower() == clean_name.lower():
                            st.session_state.master_db.at[idx, 'Selected'] = True
                            match_found = True
                            break
                    if not match_found:
                        new_guests.append(clean_name)

                existing_guests = get_guests_list()
                final_guests = list(set(existing_guests + new_guests))
                st.session_state.guest_input_val = ", ".join(final_guests)
                st.rerun()

        st.markdown("<br><b>MANUAL SELECTION</b>", unsafe_allow_html=True)
        pos_tab1, pos_tab2, pos_tab3, pos_tab4 = st.tabs(["ALL", "FWD", "MID", "DEF"])
        def render_checklist(df_subset, tab_name):
            df_subset = df_subset.sort_values("Name")
            cols = st.columns(3)
            for i, (index, row) in enumerate(df_subset.iterrows()):
                col = cols[i % 3]
                col.checkbox(f"{row['Name']}", value=bool(row['Selected']), key=f"chk_{row['Name']}_{tab_name}", on_change=toggle_selection, args=(row['Name'],))

        with pos_tab1: render_checklist(st.session_state.master_db, "all")
        with pos_tab2: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'FWD'], "fwd")
        with pos_tab3: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'MID'], "mid")
        with pos_tab4: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'DEF'], "def")

        st.write("")
        st.text_input("Guests (Comma separated)", key="guest_input_val")
        st.markdown('</div>', unsafe_allow_html=True)

        # --- MATCH SETTINGS (ABOVE BUTTON) ---
        st.markdown('<div class="section-box"><div class="section-header">MATCH SETTINGS</div>', unsafe_allow_html=True)
        
        m1, m2 = st.columns(2)
        with m1:
            match_date = st.date_input("Match Date", datetime.today())
            start_time = st.time_input("Kickoff Time", value=pd.to_datetime("07:00").time())
        with m2:
            venue_opt = st.selectbox("Ground / Venue", ["BFC", "GoatArena", "SportZ", "Other"])
            if venue_opt == "Other":
                venue = st.text_input("Enter Venue Name", "Ground Name")
            else:
                venue = venue_opt
            duration = st.slider("Duration (Mins)", 60, 120, 90, step=30)

        match_day_name = match_date.strftime("%A")
        dummy_date = datetime.combine(datetime.today(), start_time)
        end_time_dt = dummy_date + timedelta(minutes=duration)
        time_str = f"{start_time.strftime('%I:%M %p')} - {end_time_dt.strftime('%I:%M %p')}"
        
        st.session_state.match_format = st.selectbox("FORMAT", ["9 vs 9", "7 vs 7", "6 vs 6", "5 vs 5"])
        
        st.markdown('</div>', unsafe_allow_html=True)

        # --- GENERATE BUTTON ---
        if st.button("⚡ GENERATE SQUAD", type="primary"):
            active = st.session_state.master_db[st.session_state.master_db['Selected'] == True].copy()
            guests = get_guests_list()
            if guests:
                for g in guests:
                    new_guest = {"Name": g, "Position": "MID", "PAC":70,"SHO":70,"PAS":70,"DRI":70,"DEF":70,"PHY":70}
                    active = pd.concat([active, pd.DataFrame([new_guest])], ignore_index=True)
            
            if active.empty:
                st.error("⚠️ No players selected!")
            else:
                active['OVR'] = active[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
                active['Sort_OVR'] = active['OVR'] + np.random.uniform(-3.0, 3.0, size=len(active))
                active = active.sort_values('Sort_OVR', ascending=False).reset_index(drop=True)
                active['Team'] = ["Red" if i % 4 in [0, 3] else "Blue" for i in range(len(active))]
                st.session_state.match_squad = active
                st.toast("🚀 Teams Generated!", icon="🔥")
                st.rerun()

    with c2:
        st.markdown('<div class="section-box"><div class="section-header">LINEUPS PREVIEW</div>', unsafe_allow_html=True)
        if not st.session_state.match_squad.empty:
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            
            c_r, c_b = st.columns(2)
            with c_r:
                st.markdown(f"<h3 style='color:#ff4b4b; text-align:center'>RED ({len(reds)})</h3>", unsafe_allow_html=True)
                for _, p in reds.iterrows():
                    av = f"https://ui-avatars.com/api/?name={p['Name']}&background=ff4b4b&color=fff"
                    st.markdown(f"""<div class="player-card kit-red"><img src="{av}" class="card-avatar"><div><div class="card-name">{p['Name']}</div><div class="card-pos">{p['Position']}</div></div></div>""", unsafe_allow_html=True)
            with c_b:
                st.markdown(f"<h3 style='color:#1c83e1; text-align:center'>BLUE ({len(blues)})</h3>", unsafe_allow_html=True)
                for _, p in blues.iterrows():
                    av = f"https://ui-avatars.com/api/?name={p['Name']}&background=1c83e1&color=fff"
                    st.markdown(f"""<div class="player-card kit-blue"><img src="{av}" class="card-avatar"><div><div class="card-name">{p['Name']}</div><div class="card-pos">{p['Position']}</div></div></div>""", unsafe_allow_html=True)
            
            # --- COPYABLE SUMMARY ---
            st.write("---")
            st.subheader("📋 COPY MATCH SUMMARY")
            
            formatted_date = match_date.strftime("%d %b")
            red_list = "\n".join([p['Name'] for p in reds.to_dict('records')])
            blue_list = "\n".join([p['Name'] for p in blues.to_dict('records')])
            
            summary_text = f"""Date: {match_day_name}, {formatted_date}
Time: {time_str}
Ground: {venue}
Score: Blue 0-0 Red
Cost per player: ***
Gpay: ***
LateFee: 50

🔵 *BLUE TEAM*
{blue_list}

🔴 *RED TEAM*
{red_list}"""
            
            st.code(summary_text, language=None)
            st.caption("Double-click to copy.")
            
            st.write("---")
            cx1, cx2, cx3 = st.columns([3,1,3])
            s_red = cx1.selectbox("Swap Red", reds["Name"], label_visibility="collapsed")
            if cx2.button("↔️", key="swap"):
                idx_r = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_red].index[0]
                idx_b = st.session_state.match_squad[st.session_state.match_squad["Name"] == st.session_state.swap_temp].index[0]
                st.session_state.match_squad.at[idx_r, "Team"] = "Blue"
                st.session_state.match_squad.at[idx_b, "Team"] = "Red"
                st.rerun()
            st.session_state.swap_temp = cx3.selectbox("Swap Blue", blues["Name"], label_visibility="collapsed")

        else:
            active_smfc = st.session_state.master_db[st.session_state.master_db['Selected'] == True]
            guests = get_guests_list()
            if active_smfc.empty and not guests:
                st.info("Waiting for players...")
            else:
                for _, p in active_smfc.iterrows():
                    av = f"https://ui-avatars.com/api/?name={p['Name']}&background=333&color=d4af37"
                    st.markdown(f"""<div class="player-card kit-neutral"><img src="{av}" class="card-avatar"><div><div class="card-name">{p['Name']}</div><div class="card-pos">{p['Position']}</div></div></div>""", unsafe_allow_html=True)
                for g in guests:
                    av = f"https://ui-avatars.com/api/?name={g}&background=444&color=aaa"
                    st.markdown(f"""<div class="player-card kit-neutral"><img src="{av}" class="card-avatar"><div><div class="card-name">{g}</div><div class="card-pos">GUEST</div></div></div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    if not st.session_state.match_squad.empty:
        pitch = Pitch(pitch_type='custom', pitch_length=100, pitch_width=100,
                      pitch_color='#43a047', line_color='white', linewidth=2, stripe=False)
        fig, ax = pitch.draw(figsize=(14, 8))
        
        def draw_player(player, x, y, color):
            pitch.scatter(x, y, s=700, marker='h', c=color, edgecolors='white', linewidth=2, ax=ax, zorder=2)
            bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1)
            ax.text(x, y-5, player["Name"], color='black', ha='center', va='top', fontsize=11, fontweight='bold', bbox=bbox_props, zorder=3)

        fmt = st.session_state.get('match_format', '9 vs 9')
        coords_map = formation_presets.get(fmt, formation_presets['9 vs 9'])
        
        reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
        assigned_r = {"DEF":[], "MID":[], "FWD":[]}
        rem_r = []
        for _, p in reds.iterrows():
            pos = p["Position"] if p["Position"] in assigned_r else "MID"
            key = f"{pos}_R"
            if len(assigned_r[pos]) < len(coords_map.get(key, [])): assigned_r[pos].append(p)
            else: rem_r.append(p)
        for r in ["DEF","MID","FWD"]:
             key = f"{r}_R"
             while len(assigned_r[r]) < len(coords_map.get(key,[])) and rem_r: assigned_r[r].append(rem_r.pop(0))
        
        for role, players in assigned_r.items():
            key = f"{role}_R"
            if key in coords_map:
                for i, p in enumerate(players):
                    if i < len(coords_map[key]):
                        x, y = coords_map[key][i]
                        draw_player(p, x, y, '#ff4b4b') 

        blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
        assigned_b = {"DEF":[], "MID":[], "FWD":[]}
        rem_b = []
        for _, p in blues.iterrows():
            pos = p["Position"] if p["Position"] in assigned_b else "MID"
            key = f"{pos}_B"
            if len(assigned_b[pos]) < len(coords_map.get(key, [])): assigned_b[pos].append(p)
            else: rem_b.append(p)
        for r in ["DEF","MID","FWD"]:
             key = f"{r}_B"
             while len(assigned_b[r]) < len(coords_map.get(key,[])) and rem_b: assigned_b[r].append(rem_b.pop(0))

        for role, players in assigned_b.items():
            key = f"{role}_B"
            if key in coords_map:
                for i, p in enumerate(players):
                    if i < len(coords_map[key]):
                        x, y = coords_map[key][i]
                        draw_player(p, x, y, '#1c83e1')

        st.pyplot(fig)
        
        if rem_r or rem_b:
            st.info(f"🔁 SUBS | RED: {', '.join([p['Name'] for p in rem_r])} | BLUE: {', '.join([p['Name'] for p in rem_b])}")
            
    else:
        st.warning("Please Generate a Squad in Tab 1 first!")

with tab3:
    if st.text_input("PASSCODE", type="password") == "1234":
        st.data_editor(st.session_state.master_db, use_container_width=True)