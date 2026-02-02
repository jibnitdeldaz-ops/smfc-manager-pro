import streamlit as st
from mplsoccer import Pitch

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="SMFC Team Maker", layout="wide")

# --- 📌 FORMATION COORDINATES (9-a-Side) ---
# Coordinates are (x, y) where x=Length(0-120) and y=Width(0-80)
formations_9v9 = {
    "3-4-2": [
        # DEFENSE (3 Players) - Spread across the back
        (25, 20), (25, 40), (25, 60),
        # MIDFIELD (4 Players) - Spread across the middle
        (60, 10), (60, 30), (60, 50), (60, 70),
        # FORWARDS (2 Players) - Up top
        (95, 30), (95, 50)
    ]
}

# --- 🧹 FUNCTION: CLEAN & SPLIT LIST ---
def clean_and_split(text):
    """Removes numbers/dots from WhatsApp list and splits into 2 teams"""
    lines = text.split('\n')
    players = []
    for line in lines:
        # Keep only letters and spaces, remove digits and dots
        clean_name = "".join(i for i in line if not i.isdigit()).replace(".", "").strip()
        if clean_name:
            players.append(clean_name)
    
    # First 9 -> Red Team, Next 9 -> Blue Team
    return players[:9], players[9:18]

# --- 🎨 SIDEBAR: INPUTS ---
st.sidebar.header("📋 Match Squad")
st.sidebar.info("Paste your list of 18 players below:")

raw_list = st.sidebar.text_area(
    "WhatsApp List:", 
    height=300,
    placeholder="1. Akhil\n2. Aravind\n3. Isa\n4. Anchal..."
)

# Process the list immediately
red_team_names = []
blue_team_names = []

if raw_list:
    red_team_names, blue_team_names = clean_and_split(raw_list)
    total_players = len(red_team_names) + len(blue_team_names)
    st.sidebar.success(f"✅ Found {total_players} players")
    
    if total_players < 18:
        st.sidebar.warning(f"⚠️ Warning: List has {total_players}/18 players.")

# --- 🏟️ MAIN PAGE: GUI ---
st.title("⚽ SMFC Team Maker: Tactical Board")

# Toggle View
team_view = st.radio("Select View:", ["Red Team", "Blue Team"], horizontal=True)

# Set Colors
if team_view == "Red Team":
    team_color = "#cc0000"  # Red
    active_names = red_team_names
else:
    team_color = "#0000cc"  # Blue
    active_names = blue_team_names

# --- 🎨 DRAW THE PITCH ---
# 'stripe=False' removes the light/dark stripes for better readability
pitch = Pitch(pitch_color='#538053', line_color='#ffffff', stripe=False) 
fig, ax = pitch.draw(figsize=(10, 7))

# Get positions for 3-4-2
pos_list = formations_9v9["3-4-2"]

# Loop through positions and draw players
for i, pos in enumerate(pos_list):
    # Determine Name (use "?" if list is too short)
    if i < len(active_names):
        player_name = active_names[i]
    else:
        player_name = "?"

    # 1. Draw Jersey (Big Hexagon, No Outline)
    # s=2800: Bigger size
    # linewidth=0: Removes the white outline completely
    pitch.scatter(pos[0], pos[1], s=2800, marker='H', c=team_color, 
                  linewidth=0, ax=ax, zorder=1)
    
    # 2. Draw Name (Centered & Bigger)
    # fontsize=15: Much easier to read
    ax.text(pos[0], pos[1], player_name, color='white', 
            ha='center', va='center', fontweight='bold', fontsize=15, zorder=2)

st.pyplot(fig)