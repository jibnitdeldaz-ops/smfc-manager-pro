import streamlit as st
from libraries.football_lib import run_football_app

# The config must stay here for the legacy link to work correctly
st.set_page_config(page_title="SMFC Manager Pro", layout="wide", page_icon="⚽")

if __name__ == "__main__":
    run_football_app()