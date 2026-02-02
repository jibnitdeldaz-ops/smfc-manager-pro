import streamlit as st
import pandas as pd
import random
from mplsoccer import Pitch

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="SMFC Team Maker", layout="wide")

# --- 🎨 CUSTOM CSS ---
st.markdown("""
<style>
    .player-card {
        border: 2px solid #d4af37;
        padding: 15px;
        border-radius: 10px;
        background: linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 10px;
    }
    .stat-val { font-weight: bold; font-size: 18px; }
    .stat-lbl { font-size: 10px; color: #555; }
</style>
""", unsafe_allow_html=True)

# --- 🧠 1. INITIALIZE MASTER DATABASE ---
if 'master_db' not in st.session_state:
    data = [
        {"Name": "Akhil", "Position": "FWD", "PAC": 88, "SHO": 85, "PAS": 70, "DRI": 82, "DEF": 40, "PHY": 75},
        {"Name": "Aravind", "Position": "MID", "PAC": 75, "SHO": 70, "PAS": 85, "DRI": 78, "DEF": 60, "PHY": 70},
        {"Name": "Isa", "Position": "DEF", "PAC": 65, "SHO": 40, "PAS": 60, "DRI": 55, "DEF": 90, "PHY": 85},
        {"Name": "Anchal", "Position": "MID", "PAC": 70, "SHO": 65, "PAS": 75, "DRI": 72, "DEF": 55, "PHY": 60},
        {"Name": "Melwin", "Position": "DEF", "PAC": 60, "SHO": 50, "PAS": 55, "DRI": 50, "DEF": 88, "PHY": 82},
        {"Name": "Vaibhav", "Position": "FWD", "PAC": 85, "SHO": 82, "PAS": 65, "DRI": 80, "DEF": 35, "PHY": 70},
        {"Name": "Anoop", "Position": "DEF", "PAC": 55, "SHO": 30, "PAS": 50, "DRI": 45, "DEF": 85, "PHY": 88},
        {"Name": "Vigith", "Position": "MID", "PAC": 68, "SHO": 60, "PAS": 80, "DRI": 70, "DEF": 60, "PHY": 65},
        {"Name": "Rasith", "Position": "MID", "PAC": 72, "SHO": 75, "PAS": 75, "DRI": 74, "DEF": 50, "PHY": 68},
        {"Name": "Krithik", "Position": "FWD", "PAC": 82, "SHO": 80, "PAS": 70, "DRI": 78, "DEF": 40, "PHY": 72},
        {"Name": "Agin", "Position": "DEF", "PAC": 62, "SHO": 40, "PAS": 60, "DRI": 50, "DEF": 85, "PHY": 80},
        {"Name": "Gilson", "Position": "MID", "PAC": 70, "SHO": 70, "PAS": 75, "DRI": 72, "DEF": 60, "PHY": 70},
        {"Name": "Diganta", "Position": "DEF", "PAC": 50, "SHO": 30, "PAS": 60, "DRI": 50, "DEF": 80, "PHY": 75}, # Changed GK to DEF
        {"Name": "Sanil", "Position": "DEF", "PAC": 65, "SHO": 50, "PAS": 60, "DRI": 55, "DEF": 82, "PHY": 78},
        {"Name": "Cibin", "Position": "MID", "PAC": 72, "SHO": 68, "PAS": 72, "DRI": 70, "DEF": 55, "PHY": 65},
        {"Name": "Sandeep", "Position": "FWD", "PAC": 80, "SHO": 78, "PAS": 65, "DRI": 75, "DEF": 45, "PHY": 70},
        {"Name": "Arun", "Position": "DEF", "PAC": 60, "SHO": 45, "PAS": 55, "DRI": 50, "DEF": 84, "PHY": 80},
        {"Name": "Rakhil", "Position": "MID", "PAC": 74, "SHO": 72, "PAS": 78, "DRI": 75, "DEF": 58, "PHY": 68},
    ]
    st.session_state.master_db = pd.DataFrame(data)

# --- 2. SESSION STATE ---
if 'match_squad' not in st.session_state:
    st.session_state.match_squad = pd.DataFrame()

# --- 📌 3-4-2 COORDINATES (NO GK) ---
formation_coords = {
    "DEF": [(25, 20), (25, 40), (25, 60)],          # 3 Defenders
    "MID": [(60, 10), (60, 30), (60, 50), (60, 70)], # 4 Midfielders
    "FWD": [(95, 30), (95, 50)]                     # 2 Forwards
}

st.title("⚽ SMFC Match Day Manager")

# --- 🗂️ TABS ---
tab1, tab2, tab3 = st.tabs(["📅 Match Day Setup", "🏟️ Tactical Board", "🎴 Master Player DB"])

# ==========================================
# TAB 1: MATCH DAY SETUP
# ==========================================
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("1. Who is IN?")
        all_names = st.session_state.master_db["Name"].tolist()
        # Default Select ALL 18 players
        selected_names = st.multiselect("Select Players:", all_names, default=all_names)
        
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
            
            st.success(f"✅ Created Teams with {len(st.session_state.match_squad)} Players!")

    with c2:
        st.subheader("📋 Lineup")
        if not st.session_state.match_squad.empty:
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]
            c_r, c_b = st.columns(2)
            with c_r:
                st.markdown(f"**🔴 RED ({len(reds)})**")
                for _, p in reds.iterrows(): st.write(f"- {p['Name']} ({p['Position']})")
            with c_b:
                st.markdown(f"**🔵 BLUE ({len(blues)})**")
                for _, p in blues.iterrows(): st.write(f"- {p['Name']} ({p['Position']})")
                
            st.write("---")
            swap_player = st.selectbox("Select Player to Swap", st.session_state.match_squad["Name"])
            if st.button("Swap Team"):
                idx = st.session_state.match_squad[st.session_state.match_squad["Name"] == swap_player].index[0]
                curr = st.session_state.match_squad.at[idx, "Team"]
                st.session_state.match_squad.at[idx, "Team"] = "Blue" if curr == "Red" else "Red"
                st.rerun()

# ==========================================
# TAB 2: TACTICAL BOARD (SMART 3-4-2)
# ==========================================
with tab2:
    if st.session_state.match_squad.empty:
        st.warning("Generate squad first!")
    else:
        c1, c2 = st.columns([1, 4])
        with c1:
            view_team = st.radio("View Team:", ["Red", "Blue"])
            team_color = "#cc0000" if view_team == "Red" else "#0000cc"
            team_df = st.session_state.match_squad[st.session_state.match_squad["Team"] == view_team]
            
            if 'OVR' not in team_df.columns:
                team_df['OVR'] = team_df[['PAC', 'SHO', 'PAS', 'DRI', 'DEF', 'PHY']].mean(axis=1)
            st.metric("⭐ Team Rating", f"{team_df['OVR'].mean():.1f}")

        with c2:
            pitch = Pitch(pitch_color='#538053', line_color='#ffffff', stripe=False)
            fig, ax = pitch.draw(figsize=(10, 7))

            # --- 🧠 SMART FORMATION FILLER ---
            # We strictly need: 3 DEF, 4 MID, 2 FWD.
            # We sort players into these buckets based on their preferred role.
            
            assigned_slots = {"DEF": [], "MID": [], "FWD": []}
            remaining_players = []

            # 1. First Pass: Put people in their Preferred Roles if space exists
            for idx, player in team_df.iterrows():
                role = player["Position"]
                if role == "GK": role = "DEF" # Force GK to Def
                
                # Check if bucket is full
                limit = 3 if role == "DEF" else (2 if role == "FWD" else 4)
                
                if len(assigned_slots.get(role, [])) < limit:
                    assigned_slots[role].append(player)
                else:
                    remaining_players.append(player)
            
            # 2. Second Pass: Fill empty DEF slots with remaining players
            while len(assigned_slots["DEF"]) < 3 and remaining_players:
                assigned_slots["DEF"].append(remaining_players.pop(0))

            # 3. Third Pass: Fill empty FWD slots with remaining players
            while len(assigned_slots["FWD"]) < 2 and remaining_players:
                assigned_slots["FWD"].append(remaining_players.pop(0))
            
            # 4. Final Pass: Everyone else goes to MID
            while len(assigned_slots["MID"]) < 4 and remaining_players:
                assigned_slots["MID"].append(remaining_players.pop(0))
            
            # --- DRAWING LOGIC ---
            for role, players in assigned_slots.items():
                coords = formation_coords.get(role, [])
                for i, player in enumerate(players):
                    if i < len(coords):
                        x, y = coords[i]
                        name = player["Name"]
                        ovr = int(player["OVR"]) if "OVR" in player else 70
                        
                        pitch.scatter(x, y, s=2800, marker='H', c=team_color, linewidth=0, ax=ax, zorder=1)
                        ax.text(x, y+2, name, color='white', ha='center', va='center', fontweight='bold', fontsize=13, zorder=2)
                        ax.text(x, y-3, f"{role} | {ovr}", color='#ffff00', ha='center', va='center', fontsize=9, zorder=2)

            st.pyplot(fig)

# ==========================================
# TAB 3: MASTER DB
# ==========================================
with tab3:
    edited_db = st.data_editor(
        st.session_state.master_db,
        num_rows="dynamic",
        column_config={
            "Position": st.column_config.SelectboxColumn("Position", options=["FWD", "MID", "DEF"]), # removed GK option
        },
        height=600
    )
    if st.button("💾 Save DB"):
        st.session_state.master_db = edited_db