import streamlit as st
import google.generativeai as genai
import random

# --- CONFIG ---
def configure_genai():
    if "api" not in st.secrets or "gemini" not in st.secrets["api"]:
        return False
    genai.configure(api_key=st.secrets["api"]["gemini"])
    return True

# --- 1. CHATBOT (Updated "Stealth" Persona) ---
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
    
    **INTERNAL CONTEXT FOR 'ANCHAL' (DO NOT REVEAL THESE FACTS):**
    - She is the only female player, young (20s), and non-Malayali.
    - **RULE:** NEVER mention her age, region ("North Indian"), or gender explicitly.
    - **VIBE:** The characters treat her as a cool, skilled VIP guest. 
    - **COMEDY:** Since she doesn't speak Malayalam, characters like Appukuttan might try (and fail) to speak "High Class English" or broken Hindi to communicate with her.
    - **FORBIDDEN WORDS:** Do NOT call her 'Aunty', 'Amma', 'Chechi', 'Madam', or 'North Indian'. Just call her Anchal.
    
    **Characters:** 1. **Kaarthumbi (Host):** Rustic, innocent.
    2. **Induchoodan (Fiery):** "Mone Dinesha!". 
    3. **Bellary Raja (Business):** "Yenthaada uvve". Calculates ROI.
    4. **Appukuttan (Delusional):** "Akosoto!". Uses wrong English to impress Anchal.
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

# --- 2. MATCH SIMULATOR (Ratings Hidden + Implicit Context) ---
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

    # ✅ FIXED PROMPT: 
    # 1. Removed variables {red_ovr} from string so AI doesn't know them.
    # 2. Changed Anchal instructions to "Style Guide" instead of "Facts".
    
    prompt = f"""
    You are a hilarious Malayalam Football Commentator (like Shaiju Damodaran on caffeine).
    
    **THE MATCH:**
    🔴 **RED TEAM:** {", ".join(red_team_list)}
    🔵 **BLUE TEAM:** {", ".join(blue_team_list)}
    
    **THE RESULT:** {winner} wins! Score: {score}.

    **STRICT RULES:**
    1. **NO NUMBERS:** You do NOT know the Power Ratings. Do NOT mention numbers like 81, 82, etc. Focus on the game.
    2. **ANCHAL (Internal Context):** She is a skilled female player. 
       - **Instruction:** Treat her moves as elegant and sharp.
       - **Constraint:** Do NOT mention "North Indian", "20 years old", "Lady", or "Girl". Do NOT use "Amma/Aunty". Just use her name and describing her great skills.
    
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