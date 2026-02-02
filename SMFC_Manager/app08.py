import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from mplsoccer import Pitch

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="SMFC Ultimate Team", layout="wide", page_icon="⚽")

# --- 🎨 THEME: "NEON STADIUM" CSS (FIXED VISIBILITY) ---
st.markdown("""
<style>
    /* IMPORT GAMING FONT */
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');

    /* GLOBAL DARK THEME & TEXT FIXES */
    .stApp {
        background-color: #0e1117;
        font-family: 'Rajdhani', sans-serif;
    }
    
    /* FORCE TEXT WHITE */
    p, h1, h2, h3, h4, h5, span, div, label {
        color: #ffffff !important;
        text-shadow: 0 0 2px rgba(0,0,0,0.5);
    }
    
    /* FIX MULTISELECT & INPUTS */
    .stMultiSelect, .stTextInput {
        background-color: rgba(255,255,255,0.1);
        border-radius: 5px;
    }
    span[data-baseweb="tag"] {
        background-color: #ff4b4b !important; /* Red tags for selection */
    }

    /* GLASSMORPHISM CARDS */
    .glass-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
    }

    /* ULTIMATE TEAM PLAYER CARD */
    .player-card {
        display: flex;
        align-items: center;
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.2) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 8px;
        transition: transform 0.2s;
    }
    .player-card:hover {
        transform: scale(1.02);
        border-color: #d4af37; /* Gold border on hover */
    }
    .card-avatar {
        width: 45px;
        height: 45px;
        border-radius: 50%;
        margin-right: 15px;
        border: 2px solid rgba(255,255,255,0.2);
    }
    .card-info {
        flex-grow: 1;
        line-height: 1.2;
    }
    .card-name {
        font-size: 18px;
        font-weight: bold;
        text-transform: uppercase;
        color: white;
    }
    .card-pos {
        font-size: 12px;
        color: #cccccc !important;
    }
    .card-ovr {
        font-size: 22px;
        font-weight: bold;
        color: #d4af37 !important; /* Gold Rating */
    }

    /* TEAM COLORS */
    .team-red .card-avatar { border-color: #ff4b4b; box-shadow: 0 0 10px #ff4b4b; }
    .team-blue .card-avatar { border-color: #1c83e1; box-shadow: 0 0 10px #1c83e1; }
    
    /* METRIC RINGS */
    .metric-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 10px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        text-shadow: 0 0 10px currentColor;
    }
    
</style>
""", unsafe_allow_html=True)

# --- 📊 CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return pd.read_csv(url)
    except Exception:
        return pd.DataFrame(columns=["Name", "Position", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY"])

if 'master_db' not in st.session_state:
    st.session_state.master_db = load_live_data()
if 'match_squad' not in st.session_state:
    st.session_state.match_squad = pd.DataFrame()

# --- 📌 3-4-2 COORDS ---
formation_coords = {
    "DEF": [(25, 20), (25, 40), (25, 60)],
    "MID": [(60, 10), (60, 30), (60, 50), (60, 70)],
    "FWD": [(95, 30), (95, 50)]
}

st.title("⚽ SMFC ULTIMATE TEAM")

tab1, tab2, tab3 = st.tabs(["🔥 MATCH LOBBY", "🏟️ TACTICAL BOARD", "🔒 SCOUT DATABASE"])

with tab1:
    c1, c2 = st.columns([1, 1.5])
    
    # --- LEFT: CONTROLS ---
    with c1:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.subheader("1. SQUAD SELECTION")
        
        if st.button("🔄 REFRESH DATA"):
            st.session_state.master_db = load_live_data()
            st.rerun()

        all_names = st.session_state.master_db["Name"].tolist()
        selected_names = st.multiselect("ACTIVE ROSTER:", all_names, default=all_names)
        guest_input = st.text_input("GUEST PLAYERS:", placeholder="Enter names...")

        if st.button("🚀 GENERATE MATCH", type="primary", use_container_width=True):
            current_players = st.session_state.master_db[st.session_state.master_db["Name"].isin(selected_names)].copy()
            
            if guest_input:
                for g in [g.strip() for g in guest_input.split(",") if g.strip()]:
                    new_guest = {"Name": g, "Position": "MID", "PAC": 70, "SHO": 70, "PAS": 70, "DRI": 70, "DEF": 70, "PHY": 70}
                    current_players = pd.concat([current_players, pd.DataFrame([new_guest])], ignore_index=True)

            current_players['OVR'] = current_players[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
            sorted_p = current_players.sort_values(by='OVR', ascending=False).reset_index(drop=True)
            teams = ["Red" if (i % 4 == 0 or i % 4 == 3) else "Blue" for i in range(len(sorted_p))]
            sorted_p['Team'] = teams
            st.session_state.match_squad = sorted_p
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- RIGHT: SQUAD CARDS ---
    with c2:
        if not st.session_state.match_squad.empty:
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            
            # 1. METRICS
            m1, m2 = st.columns(2)
            with m1:
                st.markdown(f"""
                <div class="metric-container" style="border-bottom: 2px solid #ff4b4b;">
                    <span class="metric-value" style="color: #ff4b4b;">{reds['OVR'].mean():.1f}</span>
                    <span style="letter-spacing: 2px;">RED ATTACK</span>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="metric-container" style="border-bottom: 2px solid #1c83e1;">
                    <span class="metric-value" style="color: #1c83e1;">{blues['OVR'].mean():.1f}</span>
                    <span style="letter-spacing: 2px;">BLUE CONTROL</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("") # Spacer

            # 2. PLAYER CARDS (Grid Layout)
            col_r, col_b = st.columns(2)
            
            with col_r:
                st.markdown("### 🔴 RED SQUAD")
                for _, p in reds.iterrows():
                    # Generate Avatar URL based on name
                    avatar_url = f"https://ui-avatars.com/api/?name={p['Name'].replace(' ', '+')}&background=ff4b4b&color=fff&size=128"
                    st.markdown(f"""
                    <div class="player-card team-red">
                        <img src="{avatar_url}" class="card-avatar">
                        <div class="card-info">
                            <div class="card-name">{p['Name']}</div>
                            <div class="card-pos">{p['Position']}</div>
                        </div>
                        <div class="card-ovr">{int(p['OVR'])}</div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_b:
                st.markdown("### 🔵 BLUE SQUAD")
                for _, p in blues.iterrows():
                    avatar_url = f"https://ui-avatars.com/api/?name={p['Name'].replace(' ', '+')}&background=1c83e1&color=fff&size=128"
                    st.markdown(f"""
                    <div class="player-card team-blue">
                        <img src="{avatar_url}" class="card-avatar">
                        <div class="card-info">
                            <div class="card-name">{p['Name']}</div>
                            <div class="card-pos">{p['Position']}</div>
                        </div>
                        <div class="card-ovr">{int(p['OVR'])}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # 3. SWAP
            st.markdown("---")
            st.caption("↔️ QUICK TRADE")
            xc1, xc2, xc3 = st.columns([2,1,2])
            with xc1: s_red = st.selectbox("Red Player", reds["Name"], label_visibility="collapsed")
            with xc2: st.button("🔄", key="swap_btn")
            with xc3: s_blue = st.selectbox("Blue Player", blues["Name"], label_visibility="collapsed")
            
            if st.session_state.get("swap_btn"):
                 idx_r = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_red].index[0]
                 idx_b = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_blue].index[0]
                 st.session_state.match_squad.at[idx_r, "Team"] = "Blue"
                 st.session_state.match_squad.at[idx_b, "Team"] = "Red"
                 st.rerun()

        else:
            st.info("⚠️ WAITING FOR KICKOFF... HIT GENERATE!")

with tab2:
    if st.session_state.match_squad.empty:
        st.warning("PLEASE GENERATE TEAMS FIRST")
    else:
        view = st.radio("TACTICAL VIEW:", ["Red", "Blue"], horizontal=True)
        t_color = "#ff4b4b" if view == "Red" else "#1c83e1"
        t_df = st.session_state.match_squad[st.session_state.match_squad["Team"] == view]
        
        pitch = Pitch(pitch_color='#1a1e23', line_color='#ffffff', stripe=False)
        fig, ax = pitch.draw(figsize=(10, 7))

        assigned = {"DEF": [], "MID": [], "FWD": []}
        remaining = []
        for _, p in t_df.iterrows():
            role = p["Position"] if p["Position"] in assigned else "MID"
            limit = 3 if role == "DEF" else (2 if role == "FWD" else 4)
            if len(assigned[role]) < limit: assigned[role].append(p)
            else: remaining.append(p)
        
        for r in ["DEF", "FWD", "MID"]:
            limit = 3 if r == "DEF" else (2 if r == "FWD" else 4)
            while len(assigned[r]) < limit and remaining: assigned[r].append(remaining.pop(0))

        for role, players in assigned.items():
            coords = formation_coords[role]
            for i, p in enumerate(players):
                if i < len(coords):
                    x, y = coords[i]
                    pitch.scatter(x, y, s=3000, marker='H', c=t_color, alpha=0.3, ax=ax, zorder=1)
                    pitch.scatter(x, y, s=1500, marker='H', c=t_color, ax=ax, zorder=2)
                    ax.text(x, y+2, p["Name"], color='white', ha='center', fontweight='bold', fontsize=14, zorder=3)
                    ax.text(x, y-3, f"{int(p['OVR'])}", color='#ffff00', ha='center', fontsize=10, zorder=3)
        st.pyplot(fig)

with tab3:
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    st.subheader("🔒 RESTRICTED AREA: SCOUTING REPORT")
    password = st.text_input("ENTER ACCESS CODE:", type="password")
    
    if password == "1234":
        st.success("ACCESS GRANTED")
        edited_df = st.data_editor(st.session_state.master_db, use_container_width=True, num_rows="dynamic")
        if st.button("💾 SAVE TO CLOUD"):
            st.session_state.master_db = edited_df
            st.success("LOCAL CACHE UPDATED")
    st.markdown('</div>', unsafe_allow_html=True)