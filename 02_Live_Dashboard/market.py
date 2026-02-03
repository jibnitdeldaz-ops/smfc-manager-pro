import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import time

st.set_page_config(page_title="Market Tracker", layout="wide", page_icon="📈")

# --- 🛰️ SIDEBAR SETTINGS ---
st.sidebar.header("⚙️ Dashboard Settings")
st.sidebar.write("Select assets to track:")
crypto_choice = st.sidebar.selectbox("Choose Crypto", ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"])
stock_choice = st.sidebar.selectbox("Choose Stock", ["AAPL", "TSLA", "GOOGL", "MSFT", "NVDA"])

# --- 🛡️ SMART DATA ENGINE (Now with Caching!) ---
# This decorator tells Streamlit: "Keep this data for 300 seconds (5 mins)"
# It prevents us from getting banned by Yahoo for spamming requests.
@st.cache_data(ttl=300) 
def get_data(symbol):
    ticker = yf.Ticker(symbol)
    # 5d period gives us enough context, 15m interval is granular enough
    df = ticker.history(period="5d", interval="15m")
    return df

# --- 🖥️ MAIN DASHBOARD ---
st.title(f"🚀 {crypto_choice} vs {stock_choice}")

# Try/Except block to handle the error gracefully if it still happens
try:
    with st.spinner('Fetching live market data...'):
        crypto_data = get_data(crypto_choice)
        stock_data = get_data(stock_choice)

    # Row 1: The Big Numbers
    col1, col2 = st.columns(2)

    with col1:
        if not crypto_data.empty:
            curr_c = crypto_data['Close'].iloc[-1]
            delta_c = curr_c - crypto_data['Close'].iloc[0]
            st.metric(label=f"💰 {crypto_choice}", value=f"${curr_c:,.2f}", delta=f"{delta_c:,.2f}")
        else:
            st.error("No Data")

    with col2:
        if not stock_data.empty:
            curr_s = stock_data['Close'].iloc[-1]
            delta_s = curr_s - stock_data['Close'].iloc[0]
            st.metric(label=f"🏢 {stock_choice}", value=f"${curr_s:,.2f}", delta=f"{delta_s:,.2f}")
        else:
            st.error("No Data")

    # Row 2: Charts
    st.subheader("Market Trends (Last 5 Days)")
    tab1, tab2 = st.tabs(["📈 Crypto Chart", "📉 Stock Chart"])

    with tab1:
        if not crypto_data.empty:
            st.line_chart(crypto_data['Close'], color="#00FF00")

    with tab2:
        if not stock_data.empty:
            st.line_chart(stock_data['Close'], color="#FF4B4B")

    st.caption("Data provided by Yahoo Finance. Updates every 5 minutes to prevent rate limits.")

except Exception as e:
    st.error(f"⚠️ Yahoo Finance is currently limiting traffic. Please wait 1 minute and refresh. (Error: {e})")

st.sidebar.success("System Operational")