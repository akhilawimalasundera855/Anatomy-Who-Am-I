import streamlit as st
import time
import random
import uuid
import hashlib
import google.generativeai as genai

# --- 1. AI CONNECTION & KEY ROTATION ---
def call_gemini_rotator(prompt):
    # This matches the KEY1, KEY2, KEY3 names in your Streamlit Secrets
    key_names = ["KEY1", "KEY2", "KEY3"] 
    available_keys = [st.secrets[k] for k in key_names if k in st.secrets]
    
    if not available_keys:
        return "❌ ERROR: No API keys found in Secrets."

    random.shuffle(available_keys) 
    
    for key in available_keys:
        try:
            genai.configure(api_key=key)
            # Using the 2026 High-Capacity Flash-Lite model
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
            continue # Automatically try the next key if one is busy
            
    return "The Professor is currently overwhelmed. Please wait 10 seconds and try again."

# --- 2. ORIGINAL GAMEPLAY HELPERS ---
def generate_verification_hash(u_id, score):
    """Original research verification logic."""
    raw = f"{u_id}-{score}-{time.strftime('%Y%m%d')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:10].upper()

def call_professor(task, user_input=None, structure=None, level="Pre-clinical"):
    """Restored original prompt logic for research consistency."""
    if task == "clues":
        p = f"Act as a strict anatomy professor. Give 3 short, challenging clues for '{structure}' for a {level} student. Label them Regional, Clinical, and Surgical. Do not name the structure."
    elif task == "verify":
        p = f"Structure: {structure}. Student Guess: {user_input}. Is this correct? Reply ONLY 'YES' or 'NO'."
    elif task == "hint":
        p = f"The student guessed wrong. Give a tiny, cryptic anatomical hint for '{structure}' without naming it."
    elif task == "explain":
        p = f"Explain the anatomy of {structure} in 2 sentences. Include one 'High-Yield Clinical Pearl'."
    
    return call_gemini_rotator(p)

# --- 3. SESSION INITIALIZATION ---
st.set_page_config(page_title="Anatomy Shark", page_icon="🦈")

if "total_marks" not in st.session_state: st.session_state.total_marks = 0
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "session_id" not in st.session_state: st.session_state.session_id = str(uuid.uuid4())[:8]
if "current_structure" not in st.session_state: st.session_state.current_structure = None
if "game_stage" not in st.session_state: st.session_state.game_stage = "playing"
if "round_start_time" not in st.session_state: st.session_state.round_start_time = time.time()

# --- 4. SIDEBAR & UI ---
st.title("🦈 Anatomy: Who Am I?")

with st.sidebar:
    st.header("🔬 Session Setup")
    u_id = st.text_input("University ID / Name", placeholder="Enter to start...")
    level = st.selectbox("Level", ["Pre-clinical", "Clinical"])
    region = st.selectbox("Region", ["Thorax", "Abdomen", "Neuroanatomy", "MSK"])
    st.divider()
    st.write(f"**Session ID:** {st.session_state.session_id}")
    st.write(f"**Total Marks:** {st.session_state.total_marks}")

# --- 5. GAME ENGINE (RESTORED ORIGINAL STAGES) ---

if not u_id:
    st.info("Please enter your University ID or Name in the sidebar to begin.")
else:
    # STAGE: PLAYING
    if st.session_state.game_stage == "playing":
        # Initial clue generation for new round
        if st.session_state.current_structure is None:
            pools = {
                "Thorax": ["Heart", "Lungs", "Esophagus", "Trachea", "Aorta"],
                "Abdomen": ["Liver", "Spleen", "Kidney", "Stomach", "Pancreas", "Appendix"],
                "Neuroanatomy": ["Cerebellum", "Thalamus", "Pituitary Gland", "Midbrain"],
                "MSK": ["Deltoid", "Femur", "Biceps Brachii", "Sartorius", "Patella"]
            }
            st.session_state.current_structure = random.choice(pools.get(region, pools["Thorax"]))
            
            with st.spinner("Professor is preparing clues..."):
                clues = call_professor("clues", structure=st.session_state.current_structure, level=level)
                st.session_state.messages.append({"role": "assistant", "content": clues})

        # Display Chat
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.write(msg["content"])

        # Input Guess
        if prompt := st.chat_input("Enter your anatomical guess..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)

            with st.spinner("Verifying..."):
                result = call_professor("verify", user_input=prompt, structure=st.session_state.current_structure)

            if "YES" in result.upper():
                st.balloons()
                marks = max(10 - (st.session_state.attempts * 3), 0)
                st.session_state.total_marks += marks
                explanation = call_professor("explain", structure=st.session_state.current_structure)
                st.success(f"✅ CORRECT! It is the {st.session_state.current_structure}. (+{marks} marks)")
                st.write(f"🎓 **Synthesis:** {explanation}")
                st.session_state.game_stage = "summary"
                st.rerun()
            else:
                st.session_state.attempts += 1
                if st.session_state.attempts >= 3:
                    st.error(f"❌ Failed. It was the {st.session_state.current_structure}.")
                    st.session_state.game_stage = "summary"
                    st.rerun()
                else:
                    hint = call_professor("hint", structure=st.session_state.current_structure)
                    st.warning(f"❌ Incorrect ({st.session_state.attempts}/3). Hint: {hint}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Incorrect. Hint: {hint}"})

    # STAGE: SUMMARY (RESTORED)
    elif st.session_state.game_stage == "summary":
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Play Next Round"):
                st.session_state.messages = []
                st.session_state.attempts = 0
                st.session_state.current_structure = None
                st.session_state.game_stage = "playing"
                st.rerun()
        with col2:
            if st.button("🛑 End Session"):
                st.session_state.game_stage = "finished"
                st.rerun()

    # STAGE: FINISHED (RESTORED)
    elif st.session_state.game_stage == "finished":
        v_hash = generate_verification_hash(u_id, st.session_state.total_marks)
        st.success("Session Completed!")
        st.subheader("🏁 Your Performance Record")
        st.write(f"**Participant:** {u_id}")
        st.write(f"**Total Score:** {st.session_state.total_marks}")
        st.write(f"**Verification Hash:** `{v_hash}`")
        st.info("Please take a screenshot of this record for your evaluation form.")
        if st.button("Start New Session"):
            st.session_state.total_marks = 0
            st.session_state.game_stage = "playing"
            st.session_state.current_structure = None
            st.session_state.messages = []
            st.rerun()
