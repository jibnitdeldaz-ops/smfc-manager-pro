# libraries/backend.py
import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- DATA LOADING ---
def load_data():
    conn = None
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Sheet1", ttl=0, show_spinner=False)
        if df is None or df.empty: raise ValueError("Sheet1 returned empty data")
        if 'Selected' not in df.columns: df['Selected'] = False
        else: df['Selected'] = df['Selected'].fillna(False).astype(bool)
        try: df_matches = conn.read(worksheet="Match_History", ttl=0, show_spinner=False)
        except: df_matches = pd.DataFrame()
        return conn, df, df_matches
    except Exception as e:
        dummy_df = pd.DataFrame(columns=["Name", "Position", "Selected", "PAC", "SHO", "PAS", "DRI", "DEF", "PHY", "StarRating"])
        return conn, dummy_df, pd.DataFrame()

# --- HELPERS ---
def extract_whatsapp_players(text):
    text = re.sub(r'[\u200b\u2060\ufeff\xa0]', ' ', text)
    matches = re.findall(r'(?:^|\n)\s*\d+[\.\)]\s*([^\n\r]+)', text)
    return [m.strip() for m in matches if len(m.strip()) > 1]

def clean_player_name(text):
    text = re.sub(r'\s*\([tT]\)', '', text)
    text = re.sub(r'\s*[\(\[\{（].*?[\)\]\}）]', '', text)
    text = re.sub(r'\s+[-–].*$', '', text)
    text = re.sub(r'\s+[tTgG]$', '', text)
    text = re.sub(r'\s+(?:tentative|late|maybe|confirm|guest|paid)\b.*$', '', text, flags=re.IGNORECASE)
    return text.strip()

def get_guests_list():
    raw = st.session_state.get('guest_input_val', '')
    return [g.strip() for g in raw.split(',') if g.strip()]

def get_counts():
    smfc_count = 0
    if hasattr(st.session_state, 'master_db') and isinstance(st.session_state.master_db, pd.DataFrame):
        if 'Selected' in st.session_state.master_db.columns:
            smfc_count = st.session_state.master_db['Selected'].fillna(False).astype(bool).sum()
    guest_count = len(get_guests_list())
    return smfc_count, guest_count, smfc_count + guest_count

def toggle_selection(idx):
    if 'Selected' in st.session_state.master_db.columns:
        current_val = bool(st.session_state.master_db.at[idx, 'Selected'])
        st.session_state.master_db.at[idx, 'Selected'] = not current_val
        if 'ui_version' not in st.session_state: st.session_state.ui_version = 0
        st.session_state.ui_version += 1

# --- CALCULATIONS ---
def parse_match_log(text):
    data = {
        "Date": datetime.today().strftime('%Y-%m-%d'),
        "Time": "00:00", "Venue": "BFC",
        "Score_Blue": 0, "Score_Red": 0, "Winner": "Draw",
        "Team_Blue": "", "Team_Red": ""
    }
    try:
        date_match = re.search(r'Date:\s*(.*)', text, re.IGNORECASE)
        if date_match: 
            raw_date = date_match.group(1).strip()
            try:
                if ',' in raw_date: clean_date_str = raw_date.split(',', 1)[1].strip()
                else: clean_date_str = raw_date
                dt_obj = datetime.strptime(clean_date_str, "%d %b")
                dt_obj = dt_obj.replace(year=datetime.now().year)
                data['Date'] = dt_obj.strftime("%Y-%m-%d")
            except: data['Date'] = raw_date
        
        time_match = re.search(r'Time:\s*(.*)', text, re.IGNORECASE)
        if time_match: data['Time'] = time_match.group(1).strip()
        venue_match = re.search(r'(?:Ground|Venue):\s*(.*)', text, re.IGNORECASE)
        if venue_match: data['Venue'] = venue_match.group(1).strip()
        
        score_match = re.search(r'Score:.*?Blue\s*(\d+)\s*[-v]\s*(\d+)\s*Red', text, re.IGNORECASE)
        if score_match:
            data['Score_Blue'] = int(score_match.group(1))
            data['Score_Red'] = int(score_match.group(2))
            if data['Score_Blue'] > data['Score_Red']: data['Winner'] = "Blue"
            elif data['Score_Red'] > data['Score_Blue']: data['Winner'] = "Red"
            else: data['Winner'] = "Draw"

        clean_text = text.replace('*', '')
        blue_start = re.search(r'🔵.*?BLUE TEAM', clean_text, re.IGNORECASE)
        red_start = re.search(r'🔴.*?RED TEAM', clean_text, re.IGNORECASE)
        if blue_start and red_start:
            if blue_start.start() < red_start.start():
                blue_block = clean_text[blue_start.end():red_start.start()]
                red_block = clean_text[red_start.end():]
            else:
                red_block = clean_text[red_start.end():blue_start.start()]
                blue_block = clean_text[blue_start.end():]
            def get_names(block):
                names = []
                for line in block.split('\n'):
                    line = line.strip()
                    if len(line) > 2 and not line.lower().startswith("we had") and not any(char.isdigit() for char in line):
                        names.append(clean_player_name(line))
                return ", ".join(names)
            data['Team_Blue'] = get_names(blue_block)
            data['Team_Red'] = get_names(red_block)
    except Exception as e: print(f"Parsing Error: {e}")
    return data

def calculate_leaderboard(df_matches, official_names):
    if df_matches.empty: return pd.DataFrame()
    stats = {}
    for index, row in df_matches.iterrows():
        winner = row['Winner']
        blue_team = [x.strip() for x in str(row['Team_Blue']).split(',') if x.strip()]
        red_team = [x.strip() for x in str(row['Team_Red']).split(',') if x.strip()]
        
        def update(player_name, team_color):
            if player_name not in official_names: return
            if player_name not in stats: stats[player_name] = {'M': 0, 'W': 0, 'L': 0, 'D': 0, 'Form': []}
            p = stats[player_name]
            p['M'] += 1
            if winner == team_color: p['W'] += 1; res='W'
            elif winner == 'Draw': p['D'] += 1; res='D'
            else: p['L'] += 1; res='L'
            p['Form'].append(res)
            
        for p in blue_team: update(p, 'Blue')
        for p in red_team: update(p, 'Red')
        
    if not stats: return pd.DataFrame()
    res = pd.DataFrame.from_dict(stats, orient='index')
    res['Win %'] = ((res['W'] / res['M']) * 100).fillna(0).round(0).astype(int)
    res = res[res['M'] >= 2]
    res = res.sort_values(by=['Win %', 'W'], ascending=[False, False])
    res['Rank'] = range(1, len(res) + 1)
    
    icon_map = {'W': '✅', 'L': '❌', 'D': '➖'}
    res['Form_Icons'] = res['Form'].apply(lambda x: " ".join([icon_map.get(i, i) for i in x[-5:]]))
    return res

def calculate_player_score(row):
    stats = {
        'PAC': row.get('PAC', 70), 'SHO': row.get('SHO', 70),
        'PAS': row.get('PAS', 70), 'DRI': row.get('DRI', 70),
        'DEF': row.get('DEF', 70), 'PHY': row.get('PHY', 70)
    }
    for k, v in stats.items():
        try: stats[k] = float(v)
        except: stats[k] = 70.0

    pos = row.get('Position', 'MID')
    if pos == 'FWD': weighted_avg = (stats['SHO']*0.25 + stats['DRI']*0.2 + stats['PAC']*0.2 + stats['PAS']*0.15 + stats['PHY']*0.1 + stats['DEF']*0.1)
    elif pos == 'DEF': weighted_avg = (stats['DEF']*0.35 + stats['PHY']*0.25 + stats['PAC']*0.15 + stats['PAS']*0.15 + stats['DRI']*0.05 + stats['SHO']*0.05)
    else: weighted_avg = (stats['PAS']*0.25 + stats['DRI']*0.2 + stats['DEF']*0.15 + stats['SHO']*0.15 + stats['PAC']*0.15 + stats['PHY']*0.1)
    try: star_r = float(row.get('StarRating', 3))
    except: star_r = 3.0
    star_score = 45 + (star_r * 10)
    return round((weighted_avg * 0.6) + (star_score * 0.4), 1)

# --- 📌 PRESETS ---
formation_presets = {
    "9 vs 9": {"limit": 9, "RED_COORDS": [(10, 20), (10, 50), (10, 80), (30, 15), (30, 38), (30, 62), (30, 85), (45, 35), (45, 65)], "BLUE_COORDS": [(90, 20), (90, 50), (90, 80), (70, 15), (70, 38), (70, 62), (70, 85), (55, 35), (55, 65)]},
    "7 vs 7": {"limit": 7, "RED_COORDS": [(10, 30), (10, 70), (30, 20), (30, 50), (30, 80), (45, 35), (45, 65)], "BLUE_COORDS": [(90, 30), (90, 70), (70, 20), (70, 50), (70, 80), (55, 35), (55, 65)]},
    "6 vs 6": {"limit": 6, "RED_COORDS": [(10, 30), (10, 70), (30, 30), (30, 70), (45, 35), (45, 65)], "BLUE_COORDS": [(90, 30), (90, 70), (70, 30), (70, 70), (55, 35), (55, 65)]},
    "5 vs 5": {"limit": 5, "RED_COORDS": [(10, 30), (10, 70), (30, 50), (45, 30), (45, 70)], "BLUE_COORDS": [(90, 30), (90, 70), (70, 50), (55, 30), (55, 70)]}
}