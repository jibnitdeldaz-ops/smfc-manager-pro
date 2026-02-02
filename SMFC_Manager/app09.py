import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from mplsoccer import Pitch
import re

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="SMFC Ultimate Team", layout="wide", page_icon="⚽")

# --- 🎨 THEME: "NEON & GLASS" CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap');

    /* GLOBAL THEME */
    .stApp {
        background-color: #0e1117;
        font-family: 'Rajdhani', sans-serif;
    }
    
    /* 3D NEON BUTTONS */
    div.stButton > button {
        background: linear-gradient(145deg, #1e2329, #161b20);
        color: #d4af37 !important; /* Gold Text */
        border: 1px solid #333;
        box-shadow: 5px 5px 10px #0b0e12, -5px -5px 10px #21262e;
        border-radius: 12px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.4); /* Gold Glow */
        border-color: #d4af37;
    }
    div.stButton > button:active {
        transform: translateY(2px);
        box-shadow: inset 5px 5px 10px #0b0e12, inset -5px -5px 10px #21262e;
    }
    
    /* PRIMARY ACTION BUTTON (GENERATE) */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #ff4b4b 0%, #a60000 100%);
        color: white !important;
        box-shadow: 0 0 20px rgba(255, 75, 75, 0.4);
        border: none;
    }

    /* FIX TEXT VISIBILITY */
    h1, h2, h3, p, span, label, .stMarkdown {
        color: #e0e0e0 !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    }
    
    /* PLAYER CARD GRID (Used in Tab 1 & 2) */
    .player-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        backdrop-filter: blur(5px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .card-avatar {
        width: 40px; height: 40px; border-radius: 50%; margin-right: 12px;
        border: 2px solid rgba(255,255,255,0.2);
    }
    .card-name { font-size: 16px; font-weight: bold; color: white; }
    .card-pos { font-size: 12px; color: #888; }
    .card-ovr { font-size: 18px; font-weight: bold; color: #d4af37; margin-left: auto; }
    
    .team-red { border-left: 4px solid #ff4b4b; }
    .team-blue { border-left: 4px solid #1c83e1; }

</style>
""", unsafe_allow_html=True)

# --- 📊 CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = pd.read_csv(url)
    except Exception:
        df = pd.DataFrame(columns=["Name", "Position", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY"])
    
    # Add 'Avatar' column for the UI if missing
    if 'Avatar' not in df.columns:
        df['Avatar'] = df['Name'].apply(lambda x: f"https://ui-avatars.com/api/?name={str(x).replace(' ', '+')}&background=random&color=fff&size=64")
    
    # Add 'Selected' column for the checkbox logic (default True)
    if 'Selected' not in df.columns:
        df['Selected'] = True
        
    return df

# --- 🧠 INITIALIZE DATA ---
if 'master_db' not in st.session_state:
    st.session_state.master_db = load_live_data()
if 'match_squad' not in st.session_state:
    st.session_state.match_squad = pd.DataFrame()

formation_coords = {
    "DEF": [(25, 20), (25, 40), (25, 60)],
    "MID": [(60, 10), (60, 30), (60, 50), (60, 70)],
    "FWD": [(95, 30), (95, 50)]
}

st.title("⚽ SMFC ULTIMATE TEAM")
tab1, tab2, tab3 = st.tabs(["🔥 MATCH LOBBY", "🏟️ TACTICAL BOARD", "🔒 SCOUT DATABASE"])

# ==========================================
# TAB 1: THE NEW SQUAD SELECTOR
# ==========================================
with tab1:
    c1, c2 = st.columns([1, 1.2])
    
    # --- LEFT PANEL: SELECTION ---
    with c1:
        st.subheader("1. BUILD ROSTER")
        
        # 1. WHATSAPP IMPORTER
        with st.expander("📲 PASTE FROM WHATSAPP (Auto-Select)", expanded=True):
            whatsapp_text = st.text_area("Paste list here (e.g., '1. Akhil 2. Isa')", height=100)
            if st.button("✅ APPLY LIST"):
                # Reset all to False first
                st.session_state.master_db['Selected'] = False
                # Find names in text (simple match)
                found_count = 0
                for index, row in st.session_state.master_db.iterrows():
                    # Check if name appears in the pasted text (case insensitive)
                    if row['Name'].lower() in whatsapp_text.lower():
                        st.session_state.master_db.at[index, 'Selected'] = True
                        found_count += 1
                st.success(f"Found {found_count} players from list!")
                st.rerun()

        # 2. VISUAL ROSTER (REPLACES MULTISELECT)
        st.write("👇 **MANUAL SELECTION:**")
        
        # Interactive Table with Checkboxes & Avatars
        edited_roster = st.data_editor(
            st.session_state.master_db,
            column_config={
                "Selected": st.column_config.CheckboxColumn("Play?", width="small"),
                "Avatar": st.column_config.ImageColumn("Face", width="small"),
                "Name": st.column_config.TextColumn("Player", width="medium"),
                "Position": st.column_config.TextColumn("Pos", width="small"),
                "PAC": None, "SHO": None, "PAS": None, "DRI": None, "DEF": None, "PHY": None # Hide stats here
            },
            disabled=["Avatar", "Name", "Position"], # Only allow checking boxes
            hide_index=True,
            height=400
        )
        
        # Sync changes back to session state
        st.session_state.master_db = edited_roster

        # GUEST INPUT
        st.write("")
        guest_input = st.text_input("Deploy Guests (Comma separated):", placeholder="Friend 1, Friend 2")

        if st.button("🚀 GENERATE SQUAD", type="primary", use_container_width=True):
            # 1. Filter only 'Selected' players
            active_players = st.session_state.master_db[st.session_state.master_db['Selected'] == True].copy()
            
            # 2. Add Guests
            if guest_input:
                for g in [g.strip() for g in guest_input.split(",") if g.strip()]:
                    new_guest = {"Name": g, "Position": "MID", "PAC": 70, "SHO": 70, "PAS": 70, "DRI": 70, "DEF": 70, "PHY": 70, "Avatar": "https://ui-avatars.com/api/?name=Guest&background=random"}
                    active_players = pd.concat([active_players, pd.DataFrame([new_guest])], ignore_index=True)

            # 3. Calculate Logic
            if 'OVR' not in active_players.columns:
                active_players['OVR'] = active_players[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
            
            sorted_p = active_players.sort_values(by='OVR', ascending=False).reset_index(drop=True)
            teams = ["Red" if (i % 4 == 0 or i % 4 == 3) else "Blue" for i in range(len(sorted_p))]
            sorted_p['Team'] = teams
            st.session_state.match_squad = sorted_p
            st.rerun()

    # --- RIGHT PANEL: RESULTS ---
    with c2:
        st.subheader("2. MATCH PREVIEW")
        if not st.session_state.match_squad.empty:
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]

            # METRICS
            m1, m2 = st.columns(2)
            m1.metric("🔴 RED OVR", f"{reds['OVR'].mean():.1f}")
            m2.metric("🔵 BLUE OVR", f"{blues['OVR'].mean():.1f}")

            # ROSTER CARDS
            col_r, col_b = st.columns(2)
            with col_r:
                for _, p in reds.iterrows():
                    st.markdown(f"""
                    <div class="player-card team-red">
                        <img src="{p.get('Avatar', '')}" class="card-avatar">
                        <div><div class="card-name">{p['Name']}</div><div class="card-pos">{p['Position']}</div></div>
                        <div class="card-ovr">{int(p.get('OVR', 70))}</div>
                    </div>""", unsafe_allow_html=True)
            with col_b:
                for _, p in blues.iterrows():
                    st.markdown(f"""
                    <div class="player-card team-blue">
                        <img src="{p.get('Avatar', '')}" class="card-avatar">
                        <div><div class="card-name">{p['Name']}</div><div class="card-pos">{p['Position']}</div></div>
                        <div class="card-ovr">{int(p.get('OVR', 70))}</div>
                    </div>""", unsafe_allow_html=True)
            
            # SWAP TOOL
            st.write("---")
            cx1, cx2, cx3 = st.columns([3, 1, 3])
            s_red = cx1.selectbox("Swap Red", reds["Name"], label_visibility="collapsed")
            if cx2.button("↔️"):
                 idx_r = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_red].index[0]
                 idx_b = st.session_state.match_squad[st.session_state.match_squad["Name"] == st.session_state.swap_blue_temp].index[0]
                 st.session_state.match_squad.at[idx_r, "Team"] = "Blue"
                 st.session_state.match_squad.at[idx_b, "Team"] = "Red"
                 st.rerun()
            st.session_state.swap_blue_temp = cx3.selectbox("Swap Blue", blues["Name"], label_visibility="collapsed")

        else:
            st.info("👈 Use the WhatsApp Paste or Checkboxes to select players!")

# ==========================================
# TAB 2 & 3 (Keeping them clean)
# ==========================================
with tab2:
    if not st.session_state.match_squad.empty:
        # Same Logic as before, just ensuring it renders
        view = st.radio("VIEW:", ["Red", "Blue"], horizontal=True)
        t_color = "#ff4b4b" if view == "Red" else "#1c83e1"
        t_df = st.session_state.match_squad[st.session_state.match_squad["Team"] == view]
        pitch = Pitch(pitch_color='#1a1e23', line_color='#ffffff', stripe=False)
        fig, ax = pitch.draw(figsize=(10, 7))
        # ... (Insert Formation Logic Here if needed, simplified for brevity) ...
        # Re-using the same drawing logic from previous optimal version
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
        st.pyplot(fig)
    else:
        st.warning("Generate Teams First!")

with tab3:
    st.subheader("🔒 SCOUT DATABASE")
    if st.text_input("PASSCODE", type="password") == "1234":
        edited_df = st.data_editor(st.session_state.master_db, use_container_width=True)