import streamlit as st
import google.generativeai as genai
import time
import uuid
import random
import hashlib
import re

# --- 1. RESEARCH STATE INITIALIZATION ---
if "total_marks" not in st.session_state: st.session_state.total_marks = 0
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "session_id" not in st.session_state: st.session_state.session_id = str(uuid.uuid4())[:8]
if "current_structure" not in st.session_state: st.session_state.current_structure = None
if "game_stage" not in st.session_state: st.session_state.game_stage = "playing"
if "is_first_round" not in st.session_state: st.session_state.is_first_round = True

# --- 2. RESEARCH UTILITIES ---
def generate_verification_hash(student_id, marks):
    raw_string = f"{student_id}-{marks}-{st.session_state.session_id}"
    hash_object = hashlib.sha256(raw_string.encode())
    return f"UOM-{hash_object.hexdigest()[:6].upper()}"

# --- 3. THE ADAPTIVE STREAMING ENGINE (v8.5) ---
def get_api_key():
    """Rotates keys to support up to 500 concurrent users."""
    all_keys = []
    if "GEMINI_API_KEY" in st.secrets:
        val = st.secrets["GEMINI_API_KEY"]
        all_keys = list(val) if isinstance(val, list) else [val]
    for k in ["KEY1", "KEY2", "KEY3", "KEY4"]:
        if k in st.secrets: all_keys.append(st.secrets[k])
    return random.choice(all_keys) if all_keys else None

def get_professor_stream(prompt_type, user_input="", structure="", is_first=False):
    """Returns a stream object for word-by-word responses."""
    key = get_api_key()
    if not key: return None
    
    genai.configure(api_key=key)
    # Using 1.5 Flash: The fastest model for clinical reasoning
    model = genai.GenerativeModel('gemini-1.5-flash')
    difficulty = st.session_state.get('difficulty', 'Pre-clinical')

    # Randomized Secret Region
    body_regions = ["Thorax", "Abdomen", "Pelvis", "Head and Neck", "Upper Limb", "Lower Limb", "Neuroanatomy", "Special Senses"]
    random_region = random.choice(body_regions)

    PERSONA = (
        "You are a Senior Clinical Anatomy Professor. Your demeanor is friendly, encouraging, and professional, "
        "yet you remain a strict academic examiner. You value precise deductive reasoning and high-end clinical relevance."
    )

    intro_logic = ""
    if is_first:
        intro_logic = (
            "This is the student's first game. Briefly welcome them to 'Anatomy: Who Am I?' "
            "Explain that you provide 3 clues and they have 3 attempts. Encourage clinical thinking. "
        )

    prompts = {
        "start": (f"{PERSONA} {intro_logic} "
                  f"INTERNAL SELECTION (SECRET): Select ONE high-yield anatomical structure from the {random_region}. "
                  f"Provide 3 high-end academic clues for {difficulty} level exactly under these subheadings: "
                  f"### **Regional anatomy**\n### **clinical anatomy**\n### **Surgical anatomy**\n"
                  f"CRITICAL: Do NOT reveal the region or structure name in the clues. "
                  f"At the very end, output ONLY: [ANSWER: structure_name]"),
        
        "verify": (f"Target: '{structure}'. Student Guess: '{user_input}'. "
                   f"Strictly check abbreviations (IJV), minor typos (1-2 letters), and missing terms (e.g. 'muscle'). "
                   f"Respond ONLY 'YES' or 'NO'."),
        
        "hint": (f"{PERSONA} The student guessed '{user_input}' for '{structure}' and was wrong. "
                 f"Provide ONE NEW unique 'Blind Hint' in a friendly tone. "
                 f"DO NOT repeat clues or name the target/region."),
        
        "reveal": (f"{PERSONA} The answer was '{structure}'. Provide a structured 'Educational Synthesis': "
                   f"1. Formal Identification (Correct any shorthand used). "
                   f"2. A 2-3 sentence 'High-Yield Clinical Pearl'.")
    }

    # Verification doesn't need streaming (it's instant)
    if prompt_type == "verify":
        return model.generate_content(prompts[prompt_type]).text.strip()
    
    # Start, Hint, and Reveal use streaming for speed
    return model.generate_content(prompts[prompt_type], stream=True)

# --- 4. INTERFACE SETUP ---
st.set_page_config(page_title="Anatomy Who Am I", page_icon="🧬", layout="centered")

with st.sidebar:
    st.title("🛡️ Research Portal")
    raw_id = st.text_input("University ID Number:", placeholder="e.g. 210XXX")
    st.session_state.difficulty = st.selectbox("Select Competency Level", ["Pre-clinical", "Clinical", "Post-graduate"])
    st.divider()
    st.metric(label="Current Session Marks", value=st.session_state.total_marks)
    if st.button("♻️ Reset Session"): st.session_state.clear(); st.rerun()

# --- 5. CORE GAMEPLAY LOOP ---
st.title("🧬 Anatomy: Who Am I?")

if not raw_id:
    st.info("👋 Please enter your ID in the sidebar to begin.")
    st.stop()

# STAGE: INITIALIZATION (THE SPEED FIX)
if st.session_state.game_stage == "playing" and st.session_state.current_structure is None:
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_text = ""
        # We use st.write_stream to make the text appear word-by-word
        def response_generator():
            nonlocal full_text
            stream = get_professor_stream("start", is_first=st.session_state.is_first_round)
            for chunk in stream:
                full_text += chunk.text
                # Hide the answer tag from the student
                display_text = re.sub(r"\[ANSWER:.*?\]", "", full_text)
                yield chunk.text if "[ANSWER:" not in chunk.text else ""

        clues_only = st.write_stream(response_generator())
        
        # After stream finishes, extract the hidden answer
        match = re.search(r"\[ANSWER: (.*?)\]", full_text)
        if match:
            st.session_state.current_structure = match.group(1).strip()
        
        st.session_state.messages.append({"role": "assistant", "content": clues_only})
        st.session_state.is_first_round = False

# DISPLAY PREVIOUS CHAT
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# STAGE: GUESSING
if st.session_state.game_stage == "playing" and st.session_state.current_structure:
    if prompt := st.chat_input("Enter your anatomical guess..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            # Verification is very fast, use spinner
            with st.spinner("Verifying..."):
                is_correct = get_professor_stream("verify", user_input=prompt, structure=st.session_state.current_structure)
            
            if "YES" in is_correct.upper() and "NO" not in is_correct.upper():
                marks = [30, 20, 10][min(st.session_state.attempts, 2)]
                st.session_state.total_marks += marks
                st.success(f"✅ CORRECT! (+{marks} marks)")
                st.balloons()
                
                # Stream the revelation
                def reveal_gen():
                    stream = get_professor_stream("reveal", structure=st.session_state.current_structure)
                    for chunk in stream: yield chunk.text
                explanation = st.write_stream(reveal_gen())
                st.session_state.messages.append({"role": "assistant", "content": f"✅ CORRECT! {explanation}"})
                st.session_state.game_stage = "summary"; st.rerun()
                
            else:
                if st.session_state.attempts >= 2:
                    st.error(f"❌ Failed.")
                    def reveal_gen():
                        stream = get_professor_stream("reveal", structure=st.session_state.current_structure)
                        for chunk in stream: yield chunk.text
                    explanation = st.write_stream(reveal_gen())
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ FAILED. {explanation}"})
                    st.session_state.game_stage = "summary"; st.rerun()
                else:
                    st.session_state.attempts += 1
                    st.error(f"❌ Incorrect ({st.session_state.attempts}/3).")
                    def hint_gen():
                        stream = get_professor_stream("hint", user_input=prompt, structure=st.session_state.current_structure)
                        for chunk in stream: yield chunk.text
                    new_hint = st.write_stream(hint_gen())
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ Incorrect. Hint: {new_hint}"})

# --- SUMMARY & END ---
elif st.session_state.game_stage == "summary":
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Continue"):
            st.session_state.attempts = 0; st.session_state.current_structure = None
            st.session_state.game_stage = "playing"; st.rerun()
    with c2:
        if st.button("🛑 End Game"): st.session_state.game_stage = "finished"; st.rerun()

elif st.session_state.game_stage == "finished":
    v_hash = generate_verification_hash(raw_id, st.session_state.total_marks)
    st.success("Session Completed!")
    st.code(f"ID: {raw_id} | Total Marks: {st.session_state.total_marks} | Hash: {v_hash}")
    if st.button("New Session"): st.session_state.clear(); st.rerun()
