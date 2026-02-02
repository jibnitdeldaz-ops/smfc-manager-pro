import streamlit as st
from mplsoccer import Pitch

# --- 3-4-2 FORMATION COORDINATES ---
# We define x (length) and y (width) positions
# Defense: 3 players | Midfield: 4 players | Forwards: 2 players
formations_9v9 = {
    "3-4-2": [
        # DEFENSE (3)
        (25, 20), (25, 40), (25, 60), 
        # MIDFIELD (4)
        (60, 10), (60, 30), (60, 50), (60, 70),
        # FORWARDS (2)
        (95, 30), (95, 50)
    ]
}

st.title("⚽ SMFC 9-a-Side Team Maker")
# --- 📝 SIDEBAR: PLAYER LIST ---
st.sidebar.header("📋 Match Squad")
raw_list = st.sidebar.text_area(
    "Paste WhatsApp List (18 Names):", 
    height=300,
    placeholder="1. Akhil\n2. Aravind\n3. Isa..."
)

# Function to clean names
def clean_and_split(text):
    lines = text.split('\n')
    players = []
    for line in lines:
        # Remove numbers and dots, keep only letters
        clean_name = "".join(i for i in line if not i.isdigit()).replace(".", "").strip()
        if clean_name:
            players.append(clean_name)
    
    # Split into Red and Blue (First 9 are Red, Next 9 are Blue)
    return players[:9], players[9:18]

# Logic to handle the list
red_team_names = []
blue_team_names = []

if raw_list:
    red_team_names, blue_team_names = clean_and_split(raw_list)
    st.sidebar.success(f"✅ Loaded {len(red_team_names) + len(blue_team_names)} players!")
    
    # Check if we have enough players
    if len(red_team_names) < 9 or len(blue_team_names) < 9:
        st.sidebar.warning(f"⚠️ Need 18 players! Found {len(red_team_names) + len(blue_team_names)}")

# Select which team to view
team_view = st.sidebar.radio("View Team:", ["Red Team", "Blue Team"])
team_color = "#cc0000" if team_view == "Red Team" else "#0000cc"

# Create the pitch
pitch = Pitch(pitch_color='#224422', line_color='#ffffff', stripe=True)
fig, ax = pitch.draw(figsize=(10, 7))

# Plot the 9 players
pos_list = formations_9v9["3-4-2"]
# Select Active Team to Display
active_names = red_team_names if team_view == "Red Team" else blue_team_names

# Plot the players
pos_list = formations_9v9["3-4-2"]

for i, pos in enumerate(pos_list):
    # Draw Jersey
    pitch.scatter(pos[0], pos[1], s=800, c=team_color, edgecolors='white', linewidth=2, ax=ax)
    
    # DETERMINE NAME: If we have a list, use the name. Otherwise, use "Pos X"
    if i < len(active_names):
        player_label = active_names[i]
    else:
        player_label = f"Pos {i+1}"
        
    # Draw Name
    ax.text(pos[0], pos[1]-5, player_label, color='white', ha='center', fontweight='bold', fontsize=12)
    
st.pyplot(fig)