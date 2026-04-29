import streamlit as st
import time
import random
import google.generativeai as genai

# --- 1. CONFIGURATION & KEY ROTATION ---
# This function rotates through your different Google account keys automatically.
def call_gemini(prompt):
    # These must match the names in your Streamlit Secrets exactly
    key_names = ["KEY1", "KEY2", "KEY3"] 
    available_keys = [st.secrets[k] for k in key_names if k in st.secrets]
    
    if not available_keys:
        return "❌ ERROR: No API keys found in Streamlit Secrets."

    random.shuffle(available_keys) 
    last_error = ""

    for key in available_keys:
        try:
            genai.configure(api_key=key)
            # UPDATED FOR 2026: Using the current stable 2.5-flash model
            model = genai.GenerativeModel('gemini-2.5-flash')
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
            continue 
            
    return f"⚠️ SYSTEM ERROR: {last_error}"

# --- 2. THE GAME UI ---
st.set_page_config(page_title="Anatomy Shark", page_icon="🦈", layout="centered")
st.title("🦈 Anatomy: Who Am I?")
st.markdown("---")

# Initialize session state variables
if "messages" not in st.session_state: st.session_state.messages = []
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "current_structure" not in st.session_state: st.session_state.current_structure = None

# Sidebar Setup
with st.sidebar:
    st.header("🔬 Session Settings")
    u_id = st.text_input("University ID / Name", key="u_id", placeholder="Enter to begin...")
    level = st.selectbox("Competency Level", ["Pre-clinical", "Clinical"])
    region = st.selectbox("Anatomical Region", ["Thorax", "Abdomen", "Neuroanatomy", "MSK"])
    
    if st.button("🔄 Start New Game"):
        st.session_state.current_structure = None
        st.session_state.messages = []
        st.session_state.attempts = 0
        st.rerun()

# --- 3. CORE GAME LOGIC ---

# 1. Trigger the "Professor" to pick a structure and give clues
if u_id and st.session_state.current_structure is None:
    # Anatomy Pool based on region selection
    pools = {
        "Thorax": ["Heart", "Lungs", "Esophagus", "Thymus", "Trachea"],
        "Abdomen": ["Liver", "Spleen", "Kidney", "Stomach", "Pancreas", "Appendix"],
        "Neuroanatomy": ["Cerebellum", "Thalamus", "Pituitary Gland", "Hippocampus"],
        "MSK": ["Deltoid", "Femur", "Biceps Brachii", "Sartorius"]
    }
    st.session_state.current_structure = random.choice(pools.get(region, pools["Thorax"]))
    
    # Prompt the AI for the clues
    prompt = f"Act as a strict anatomy professor. Give 3 short clues for the '{st.session_state.current_structure}' for a {level} student. Label them Regional, Clinical, and Surgical. Be brief."
    
    with st.spinner("Professor is thinking..."):
        first_message = call_gemini(prompt)
        st.session_state.messages.append({"role": "assistant", "content": first_message})

# 2. Display the conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 3. Handle student guesses
if prompt := st.chat_input("Enter your anatomical guess..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.write(prompt)

    # Verification Logic
    with st.spinner("Verifying..."):
        check_prompt = f"The structure is '{st.session_state.current_structure}'. The student guessed '{prompt}'. Is this correct? Reply ONLY 'YES' or 'NO'."
        result = call_gemini(check_prompt)

    if "YES" in result.upper():
        st.balloons()
        st.success(f"✅ CORRECT! It is the {st.session_state.current_structure}.")
        pearl_prompt = f"Explain the anatomy of the {st.session_state.current_structure} in 2 sentences and include one 'High-Yield Clinical Pearl'."
        explanation = call_gemini(pearl_prompt)
        st.write(f"🎓 **Professor's Synthesis:** {explanation}")
    else:
        st.session_state.attempts += 1
        if st.session_state.attempts >= 3:
            st.error(f"❌ Game Over! The structure was the **{st.session_state.current_structure}**.")
            st.info("Click 'Start New Game' in the sidebar to try again.")
        else:
            hint_prompt = f"The student guessed wrong. Give a very tiny, cryptic anatomical hint for '{st.session_state.current_structure}' without naming it."
            hint = call_gemini(hint_prompt)
            st.warning(f"❌ Incorrect ({st.session_state.attempts}/3). **Hint:** {hint}")
            st.session_state.messages.append({"role": "assistant", "content": f"Incorrect. Hint: {hint}"})
