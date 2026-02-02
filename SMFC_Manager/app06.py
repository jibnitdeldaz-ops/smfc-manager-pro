import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from mplsoccer import Pitch

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="SMFC Live Manager", layout="wide")

# --- 📊 CLOUD CONNECTION ---
# Using the secret URL from your secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_data():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return pd.read_csv(url)
    except Exception as e:
        # Fallback to local if cloud is being stubborn
        return pd.read_csv("players.csv")

# --- 🧠 INITIALIZE ---
if 'master_db' not in st.session_state:
    st.session_state.master_db = load_live_data()
if 'match_squad' not in st.session_state:
    st.session_state.match_squad = pd.DataFrame()

formation_coords = {
    "DEF": [(25, 20), (25, 40), (25, 60)],
    "MID": [(60, 10), (60, 30), (60, 50), (60, 70)],
    "FWD": [(95, 30), (95, 50)]
}

st.title("⚽ SMFC Live Match Day Manager")
tab1, tab2, tab3 = st.tabs(["📅 Match Setup", "🏟️ Tactical Board", "🎴 Master DB"])

# ==========================================
# TAB 1: MATCH SETUP (Restored Features)
# ==========================================
with tab1:
    c1, c2 = st.columns([1, 1.2])
    
    # --- COLUMN 1: INPUTS ---
    with c1:
        if st.button("🔄 Refresh Players from Cloud"):
            st.session_state.master_db = load_live_data()
            st.rerun()

        st.subheader("1. Who is IN?")
        all_names = st.session_state.master_db["Name"].tolist()
        selected_names = st.multiselect("Select Players:", all_names, default=all_names)
        
        # Guest Input
        guest_input = st.text_input("Add Guests:", placeholder="Name 1, Name 2")

        if st.button("🚀 GENERATE SQUAD", type="primary"):
            # 1. Filter Players
            current_players = st.session_state.master_db[st.session_state.master_db["Name"].isin(selected_names)].copy()
            
            # 2. Add Guests
            if guest_input:
                guests = [g.strip() for g in guest_input.split(",") if g.strip()]
                for g in guests:
                    new_guest = {"Name": g, "Position": "MID", "PAC": 65, "SHO": 65, "PAS": 65, "DRI": 65, "DEF": 65, "PHY": 65}
                    current_players = pd.concat([current_players, pd.DataFrame([new_guest])], ignore_index=True)

            # 3. Calculate OVR & Shuffle
            current_players['OVR'] = current_players[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
            sorted_p = current_players.sort_values(by='OVR', ascending=False).reset_index(drop=True)
            
            # Snake Draft for Balance
            teams = ["Red" if (i % 4 == 0 or i % 4 == 3) else "Blue" for i in range(len(sorted_p))]
            sorted_p['Team'] = teams
            st.session_state.match_squad = sorted_p
            st.rerun()

    # --- COLUMN 2: TEAM INFO (Restored!) ---
    with c2:
        st.subheader("📋 Team Lineups & Stats")
        
        if not st.session_state.match_squad.empty:
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            
            # 1. TEAM STATS HEADER
            r_ovr = reds['OVR'].mean() if 'OVR' in reds else 0
            b_ovr = blues['OVR'].mean() if 'OVR' in blues else 0
            
            m1, m2 = st.columns(2)
            m1.metric("🔴 Red Strength", f"{r_ovr:.1f}")
            m2.metric("🔵 Blue Strength", f"{b_ovr:.1f}")
            
            st.divider()

            # 2. ROSTERS
            cr, cb = st.columns(2)
            with cr: 
                st.markdown(f":red[**RED TEAM ({len(reds)})**]")
                for _, p in reds.iterrows(): 
                    st.caption(f"**{p['Name']}** ({p['Position']}) - {int(p['OVR'])}")
            with cb: 
                st.markdown(f":blue[**BLUE TEAM ({len(blues)})**]")
                for _, p in blues.iterrows(): 
                    st.caption(f"**{p['Name']}** ({p['Position']}) - {int(p['OVR'])}")

            st.divider()

            # 3. EXCHANGE PLAYERS
            st.subheader("↔️ Transfer Market")
            ex1, ex2, ex3 = st.columns([2, 0.5, 2])
            with ex1:
                s_red = st.selectbox("From Red", reds["Name"].tolist(), key="s_r")
            with ex2:
                st.write("\n\n⚡")
            with ex3:
                s_blue = st.selectbox("From Blue", blues["Name"].tolist(), key="s_b")
                
            if st.button("Confirm Exchange 🔄", use_container_width=True):
                idx_r = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_red].index[0]
                idx_b = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_blue].index[0]
                # Swap logic
                st.session_state.match_squad.at[idx_r, "Team"] = "Blue"
                st.session_state.match_squad.at[idx_b, "Team"] = "Red"
                st.rerun()
        else:
            st.info("👈 Select players and Click 'Generate Squad' to see the teams!")

# ==========================================
# TAB 2: TACTICAL BOARD
# ==========================================
with tab2:
    if st.session_state.match_squad.empty:
        st.warning("Please Generate Squad in Tab 1 first.")
    else:
        view = st.radio("View Team:", ["Red", "Blue"], horizontal=True)
        t_color = "#cc0000" if view == "Red" else "#0000cc"
        t_df = st.session_state.match_squad[st.session_state.match_squad["Team"] == view]
        
        pitch = Pitch(pitch_color='#538053', line_color='#ffffff', stripe=False)
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
                    pitch.scatter(x, y, s=2800, marker='H', c=t_color, linewidth=0, ax=ax, zorder=1)
                    ax.text(x, y+2, p["Name"], color='white', ha='center', fontweight='bold', fontsize=13, zorder=2)
                    ax.text(x, y-3, f"{int(p['OVR'])}", color='#ffff00', ha='center', fontweight='bold', fontsize=10, zorder=2)
        st.pyplot(fig)

# ==========================================
# TAB 3: MASTER DB
# ==========================================
with tab3:
    st.subheader("🛠️ Cloud Database Editor")
    st.info("Edit ratings here -> Click Update -> Saves to Google Sheets.")
    
    updated_df = st.data_editor(st.session_state.master_db, num_rows="dynamic")
    
    if st.button("💾 Update Cloud Sheet"):
        # We need to write back to the CSV URL if using gsheets_connection
        # Note: Writing to a Public CSV export link is NOT possible.
        # Writing requires Service Account Auth (Complex).
        # For now, we update the SESSION only to keep the game going.
        st.session_state.master_db = updated_df
        st.success("Session Updated! (To save permanently, edit the Google Sheet directly)")