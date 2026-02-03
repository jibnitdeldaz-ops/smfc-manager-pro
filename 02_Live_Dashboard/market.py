import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Market Tracker", layout="wide", page_icon="📈")

# --- 🛰️ SIDEBAR SETTINGS ---
st.sidebar.header("⚙️ Dashboard Settings")
st.sidebar.write("Select assets to track:")

# 1. Crypto Selection
crypto_choice = st.sidebar.selectbox("Choose Crypto", ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"])

# 2. Stock Selection (New Feature!)
stock_choice = st.sidebar.selectbox("Choose Stock", ["AAPL", "TSLA", "GOOGL", "MSFT", "NVDA"])

# --- 📊 DATA ENGINE ---
def get_data(symbol):
    ticker = yf.Ticker(symbol)
    # Get 5 days of data for better trends
    df = ticker.history(period="5d", interval="15m")
    return df

# --- 🖥️ MAIN DASHBOARD ---
st.title(f"🚀 {crypto_choice} vs {stock_choice}")

# Get Data
crypto_data = get_data(crypto_choice)
stock_data = get_data(stock_choice)

# Row 1: The Big Numbers
col1, col2 = st.columns(2)

with col1:
    curr_c = crypto_data['Close'].iloc[-1]
    delta_c = curr_c - crypto_data['Close'].iloc[0]
    st.metric(label=f"💰 {crypto_choice}", value=f"${curr_c:,.2f}", delta=f"{delta_c:,.2f}")

with col2:
    curr_s = stock_data['Close'].iloc[-1]
    delta_s = curr_s - stock_data['Close'].iloc[0]
    st.metric(label=f"🏢 {stock_choice}", value=f"${curr_s:,.2f}", delta=f"{delta_s:,.2f}")

# Row 2: Charts
st.subheader("Market Trends (Last 5 Days)")

tab1, tab2 = st.tabs(["📈 Crypto Chart", "📉 Stock Chart"])

with tab1:
    st.line_chart(crypto_data['Close'], color="#00FF00")

with tab2:
    st.line_chart(stock_data['Close'], color="#FF4B4B")

st.sidebar.success("Data Live from Yahoo Finance")
