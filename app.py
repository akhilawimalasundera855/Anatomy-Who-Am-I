import streamlit as st
import time
import random
import google.generativeai as genai

# --- 1. CONFIGURATION & ERROR DIAGNOSTICS ---
def call_gemini(prompt):
    key_names = ["KEY1", "KEY2", "KEY3"] 
    available_keys = [st.secrets[k] for k in key_names if k in st.secrets]
    
    if not available_keys:
        return "❌ ERROR: No API keys found in Streamlit Secrets. Check the naming (KEY1, KEY2, etc.)"

    random.shuffle(available_keys) 
    last_error = ""

    for key in available_keys:
        try:
            genai.configure(api_key=key)
            # We try both 1.5-flash and 2.5-flash (common in 2026)
            model = genai.GenerativeModel('gemini-1.5-flash')
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
        except Exception as e:
            last_error = str(e)
            time.sleep(0.5) # Short wait before next key
            continue 
            
    # If all keys fail, tell the user the SPECIFIC error
    return f"⚠️ SYSTEM ERROR: All keys failed. Last error: {last_error}"

# --- 2. GAME UI ---
st.set_page_config(page_title="Anatomy Shark", page_icon="🦈")
st.title("🦈 Anatomy: Who Am I?")

if "messages" not in st.session_state: st.session_state.messages = []
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "current_structure" not in st.session_state: st.session_state.current_structure = None

with st.sidebar:
    st.header("Setup")
    u_id = st.text_input("University ID / Name", key="u_id")
    level = st.selectbox("Level", ["Pre-clinical", "Clinical"])
    region = st.selectbox("Region", ["Thorax", "Abdomen", "Neuroanatomy", "MSK"])
    if st.button("Reset Game"):
        st.session_state.current_structure = None
        st.session_state.messages = []
        st.rerun()

# Logic to start the first round
if u_id and st.session_state.current_structure is None:
    pool = ["Heart", "Lungs", "Liver", "Spleen", "Kidney", "Stomach", "Pancreas", "Diaphragm", "Appendix"]
    st.session_state.current_structure = random.choice(pool)
    
    prompt = f"Act as an anatomy professor. Give 3 short clues for the '{st.session_state.current_structure}' for a {level} student. Label them Regional, Clinical, and Surgical. Be brief."
    with st.spinner("Professor is thinking..."):
        first_message = call_gemini(prompt)
        st.session_state.messages.append({"role": "assistant", "content": first_message})

# Display Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.write(msg["content"])

# User Guess
if prompt := st.chat_input("Your guess?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    check_prompt = f"Structure: {st.session_state.current_structure}. Guess: {prompt}. Is it correct? Reply ONLY 'YES' or 'NO'."
    result = call_gemini(check_prompt)

    if "YES" in result.upper():
        st.balloons()
        st.success(f"CORRECT! It is the {st.session_state.current_structure}.")
        pearl = call_gemini(f"Explain {st.session_state.current_structure} in 2 sentences with 1 clinical pearl.")
        st.write(pearl)
    else:
        st.session_state.attempts += 1
        if st.session_state.attempts >= 3:
            st.error(f"Game Over! It was the {st.session_state.current_structure}.")
        else:
            hint = call_gemini(f"Give a tiny hint for {st.session_state.current_structure} without naming it.")
            st.warning(f"Wrong ({st.session_state.attempts}/3). Hint: {hint}")
