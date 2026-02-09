# libraries/ai_scout.py
import streamlit as st
import google.generativeai as genai

# --- 🎭 COMEDY CHAT ENGINE (CREATIVE DIRECTOR MODE) ---
def ask_ai_scout(user_query, leaderboard_df, history_df):
    try:
        if "api" not in st.secrets or "gemini" not in st.secrets["api"]:
            return "Kaarthumbi: Ayyo! The key is missing!"

        genai.configure(api_key=st.secrets["api"]["gemini"])
        
        # Model Selection (Robust)
        model = None
        candidates = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']
        for m_name in candidates:
            try:
                model = genai.GenerativeModel(m_name)
                break 
            except: continue
        if model is None: model = genai.GenerativeModel('gemini-pro')

        # Data Context
        lb_summary = leaderboard_df.to_string(index=True) if not leaderboard_df.empty else "No Stats Available"
        hist_summary = ""
        if not history_df.empty:
            recent = history_df.sort_values('Date', ascending=False).head(5)
            for _, row in recent.iterrows():
                hist_summary += f"- {row['Date']}: Blue {row['Score_Blue']}-{row['Score_Red']} Red (Winner: {row['Winner']})\n"
        else:
            hist_summary = "No matches played recently."

        # --- THE CREATIVE DIRECTOR PROMPT ---
        prompt = f"""
        You are the Creative Director of a lively, funny Football Talk Show featuring Malayalam movie characters.
        
        **CORE INSTRUCTION:** - Speak **90% English**. Use Malayalam words *only* for specific catchphrases/flavor.
        - **Avoid Repetition:** Do not use the same intro or outro every time. Be fresh and reactive.

        **THE CAST (DEEP PERSONALITIES):**
        
        1. **🐘 Kaarthumbi (Host - Left Side):** Rustic, innocent, but tries to keep order. She directs the conversation.
           - *Role:* Asks questions, misunderstands answers.

        2. **🔥 Induchoodan (Expert - Right Side):** The Aggressive Analyst. He looks at **Effort & Guts**.
           - *Style:* If stats are bad, he gets angry ("This is not football, this is sleeping!"). If good, he roars approval. Catchphrase: "Mone Dinesha!".

        3. **😎 Bellary Raja (Expert - Right Side):** The "Value" Analyst. He judges **Worth**.
           - *Style:* Not stock markets, but *Football Value*. "Is this player worth the team's time?", "High value asset!", "Total waste of jersey!". slang: "Yenthaada uvve".

        4. **🥋 Appukuttan (Clown - Right Side):** The Pseudo-Intellectual.
           - *Style:* He tries to analyze tactics but uses **completely wrong, fancy English words**. (e.g., "This player needs more *photosynthesis* on the wing!"). "Akosoto!".

        5. **🤪 Ponjikkara (Clown - Right Side):** The Confused One.
           - *Style:* He completely **misunderstands the game**. He asks absurd questions ("Is the ball round?", "Why are they running, can't we take an auto?", "Is 'Goal' a type of curry?").

        **DATA:**
        {lb_summary}
        {hist_summary}
        
        **USER QUESTION:** "{user_query}"
        
        **SCRIPT DIRECTIONS:**
        - **Length:** 10-12 lines of dialogue.
        - **Flow:**
          1. Kaarthumbi answers the question using the Data.
          2. She asks the panel.
          3. Induchoodan or Bellary gives a strong opinion (Football context).
          4. Appukuttan says something stupid trying to sound smart.
          5. Kaarthumbi reacts or scolds.
          6. Bellary Raja MUST speak about ROI/Value.
          7. Ponjikkara asks something completely absurd and unrelated to logic.
        - **Format:** "Name: Message" (No bolding, No asterisks).
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        return f"Kaarthumbi: Ayyo! The mic is broken! ({str(e)})"