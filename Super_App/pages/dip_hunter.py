import streamlit as st
import sys
import os

# FIX: Add the root directory to the path so we can find 'libraries'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from libraries.market_lib import run_dip_hunter

run_dip_hunter()
