import streamlit as st
import google.generativeai as genai
import random

# --- CONFIG ---
def configure_genai():
    if "api" not in st.secrets or "gemini" not in st.secrets["api"]:
        return False
    genai.configure(api_key=st.secrets["api"]["gemini"])
    return True

# --- 1. CHATBOT (Updated Persona) ---
def ask_ai_scout(user_query, leaderboard_df, history_df):
    if not configure_genai(): return "Kaarthumbi: Ayyo! API Key missing!"
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    
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
    
    **SPECIAL RULE FOR 'ANCHAL':**
    - Anchal is the **ONLY Female player**.
    - **Identity:** She is **Young (20s)** and **North Indian (Non-Malayali)**.
    - **Vibe:** The Malayali characters treat her as a cool, skilled guest. They might try (and fail) to speak English or Hindi to include her.
    - **FORBIDDEN:** Do NOT call her 'Aunty', 'Amma', 'Chechi', or 'Malayali'. 
    
    **Characters:** 1. **Kaarthumbi (Host):** Rustic, innocent.
    2. **Induchoodan (Fiery):** "Mone Dinesha!". 
    3. **Bellary Raja (Business):** "Yenthaada uvve". Calculates ROI.
    4. **Appukuttan (Delusional):** "Akosoto!". Uses wrong English.
    5. **Ponjikkara (Confused):** "I want to go home".

    **Data:** {lb_summary}
    **User Question:** "{user_query}"
    
    **Instructions:** Write a 10-line funny script. Kaarthumbi starts. 90% English.
    **Format:** Name: Message
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Kaarthumbi: Ayyo! The spirits are silent! ({str(e)})"

# --- 2. MATCH SIMULATOR (Ratings Hidden + Persona Fixed) ---
def simulate_match_commentary(red_team_list, blue_team_list, red_ovr, blue_ovr):
    if not configure_genai(): return "System: API Key missing!"
    
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Determine Winner Logic
    red_weight = red_ovr / (red_ovr + blue_ovr)
    if random.random() < red_weight:
        winner = "RED"
        score = f"{random.randint(2,4)} - {random.randint(0,2)}"
    else:
        winner = "BLUE"
        score = f"{random.randint(0,2)} - {random.randint(2,4)}"

    # ✅ FIXED PROMPT: Removed Power Numbers from display string
    prompt = f"""
    You are a hilarious Malayalam Football Commentator (like Shaiju Damodaran on caffeine).
    
    **THE MATCH:**
    🔴 **RED TEAM:** {", ".join(red_team_list)}
    🔵 **BLUE TEAM:** {", ".join(blue_team_list)}
    
    **THE RESULT:** {winner} wins! Score: {score}.

    **STRICT RULES:**
    1. **NO SECRET DATA:** NEVER mention "Power Ratings", "Points", or "Numbers" (like 81, 82). Just talk about their skill on the field.
    2. **ANCHAL:** She is a young (20s) North Indian female player. Use She/Her. Do NOT use terms like 'Amma' or 'Aunty'. Describe her skill respectfully.
    
    **INSTRUCTIONS:**
    - Write a **funny 5-point commentary** of key moments.
    - **Style:** High energy, movie references (Lucifer, Spadikam, CBI), exaggeration.
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