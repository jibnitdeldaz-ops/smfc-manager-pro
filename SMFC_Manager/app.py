import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from libraries.football_lib import run_football_app

st.set_page_config(page_title="SMFC Manager Pro", layout="wide", page_icon="⚽")

if __name__ == "__main__":
    run_football_app()
