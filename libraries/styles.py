# libraries/styles.py
import streamlit as st

def apply_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@700;900&family=Courier+Prime:wght@700&display=swap');
        .stApp { background-color: #0e1117; font-family: 'Rajdhani', sans-serif; background-image: radial-gradient(circle at 50% 0%, #1c2026 0%, #0e1117 70%); color: #e0e0e0; }
        
        .neon-white { color: #ffffff; text-shadow: 0 0 5px #ffffff, 0 0 10px #ffffff; font-weight: 800; text-transform: uppercase; }
        .neon-red { color: #ff4b4b; text-shadow: 0 0 5px #ff4b4b, 0 0 10px #ff4b4b; font-weight: 800; text-transform: uppercase; }
        .neon-blue { color: #1c83e1; text-shadow: 0 0 5px #1c83e1, 0 0 10px #1c83e1; font-weight: 800; text-transform: uppercase; }
        
        .neon-gold { color: #FFEB3B !important; font-weight: 900 !important; font-size: 14px !important; text-shadow: 1px 1px 0 #000; letter-spacing: 0.5px; }
        .dull-grey { color: #888; font-weight: 600; font-size: 12px; opacity: 0.8; }
        .draw-text { color: #ccc; font-weight: 700; font-size: 13px; }

        input, div[data-baseweb="input"] { background-color: #ffffff !important; color: #000 !important; border-radius: 5px; }
        div[data-baseweb="base-input"] input { color: #000000 !important; font-weight: bold; }
        div[data-baseweb="select"] div { background-color: #ffffff !important; color: #000000 !important; }
        
        /* CHAT STYLES */
        .chat-container { display: flex; flex-direction: column; gap: 15px; margin-bottom: 20px; padding: 10px; }
        
        /* Added margin-bottom to create space between bubbles */
        .chat-row { display: flex; align-items: flex-start; gap: 10px; width: 100%; margin-bottom: 15px; }
        
        /* HOST (LEFT) */
        .chat-row.char-kaarthumbi { justify-content: flex-start; }
        .char-kaarthumbi .chat-avatar { background: #43a047; order: 1; margin-right: 10px; }
        .char-kaarthumbi .chat-bubble { background: linear-gradient(135deg, #2E7D32, #1B5E20); order: 2; border-top-left-radius: 0; }

        /* GUESTS (RIGHT) */
        .chat-row.guest-style { justify-content: flex-end; }
        .chat-row.guest-style .chat-avatar { order: 2; margin-left: 10px; }
        .chat-row.guest-style .chat-bubble { order: 1; border-top-right-radius: 0; text-align: right; }
        .chat-row.guest-style .chat-name { text-align: right; }

        .chat-avatar { width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; border: 2px solid rgba(255,255,255,0.2); flex-shrink: 0; }
        .chat-bubble { padding: 12px 16px; border-radius: 12px; font-family: 'Rajdhani', sans-serif; font-size: 16px; line-height: 1.4; max-width: 80%; box-shadow: 0 2px 5px rgba(0,0,0,0.2); color: #fff; }
        .chat-name { font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 2px; opacity: 0.8; letter-spacing: 1px; }

        /* GUEST COLORS */
        .char-bellary .chat-avatar { background: #FFC107; color: black; }
        .char-bellary .chat-bubble { background: linear-gradient(135deg, #FFB300, #FF8F00); color: black; font-weight: 600; }
        .char-induchoodan .chat-avatar { background: #D50000; }
        .char-induchoodan .chat-bubble { background: linear-gradient(135deg, #B71C1C, #D50000); }
        .char-appukuttan .chat-avatar { background: #FF5722; }
        .char-appukuttan .chat-bubble { background: linear-gradient(135deg, #D84315, #BF360C); }
        .char-ponjikkara .chat-avatar { background: #607D8B; }
        .char-ponjikkara .chat-bubble { background: linear-gradient(135deg, #546E7A, #455A64); font-style: italic; }
        
        /* ANALYTICS CARD STYLES */
        .lb-card { background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%); border: 1px solid rgba(255,255,255,0.1); border-left: 4px solid #FF5722; border-radius: 10px; padding: 15px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; }
        .lb-rank { font-size: 24px; font-weight: 900; color: #FF5722; width: 40px; }
        .lb-info { flex-grow: 1; padding-left: 10px; }
        .lb-name { font-size: 18px; font-weight: 800; color: #fff; text-transform: uppercase; }
        .lb-stats { font-size: 12px; color: #bbb; margin-top: 2px; }
        .lb-form { font-size: 14px; margin-right: 15px; letter-spacing: 2px; }
        .lb-winrate { font-size: 22px; font-weight: 900; color: #00E676; text-shadow: 0 0 10px rgba(0, 230, 118, 0.4); }
        
        .spotlight-box { background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%); border-radius: 10px; padding: 15px; text-align: center; height: 100%; border: 1px solid rgba(255,255,255,0.1); }
        .sp-value { font-size: 32px; font-weight: 900; color: #ffffff; margin: 5px 0; text-shadow: 0 0 15px rgba(255,255,255,0.9); }
        .sp-title { font-size: 14px; font-weight: 900; color: #ffffff; text-transform: uppercase; margin-bottom: 10px; }
        .sp-name { color: #ffffff; font-size: 18px; font-weight: 900; text-transform: uppercase; }
        
        /* MOBILE OPTIMIZATION */
        @media (max-width: 600px) {
            .stApp { background-image: none; background-color: #0e1117; } /* Solid dark bg for mobile performance */
            .lb-card { flex-direction: column; align-items: flex-start; }
            .lb-rank { margin-bottom: 5px; }
            .lb-info { padding-left: 0; margin-bottom: 10px; }
            .lb-winrate { align-self: flex-end; }
            .spotlight-box { margin-bottom: 10px; height: auto; }
            .chat-bubble { max-width: 90%; font-size: 14px; }
            .chat-avatar { width: 35px; height: 35px; font-size: 18px; }
        }
        
        .ai-box { background: rgba(0, 100, 0, 0.1); border: 1px solid rgba(0, 255, 100, 0.2); border-radius: 10px; padding: 15px; margin-bottom: 25px; }
        .ai-title { color: #76FF03; font-weight: 900; font-family: 'Orbitron'; letter-spacing: 1.5px; font-size: 18px; text-shadow: 0 0 10px rgba(118, 255, 3, 0.5); }
        div.stButton > button { background: linear-gradient(90deg, #D84315 0%, #FF5722 100%) !important; color: white !important; font-weight: 900 !important; border: none !important; height: 55px; font-size: 20px !important; width: 100%; }
    </style>
    """, unsafe_allow_html=True)