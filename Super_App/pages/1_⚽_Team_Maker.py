import streamlit as st
from libraries.football_lib import run_football_app

# No set_page_config here because Home.py handles the main settings
run_football_app()
