import streamlit as st
from libraries.market_lib import run_dip_hunter

# The config stays here for the legacy link
st.set_page_config(page_title="Dip Hunter", layout="wide", page_icon="📉")

if __name__ == "__main__":
    run_dip_hunter()