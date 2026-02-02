import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# --- ⚙️ PAGE CONFIG (Must be first) ---
st.set_page_config(page_title="SMFC Ultimate Team", layout="wide", page_icon="⚽")

# --- 🎨 THEME: "NEON STADIUM" CSS ---
st.markdown("""
<style>
    /* IMPORT GAMING FONT */
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');

    /* GLOBAL APP THEME */
    .stApp {
        background-color: #0e1117;
        font-family: 'Rajdhani', sans-serif;
    }
    
    /* NEON HEADERS */
    h1, h2, h3 {
        color: white;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
    }
    
    /* GLASSMORPHISM CARDS */
    .glass-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }

    /* TEAM CARDS */
    .red-team-card {
        border-left: 4px solid #ff4b4b;
        background: linear-gradient(90deg, rgba(255, 75, 75, 0.1) 0%, rgba(0,0,0,0) 100%);
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        color: white;
    }
    .blue-team-card {
        border-left: 4px solid #1c83e1;
        background: linear-gradient(90deg, rgba(28, 131, 225, 0.1) 0%, rgba(0,0,0,0) 100%);
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        color: white;
    }

    /* CUSTOM METRIC RINGS */
    .metric-ring-red {
        border: 3px solid #ff4b4b;
        border-radius: 50%;
        width: 100px;
        height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: bold;
        color: #ff4b4b;
        box-shadow: 0 0 15px #ff4b4b;
        margin: auto;
    }
    .metric-ring-blue {
        border: 3px solid #1c83e1;
        border-radius: 50%;
        width: 100px;
        height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: bold;
        color: #1c83e1;
        box-shadow: 0 0 15px #1c83e1;
        margin: auto;
    }
    
    /* BUTTON STYLING */
    .stButton>button {
        background: linear-gradient(45deg, #d4af37, #f7df83);
        color: black;
        font-weight: bold;
        border: none;
        border-radius: 5px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# --- 📊 CLOUD CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return pd.read_csv(url)
    except Exception:
        # Fallback for dev mode if secrets aren't loaded yet
        return pd.DataFrame(columns=["Name", "Position", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY"])

# --- 🧠 INITIALIZE DATA ---
if 'master_db' not in st.session_state:
    st.session_state.master_db = load_live_data()
if 'match_squad' not in st.session_state:
    st.session_state.match_squad = pd.DataFrame()

# --- 📌 FORMATION COORDS ---
formation_coords = {
    "DEF": [(25, 20), (25, 40), (25, 60)],
    "MID": [(60, 10), (60, 30), (60, 50), (60, 70)],
    "FWD": [(95, 30), (95, 50)]
}

st.title("⚽ SMFC ULTIMATE TEAM")

# --- 🗂️ TABS ---
tab1, tab2, tab3 = st.tabs(["🔥 MATCH LOBBY", "🏟️ TACTICAL BOARD", "🔒 SCOUT DATABASE"])

# ==========================================
# TAB 1: THE GAMING LOBBY
# ==========================================
with tab1:
    c1, c2 = st.columns([1, 1.5])
    
    # --- LEFT: SQUAD SELECTOR ---
    with c1:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.subheader("1. SQUAD SELECTION")
        
        if st.button("🔄 Sync Cloud Data"):
            st.session_state.master_db = load_live_data()
            st.rerun()

        all_names = st.session_state.master_db["Name"].tolist()
        selected_names = st.multiselect("Active Players:", all_names, default=all_names)
        guest_input = st.text_input("Deploy Guests:", placeholder="Guest1, Guest2")

        if st.button("🚀 GENERATE MATCH", type="primary", use_container_width=True):
            # 1. Filter
            current_players = st.session_state.master_db[st.session_state.master_db["Name"].isin(selected_names)].copy()
            
            # 2. Add Guests
            if guest_input:
                guests = [g.strip() for g in guest_input.split(",") if g.strip()]
                for g in guests:
                    new_guest = {"Name": g, "Position": "MID", "PAC": 70, "SHO": 70, "PAS": 70, "DRI": 70, "DEF": 70, "PHY": 70}
                    current_players = pd.concat([current_players, pd.DataFrame([new_guest])], ignore_index=True)

            # 3. Calculate OVR
            current_players['OVR'] = current_players[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
            
            # 4. Balanced Shuffle
            sorted_p = current_players.sort_values(by='OVR', ascending=False).reset_index(drop=True)
            teams = ["Red" if (i % 4 == 0 or i % 4 == 3) else "Blue" for i in range(len(sorted_p))]
            sorted_p['Team'] = teams
            st.session_state.match_squad = sorted_p
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- RIGHT: LIVE SQUAD PREVIEW ---
    with c2:
        if not st.session_state.match_squad.empty:
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            
            # TEAM STRENGTH RINGS
            r_ovr = reds['OVR'].mean()
            b_ovr = blues['OVR'].mean()
            
            col_metrics1, col_metrics2 = st.columns(2)
            with col_metrics1:
                st.markdown(f"""
                    <div class="metric-ring-red">
                        {r_ovr:.1f}
                    </div>
                    <p style='text-align:center; color:#ff4b4b; font-weight:bold;'>RED ATTACK</p>
                """, unsafe_allow_html=True)
            with col_metrics2:
                st.markdown(f"""
                    <div class="metric-ring-blue">
                        {b_ovr:.1f}
                    </div>
                    <p style='text-align:center; color:#1c83e1; font-weight:bold;'>BLUE CONTROL</p>
                """, unsafe_allow_html=True)

            # SQUAD LISTS
            st.markdown('<div class="glass-container">', unsafe_allow_html=True)
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown("### 🔴 RED TEAM")
                for _, p in reds.iterrows():
                    st.markdown(f'<div class="red-team-card"><b>{p["Name"]}</b> <span style="float:right; opacity:0.7">{int(p["OVR"])}</span></div>', unsafe_allow_html=True)
            with sc2:
                st.markdown("### 🔵 BLUE TEAM")
                for _, p in blues.iterrows():
                    st.markdown(f'<div class="blue-team-card"><b>{p["Name"]}</b> <span style="float:right; opacity:0.7">{int(p["OVR"])}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # SWAP ZONE
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
            st.info("⚠️ WAITING FOR KICKOFF... GENERATE SQUAD TO BEGIN")

# ==========================================
# TAB 2: NIGHT MODE TACTICAL BOARD
# ==========================================
with tab2:
    if st.session_state.match_squad.empty:
        st.warning("PLEASE GENERATE TEAMS FIRST")
    else:
        view = st.radio("TACTICAL VIEW:", ["Red", "Blue"], horizontal=True)
        t_color = "#ff4b4b" if view == "Red" else "#1c83e1"
        t_df = st.session_state.match_squad[st.session_state.match_squad["Team"] == view]
        
        # DARK PITCH THEME
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
                    # GLOW EFFECT DOTS
                    pitch.scatter(x, y, s=3000, marker='H', c=t_color, alpha=0.3, ax=ax, zorder=1)
                    pitch.scatter(x, y, s=1500, marker='H', c=t_color, ax=ax, zorder=2)
                    ax.text(x, y+2, p["Name"], color='white', ha='center', fontweight='bold', fontsize=14, zorder=3)
                    ax.text(x, y-3, f"{int(p['OVR'])}", color='#ffff00', ha='center', fontsize=10, zorder=3)
        
        st.pyplot(fig)

# ==========================================
# TAB 3: SECURE SCOUT DB
# ==========================================
with tab3:
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    st.subheader("🔒 RESTRICTED AREA: SCOUTING REPORT")
    
    # PASSCODE LOCK
    password = st.text_input("ENTER ACCESS CODE:", type="password")
    
    if password == "1234":  # SIMPLE PASSCODE
        st.success("ACCESS GRANTED")
        edited_df = st.data_editor(
            st.session_state.master_db, 
            use_container_width=True,
            num_rows="dynamic"
        )
        if st.button("💾 SAVE TO CLOUD"):
            # Note: Public export links are read-only. 
            # We save to session state for now to keep game running.
            st.session_state.master_db = edited_df
            st.success("LOCAL CACHE UPDATED")
    elif password:
        st.error("⛔ ACCESS DENIED")
    else:
        st.info("This area is restricted to Team Managers.")
    
    st.markdown('</div>', unsafe_allow_html=True)