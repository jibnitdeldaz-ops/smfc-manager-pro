import streamlit as st

# --- ⚙️ PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Jibins AI Lab",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 PRO CYBERPUNK THEME ---
st.markdown("""
<style>
    /* 1. MAIN BACKGROUND */
    .stApp {
        background-color: #0e1117;
        background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%);
        color: #e0e0e0;
        font-family: 'Rajdhani', sans-serif;
    }

    /* 2. TITLE GLOW */
    .glow-title {
        font-size: 4rem;
        font-weight: 900;
        text-align: center;
        background: -webkit-linear-gradient(45deg, #00C9FF, #92FE9D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 30px rgba(0, 201, 255, 0.3);
        margin-bottom: 10px;
    }
    
    /* 3. SUBTITLE */
    .subtitle {
        text-align: center;
        font-size: 1.2rem;
        color: #a0a0a0;
        margin-bottom: 50px;
    }

    /* 4. APP CARDS (CONTAINERS) */
    /* Make columns a flex container to align buttons at the bottom */
    div[data-testid="column"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 15px;
        padding: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        display: flex;
        flex-direction: column;
        height: 100%; /* Ensure columns are full height */
    }
    div[data-testid="column"]:hover {
         border-color: rgba(0, 201, 255, 0.5);
         box-shadow: 0 0 20px rgba(0, 201, 255, 0.2);
    }

    /* 5. UNIFORM IMAGE SIZING */
    div[data-testid="stImage"] img {
        height: 300px !important; /* Fixed height for all images */
        width: 100%;
        object-fit: cover; /* Crop image to fit without distorting */
        border-radius: 10px;
    }

    /* 6. PUSH BUTTONS TO BOTTOM */
    /* This targets the container that holds the button */
    div[data-testid="column"] > div:last-child {
        margin-top: auto;
    }
    
    /* 7. BUTTON STYLING */
    div.stButton > button {
        width: 100%;
        height: 55px;
        border-radius: 8px;
        font-size: 18px;
        font-weight: 800;
        text-transform: uppercase;
        border: none !important;
        color: white !important;
        transition: all 0.3s;
    }
    
    /* Specific Gradients */
    div[data-testid="stButton"] > button[key="btn_football"] {
        background: linear-gradient(90deg, #FF512F 0%, #DD2476 100%) !important;
        box-shadow: 0 4px 15px rgba(221, 36, 118, 0.4);
    }

    div[data-testid="stButton"] > button[key="btn_market"] {
        background: linear-gradient(90deg, #1FA2FF 0%, #12D8FA 100%) !important;
        box-shadow: 0 4px 15px rgba(31, 162, 255, 0.4);
    }
    
    /* Hover Effects */
    div.stButton > button:hover {
        transform: translateY(-3px);
        opacity: 0.9;
    }

</style>
""", unsafe_allow_html=True)

# --- 🚀 HEADER SECTION ---
st.markdown('<div class="glow-title">JIBINS AI LAB</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Next-Gen Tools for Sports & Finance</div>', unsafe_allow_html=True)

# --- 🗂️ APP GRID ---
col1, col2 = st.columns(2, gap="large")

with col1:
    # Football Image
    st.image("https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=1000&auto=format&fit=crop")
    st.markdown("### ⚽ SMFC Team Maker")
    st.markdown("The ultimate squad balancer. Create fair teams, manage guest players, and generate match summaries instantly.")
    st.write("")
    if st.button("🚀 LAUNCH TEAM MAKER", key="btn_football", type="primary"):
        st.switch_page("pages/1_⚽_Team_Maker.py")

with col2:
    # Your New Dip Hunter Image
    st.image("https://i.imgur.com/J8x686e.jpeg")
    st.markdown("### 📉 Dip Hunter")
    st.markdown("Live market scanner. Identify falling knives and buy opportunities in ETFs and Stocks with real-time visualization.")
    st.write("")
    if st.button("🚀 LAUNCH DIP HUNTER", key="btn_market", type="primary"):
        st.switch_page("pages/2_📉_Dip_Hunter.py")

# --- 📱 MOBILE FOOTER ---
st.write("---")
st.markdown("""
<div style="text-align: center; color: #555; font-size: 12px;">
    SYSTEM ONLINE • V 2.2 • JIBIN ENGINEERING
</div>
""", unsafe_allow_html=True)