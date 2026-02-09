import streamlit as st
import google.generativeai as genai
import random

# --- CONFIG ---
def configure_genai():
    if "api" not in st.secrets or "gemini" not in st.secrets["api"]:
        return False
    genai.configure(api_key=st.secrets["api"]["gemini"])
    return True

# --- 1. CHATBOT (Existing) ---
def ask_ai_scout(user_query, leaderboard_df, history_df):
    if not configure_genai(): return "Kaarthumbi: Ayyo! API Key missing!"
    
    model = genai.GenerativeModel('gemini-pro')
    
    # Context
    lb_summary = leaderboard_df.to_string(index=True) if not leaderboard_df.empty else "No Stats Available"
    hist_summary = ""
    if not history_df.empty:
        recent = history_df.sort_values('Date', ascending=False).head(5)
        for _, row in recent.iterrows():
            hist_summary += f"- {row['Date']}: Blue {row['Score_Blue']}-{row['Score_Red']} Red (Winner: {row['Winner']})\n"
    else:
        hist_summary = "No matches played recently."

    prompt = f"""
    You are the Creative Director of a funny Malayalam movie character football panel.
    **Characters:** Kaarthumbi (Host), Induchoodan (Fiery), Bellary Raja (Business), Appukuttan (Delusional), Ponjikkara (Confused).
    **Data:** {lb_summary}
    **User Question:** "{user_query}"
    **Instructions:** Write a 10-line funny script. Kaarthumbi starts. Bellary speaks about Value/ROI. Induchoodan speaks about Guts. Ponjikkara is confused. 90% English.
    **Format:** Name: Message
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Kaarthumbi: Ayyo! The spirits are silent! ({str(e)})"

# --- 2. MATCH SIMULATOR (New Feature!) ---
def simulate_match_commentary(red_team_list, blue_team_list, red_ovr, blue_ovr):
    if not configure_genai(): return "System: API Key missing!"
    
    model = genai.GenerativeModel('gemini-pro')

    # Determine Winner Logic (Weighted Random)
    red_weight = red_ovr / (red_ovr + blue_ovr)
    if random.random() < red_weight:
        winner = "RED"
        score = f"{random.randint(2,4)} - {random.randint(0,2)}"
    else:
        winner = "BLUE"
        score = f"{random.randint(0,2)} - {random.randint(2,4)}"

    prompt = f"""
    You are a hilarious Malayalam Football Commentator (like Shaiju Damodaran on caffeine).
    
    **THE MATCH:**
    🔴 **RED TEAM (Power {red_ovr}):** {", ".join(red_team_list)}
    🔵 **BLUE TEAM (Power {blue_ovr}):** {", ".join(blue_team_list)}
    
    **THE RESULT:** {winner} wins! Score: {score}.
    
    **INSTRUCTIONS:**
    - Write a **funny 5-point commentary** of key moments.
    - Mention specific players from the lists above doing funny or heroic things.
    - **Style:** High energy, movie references, exaggeration.
    - **Format:**
      ⏰ **Min 10:** [Event]
      ⏰ **Min 35:** [Event]
      ...
      🏆 **FULL TIME:** [Summary]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Commentary Box: Signal Lost! ({str(e)})"