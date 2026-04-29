import streamlit as st
import time
import random
import google.generativeai as genai

# --- 1. HIGH-CAPACITY ENGINE ---
def call_gemini(prompt):
    # This looks for KEY1, KEY2, KEY3 in your Streamlit Secrets
    key_names = ["KEY1", "KEY2", "KEY3"] 
    available_keys = [st.secrets[k] for k in key_names if k in st.secrets]
    
    if not available_keys:
        return "❌ ERROR: No API keys found. Please check Secrets."

    # Shuffle keys to distribute the 13-student load
    random.shuffle(available_keys) 
    
    for key in available_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.5-flash-lite') 
            response = model.generate_content(
                prompt,
                safety_settings={
                    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
                }
            )
            return response.text
        except Exception:
            continue # If one account is busy, try the next account immediately
            
    return "😴 The Professor is temporarily busy. Please wait 10 seconds and try again."

# --- 2. THE STUDENT UI ---
st.set_page_config(page_title="Anatomy Shark", page_icon="🦈", layout="centered")
st.title("🦈 Anatomy: Who Am I?")
st.markdown("---")

if "messages" not in st.session_state: st.session_state.messages = []
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "current_structure" not in st.session_state: st.session_state.current_structure = None

with st.sidebar:
    st.header("🔬 Student Setup")
    u_id = st.text_input("University ID / Name", key="u_id")
    level = st.selectbox("Level", ["Pre-clinical", "Clinical"])
    region = st.selectbox("Region", ["Thorax", "Abdomen", "Neuroanatomy", "MSK"])
    if st.button("🔄 New Structure"):
        st.session_state.current_structure = None
        st.session_state.messages = []
        st.session_state.attempts = 0
        st.rerun()

# --- 3. GAMEPLAY ---
if u_id and st.session_state.current_structure is None:
    pools = {
        "Thorax": ["Heart", "Lungs", "Esophagus", "Trachea", "Aorta"],
        "Abdomen": ["Liver", "Spleen", "Kidney", "Stomach", "Pancreas", "Appendix"],
        "Neuroanatomy": ["Cerebellum", "Thalamus", "Pituitary Gland", "Midbrain"],
        "MSK": ["Deltoid", "Femur", "Biceps Brachii", "Sartorius", "Patella"]
    }
    st.session_state.current_structure = random.choice(pools.get(region, pools["Thorax"]))
    
    p = f"Act as an anatomy professor. Give 3 short clues for the '{st.session_state.current_structure}' for a {level} medical student. Label them Regional, Clinical, and Surgical."
    with st.spinner("Professor is preparing your clues..."):
        first_clue = call_gemini(p)
        st.session_state.messages.append({"role": "assistant", "content": first_clue})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

if user_guess := st.chat_input("What is your guess?"):
    st.session_state.messages.append({"role": "user", "content": user_guess})
    with st.chat_message("user"): st.write(user_guess)

    check_p = f"Structure: {st.session_state.current_structure}. Guess: {user_guess}. Is it correct? Reply ONLY 'YES' or 'NO'."
    result = call_gemini(check_p)

    if "YES" in result.upper():
        st.balloons()
        st.success(f"✅ CORRECT! It is the {st.session_state.current_structure}.")
        pearl = call_gemini(f"Explain {st.session_state.current_structure} in 2 sentences with 1 high-yield clinical pearl.")
        st.write(f"🎓 **Professor's Synthesis:** {pearl}")
    else:
        st.session_state.attempts += 1
        if st.session_state.attempts >= 3:
            st.error(f"❌ Out of tries! The structure was the **{st.session_state.current_structure}**.")
        else:
            hint = call_gemini(f"Give a very tiny anatomical hint for {st.session_state.current_structure} without naming it.")
            st.warning(f"❌ Incorrect. **Hint:** {hint}")
