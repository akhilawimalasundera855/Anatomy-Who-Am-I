import streamlit as st
import requests
import time
import uuid
import random
import hashlib
from datetime import datetime

# --- 1. RESEARCH STATE INITIALIZATION ---
if "total_marks" not in st.session_state: st.session_state.total_marks = 0
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "session_id" not in st.session_state: st.session_state.session_id = str(uuid.uuid4())[:8]
if "current_structure" not in st.session_state: st.session_state.current_structure = None
if "round_start_time" not in st.session_state: st.session_state.round_start_time = time.time()
if "game_stage" not in st.session_state: st.session_state.game_stage = "playing"

# --- 2. RESEARCH UTILITIES (RETAINED) ---
def generate_verification_hash(student_id, marks):
    """Generates the unique research code at the end of the session."""
    raw_string = f"{student_id}-{marks}-{st.session_state.session_id}"
    hash_object = hashlib.sha256(raw_string.encode())
    return f"UOM-{hash_object.hexdigest()[:6].upper()}"

# --- 3. PERFECT KEY ROTATOR & AI ENGINE ---
def call_professor(prompt_type, user_input="", structure=""):
    difficulty = st.session_state.get('difficulty', 'Pre-clinical')
    
    # Retrieves KEY1, KEY2, KEY3 from Streamlit Secrets
    key_names = ["KEY1", "KEY2", "KEY3"]
    available_keys = [st.secrets[k] for k in key_names if k in st.secrets]
    random.shuffle(available_keys) # Ensures balanced load across your accounts

    body_regions = ["Thorax", "Abdomen", "Pelvis", "Head and Neck", "Upper Limb", "Lower Limb", "Neuroanatomy", "Special Senses"]
    random_region = random.choice(body_regions)

    prompts = {
        "start": (f"You are a Senior Anatomy Professor. Select ONE anatomical structure from {random_region}. "
                  f"Provide 3 clues for {difficulty} level: Regional, Clinical, Surgical. [ANSWER: structure_name]"),
        "verify": (f"Target: '{structure}'. Student Guess: '{user_input}'. "
                   "Role: You are a clinical anatomy examiner. "
                   "Task: Is the guess correct? Answer ONLY 'YES' or 'NO'. "
                   "GUIDELINES: 1. Be STRICT on location. 2. Be FLEXIBLE on synonyms. 3. Accept common abbreviations. 4. Reject vague answers."),
        "hint": (f"The student guessed '{user_input}' for '{structure}' and was wrong. Provide ONE new specific clue."),
        "reveal": (f"The answer was {structure}. Provide a structured 'Educational Synthesis' for a {difficulty} level: "
                   "1. The Answer (with synonyms), 2. Synthesis of Clues, 3. A High-Yield Clinical Pearl.")
    }

    payload = {"contents": [{"role": "user", "parts": [{"text": prompts[prompt_type]}]}]}

    # ROTATION LOGIC: Try every key until one succeeds
# ADVANCED ROTATION: Try every key up to 2 times with a slight delay if busy
    # This spreads the 13 students across the 1-minute quota window.
    for attempt in range(len(available_keys) * 2):
        key = available_keys[attempt % len(available_keys)]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={key}"
        
        try:
            response = requests.post(url, json=payload, timeout=12)
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
            elif response.status_code == 429:
                # Key is busy. Wait 1.5 seconds and try a different key.
                time.sleep(1.5)
                continue
        except Exception:
            continue
            
    return "The Professor is currently overwhelmed by students. Please wait 10 seconds and resubmit your guess."
# --- 4. SIDEBAR & RESEARCH PORTAL ---
st.set_page_config(page_title="Anatomy Who Am I", page_icon="🧬", layout="centered")

with st.sidebar:
    st.title("🛡️ Research Portal")
    raw_id = st.text_input("University ID Number:", placeholder="e.g. 210XXX")
    st.session_state.is_admin = (raw_id == "ADMIN789")
    display_id = "RESEARCH_TEAM" if st.session_state.is_admin else raw_id
    st.session_state.difficulty = st.selectbox("Select Competency Level", ["Pre-clinical", "Clinical", "Post-graduate"])
    st.divider()
    st.metric(label="Current Session Marks", value=st.session_state.total_marks)
    
    if st.button("♻️ Reset Session"): 
        st.session_state.clear()
        st.rerun()

# --- 5. INTERFACE & CORE GAME LOGIC ---
st.title("🧬 Anatomy: Who Am I?")

if not raw_id:
    st.info("👋 Please enter your ID in the sidebar to begin.")
    st.stop()

# STAGE: START ROUND
if st.session_state.game_stage != "finished":
    if not st.session_state.messages:
        with st.spinner("Professor is selecting a structure..."):
            full_res = call_professor("start")
            if "[ANSWER:" in full_res:
                st.session_state.current_structure = full_res.split("[ANSWER:")[1].split("]")[0].strip()
                st.session_state.messages.append({"role": "assistant", "content": full_res.split("[ANSWER:")[0].strip()})
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

# STAGE: PLAYING
if st.session_state.game_stage == "playing":
    if prompt := st.chat_input("Enter your anatomical guess..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Verifying..."):
                is_correct_raw = call_professor("verify", user_input=prompt, structure=st.session_state.current_structure)
            
            if "YES" in is_correct_raw.upper() and "NO" not in is_correct_raw.upper():
                # Original marks logic: 30 for 1st try, 20 for 2nd, 10 for 3rd
                marks_earned = [30, 20, 10][min(st.session_state.attempts, 2)]
                st.session_state.total_marks += marks_earned
                st.success(f"✅ CORRECT! (+{marks_earned} marks)")
                st.balloons()
                
                explanation = call_professor("reveal", structure=st.session_state.current_structure)
                st.markdown(explanation)
                st.session_state.messages.append({"role": "assistant", "content": f"✅ CORRECT! {explanation}"})
                st.session_state.game_stage = "summary"
                st.rerun()
                
            else:
                if st.session_state.attempts >= 2:
                    st.error(f"❌ Failed. The structure was the **{st.session_state.current_structure}**.")
                    explanation = call_professor("reveal", structure=st.session_state.current_structure)
                    st.markdown(explanation)
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ FAILED. {explanation}"})
                    st.session_state.game_stage = "summary"
                    st.rerun()
                else:
                    st.session_state.attempts += 1
                    new_hint = call_professor("hint", user_input=prompt, structure=st.session_state.current_structure)
                    st.error(f"❌ Incorrect ({st.session_state.attempts}/3).")
                    st.info(f"💡 Hint: {new_hint}")
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ Incorrect. Hint: {new_hint}"})

# STAGE: SUMMARY
elif st.session_state.game_stage == "summary":
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Continue Playing"):
            st.session_state.messages = []
            st.session_state.attempts = 0
            st.session_state.current_structure = None
            st.session_state.game_stage = "playing"
            st.session_state.round_start_time = time.time()
            st.rerun()
    with col2:
        if st.button("🛑 End Game"):
            st.session_state.game_stage = "finished"
            st.rerun()

# STAGE: FINISHED
elif st.session_state.game_stage == "finished":
    v_hash = generate_verification_hash(display_id, st.session_state.total_marks)
    st.success("Session Completed!")
    st.subheader("🏁 Performance Record")
    st.code(f"ID: {display_id} | Total Marks: {st.session_state.total_marks} | Hash: {v_hash}")
    st.info("📸 Please take a screenshot for your evaluation record.")
    if st.button("Start New Session"):
        st.session_state.clear()
        st.rerun()
