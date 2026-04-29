import streamlit as st
import time
import random
import google.generativeai as genai

# --- 1. CONFIGURATION & KEY ROTATION ---
# This function tries all your keys one by one until one works.
def call_gemini(prompt):
    # List the names of the keys you have in your Streamlit Secrets
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4"] 
    available_keys = [st.secrets[k] for k in key_names if k in st.secrets]
    
    random.shuffle(available_keys) # Spread the load across accounts
    
    for key in available_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Disable safety filters to prevent silent empty responses
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
            continue # Try the next key if this one fails/is busy
    return "The Professor is currently busy with another student. Please wait 10 seconds and try again."

# --- 2. GAME LOGIC ---
st.set_page_config(page_title="Anatomy Shark", page_icon="🦈")
st.title("🦈 Anatomy: Who Am I?")

# Initialize session
if "messages" not in st.session_state: st.session_state.messages = []
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "current_structure" not in st.session_state: st.session_state.current_structure = None

# Sidebar Setup
with st.sidebar:
    st.header("Setup")
    u_id = st.text_input("University ID / Name", placeholder="Enter to start...")
    level = st.selectbox("Level", ["Pre-clinical", "Clinical"])
    region = st.selectbox("Region", ["Thorax", "Abdomen", "Neuroanatomy", "MSK"])

# Start Game Logic
if u_id and st.session_state.current_structure is None:
    pool = ["Heart", "Lungs", "Liver", "Spleen", "Kidney", "Stomach", "Pancreas", "Diaphragm", "Appendix"]
    st.session_state.current_structure = random.choice(pool)
    
    prompt = f"Act as a strict anatomy professor. Give 3 short, challenging clues for the '{st.session_state.current_structure}' for a {level} student. Label them Regional, Clinical, and Surgical. Do not reveal the name."
    with st.spinner("Professor is thinking..."):
        first_message = call_gemini(prompt)
        st.session_state.messages.append({"role": "assistant", "content": first_message})

# Display Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

# User Input
if prompt := st.chat_input("Enter your anatomical guess..."):
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Verify Logic
    check_prompt = f"The structure is '{st.session_state.current_structure}'. The student guessed '{prompt}'. Is this correct? Reply ONLY 'YES' or 'NO'."
    result = call_gemini(check_prompt)

    if "YES" in result.upper():
        st.balloons()
        final_prompt = f"Explain the structure '{st.session_state.current_structure}' in 2 sentences. Include one 'High-Yield Clinical Pearl'."
        explanation = call_gemini(final_prompt)
        st.success(f"CORRECT! It is the {st.session_state.current_structure}.")
        st.write(explanation)
        if st.button("Play Next Round"):
            st.session_state.current_structure = None
            st.session_state.messages = []
            st.rerun()
    else:
        st.session_state.attempts += 1
        if st.session_state.attempts >= 3:
            st.error(f"Out of tries! It was the {st.session_state.current_structure}.")
            if st.button("Try a New Structure"):
                st.session_state.current_structure = None
                st.session_state.messages = []
                st.session_state.attempts = 0
                st.rerun()
        else:
            hint_prompt = f"The student guessed wrong. Give a very tiny hint for '{st.session_state.current_structure}' without naming it."
            hint = call_gemini(hint_prompt)
            st.warning(f"Incorrect ({st.session_state.attempts}/3). Hint: {hint}")
