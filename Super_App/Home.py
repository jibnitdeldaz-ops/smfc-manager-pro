import streamlit as st
import os

# --- 1. CONFIG MUST BE FIRST ---
st.set_page_config(page_title="Jibins AI Lab", layout="wide")

# --- 2. SETUP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
logo_path = os.path.join(parent_dir, "images", "logo.png")
dip_path = os.path.join(parent_dir, "images", "dip_hunter.png")

# --- 3. DEFINE PAGES ---
# We renamed "Team Maker" to "SMFC Manager" since it now includes Analytics
manager_page = st.Page("pages/team_maker.py", title="SMFC Manager", icon="⚽")
dip_page = st.Page("pages/dip_hunter.py", title="Dip Hunter", icon="📉")

# --- 4. DASHBOARD FUNCTION ---
def dashboard():
    # --- CYBERPUNK STYLING ---
    st.markdown("""
    <style>
        .stApp {
            background-color: #0e1117;
            background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%);
            color: #e0e0e0;
            font-family: 'Rajdhani', sans-serif;
        }
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
        .subtitle {
            text-align: center;
            font-size: 1.2rem;
            color: #a0a0a0;
            margin-bottom: 50px;
        }
        div.stButton > button {
            width: 100%; height: 55px; border-radius: 8px; font-size: 18px; font-weight: 800;
            text-transform: uppercase; border: none !important; color: white !important; transition: all 0.3s;
        }
        div[data-testid="stButton"] > button[key="btn_football"] {
            background: linear-gradient(90deg, #FF512F 0%, #DD2476 100%) !important;
            box-shadow: 0 4px 15px rgba(221, 36, 118, 0.4);
        }
        div[data-testid="stButton"] > button[key="btn_market"] {
            background: linear-gradient(90deg, #1FA2FF 0%, #12D8FA 100%) !important;
            box-shadow: 0 4px 15px rgba(31, 162, 255, 0.4);
        }
        div.stButton > button:hover { transform: translateY(-3px); opacity: 0.9; }
        [data-testid="stSidebarNav"] > div > div > span {
            font-weight: 900 !important; color: #00C9FF !important; text-transform: uppercase; letter-spacing: 1px; margin-top: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- CONTENT ---
    st.markdown('<div class="glow-title">JIBINS AI LAB</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Next-Gen Tools for Sports & Finance</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        if os.path.exists(logo_path): st.image(logo_path)
        else: st.info("⚽")
            
        st.markdown("### ⚽ SMFC MANAGER PRO")
        st.markdown("Squad balancer, match logging, and player analytics.")
        st.write("")
        if st.button("LAUNCH APP", key="btn_football", type="primary"):
            st.switch_page(manager_page)

    with col2:
        if os.path.exists(dip_path): st.image(dip_path)
        else: st.info("📉")
            
        st.markdown("### 📉 ETF DIP HUNTER")
        st.markdown("Live market scanner for buying opportunities.")
        st.write("")
        if st.button("LAUNCH APP", key="btn_market", type="primary"):
            st.switch_page(dip_page)

    st.write("---")
    st.markdown('<div style="text-align: center; color: #555;">SYSTEM ONLINE • V 3.0</div>', unsafe_allow_html=True)

# --- 5. NAVIGATION SETUP ---
home_page = st.Page(dashboard, title="Home", icon="🏠", default=True)

my_pages = {
    "Start": [home_page],
    "🏆 Sports Suite": [manager_page],  # Cleaned up!
    "💰 Finance Suite": [dip_page],
}

pg = st.navigation(my_pages)
pg.run()