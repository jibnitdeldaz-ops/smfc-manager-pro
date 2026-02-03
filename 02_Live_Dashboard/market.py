import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from libraries.market_lib import run_dip_hunter

st.set_page_config(page_title="Dip Hunter", layout="wide", page_icon="📉")

if __name__ == "__main__":
    run_dip_hunter()
