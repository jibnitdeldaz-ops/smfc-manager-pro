import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="Portfolio Lab", layout="wide", page_icon="🌤️")

# --- 🎨 FINAL CSS ---
st.markdown("""
<style>
    /* 1. BACKGROUND */
    .stApp {
        background: linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%);
        color: #102a43;
    }
    
    /* 2. REMOVE PADDING/MARGINS */
    div[data-testid="stVerticalBlock"] > div > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    
    /* 3. TYPOGRAPHY */
    div.asset-title {
        font-family: 'Helvetica Neue', sans-serif;
        color: #486581;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    
    div.hero-price {
        font-family: 'Inter', sans-serif;
        color: #102a43;
        font-size: 46px; 
        font-weight: 800;
        line-height: 1;
        letter-spacing: -1.5px;
    }

    div.return-text {
        font-size: 14px;
        color: #627d98;
        margin-top: 6px;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
    }
    
    div.category-header {
        color: #829ab1;
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 1.5px;
        margin-top: 30px;
        margin-bottom: 15px;
        text-transform: uppercase;
        border-bottom: 1px solid rgba(0,0,0,0.05);
        padding-bottom: 5px;
    }

    /* 4. BUTTONS */
    div.stButton > button {
        border-radius: 50px;
        font-size: 12px;
        font-weight: 600;
        height: 2.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .js-plotly-plot .plotly .main-svg { background: transparent !important; }
    div.block-container { padding-top: 2rem; }
    hr { margin-top: 15px; margin-bottom: 25px; border-color: #d9e2ec; }
</style>
""", unsafe_allow_html=True)

# --- 📋 ASSET LIST ---
ASSETS = {
    "🟡 COMMODITIES": { "Gold Bees": "GOLDBEES.NS", "Silver Bees": "SILVERBEES.NS" },
    "🇺🇸 US ETFs (INR)": { "Motilal Nasdaq 100": "MON100.NS", "Mirae S&P 500": "MASPTOP50.NS", "Mirae Fang+": "MAFANG.NS", "Motilal Nasdaq Q50": "MONQ50.NS" },
    "🇨🇳 CHINESE ETFs": { "Hang Seng Bees": "HNGSNGBEES.NS", "Mirae Hang Seng Tech": "MAHKTECH.NS" },
    "🇮🇳 INDIAN ETFs": { "CPSE ETF": "CPSEETF.NS", "Groww Power": "GROWWPOWER.NS", "Groww Rail": "GROWWRAIL.NS", "Alpha Low Vol 30": "ALPL30IETF.NS", "Smallcap 250": "HDFCSML250.NS", "Momentum 30": "MOMOMENTUM.NS", "Defense ETF": "MODEFENCE.NS", "Realty ETF": "MOREALTY.NS", "Auto Bees": "AUTOBEES.NS", "Pharma Bees": "PHARMABEES.NS", "Bank Bees": "BANKBEES.NS", "Junior Bees": "JUNIORBEES.NS", "IT Bees": "ITBEES.NS", "PSU Bank Bees": "PSUBNKBEES.NS" },
    "💵 US STOCKS (USD)": { "Google": "GOOGL", "MaxLinear": "MXL" }
}

# --- 🔄 STATE ---
if 'selected_window' not in st.session_state: st.session_state.selected_window = '1W'
def set_window(val): st.session_state.selected_window = val
WINDOW_MAP = {'1D': 2, '2D': 3, '3D': 4, '4D': 5, '1W': 6, '2W': 11, '3W': 16, '4W': 23}

# --- 🛡️ DATA ENGINE ---
@st.cache_data(ttl=600)
def get_history(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo", interval="1d", timeout=3)
        return None if df.empty else df
    except:
        return None

# --- 🧪 INTEGRATED TUBE (SMART LABELS) ---
def create_integrated_tube(curr, high, low, drawdown, trend_color):
    fig = go.Figure()

    # 1. Background Track
    fig.add_trace(go.Scatter(
        x=[0, 0], y=[low, high],
        mode='lines',
        line=dict(color='#dceefb', width=18),
        hoverinfo='skip'
    ))

    # 2. Liquid Fill
    fig.add_trace(go.Scatter(
        x=[0, 0], y=[low, curr],
        mode='lines',
        line=dict(color=trend_color, width=18),
        hoverinfo='skip'
    ))

    # 3. White Cap
    fig.add_trace(go.Scatter(
        x=[0], y=[curr],
        mode='markers',
        marker=dict(color='white', size=16, line=dict(color=trend_color, width=4)),
        hoverinfo='skip'
    ))

    # 4. STATIC LABELS (LEFT SIDE - INCREASED FONT SIZE)
    # Increased size from 10 to 12. pushed x to -0.2 for more space
    fig.add_annotation(x=-0.2, y=high, text=f"H {high:,.0f}", showarrow=False, xanchor="right", font=dict(color="#486581", size=12, weight="bold"))
    fig.add_annotation(x=-0.2, y=low, text=f"L {low:,.0f}", showarrow=False, xanchor="right", font=dict(color="#486581", size=12, weight="bold"))
    
    # 5. DYNAMIC PERCENTAGE (RIGHT SIDE - SMART LOGIC)
    # If Drawdown is negligible (e.g. -0.05%), show "MAX" instead of "0.0%"
    if abs(drawdown) < 0.1:
        label_text = "<b>🔥 MAX</b>"
        sub_text = "" # No subtext needed for Max
    else:
        label_text = f"<b>{drawdown:.1f}%</b>"
        sub_text = "<br><span style='font-size:9px; color:#627d98'>from High</span>"

    # Pushed x to 0.2 to avoid overlap with tube
    fig.add_annotation(
        x=0.2, y=curr, 
        text=f"{label_text}{sub_text}", 
        showarrow=False, xanchor="left", yanchor="middle",
        font=dict(color=trend_color, size=16, family="Inter")
    )
    
    # 6. Range (Bottom)
    range_pts = high - low
    fig.add_annotation(
        x=0, y=low - (range_pts * 0.15),
        text=f"Range: {range_pts:,.0f}",
        showarrow=False, font=dict(color="#bcccdc", size=10)
    )

    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.8, 1.0]), # WIDENED X-AXIS to fit larger labels
        yaxis=dict(visible=False, range=[low - (range_pts*0.2), high + (range_pts*0.1)]),
        margin=dict(l=0, r=0, t=0, b=0),
        height=140,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    return fig

# --- 🖥️ HEADER ---
c_title, c_time = st.columns([2, 1])
with c_title:
    st.markdown("<h1 style='color:#102a43; font-weight:800; font-size: 28px; margin:0;'>🌤️ Market Lab</h1>", unsafe_allow_html=True)
with c_time:
    st.markdown(f"<div style='text-align: right; color: #627d98; font-weight:600; padding-top:10px;'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

# --- 🔘 BUTTON ROW ---
st.write("")
st.markdown("<div style='font-size:12px; font-weight:700; color:#486581; margin-bottom:5px;'>SELECT TIMEFRAME</div>", unsafe_allow_html=True)

cols = st.columns(8)
options = ['1D', '2D', '3D', '4D', '1W', '2W', '3W', '4W']
current_window = st.session_state.selected_window

for i, opt in enumerate(options):
    btn_type = "primary" if current_window == opt else "secondary"
    if cols[i].button(opt, key=f"btn_{opt}", type=btn_type, use_container_width=True):
        set_window(opt)
        st.rerun()

days_back = WINDOW_MAP.get(current_window, 6)
st.markdown("<hr>", unsafe_allow_html=True)

# --- 🔄 MAIN GRID ---
outer_cols = st.columns(3)
col_counter = 0

for category, tokens in ASSETS.items():
    st.markdown(f"<div class='category-header'>{category}</div>", unsafe_allow_html=True)
    
    outer_cols = st.columns(3)
    col_counter = 0

    for name, ticker in tokens.items():
        curr_col = outer_cols[col_counter % 3]
        
        with curr_col:
            df = get_history(ticker)
            
            if df is not None and len(df) >= 2:
                df_slice = df.tail(days_back)
                curr = df_slice['Close'].iloc[-1]
                high = df_slice['Close'].max()
                low = df_slice['Close'].min()
                
                # METRIC 1: Time Return
                start_price = df_slice['Close'].iloc[0]
                pct_return = ((curr - start_price) / start_price) * 100
                
                # METRIC 2: Drawdown
                drawdown = ((curr - high) / high) * 100
                
                currency = "$" if "USD" in category else "₹"
                trend_color = "#10b981" if pct_return >= 0 else "#ef4444"
                
                c_info, c_vis = st.columns([0.8, 1])
                
                with c_info:
                    st.markdown(f"<div class='asset-title'>{name}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='hero-price'>{currency}{curr:,.0f}</div>", unsafe_allow_html=True)
                    
                    arrow = "▲" if pct_return >= 0 else "▼"
                    st.markdown(f"""
                        <div class='return-text' style='color:{trend_color}'>
                            {arrow} {pct_return:+.2f}% <span style='color:#829ab1; font-size:12px; font-weight:500'>since {current_window}</span>
                        </div>
                    """, unsafe_allow_html=True)

                with c_vis:
                    st.plotly_chart(
                        create_integrated_tube(curr, high, low, drawdown, trend_color),
                        use_container_width=True,
                        config={'staticPlot': True}
                    )
            else:
                st.markdown(f"**{name}**")
                st.warning("Loading...")
                
        col_counter += 1
        if col_counter % 3 == 0: st.write("")

    st.markdown("<hr>", unsafe_allow_html=True)

if st.button("Refresh System"):
    st.cache_data.clear()
    st.rerun()