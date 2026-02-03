import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 📋 ASSETS CONFIGURATION ---
ASSETS = {
    "🟡 COMMODITIES ETF ": { "Gold Bees": "GOLDBEES.NS", "Silver Bees": "SILVERBEES.NS" },
    "🇺🇸 US ETFs (INR)": { "Motilal Nasdaq 100": "MON100.NS", "Mirae S&P 500": "MASPTOP50.NS", "Mirae Fang+": "MAFANG.NS", "Motilal Nasdaq Q50": "MONQ50.NS" },
    "🇨🇳 CHINESE ETFs": { "Hang Seng Bees": "HNGSNGBEES.NS", "Mirae Hang Seng Tech": "MAHKTECH.NS" },
    "🇮🇳 INDIAN ETFs": { "CPSE ETF": "CPSEETF.NS", "Groww Power": "GROWWPOWER.NS", "Groww Rail": "GROWWRAIL.NS", "Alpha Low Vol 30": "ALPL30IETF.NS", "Smallcap 250": "HDFCSML250.NS", "Momentum 30": "MOMOMENTUM.NS", "Defense ETF": "MODEFENCE.NS", "Realty ETF": "MOREALTY.NS", "Auto Bees": "AUTOBEES.NS", "Pharma Bees": "PHARMABEES.NS", "Bank Bees": "BANKBEES.NS", "Junior Bees": "JUNIORBEES.NS", "IT Bees": "ITBEES.NS", "PSU Bank Bees": "PSUBNKBEES.NS" },
}

WINDOW_MAP = {'1D': 2, '2D': 3, '3D': 4, '4D': 5, '1W': 6, '2W': 11, '3W': 16, '4W': 23}

# --- 🛡️ DATA ENGINE (Helper Functions) ---

@st.cache_data(ttl=600)
def get_history(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo", interval="1d", timeout=3)
        return None if df.empty else df
    except:
        return None

def create_drop_chart(curr, high, low, drawdown):
    fig = go.Figure()
    
    drop_magnitude = abs(drawdown)
    
    if drop_magnitude < 3:
        bar_color = "#cbd5e1" # Light Grey
        text_color = "#94a3b8"
    elif drop_magnitude < 10:
        bar_color = "#f59e0b" # Amber/Orange
        text_color = "#d97706"
    else:
        bar_color = "#ef4444" # Red
        text_color = "#dc2626"

    # 1. Full Range Backbone
    fig.add_trace(go.Scatter(
        x=[0, 0], y=[low, high],
        mode='lines',
        line=dict(color='#e2e8f0', width=6),
        hoverinfo='skip'
    ))

    # 2. THE DROP BAR (High DOWN to Current)
    fig.add_trace(go.Scatter(
        x=[0, 0], y=[high, curr],
        mode='lines',
        line=dict(color=bar_color, width=12),
        hoverinfo='skip'
    ))

    # 3. Current Price Marker
    fig.add_trace(go.Scatter(
        x=[0], y=[curr],
        mode='markers',
        marker=dict(color='white', size=14, line=dict(color=bar_color, width=3)),
        hoverinfo='skip'
    ))
    
    # 4. Top Anchor
    fig.add_trace(go.Scatter(
        x=[0], y=[high],
        mode='markers',
        marker=dict(color=bar_color, size=6),
        hoverinfo='skip'
    ))

    # 5. LABELS
    fig.add_annotation(x=-0.2, y=high, text=f"H {high:,.0f}", showarrow=False, xanchor="right", font=dict(color="#64748b", size=11, weight="bold"))
    fig.add_annotation(x=-0.2, y=low, text=f"L {low:,.0f}", showarrow=False, xanchor="right", font=dict(color="#64748b", size=11, weight="bold"))
    
    # 6. THE PERCENTAGE
    mid_point = (high + curr) / 2
    
    if drop_magnitude > 0.1:
        fig.add_annotation(
            x=0.2, y=mid_point, 
            text=f"<b>{drawdown:.1f}%</b>", 
            showarrow=False, xanchor="left",
            font=dict(color=text_color, size=15, family="Inter")
        )

    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.8, 1.0]),
        yaxis=dict(visible=False, range=[low - (high-low)*0.1, high + (high-low)*0.1]),
        margin=dict(l=0, r=0, t=0, b=0),
        height=140,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    return fig

# --- 🚀 MAIN APPLICATION LOGIC ---

def run_dip_hunter():
    # --- 🎨 FINAL CSS POLISH ---
    st.markdown("""
    <style>
        /* 1. BACKGROUND */
        .stApp {
            background: linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%);
            color: #102a43;
        }
        
        /* 2. REMOVE DEFAULT PADDING */
        div[data-testid="stVerticalBlock"] > div > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }
        
        /* 3. TYPOGRAPHY & HEADERS */
        div.section-title {
            color: #102a43;
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 800;
            font-size: 26px; /* BIGGER */
            letter-spacing: 0.5px;
            margin-top: 50px; /* More space above */
            margin-bottom: 10px;
            text-transform: uppercase;
            display: flex;
            align-items: center;
        }
        
        /* subtle separator line */
        div.section-line {
            height: 2px;
            background: linear-gradient(to right, #102a43, transparent);
            margin-bottom: 25px;
            opacity: 0.2;
        }

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

        div.trend-text {
            font-size: 14px;
            color: #627d98;
            margin-top: 6px;
            font-weight: 600;
            font-family: 'Inter', sans-serif;
        }

        /* 4. INFO CARD (LEGEND) */
        div.legend-card {
            background: rgba(255, 255, 255, 0.75);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.9);
            border-radius: 16px;
            padding: 20px 30px;
            margin: 20px 0 40px 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            font-family: 'Inter', sans-serif;
        }

        /* 5. TIMEFRAME LABEL */
        div.timeframe-label {
            font-size: 14px; /* INCREASED */
            font-weight: 800;
            color: #334e68;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        /* 6. BUTTONS */
        div.stButton > button {
            border-radius: 50px;
            font-size: 13px; /* Slightly bigger */
            font-weight: 600;
            height: 2.5rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border: 1px solid rgba(255,255,255,0.5);
        }
        
        .js-plotly-plot .plotly .main-svg { background: transparent !important; }
        div.block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    # --- 🔄 STATE ---
    if 'selected_window' not in st.session_state: st.session_state.selected_window = '1W'
    
    def set_window(val): 
        st.session_state.selected_window = val

    # --- 🖥️ HEADER ---
    c_title, c_time = st.columns([2, 1])
    with c_title:
        st.markdown("<h1 style='color:#102a43; font-weight:800; font-size: 42px; margin:0;'>📉 ETF DIP HUNTER</h1>", unsafe_allow_html=True)
    with c_time:
        st.markdown(f"<div style='text-align: right; color: #627d98; font-weight:600; padding-top:10px;'>{datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

    # --- 🔘 BUTTONS ---
    st.write("")
    st.markdown("<div class='timeframe-label'>TIMEFRAME (Lookback Period)</div>", unsafe_allow_html=True)

    cols = st.columns(8)
    options = ['1D', '2D', '3D', '4D', '1W', '2W', '3W', '4W']
    current_window = st.session_state.selected_window

    for i, opt in enumerate(options):
        btn_type = "primary" if current_window == opt else "secondary"
        if cols[i].button(opt, key=f"btn_{opt}", type=btn_type, use_container_width=True):
            set_window(opt)
            st.rerun()

    days_back = WINDOW_MAP.get(current_window, 6)

    # --- 📘 IMPROVED LEGEND CARD ---
    st.markdown("""
    <div class='legend-card'>
        <div style='display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 20px;'>
            <div style='flex: 1; min-width: 250px;'>
                <div style='font-size: 16px; font-weight: 800; color: #102a43; margin-bottom: 5px;'>📊 HOW TO READ THIS CHART</div>
                <div style='font-size: 14px; color: #486581;'>
                    The vertical bar represents the <span style='color:#ef4444; font-weight:bold'>Drawdown</span> (Percentage drop from the recent High).
                </div>
            </div>
            <div style='flex: 2; display: flex; gap: 30px; justify-content: flex-end; flex-wrap: wrap;'>
                <div style='display:flex; align-items:center;'>
                    <div style='width:14px; height:14px; background:#cbd5e1; border-radius:4px; margin-right:8px;'></div>
                    <div style='font-size:14px; line-height:1.2'>
                        <span style='color:#64748b; font-weight:700'>Small Dip (<3%)</span><br>
                        <span style='color:#94a3b8; font-size:12px'>Ignore</span>
                    </div>
                </div>
                <div style='display:flex; align-items:center;'>
                    <div style='width:14px; height:14px; background:#f59e0b; border-radius:4px; margin-right:8px;'></div>
                    <div style='font-size:14px; line-height:1.2'>
                        <span style='color:#d97706; font-weight:700'>Medium Dip (3-10%)</span><br>
                        <span style='color:#94a3b8; font-size:12px'>Watchlist</span>
                    </div>
                </div>
                <div style='display:flex; align-items:center;'>
                    <div style='width:14px; height:14px; background:#ef4444; border-radius:4px; margin-right:8px;'></div>
                    <div style='font-size:14px; line-height:1.2'>
                        <span style='color:#ef4444; font-weight:700'>CRASH (>10%)</span><br>
                        <span style='color:#94a3b8; font-size:12px'>Opportunity</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- 🔄 MAIN GRID ---
    outer_cols = st.columns(3)
    col_counter = 0

    for category, tokens in ASSETS.items():
        # MODERN SECTION HEADER
        st.markdown(f"""
            <div class='section-title'>
                {category}
            </div>
            <div class='section-line'></div>
        """, unsafe_allow_html=True)
        
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
                    
                    c_info, c_vis = st.columns([0.8, 1])
                    
                    with c_info:
                        st.markdown(f"<div class='asset-title'>{name}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='hero-price'>{currency}{curr:,.0f}</div>", unsafe_allow_html=True)
                        
                        # Trend Text
                        trend_color = "#10b981" if pct_return >= 0 else "#ef4444"
                        arrow = "▲" if pct_return >= 0 else "▼"
                        st.markdown(f"""
                            <div class='trend-text' style='color:{trend_color}'>
                                {arrow} {pct_return:+.2f}% <span style='color:#94a3b8; font-weight:400'>since {current_window}</span>
                            </div>
                        """, unsafe_allow_html=True)

                    with c_vis:
                        st.plotly_chart(
                            create_drop_chart(curr, high, low, drawdown),
                            use_container_width=True,
                            config={'staticPlot': True}
                        )
                else:
                    st.markdown(f"**{name}**")
                    st.warning("Loading...")
                    
            col_counter += 1
            if col_counter % 3 == 0: st.write("")

    if st.button("Refresh Prices"):
        st.cache_data.clear()
        st.rerun()