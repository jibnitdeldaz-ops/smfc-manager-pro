import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- ⚙️ PAGE CONFIG ---
st.set_page_config(page_title="My Portfolio Tracker", layout="wide", page_icon="📈")

# --- 📋 ASSET LIST (The "Master List") ---
# Dictionary structure: "Label Name": "Yahoo Ticker"
ASSETS = {
    "🟡 COMMODITIES": {
        "Gold Bees": "GOLDBEES.NS",
        "Silver Bees": "SILVERBEES.NS"
    },
    "🇺🇸 US ETFs (INR)": {
        "Motilal Nasdaq 100": "MON100.NS",
        "Mirae S&P 500 Top 50": "MASPTOP50.NS",
        "Mirae Fang+": "MAFANG.NS",
        "Motilal Nasdaq Q50": "MONQ50.NS"
    },
    "🇨🇳 CHINESE ETFs": {
        "Hang Seng Bees": "HNGBEES.NS",
        "Mirae Hang Seng Tech": "MAHKTECH.NS"
    },
    "🇮🇳 INDIAN ETFs": {
        "CPSE ETF": "CPSEETF.NS",
        "Groww Power": "GROWWPOWER.NS",
        "Groww Rail": "GROWWRAIL.NS",
        "Alpha Low Vol 30": "ALPL30IETF.NS",
        "Metal Bees": "METALBEES.NS",
        "Smallcap 250 (HDFC)": "HDFCSML250.NS", # Proxy for generic Smallcap
        "Momentum 30": "MOMOMENTUM.NS",
        "Defense ETF": "MODEFENCE.NS",
        "Realty ETF": "MOREALTY.NS",
        "Auto Bees": "AUTOBEES.NS",
        "Pharma Bees": "PHARMABEES.NS",
        "Bank Bees": "BANKBEES.NS",
        "Junior Bees": "JUNIORBEES.NS",
        "IT Bees": "ITBEES.NS",
        "PSU Bank Bees": "PSUBNKBEES.NS"
    },
    "💵 US STOCKS (USD)": {
        "Google (Alphabet)": "GOOGL",
        "MaxLinear Tech": "MXL"
    }
}

# --- 🛡️ DATA ENGINE (Cached) ---
@st.cache_data(ttl=300) # Cache for 5 minutes
def get_live_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # Get 5 days of history to calculate changes
        df = stock.history(period="5d", interval="1d")
        if df.empty:
            return None
        return df
    except Exception:
        return None

# --- 🎨 UI LAYOUT ---
st.title("📈 Strategic Portfolio Tracker")
st.markdown(f"**Live Tracking for:** India (NSE) • US (Nasdaq) • China (Hang Seng)")
st.divider()

# --- 🔄 MAIN LOOP ---
# We loop through each category in your dictionary
for category, tokens in ASSETS.items():
    st.subheader(f"{category}")
    
    # Create columns dynamically (3 cards per row)
    cols = st.columns(4)
    col_index = 0

    for name, ticker in tokens.items():
        # Fetch Data
        df = get_live_data(ticker)
        
        # Determine current column
        with cols[col_index % 4]:
            if df is not None:
                # Calculate Metrics
                current_price = df['Close'].iloc[-1]
                prev_close = df['Close'].iloc[-2]
                change = current_price - prev_close
                pct_change = (change / prev_close) * 100
                
                # Currency Symbol Logic
                currency = "$" if "USD" in category else "₹"
                
                # Color Logic
                color = "normal" 
                if pct_change > 0: color = "normal" # Streamlit handles green auto via delta
                
                # Display Card
                st.metric(
                    label=name,
                    value=f"{currency}{current_price:,.2f}",
                    delta=f"{change:,.2f} ({pct_change:.2f}%)"
                )
                
                # Mini Chart (Line)
                st.line_chart(df['Close'], height=50)
                
            else:
                st.warning(f"{name}: No Data")
        
        col_index += 1
    
    st.divider()

# --- ℹ️ FOOTER ---
if st.button("🔄 Refresh Prices"):
    st.cache_data.clear()
    st.rerun()

st.caption("Data Source: Yahoo Finance | Updates every 5 mins")