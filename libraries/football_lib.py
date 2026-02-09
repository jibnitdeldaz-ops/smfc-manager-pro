import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import os
import io
import streamlit.components.v1 as components
from mplsoccer import Pitch
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects

# --- IMPORTS ---
try:
    from libraries.styles import apply_custom_css
    from libraries.backend import (
        load_data, get_counts, get_guests_list, extract_whatsapp_players, 
        clean_player_name, toggle_selection, calculate_player_score, 
        calculate_leaderboard, parse_match_log, formation_presets
    )
    from libraries.ai_scout import ask_ai_scout, simulate_match_commentary
except ImportError:
    from styles import apply_custom_css
    from backend import (
        load_data, get_counts, get_guests_list, extract_whatsapp_players, 
        clean_player_name, toggle_selection, calculate_player_score, 
        calculate_leaderboard, parse_match_log, formation_presets
    )
    from ai_scout import ask_ai_scout, simulate_match_commentary

# --- MAIN APP ---
def run_football_app():
    if 'ui_version' not in st.session_state: st.session_state.ui_version = 0
    if 'checklist_version' not in st.session_state: st.session_state.checklist_version = 0
    if 'parsed_match_data' not in st.session_state: st.session_state.parsed_match_data = None
    if 'position_changes' not in st.session_state: st.session_state.position_changes = []
    if 'transfer_log' not in st.session_state: st.session_state.transfer_log = []
    if 'match_squad' not in st.session_state: st.session_state.match_squad = pd.DataFrame()
    if 'guest_input_val' not in st.session_state: st.session_state.guest_input_val = ""
    if 'ai_chat_response' not in st.session_state: st.session_state.ai_chat_response = ""
    if 'match_simulation' not in st.session_state: st.session_state.match_simulation = ""

    apply_custom_css()

    if 'master_db' not in st.session_state or (isinstance(st.session_state.master_db, pd.DataFrame) and st.session_state.master_db.empty):
        conn, df_p, df_m = load_data()
        st.session_state.conn = conn; st.session_state.master_db = df_p; st.session_state.match_db = df_m
    else:
        if 'conn' not in st.session_state: conn, df_p, df_m = load_data(); st.session_state.conn = conn

    st.markdown("<h1 style='text-align:center; font-family:Rajdhani; font-size: 3.5rem; background: -webkit-linear-gradient(45deg, #D84315, #FF5722); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>SMFC MANAGER PRO</h1>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh Data"): 
        st.session_state.pop('master_db', None)
        st.session_state.ui_version += 1
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["MATCH LOBBY", "TACTICAL BOARD", "ANALYTICS", "DATABASE"])

    # --- TAB 1: LOBBY ---
    with tab1:
        smfc_n, guest_n, total_n = get_counts()
        st.markdown(f"""<div class="section-box"><div style="display:flex; justify-content:space-between; align-items:center;"><div style="color:#FF5722; font-weight:bold; font-size:20px; font-family:Rajdhani;">PLAYER POOL</div><div class="badge-box"><div class="badge-smfc">{smfc_n} SMFC</div><div class="badge-guest">{guest_n} GUEST</div><div class="badge-total">{total_n} TOTAL</div></div></div>""", unsafe_allow_html=True)
        
        with st.expander("📋 PASTE FROM WHATSAPP", expanded=True):
            whatsapp_text = st.text_area("List:", height=150, label_visibility="collapsed", placeholder="Paste list here...")
            if st.button("Select Players", key="btn_select"):
                if 'Selected' in st.session_state.master_db.columns:
                    st.session_state.master_db['Selected'] = False 
                    new_guests = []
                    raw_lines = extract_whatsapp_players(whatsapp_text)
                    for line in raw_lines:
                        match = False
                        clean_input = clean_player_name(line).lower()
                        for idx, row in st.session_state.master_db.iterrows():
                            db_name = clean_player_name(str(row['Name'])).lower()
                            if db_name == clean_input:
                                st.session_state.master_db.at[idx, 'Selected'] = True; match = True; break
                        if not match: new_guests.append(clean_player_name(line))
                    current = get_guests_list()
                    for g in new_guests:
                        if g not in current: current.append(g)
                    st.session_state.guest_input_val = ", ".join(current)
                    st.session_state.ui_version += 1
                    st.toast(f"✅ Found players. {len(new_guests)} guests added!"); st.rerun()

        pos_tabs = st.tabs(["ALL", "FWD", "MID", "DEF"])
        def render_checklist(df_s, t_n):
            if df_s.empty or 'Name' not in df_s.columns: return
            df_s = df_s.sort_values("Name")
            cols = st.columns(3) 
            for i, (idx, row) in enumerate(df_s.iterrows()):
                key_id = f"chk_{idx}_{t_n}_v{st.session_state.ui_version}"
                cols[i % 3].checkbox(f"{row['Name']}", value=bool(row.get('Selected', False)), key=key_id, on_change=toggle_selection, args=(idx,))
        
        with pos_tabs[0]: render_checklist(st.session_state.master_db, "all")
        with pos_tabs[1]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'FWD'], "fwd")
        with pos_tabs[2]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'MID'], "mid")
        with pos_tabs[3]: render_checklist(st.session_state.master_db[st.session_state.master_db['Position'] == 'DEF'], "def")
        st.write(""); st.text_input("Guests (Comma separated)", key="guest_input_val"); st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("⚙️ MATCH SETTINGS (Date, Time, Venue)", expanded=False):
            c1, c2 = st.columns(2)
            match_date = c1.date_input("Match Date", datetime.today(), key="match_date_input")
            match_time = c1.time_input("Kickoff", datetime.now().time(), key="match_time_input")
            venue_opt = c2.selectbox("Venue", ["BFC", "GoatArena", "SportZ", "Other"], key="venue_select")
            venue = c2.text_input("Venue Name", "Ground", key="venue_text") if venue_opt == "Other" else venue_opt
            duration = c2.slider("Duration (Mins)", 60, 120, 90, 30, key="duration_slider")
            st.session_state.match_format = st.selectbox("Format", ["9 vs 9", "7 vs 7", "6 vs 6", "5 vs 5"], key="fmt_select")

        guests = get_guests_list()
        if guests:
            st.write("---"); st.markdown("<h3 style='color:#FFD700; text-align:center; margin-bottom: 15px;'>GUEST SQUAD SETUP</h3>", unsafe_allow_html=True)
            for g_name in guests:
                c_name, c_pos, c_lvl = st.columns([3.5, 2, 2.5])
                with c_name: st.markdown(f"<div class='guest-row-label'>{g_name}</div>", unsafe_allow_html=True)
                with c_pos: st.selectbox("Pos", ["FWD", "MID", "DEF", "GK"], key=f"g_pos_{g_name}", label_visibility="collapsed")
                with c_lvl: st.selectbox("Lvl", ["⭐⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐", "⭐"], index=2, key=f"g_lvl_{g_name}", label_visibility="collapsed")
            st.write("---")

        with st.expander("🛠️ EDIT POSITIONS (Session Only)", expanded=False):
            selected_players = st.session_state.master_db[st.session_state.master_db['Selected'] == True]
            if not selected_players.empty:
                c_p_sel, c_p_pos, c_p_btn = st.columns([3.5, 2, 2.5])
                with c_p_sel:
                    p_opts = [f"{row['Name']} ({row['Position']})" for _, row in selected_players.iterrows()]
                    p_to_edit_str = st.selectbox("Select Player", p_opts, key="edit_pos_player")
                with c_p_pos: new_pos = st.selectbox("New Position", ["FWD", "MID", "DEF", "GK"], key="edit_pos_new")
                with c_p_btn:
                    st.write(""); st.write("")
                    if st.button("UPDATE POS", key="btn_update_pos"):
                        p_name_clean = p_to_edit_str.rsplit(" (", 1)[0]
                        idx = st.session_state.master_db[st.session_state.master_db['Name'] == p_name_clean].index[0]
                        old_pos = st.session_state.master_db.at[idx, 'Position']
                        st.session_state.master_db.at[idx, 'Position'] = new_pos
                        st.session_state.master_db.at[idx, 'Selected'] = True 
                        st.session_state.ui_version += 1
                        st.session_state.position_changes.append(f"{p_name_clean}: {old_pos} → {new_pos}")
                        st.rerun()
                if st.session_state.position_changes:
                    st.write(""); 
                    for change in st.session_state.position_changes: st.markdown(f"<div class='change-log-item'>{change}</div>", unsafe_allow_html=True)
            else: st.info("Select players first.")

        st.write(""); 
        if st.button("⚡ GENERATE SQUAD"):
            if 'Selected' in st.session_state.master_db.columns:
                active = st.session_state.master_db[st.session_state.master_db['Selected'] == True].copy()
                guest_rows = []
                star_map = {"⭐": 1, "⭐⭐": 2, "⭐⭐⭐": 3, "⭐⭐⭐⭐": 4, "⭐⭐⭐⭐⭐": 5}
                for g in get_guests_list():
                    chosen_pos = st.session_state.get(f"g_pos_{g}", "MID")
                    chosen_stars = st.session_state.get(f"g_lvl_{g}", "⭐⭐⭐")
                    rating_val = star_map.get(chosen_stars, 3)
                    guest_rows.append({"Name": g, "Position": chosen_pos, "StarRating": rating_val, "PAC":70,"SHO":70,"PAS":70,"DRI":70,"DEF":70,"PHY":70})
                if guest_rows: active = pd.concat([active, pd.DataFrame(guest_rows)], ignore_index=True)
                if not active.empty:
                    active['Power'] = active.apply(calculate_player_score, axis=1)
                    active = active.sort_values(['Position', 'Power'], ascending=[True, False])
                    df_red = active.iloc[::2].copy(); df_red['Team'] = 'Red'
                    df_blue = active.iloc[1::2].copy(); df_blue['Team'] = 'Blue'
                    st.session_state.match_squad = pd.concat([df_red, df_blue], ignore_index=True)
                    st.session_state.red_ovr = int(df_red['Power'].mean()) if not df_red.empty else 0
                    st.session_state.blue_ovr = int(df_blue['Power'].mean()) if not df_blue.empty else 0
                    st.session_state.match_simulation = "" 
                    st.rerun()
            else: st.error("Database offline.")

        if not st.session_state.match_squad.empty:
            pos_map = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
            st.session_state.match_squad['Pos_Ord'] = st.session_state.match_squad['Position'].map(pos_map).fillna(4)
            reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"].sort_values('Pos_Ord')
            blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"].sort_values('Pos_Ord')
            r_ovr = st.session_state.get('red_ovr', 0); b_ovr = st.session_state.get('blue_ovr', 0)
            
            # --- DISPLAY LINEUPS ---
            red_html = ""; blue_html = ""
            for _, p in reds.iterrows(): red_html += f"<div class='player-card kit-red'><span class='card-name'>{p['Name']}</span><span class='pos-badge'>{p['Position']}</span></div>"
            for _, p in blues.iterrows(): blue_html += f"<div class='player-card kit-blue'><span class='card-name'>{p['Name']}</span><span class='pos-badge'>{p['Position']}</span></div>"
            st.markdown(f"""
            <div class="section-box">
                <div style="color:#FF5722; font-weight:bold; font-size:18px; margin-bottom: 10px;">LINEUPS</div>
                <div style="display: flex; gap: 8px;">
                    <div style="flex: 1; min-width: 0;"><h4 style='color:#ff4b4b; text-align:center; margin:0 0 5px 0; font-size:16px;'>RED <span style='font-size:12px; color:#aaa;'>({r_ovr})</span></h4>{red_html}</div>
                    <div style="width: 1px; background: rgba(255,255,255,0.1);"></div>
                    <div style="flex: 1; min-width: 0;"><h4 style='color:#1c83e1; text-align:center; margin:0 0 5px 0; font-size:16px;'>BLUE <span style='font-size:12px; color:#aaa;'>({b_ovr})</span></h4>{blue_html}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            dt_match = datetime.combine(match_date, match_time)
            dt_end = dt_match + timedelta(minutes=duration)
            str_date = dt_match.strftime('%A, %d %b'); str_time = f"{dt_match.strftime('%I:%M %p')} - {dt_end.strftime('%I:%M %p')}"
            r_list = "\n".join([p['Name'] for p in reds.to_dict('records')]); b_list = "\n".join([p['Name'] for p in blues.to_dict('records')])
            summary = f"Date: {str_date}\nTime: {str_time}\nGround: {venue}\nScore: Blue 0-0 Red\nCost per player: *\nGpay: *\nLateFee: 50\n\n🔵 *BLUE TEAM* ({b_ovr})\n{b_list}\n\n🔴 *RED TEAM* ({r_ovr})\n{r_list}"
            components.html(f"""<textarea id="text_to_copy_v2" style="position:absolute; left:-9999px;">{summary}</textarea><button onclick="var c=document.getElementById('text_to_copy_v2');c.select();document.execCommand('copy');this.innerText='✅ COPIED!';" style="background:linear-gradient(90deg, #FF5722, #FF8A65); color:white; font-weight:800; padding:15px 0; border:none; border-radius:8px; width:100%; cursor:pointer; font-size:16px; margin-top:10px;">📋 COPY TEAM LIST</button>""", height=70)
            
            st.write("---"); st.markdown("<h3 style='text-align:center; color:#FF5722;'>TRANSFER WINDOW</h3>", unsafe_allow_html=True)
            col_tr_red, col_btn, col_tr_blue = st.columns([4, 1, 4])
            red_opts = [f"{r['Name']} ({r['Position']})" for _, r in reds.iterrows()]; blue_opts = [f"{r['Name']} ({r['Position']})" for _, r in blues.iterrows()]
            with col_tr_red: s_red_str = st.selectbox("Select Red", red_opts, key="sel_red", label_visibility="collapsed")
            with col_tr_blue: s_blue_str = st.selectbox("Select Blue", blue_opts, key="sel_blue", label_visibility="collapsed")
            with col_btn:
                if st.button("↔️", key="swap_btn"):
                    s_red = s_red_str.rsplit(" (", 1)[0]; s_blue = s_blue_str.rsplit(" (", 1)[0]
                    idx_r = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_red].index[0]
                    idx_b = st.session_state.match_squad[st.session_state.match_squad["Name"] == s_blue].index[0]
                    st.session_state.match_squad.at[idx_r, "Team"] = "Blue"; st.session_state.match_squad.at[idx_b, "Team"] = "Red"
                    st.session_state.transfer_log.append(f"{s_red} (RED) ↔ {s_blue} (BLUE)")
                    st.session_state.red_ovr = int(st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"]['Power'].mean())
                    st.session_state.blue_ovr = int(st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"]['Power'].mean())
                    st.rerun()
            if st.session_state.transfer_log:
                st.write(""); 
                for log in st.session_state.transfer_log: st.markdown(f"<div class='change-log-item'>{log}</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: PITCH ---
    with tab2:
        if not st.session_state.match_squad.empty:
            c_pitch, c_subs = st.columns([3, 1])
            with c_pitch:
                # 1. SETUP FIGURE
                pitch = Pitch(pitch_type='custom', pitch_length=100, pitch_width=100, pitch_color='#43a047', line_color='white')
                fig, ax = pitch.draw(figsize=(10, 12)) 
                
                # 2. HEADER (UPDATED STYLING)
                # ✅ Added day of week (%a)
                str_date = datetime.combine(match_date, match_time).strftime('%d %b %Y (%a), %I:%M %p')
                # ✅ Changed color to theme orange
                ax.text(50, 107, "SMFC MATCH DAY", color='#FF5722', ha='center', fontsize=22, fontweight='900', fontfamily='sans-serif', path_effects=[path_effects.withStroke(linewidth=3, foreground='black')])
                # ✅ Increased fontsize to 14
                ax.text(50, 103, f"{str_date} | {venue}", color='#FFD700', ha='center', fontsize=14, fontweight='bold', path_effects=[path_effects.withStroke(linewidth=2, foreground='black')])
                
                # 3. PLAYERS ON PITCH
                def draw_player(player_name, x, y, color):
                    pitch.scatter(x, y, s=600, marker='h', c=color, edgecolors='white', linewidth=2, ax=ax, zorder=2)
                    ax.text(x, y-4, player_name, color='black', ha='center', fontsize=10, fontweight='bold', bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", lw=1), zorder=3)
                
                fmt = st.session_state.get('match_format', '9 vs 9')
                coords_map = formation_presets.get(fmt, formation_presets['9 vs 9'])
                r_spots = coords_map.get("RED_COORDS", []); b_spots = coords_map.get("BLUE_COORDS", [])
                
                reds = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Red"].sort_values('Pos_Ord')
                blues = st.session_state.match_squad[st.session_state.match_squad["Team"] == "Blue"].sort_values('Pos_Ord')
                r_ovr = st.session_state.get('red_ovr', 0); b_ovr = st.session_state.get('blue_ovr', 0)
                
                subs_r = []
                for i, row in enumerate(reds.itertuples()):
                    if i < len(r_spots): draw_player(row.Name, r_spots[i][0], r_spots[i][1], '#ff4b4b')
                    else: subs_r.append(row.Name)
                subs_b = []
                for i, row in enumerate(blues.itertuples()):
                    if i < len(b_spots): draw_player(row.Name, b_spots[i][0], b_spots[i][1], '#1c83e1')
                    else: subs_b.append(row.Name)
                
                # 4. DRAW SUBSTITUTES FOOTER
                if subs_r or subs_b:
                    ax.text(50, -2, "SUBSTITUTES", color='white', ha='center', fontsize=14, fontweight='bold', path_effects=[path_effects.withStroke(linewidth=2, foreground='black')])
                    r_text = "\n".join(subs_r) if subs_r else "None"
                    ax.text(25, -5, f"RED SQUAD\n{r_text}", color='#ff4b4b', ha='center', va='top', fontsize=10, fontweight='bold', path_effects=[path_effects.withStroke(linewidth=1, foreground='black')])
                    b_text = "\n".join(subs_b) if subs_b else "None"
                    ax.text(75, -5, f"BLUE SQUAD\n{b_text}", color='#1c83e1', ha='center', va='top', fontsize=10, fontweight='bold', path_effects=[path_effects.withStroke(linewidth=1, foreground='black')])

                st.pyplot(fig)

                # 5. DOWNLOAD BUTTON
                fn = f"SMFC_Lineup_{match_date}.png"
                img_buf = io.BytesIO()
                fig.savefig(img_buf, format='png', bbox_inches='tight', dpi=150, facecolor='#43a047')
                img_buf.seek(0)
                st.download_button(label="📸 DOWNLOAD MATCH CARD", data=img_buf, file_name=fn, mime="image/png", use_container_width=True)

            with c_subs:
                st.markdown("<h4 style='color:#FF5722; text-align:center;'>SUBSTITUTES</h4>", unsafe_allow_html=True)
                if subs_r:
                    st.markdown("<div style='color:#ff4b4b; font-weight:bold;'>🔴 RED SUBS</div>", unsafe_allow_html=True)
                    for s in subs_r: st.markdown(f"- {s}")
                if subs_b:
                    st.markdown("<div style='color:#1c83e1; font-weight:bold; margin-top:10px;'>🔵 BLUE SUBS</div>", unsafe_allow_html=True)
                    for s in subs_b: st.markdown(f"- {s}")
            
            # SIDE-BY-SIDE LISTS
            red_html_t2 = ""; blue_html_t2 = ""
            for _, p in reds.iterrows(): red_html_t2 += f"<div class='player-card kit-red' style='padding: 4px 8px;'><span class='card-name' style='font-size:12px;'>{p['Name']}</span></div>"
            for _, p in blues.iterrows(): blue_html_t2 += f"<div class='player-card kit-blue' style='padding: 4px 8px;'><span class='card-name' style='font-size:12px;'>{p['Name']}</span></div>"
            
            st.write("---")
            st.markdown(f"""
            <div style="display: flex; gap: 5px; margin-top: 10px;">
                <div style="flex: 1; min-width: 0;"><h6 style='color:#ff4b4b; text-align:center; margin:0 0 5px 0;'>RED ({r_ovr})</h6>{red_html_t2}</div>
                <div style="flex: 1; min-width: 0;"><h6 style='color:#1c83e1; text-align:center; margin:0 0 5px 0;'>BLUE ({b_ovr})</h6>{blue_html_t2}</div>
            </div>
            """, unsafe_allow_html=True)

            # MATCH SIMULATION
            st.write("---")
            if st.button("🔮 SIMULATE MATCH SCENARIO"):
                with st.spinner("AI is analyzing player stats and generating simulation..."):
                    r_names = [p['Name'] for p in reds.to_dict('records')]
                    b_names = [p['Name'] for p in blues.to_dict('records')]
                    st.session_state.match_simulation = simulate_match_commentary(r_names, b_names, r_ovr, b_ovr)
            
            if st.session_state.match_simulation:
                st.markdown(f"""
                <div style="background:rgba(0,0,0,0.5); padding:20px; border-radius:10px; border-left: 5px solid #FFD700; margin-top:20px;">
                    <h3 style="color:#FFD700; margin-top:0;">🎙️ MATCH COMMENTARY</h3>
                    <div style="white-space: pre-line; line-height: 1.6; font-family: monospace; font-size: 14px;">
                        {st.session_state.match_simulation}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        else: st.info("Generate Squad First")

    # --- TAB 3: ANALYTICS ---
    with tab3:
        if 'match_db' in st.session_state and not st.session_state.match_db.empty:
            df_m = st.session_state.match_db
            official_names = set(st.session_state.master_db['Name'].unique()) if 'Name' in st.session_state.master_db.columns else set()
            total_goals = pd.to_numeric(df_m['Score_Blue'], errors='coerce').sum() + pd.to_numeric(df_m['Score_Red'], errors='coerce').sum()
            
            st.markdown("<div class='ai-box'>", unsafe_allow_html=True)
            col_avatar, col_title = st.columns([1, 5])
            with col_avatar:
                if os.path.exists("kaarthumbi.png"): st.image("kaarthumbi.png", width=60)
                else: st.markdown("🐘", unsafe_allow_html=True) 
            with col_title:
                st.markdown("<div class='ai-title'>KAARTHUMBI'S CORNER</div>", unsafe_allow_html=True)
            
            user_q = st.text_input("Ask the panel...", key="ai_q", placeholder="E.g. Who played well? What about Gilson?")
            if st.button("📢 Ask Kaarthumbi"):
                with st.spinner("Panel is arguing..."):
                    lb = calculate_leaderboard(df_m, official_names)
                    ans = ask_ai_scout(user_q, lb, df_m)
                    st.session_state.ai_chat_response = ans
            
            if st.session_state.ai_chat_response:
                st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
                lines = st.session_state.ai_chat_response.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    parts = line.split(':', 1)
                    if len(parts) < 2: continue
                    
                    raw_name = parts[0].lower().replace('*', '').strip()
                    msg = parts[1].strip()
                    char_class = "guest-style"
                    avatar = "👤"
                    name = parts[0].replace('*', '').strip().upper()
                    
                    if "kaarthumbi" in raw_name: char_class = "char-kaarthumbi"; avatar = "🐘"
                    elif "bellary" in raw_name: char_class = "char-bellary guest-style"; avatar = "😎"
                    elif "induchoodan" in raw_name: char_class = "char-induchoodan guest-style"; avatar = "🔥"
                    elif "appukuttan" in raw_name: char_class = "char-appukuttan guest-style"; avatar = "🥋"
                    elif "ponjikkara" in raw_name: char_class = "char-ponjikkara guest-style"; avatar = "🤪"
                    
                    st.markdown(f"""<div class="chat-row {char_class}"><div class="chat-avatar">{avatar}</div><div class="chat-bubble"><div class="chat-name">{name}</div>{msg}</div></div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.write("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("MATCHES", len(df_m)); c2.metric("GOALS", int(total_goals)); c3.metric("PLAYERS", len(official_names))
            lb = calculate_leaderboard(df_m, official_names)
            
            if not lb.empty:
                max_m = lb['M'].max(); names_m = ", ".join(lb[lb['M'] == max_m].index.tolist())
                top_player = lb.iloc[0]; val_w = f"{top_player['Win %']}%"; name_w = lb.index[0]
                max_l = lb['L'].max(); names_l = ", ".join(lb[lb['L'] == max_l].index.tolist())
                sp1, sp2, sp3 = st.columns(3)
                with sp1: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #00C9FF;'><div class='sp-value'>{max_m}</div><div class='sp-title'>COMMITMENT</div><div class='sp-name'>{names_m}</div></div>", unsafe_allow_html=True)
                with sp2: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #FFD700;'><div class='sp-value'>{val_w}</div><div class='sp-title'>STAR</div><div class='sp-name'>{name_w}</div></div>", unsafe_allow_html=True)
                with sp3: st.markdown(f"<div class='spotlight-box' style='border-bottom:4px solid #ff4b4b;'><div class='sp-value'>{max_l}</div><div class='sp-title'>LOSSES</div><div class='sp-name'>{names_l}</div></div>", unsafe_allow_html=True)
                
                st.write("---")
                for p, r in lb.iterrows(): 
                    st.markdown(f"""<div class='lb-card'><div class='lb-rank'>#{r['Rank']}</div><div class='lb-info'><div class='lb-name'>{p}</div><div class='lb-stats'>{r['M']} Matches • {r['W']} Wins</div></div><div class='lb-form'>{r['Form_Icons']}</div><div class='lb-winrate'>{r['Win %']}%</div></div>""", unsafe_allow_html=True)
            
            st.write("---")
            st.markdown("<h4 class='neon-white'>RECENT MATCHES</h4>", unsafe_allow_html=True)
            history = df_m.sort_values('Date', ascending=False).head(10)
            for _, row in history.iterrows():
                score_b, score_r = int(row['Score_Blue']), int(row['Score_Red'])
                b_cls, r_cls, border = "mc-score-draw", "mc-score-draw", "#555"
                win_txt, lose_txt, win_cls, lose_cls = row['Team_Blue'], row['Team_Red'], "draw-text", "draw-text"
                if row['Winner'] == "Blue": b_cls, border, win_txt, lose_txt, win_cls, lose_cls = "mc-score-blue", "#1c83e1", row['Team_Blue'], row['Team_Red'], "neon-gold", "dull-grey"
                elif row['Winner'] == "Red": r_cls, border, win_txt, lose_txt, win_cls, lose_cls = "mc-score-red", "#ff4b4b", row['Team_Red'], row['Team_Blue'], "neon-gold", "dull-grey"
                st.markdown(f"""<div class='match-card' style='border-left: 4px solid {border};'><div class='mc-left'><div class='mc-date'>{row['Date']} | {row['Venue']}</div><div class='mc-score'><span class='{b_cls}'>BLUE {score_b}</span> - <span class='{r_cls}'>{score_r} RED</span></div></div><div class='mc-right'><div class='{win_cls}'>{win_txt}</div><div class='{lose_cls}'>{lose_txt}</div></div></div>""", unsafe_allow_html=True)

            with st.expander("⚙️ LOG MATCH"):
                wa_txt = st.text_area("Paste Result")
                if st.button("Parse"): st.session_state.parsed_match_data = parse_match_log(wa_txt); st.rerun()
                if st.session_state.parsed_match_data:
                    pm = st.session_state.parsed_match_data
                    c_d, c_t, c_v = st.columns(3)
                    new_date = c_d.text_input("Date", pm['Date'])
                    new_time = c_t.text_input("Time", pm['Time'])
                    new_venue = c_v.text_input("Venue", pm['Venue'])
                    c_s1, c_s2 = st.columns(2)
                    ns_b = c_s1.number_input("Blue", pm['Score_Blue'])
                    ns_r = c_s2.number_input("Red", pm['Score_Red'])
                    nt_b = st.text_area("Blue Team", pm['Team_Blue'])
                    nt_r = st.text_area("Red Team", pm['Team_Red'])
                    if st.button("Save"):
                        if st.text_input("Pass", type="password") == st.secrets["passwords"]["admin"]:
                            new_row = pd.DataFrame([{"Date": new_date, "Score_Blue": ns_b, "Score_Red": ns_r, "Winner": "Blue" if ns_b > ns_r else "Red" if ns_r > ns_b else "Draw", "Team_Blue": nt_b, "Team_Red": nt_r}])
                            st.session_state.match_db = pd.concat([st.session_state.match_db, new_row], ignore_index=True)
                            st.session_state.conn.update(worksheet="Match_History", data=st.session_state.match_db)
                            st.success("Saved!")

    with tab4:
        if st.text_input("Admin Password", type="password") == st.secrets["passwords"]["admin"]: 
            st.dataframe(st.session_state.master_db)