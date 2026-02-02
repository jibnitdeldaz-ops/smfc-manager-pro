import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection
from mplsoccer import Pitch

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="SMFC Manager Pro", layout="wide", page_icon="⚽")

# --- 🎨 THEME: "PRO STADIUM" ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');

    .stApp {
        background-color: #0e1117;
        font-family: 'Rajdhani', sans-serif;
        background-image: radial-gradient(#1c2026 10%, #0e1117 90%);
    }

    h1, h2, h3, h4, p, label, .stMarkdown, div, span {
        color: #e0e0e0 !important;
        text-shadow: 0 0 5px rgba(0,0,0,0.8);
    }

    /* SECTION BOX */
    .section-box {
        background: rgba(255, 255, 255, 0.02);
        border: 2px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
        position: relative;
    }
    .section-header {
        font-size: 20px; font-weight: bold; color: #d4af37 !important;
        text-transform: uppercase; margin-bottom: 15px;
        border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px;
    }

    /* COUNTER */
    .counter-row {
        display: flex; gap: 15px; position: absolute; top: 15px; right: 20px;
    }
    .count-box {
        text-align: center; border: 1px solid #444; padding: 2px 10px; border-radius: 6px; background: rgba(0,0,0,0.5);
    }
    .count-num { font-size: 20px; font-weight: bold; color: white; display: block; line-height: 1; }
    .count-lbl { font-size: 10px; color: #888; text-transform: uppercase; }
    .count-box.total { border-color: #d4af37; }
    .count-box.total .count-num { color: #d4af37; }

    /* CHECKBOXES & CARDS */
    .stCheckbox { background: rgba(0,0,0,0.2); padding: 5px; border-radius: 5px; margin-bottom: 5px; }
    .player-card {
        border-radius: 8px; padding: 8px; margin-bottom: 6px;
        display: flex; align-items: center; background: rgba(20, 20, 20, 0.9);
        border: 1px solid rgba(255,255,255,0.1);
    }
    .card-avatar {
        width: 35px; height: 35px; border-radius: 50%; margin-right: 10px;
        border: 2px solid rgba(255,255,255,0.2);
    }
    .card-name { font-size: 15px; font-weight: bold; color: white; text-transform: uppercase; }
    .card-pos { font-size: 10px; color: #aaa; font-weight: bold; }
    .card-ovr { font-size: 16px; font-weight: bold; color: #d4af37; margin-left: auto; }

    .kit-red { border-left: 4px solid #ff4b4b; background: linear-gradient(90deg, rgba(60, 10, 10, 0.9), rgba(20,20,20,0.9)); }
    .kit-blue { border-left: 4px solid #1c83e1; background: linear-gradient(90deg, rgba(10, 20, 60, 0.9), rgba(20,20,20,0.9)); }
    .kit-neutral { border-left: 4px solid #d4af37; }

    /* GENERATE BUTTON */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #ff4b4b 0%, #1c83e1 100%);
        color: white; border: none; height: 60px; font-size: 22px !important;
        text-transform: uppercase; letter-spacing: 2px; width: 100%;
        box-shadow: 0 0 20px rgba(255, 255, 255, 0.2);
    }
    div.stButton > button[kind="secondary"] {
        background: #2ea043; color: white; border: none; width: 100%;
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

# --- 📌 TACTICS ---
formation_presets = {
    "9 vs 9": {"limit": 9, "DEF": [(30,20),(30,50),(30,80)], "MID": [(60,15),(60,38),(60,62),(60,85)], "FWD": [(90,35),(90,65)]},
    "7 vs 7": {"limit": 7, "DEF": [(30,30),(30,70)], "MID": [(60,20),(60,50),(60,80)], "FWD": [(90,35),(90,65)]},
    "6 vs 6": {"limit": 6, "DEF": [(30,30),(30,70)], "MID": [(60,30),(60,70)], "FWD": [(90,35),(90,65)]},
    "5 vs 5": {"limit": 5, "DEF": [(30,30),(30,70)], "MID": [(60,30),(60,70)], "FWD": [(90,50)]}
}

# --- 🧮 HELPERS ---
def get_guests_list():
    raw = st.session_state.get('guest_input_val', '')
    return [g.strip() for g in raw.split(',') if g.strip()]

def get_counts():
    smfc_count = st.session_state.master_db['Selected'].sum()
    guest_count = len(get_guests_list())
    return smfc_count, guest_count, smfc_count + guest_count

# --- 🔄 CALLBACK: The Key Fix ---
def toggle_selection(player_name):
    """Only runs when a user PHYSICALLY clicks a checkbox"""
    # Find player index by name
    idx = st.session_state.master_db[st.session_state.master_db['Name'] == player_name].index[0]
    # Toggle the value
    current_val = st.session_state.master_db.at[idx, 'Selected']
    st.session_state.master_db.at[idx, 'Selected'] = not current_val

# --- 📌 APP LAYOUT ---
st.title("⚽ SMFC MANAGER PRO")
tab1, tab2, tab3 = st.tabs(["🔥 MATCH LOBBY", "🏟️ TACTICAL BOARD", "🔒 DATABASE"])

with tab1:
    c1, c2 = st.columns([1.2, 1])
    
    # --- LEFT: THE POOL ---
    with c1:
        smfc_n, guest_n, total_n = get_counts()
        
        st.markdown(f"""
        <div class="section-box">
            <div class="section-header">1. PLAYER POOL</div>
            <div class="counter-row">
                <div class="count-box"><span class="count-num">{smfc_n}</span><span class="count-lbl">SMFC</span></div>
                <div class="count-box"><span class="count-num">{guest_n}</span><span class="count-lbl">GUEST</span></div>
                <div class="count-box total"><span class="count-num">{total_n}</span><span class="count-lbl">TOTAL</span></div>
            </div>
        """, unsafe_allow_html=True)
        
        # A. WhatsApp Processor
        with st.expander("📲 PASTE FROM WHATSAPP", expanded=True):
            whatsapp_text = st.text_area("Paste list:", height=80, placeholder="1. Akhil\n2. New Guy...", label_visibility="collapsed")
            if st.button("Select Players", type="secondary"):
                st.session_state.master_db['Selected'] = False
                new_guests = []
                
                lines = whatsapp_text.split('\n')
                for line in lines:
                    clean_name = line.strip()
                    import re
                    clean_name = re.sub(r'^\d+[\.\)]\s*', '', clean_name) # Remove "1. "
                    if len(clean_name) < 2: continue
                    
                    # Match Logic
                    match_found = False
                    for idx, row in st.session_state.master_db.iterrows():
                        if str(row['Name']).lower().strip() == clean_name.lower().strip():
                            st.session_state.master_db.at[idx, 'Selected'] = True
                            match_found = True
                            break
                    if not match_found:
                        new_guests.append(clean_name)

                # Append Guests
                existing_guests = get_guests_list()
                final_guests = list(set(existing_guests + new_guests))
                st.session_state.guest_input_val = ", ".join(final_guests)
                st.rerun()

        st.write("")
        
        # B. Manual Checkboxes (Using Callback)
        st.caption("👇 MANUAL SELECTION (SMFC)")
        pos_tab1, pos_tab2, pos_tab3, pos_tab4 = st.tabs(["ALL", "FWD", "MID", "DEF"])
        
        def render_checklist(df_subset, tab_name):
            df_subset = df_subset.sort_values("Name")
            cols = st.columns(3)
            for i, (index, row) in enumerate(df_subset.iterrows()):
                col = cols[i % 3]
                
                # KEY FIX: on_change callback prevents auto-uncheck
                col.checkbox(
                    f"{row['Name']}", 
                    value=bool(row['Selected']), 
                    key=f"chk_{row['Name']}_{tab_name}",
                    on_change=toggle_selection,
                    args=(row['Name'],) # Pass name to callback
                )

        with pos_tab1: render_checklist(st.session_state.master_db, "all")
        with pos_tab2: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'FWD'], "fwd")
        with pos_tab3: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'MID'], "mid")
        with pos_tab4: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'DEF'], "def")

        st.write("")
        
        # C. Guest Input
        st.caption("➕ GUESTS")
        st.text_input("Guests", key="guest_input_val", placeholder="Name 1, Name 2", label_visibility="collapsed")
        
        st.markdown('</div>', unsafe_allow_html=True)

        # 2. ACTION AREA
        c_fmt, c_btn = st.columns([1, 2])
        with c_fmt:
            st.session_state.match_format = st.selectbox("FORMAT", ["9 vs 9", "7 vs 7", "6 vs 6", "5 vs 5"])
        with c_btn:
            st.write("")
            st.write("") 
            if st.button("⚡ GENERATE SQUAD", type="primary"):
                # 1. Combine All Players
                active = st.session_state.master_db[st.session_state.master_db['Selected'] == True].copy()
                guests = get_guests_list()
                
                if guests:
                    for g in guests:
                        new_guest = {"Name": g, "Position": "MID", "PAC":70,"SHO":70,"PAS":70,"DRI":70,"DEF":70,"PHY":70}
                        active = pd.concat([active, pd.DataFrame([new_guest])], ignore_index=True)
                
                if active.empty:
                    st.error("⚠️ No players selected! Please paste list or tick boxes.")
                else:
                    # 2. Engine
                    active['OVR'] = active[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
                    active['Sort_OVR'] = active['OVR'] + np.random.uniform(-3.0, 3.0, size=len(active))
                    active = active.sort_values('Sort_OVR', ascending=False).reset_index(drop=True)
                    
                    # 3. Assign
                    active['Team'] = ["Red" if i % 4 in [0, 3] else "Blue" for i in range(len(active))]
                    
                    st.session_state.match_squad = active
                    st.toast("🚀 Teams Generated!", icon="🔥")
                    st.rerun()

    # --- RIGHT: LINEUPS ---
    with c2:
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">2. LINEUPS</div>', unsafe_allow_html=True)
        
        if not st.session_state.match_squad.empty:
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            
            m1, m2 = st.columns(2)
            m1.markdown(f"<h1 style='color:#ff4b4b; text-align:center; margin:0;'>{reds['OVR'].mean():.1f}</h1>", unsafe_allow_html=True)
            m2.markdown(f"<h1 style='color:#1c83e1; text-align:center; margin:0;'>{blues['OVR'].mean():.1f}</h1>", unsafe_allow_html=True)
            
            col_r, col_b = st.columns(2)
            with col_r:
                st.caption("RED TEAM")
                for _, p in reds.iterrows():
                    av = f"https://ui-avatars.com/api/?name={p['Name']}&background=ff4b4b&color=fff"
                    st.markdown(f"""<div class="player-card kit-red"><img src="{av}" class="card-avatar"><div><div class="card-name">{p['Name']}</div><div class="card-pos">{p['Position']}</div></div><div class="card-ovr">{int(p['OVR'])}</div></div>""", unsafe_allow_html=True)
            with col_b:
                st.caption("BLUE TEAM")
                for _, p in blues.iterrows():
                    av = f"https://ui-avatars.com/api/?name={p['Name']}&background=1c83e1&color=fff"
                    st.markdown(f"""<div class="player-card kit-blue"><img src="{av}" class="card-avatar"><div><div class="card-name">{p['Name']}</div><div class="card-pos">{p['Position']}</div></div><div class="card-ovr">{int(p['OVR'])}</div></div>""", unsafe_allow_html=True)
            
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
            active_guests = get_guests_list()
            
            if active_smfc.empty and not active_guests:
                st.info("👈 Select players to see Preview.")
            else:
                st.caption(f"PREVIEW: {len(active_smfc) + len(active_guests)} PLAYERS")
                for _, p in active_smfc.iterrows():
                    av = f"https://ui-avatars.com/api/?name={p['Name']}&background=333&color=d4af37"
                    st.markdown(f"""<div class="player-card kit-neutral"><img src="{av}" class="card-avatar"><div><div class="card-name">{p['Name']}</div><div class="card-pos">{p['Position']}</div></div></div>""", unsafe_allow_html=True)
                for g in active_guests:
                    av = f"https://ui-avatars.com/api/?name={g}&background=444&color=aaa"
                    st.markdown(f"""<div class="player-card kit-neutral"><img src="{av}" class="card-avatar"><div><div class="card-name">{g}</div><div class="card-pos">GUEST</div></div></div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    if not st.session_state.match_squad.empty:
        view = st.radio("VIEW:", ["Red", "Blue"], horizontal=True)
        t_color = "#ff4b4b" if view == "Red" else "#1c83e1"
        t_df = st.session_state.match_squad[st.session_state.match_squad["Team"] == view]
        
        pitch = Pitch(pitch_color='#1a1e23', line_color='#ffffff', stripe=False)
        fig, ax = pitch.draw(figsize=(10, 7))
        
        fmt = st.session_state.get('match_format', '9 vs 9')
        coords_map = formation_presets.get(fmt, formation_presets['9 vs 9'])
        
        assigned = {"DEF":[], "MID":[], "FWD":[]}
        rem = []
        for _, p in t_df.iterrows():
            pos = p["Position"] if p["Position"] in assigned else "MID"
            if len(assigned[pos]) < len(coords_map.get(pos, [])): assigned[pos].append(p)
            else: rem.append(p)
        
        for r in ["DEF","MID","FWD"]:
             while len(assigned[r]) < len(coords_map.get(r,[])) and rem: assigned[r].append(rem.pop(0))
        
        for role, players in assigned.items():
            if role in coords_map:
                for i, p in enumerate(players):
                    if i < len(coords_map[role]):
                        x, y = coords_map[role][i]
                        pitch.scatter(x, y, s=3000, c=t_color, ax=ax, alpha=0.7, edgecolors='white')
                        ax.text(x, y+2, p["Name"], color='white', ha='center', fontweight='bold', fontsize=12)
        st.pyplot(fig)
    else: st.warning("Generate Teams First!")

with tab3:
    if st.text_input("PASSCODE", type="password") == "1234":
        st.data_editor(st.session_state.master_db, use_container_width=True)