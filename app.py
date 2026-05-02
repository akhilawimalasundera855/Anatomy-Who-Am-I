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

# --- 2. RESEARCH UTILITIES ---
def generate_verification_hash(student_id, marks):
    raw_string = f"{student_id}-{marks}-{st.session_state.session_id}"
    hash_object = hashlib.sha256(raw_string.encode())
    return f"UOM-{hash_object.hexdigest()[:6].upper()}"


# --- 3. ROBUST AI ENGINE (ADAPTIVE PROFESSOR v7.0) ---
def call_professor(prompt_type, user_input="", structure="", is_first=False):
    difficulty = st.session_state.get('difficulty', 'Pre-clinical')
    
    # Flexible Key Retrieval
    all_keys = []
    if "GEMINI_API_KEY" in st.secrets:
        val = st.secrets["GEMINI_API_KEY"]
        all_keys = list(val) if isinstance(val, list) else [val]
    for k in ["KEY1", "KEY2", "KEY3", "KEY4"]:
        if k in st.secrets: all_keys.append(st.secrets[k])
    
    if not all_keys:
        return "❌ ERROR: No API keys found in Streamlit Secrets."

    body_regions = ["Thorax", "Abdomen", "Pelvis", "Head and Neck", "Upper Limb", "Lower Limb", "Neuroanatomy", "Special Senses"]
    random_region = random.choice(body_regions)

    # Master Persona: Friendly but Strict Senior Professor
    PERSONA = (
        "You are a Senior Clinical Anatomy Professor. Your demeanor is friendly, encouraging, and professional, "
        "yet you remain a strict academic examiner[cite: 9]. You value precise deductive reasoning and high-end clinical relevance."
    )

    # Gameplay Explanation (Only for the first round)
    intro_logic = ""
    if is_first:
        intro_logic = (
            "This is the student's first game. Briefly and warmly welcome them to 'Anatomy: Who Am I?' game session "
            "Explain that you will provide three clues, and they have three attempts to guess the structure. "
            "Encourage them to think clinically before you begin. "
        )

    prompts = {
        "start": (f"{PERSONA} {intro_logic} "
                  f"INTERNAL SELECTION (SECRET): Select ONE high-yield anatomical structure from the {random_region}[cite: 9]. "
                  f"Provide 3 high-end academic clues for {difficulty} level exactly under these subheadings: "
                  f"### **Regional anatomy**\n### **clinical anatomy**\n### **Surgical anatomy**\n"
                  f"CRITICAL: Do NOT reveal the region name or structure name yet. "
                  f"Format: [Clues Text] [ANSWER: structure_name]"),
        
        "verify": (f"{PERSONA} Target: '{structure}'. Student Guess: '{user_input}'. "
                   f"Evaluation Logic: You MUST accept the answer if: "
                   f"1. It is the standard abbreviated form (e.g., 'IJV' for Internal Jugular Vein). "
                   f"2. It contains minor spelling errors (1-2 letters changed). "
                   f"3. It is missing descriptive terms like 'artery', 'muscle', 'tendon', or 'nerve' but the core name is correct (e.g., 'Supraspinatus' for Supraspinatus Tendon). "
                   f"Respond ONLY with 'YES' if it meets these criteria, otherwise 'NO'."),
        
        "hint": (f"{PERSONA} The student guessed '{user_input}' for '{structure}' and was wrong. "
                 f"Provide ONE NEW specific and anatomically accurate 'Blind Hint' in your friendly, academic tone. "
                 f"DO NOT repeat previous clues or name the target/region."),
        
        "reveal": (f"{PERSONA} The answer was '{structure}'. Provide a structured 'Educational Synthesis'[cite: 4, 9]: "
                   f"1. The Formal Identification (acknowledge if their shorthand/spelling was close but provide the full standard name). "
                   f"2. A 2-3 sentence 'High-Yield Clinical Pearl'[cite: 4, 9].")
    }

    payload = {"contents": [{"role": "user", "parts": [{"text": prompts[prompt_type]}]}]}

    random.shuffle(all_keys)
    for key in all_keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={key}"
        try:
            response = requests.post(url, json=payload, timeout=12)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            elif response.status_code == 429:
                continue 
        except:
            continue
            
    return "Professor is currently overwhelmed. Please wait 5 seconds and click the button again."

# --- 4. SIDEBAR & RESEARCH PORTAL ---
st.set_page_config(page_title="Anatomy Who Am I", page_icon="🧬", layout="centered")

with st.sidebar:
    st.title("🛡️ Research Portal")
    raw_id = st.text_input("University ID Number:", placeholder="e.g. 210XXX")
    st.session_state.difficulty = st.selectbox("Select Competency Level", ["Pre-clinical", "Clinical", "Post-graduate"])
    st.divider()
    st.metric(label="Current Session Marks", value=st.session_state.total_marks)
    if st.button("♻️ Reset Session"): st.session_state.clear(); st.rerun()

# --- 5. INTERFACE & CORE GAMEPLAY ---
st.title("🧬 Anatomy: Who Am I?")

if not raw_id:
    st.info("👋 Please enter your ID in the sidebar to begin.")
    st.stop()


# STAGE: INITIALIZATION
if st.session_state.game_stage == "playing" and st.session_state.current_structure is None:
    time.sleep(random.uniform(0.5, 2.5))
    with st.spinner("Professor is preparing your clues..."):
        # Pass the first_round flag to the professor
        full_res = call_professor("start", is_first=st.session_state.is_first_round)
        
        if "[ANSWER:" in full_res:
            st.session_state.current_structure = full_res.split("[ANSWER:")[1].split("]")[0].strip()
            st.session_state.messages.append({"role": "assistant", "content": full_res.split("[ANSWER:")[0].strip()})
            # Flip the flag so the intro only happens once
            st.session_state.is_first_round = False 
        else:
            st.error(full_res)
            if st.button("Retry Clue Generation"): st.rerun()

# DISPLAY MESSAGES
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# STAGE: GUESSING
if st.session_state.game_stage == "playing" and st.session_state.current_structure:
    if prompt := st.chat_input("Enter your anatomical guess..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Verifying..."):
                is_correct_raw = call_professor("verify", user_input=prompt, structure=st.session_state.current_structure)
            
            if "YES" in is_correct_raw.upper() and "NO" not in is_correct_raw.upper():
                # Weighted Scoring: 30, 20, 10 marks
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
                    st.error(f"❌ Failed. Target: {st.session_state.current_structure}")
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

elif st.session_state.game_stage == "finished":
    v_hash = generate_verification_hash(raw_id, st.session_state.total_marks)
    st.success("Session Completed!")
    st.subheader("🏁 Performance Record")
    st.code(f"ID: {raw_id} | Total Marks: {st.session_state.total_marks} | Hash: {v_hash}")
    st.info("📸 Please take a screenshot for your evaluation record.")
    if st.button("Start New Session"):
        st.session_state.clear()
        st.rerun()
