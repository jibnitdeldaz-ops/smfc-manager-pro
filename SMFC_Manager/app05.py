import streamlit as st
import pandas as pd
import random
import os
from mplsoccer import Pitch

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="SMFC Team Maker", layout="wide")

# --- 🎨 CUSTOM CSS ---
st.markdown("""
<style>
    .player-card {
        border: 2px solid #d4af37;
        padding: 10px;
        border-radius: 10px;
        background: #fff;
        text-align: center;
        margin-bottom: 5px;
    }
    .swap-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ccc;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 📁 FILE MANAGEMENT ---
CSV_FILE = "players.csv"

def load_data():
    """Loads player data from CSV. Creates default if missing."""
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        st.error(f"❌ Could not find {CSV_FILE}. Please create it!")
        return pd.DataFrame(columns=["Name", "Position", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY"])

def save_data(df):
    """Saves the dataframe to CSV."""
    df.to_csv(CSV_FILE, index=False)

# --- 🧠 1. INITIALIZE MASTER DATABASE ---
if 'master_db' not in st.session_state:
    st.session_state.master_db = load_data()

# --- 2. SESSION STATE ---
if 'match_squad' not in st.session_state:
    st.session_state.match_squad = pd.DataFrame()

# --- 📌 3-4-2 COORDINATES ---
formation_coords = {
    "DEF": [(25, 20), (25, 40), (25, 60)],
    "MID": [(60, 10), (60, 30), (60, 50), (60, 70)],
    "FWD": [(95, 30), (95, 50)]
}

st.title("⚽ SMFC Match Day Manager")

# --- 🗂️ TABS ---
tab1, tab2, tab3 = st.tabs(["📅 Match Day Setup", "🏟️ Tactical Board", "🎴 Master Player DB"])

# ==========================================
# TAB 1: MATCH DAY SETUP
# ==========================================
with tab1:
    c1, c2 = st.columns([1, 1.2]) 
    with c1:
        st.subheader("1. Who is IN?")
        if not st.session_state.master_db.empty:
            all_names = st.session_state.master_db["Name"].tolist()
            selected_names = st.multiselect("Select Players:", all_names, default=all_names)
        else:
            st.warning("No players found in Database!")
            selected_names = []
        
        guest_input = st.text_input("Add Guests:", placeholder="Name 1, Name 2")
        
        st.subheader("2. Create Teams")
        shuffle_mode = st.radio("Shuffle Mode:", ["Balanced by Skill (OVR)", "Random"])
        
        if st.button("🚀 GENERATE SQUAD", type="primary"):
            current_players = st.session_state.master_db[st.session_state.master_db["Name"].isin(selected_names)].copy()
            
            if guest_input:
                guests = [g.strip() for g in guest_input.split(",") if g.strip()]
                for g in guests:
                    new_guest = {"Name": g, "Position": "MID", "PAC": 65, "SHO": 65, "PAS": 65, "DRI": 65, "DEF": 65, "PHY": 65}
                    current_players = pd.concat([current_players, pd.DataFrame([new_guest])], ignore_index=True)
            
            # --- BALANCING LOGIC ---
            if shuffle_mode == "Random":
                shuffled = current_players.sample(frac=1).reset_index(drop=True)
                mid = len(shuffled) // 2
                shuffled.loc[:mid-1, "Team"] = "Red"
                shuffled.loc[mid:, "Team"] = "Blue"
                st.session_state.match_squad = shuffled
            else:
                current_players['OVR'] = current_players[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
                sorted_players = current_players.sort_values(by='OVR', ascending=False).reset_index(drop=True)
                teams = []
                for i in range(len(sorted_players)):
                    teams.append("Red" if (i % 4 == 0 or i % 4 == 3) else "Blue")
                sorted_players['Team'] = teams
                st.session_state.match_squad = sorted_players
            
            st.success(f"✅ Teams Ready!")

    with c2:
        st.subheader("📋 Lineup & Swaps")
        if not st.session_state.match_squad.empty:
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            
            col_r, col_b = st.columns(2)
            with col_r:
                st.markdown(f":red[**RED TEAM ({len(reds)})**]")
                for _, p in reds.iterrows(): st.caption(f"{p['Name']} ({p['Position']})")
            with col_b:
                st.markdown(f":blue[**BLUE TEAM ({len(blues)})**]")
                for _, p in blues.iterrows(): st.caption(f"{p['Name']} ({p['Position']})")
                
            # --- ↔️ TRANSFER MARKET ---
            st.markdown("---")
            st.markdown("### ↔️ Direct Exchange")
            
            with st.container():
                st.markdown('<div class="swap-box">', unsafe_allow_html=True)
                cs1, cs2, cs3 = st.columns([2, 0.5, 2])
                
                with cs1:
                    swap_red = st.selectbox("From Red 🔴", reds["Name"].tolist(), key="s_red")
                with cs2:
                    st.write("")
                    st.write("⚡") 
                with cs3:
                    swap_blue = st.selectbox("From Blue 🔵", blues["Name"].tolist(), key="s_blue")
                
                if st.button("Confirm Swap 🔄", use_container_width=True):
                    idx_red = st.session_state.match_squad[st.session_state.match_squad["Name"] == swap_red].index[0]
                    idx_blue = st.session_state.match_squad[st.session_state.match_squad["Name"] == swap_blue].index[0]
                    
                    st.session_state.match_squad.at[idx_red, "Team"] = "Blue"
                    st.session_state.match_squad.at[idx_blue, "Team"] = "Red"
                    
                    st.success(f"Swapped {swap_red} ↔️ {swap_blue}")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
        else:
            st.info("Waiting for Squad Generation...")

# ==========================================
# TAB 2: TACTICAL BOARD
# ==========================================
with tab2:
    if st.session_state.match_squad.empty:
        st.warning("Generate squad first!")
    else:
        c1, c2 = st.columns([1, 4])
        with c1:
            view_team = st.radio("View Team:", ["Red", "Blue"], horizontal=True)
            team_color = "#cc0000" if view_team == "Red" else "#0000cc"
            team_df = st.session_state.match_squad[st.session_state.match_squad["Team"] == view_team]
            
            if 'OVR' not in team_df.columns:
                team_df['OVR'] = team_df[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
            
            st.metric("⭐ Team Strength", f"{team_df['OVR'].mean():.1f}")
            st.write(f"**Players:** {len(team_df)}")

        with c2:
            pitch = Pitch(pitch_color='#538053', line_color='#ffffff', stripe=False)
            fig, ax = pitch.draw(figsize=(10, 7))

            assigned_slots = {"DEF": [], "MID": [], "FWD": []}
            remaining_players = []

            for idx, player in team_df.iterrows():
                role = player["Position"]
                if role == "GK": role = "DEF" 
                limit = 3 if role == "DEF" else (2 if role == "FWD" else 4)
                if len(assigned_slots.get(role, [])) < limit:
                    assigned_slots[role].append(player)
                else:
                    remaining_players.append(player)
            
            while len(assigned_slots["DEF"]) < 3 and remaining_players:
                assigned_slots["DEF"].append(remaining_players.pop(0))
            while len(assigned_slots["FWD"]) < 2 and remaining_players:
                assigned_slots["FWD"].append(remaining_players.pop(0))
            while len(assigned_slots["MID"]) < 4 and remaining_players:
                assigned_slots["MID"].append(remaining_players.pop(0))
            
            for role, players in assigned_slots.items():
                coords = formation_coords.get(role, [])
                for i, player in enumerate(players):
                    if i < len(coords):
                        x, y = coords[i]
                        ovr = int(player["OVR"]) if "OVR" in player else 70
                        pitch.scatter(x, y, s=2800, marker='H', c=team_color, linewidth=0, ax=ax, zorder=1)
                        ax.text(x, y+2, player["Name"], color='white', ha='center', va='center', fontweight='bold', fontsize=13, zorder=2)
                        ax.text(x, y-3, f"{role} | {ovr}", color='#ffff00', ha='center', va='center', fontsize=9, zorder=2)
            st.pyplot(fig)

# ==========================================
# TAB 3: MASTER DB (FILE SYSTEM)
# ==========================================
with tab3:
    st.subheader("🛠️ Master Player Database (players.csv)")
    st.info("Changes here are saved permanently to the CSV file.")
    
    edited_db = st.data_editor(
        st.session_state.master_db,
        num_rows="dynamic",
        column_config={
            "Position": st.column_config.SelectboxColumn("Position", options=["FWD", "MID", "DEF"]), 
            "PAC": st.column_config.NumberColumn("Pace", min_value=0, max_value=99),
            "SHO": st.column_config.NumberColumn("Shooting", min_value=0, max_value=99),
        },
        height=600
    )
    
    if st.button("💾 Save Changes to CSV"):
        save_data(edited_db)
        st.session_state.master_db = edited_db
        st.success("✅ Saved to players.csv successfully!")