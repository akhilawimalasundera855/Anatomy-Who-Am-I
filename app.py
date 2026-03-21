import streamlit as st
import requests
import time
import uuid
import random
import hashlib
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. INITIALIZATION ---
if "total_marks" not in st.session_state:
    st.session_state.total_marks = 0
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "current_structure" not in st.session_state:
    st.session_state.current_structure = None
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()
if "round_start_time" not in st.session_state:
    st.session_state.round_start_time = time.time()
if "game_stage" not in st.session_state:
    st.session_state.game_stage = "playing" 

# --- 2. CLOUD DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def log_to_cloud(data_dict):
    """Silently appends round data to the Google Sheet with collision protection."""
    try:
        time.sleep(random.uniform(0.1, 0.8))
        existing_data = conn.read(ttl=0) 
        new_row = pd.DataFrame([data_dict])
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(data=updated_df)
    except Exception as e:
        if st.session_state.get("is_admin"):
            st.sidebar.error(f"Database Sync Error: {e}")

# --- 3. RESEARCH UTILITIES ---
def generate_verification_hash(student_id, marks):
    raw_string = f"{student_id}-{marks}-{st.session_state.session_id}"
    hash_object = hashlib.sha256(raw_string.encode())
    return f"UOM-{hash_object.hexdigest()[:6].upper()}"

# --- 4. THE CLINICALLY INTELLIGENT ENGINE ---
def call_professor(prompt_type, user_input="", structure=""):
    difficulty = st.session_state.get('difficulty', 'Pre-clinical')
    # Fixed to match the singular 'GEMINI_API_KEY' usually used in secrets.toml
    api_keys = st.secrets["GEMINI_API_KEY"] 
    
    body_regions = ["Thorax", "Abdomen", "Pelvis", "Head and Neck", "Upper Limb", "Lower Limb", "Neuroanatomy", "Special Senses"]
    random_region = random.choice(body_regions)

    prompts = {
        "start": (f"You are a Senior Anatomy Professor. Select ONE anatomical structure from {random_region}. "
                  f"Provide 3 clues for {difficulty} level: Regional, Clinical, Surgical. [ANSWER: structure_name]"),
"verify": (f"Target: '{structure}'. Student Guess: '{user_input}'. "
                   "Role: You are a clinical anatomy examiner. "
                   "Task: Is the guess correct? Answer ONLY 'YES' or 'NO'. "
                   "GUIDELINES: "
                   "1. Be STRICT on location: If they guess a different structure in the same region, answer NO. "
                   "2. Be FLEXIBLE on nomenclature: Accept standard synonyms (e.g., 'Lens' or 'Eye lens' for 'Ocular lens'). "
                   "3. Be SMART on abbreviations: Accept 'Sciatic' for 'Sciatic Nerve' or 'Radial' for 'Radial artery'. "
                   "4. Reject vague answers: 'Nerve', 'Bone', or 'Artery' alone are always NO. "
                   "Answer ONLY 'YES' or 'NO'."),
        "hint": (f"The student guessed '{user_input}' for '{structure}' and was wrong. Provide ONE new specific clue."),
        "reveal": (f"The answer was {structure}. Provide a structured 'Educational Synthesis' for a {difficulty} level: "
                   "1. The Answer (with synonyms), 2. Synthesis of Clues, 3. A High-Yield Clinical Pearl.")
    }

    payload = {"contents": [{"role": "user", "parts": [{"text": prompts[prompt_type]}]}]}
    available_keys = list(api_keys)
    random.shuffle(available_keys)

    for key in available_keys:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={key}"
        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            if 'candidates' in data: 
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
        except: continue
    return "⚠️ Professor is busy. Please resubmit your guess."

# --- 5. SIDEBAR WITH RESEARCHER BACKDOOR ---
st.set_page_config(page_title="Anatomy Who Am I", page_icon="🧬", layout="centered")

with st.sidebar:
    st.title("🛡️ Research Portal")
    raw_id = st.text_input("University ID Number:", placeholder="e.g. 210XXX")
    st.session_state.is_admin = (raw_id == "ADMIN789")
    display_id = "RESEARCH_TEAM" if st.session_state.is_admin else raw_id
    st.session_state.difficulty = st.selectbox("Select Competency Level", ["Pre-clinical", "Clinical", "Post-graduate"])
    st.divider()
    st.metric(label="Current Session Marks", value=st.session_state.total_marks)
    
    if st.session_state.is_admin:
        st.warning("🕵️ Researcher Mode Active")
        try:
            full_db = conn.read(ttl=0)
            if not full_db.empty:
                master_csv_df = full_db.groupby(['Student_ID', 'Level']).agg({
                    'Marks': ['mean', 'sum', 'count'],
                    'Time_Seconds': 'mean'
                }).reset_index()
                master_csv_df.columns = ['Student_ID', 'Level', 'Avg_Score', 'Total_Marks', 'Total_Questions', 'Avg_Time_Per_Round']
                csv_data = master_csv_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Master Research Data", data=csv_data, file_name="Research_Master.csv", mime="text/csv")
        except: st.error("Cloud Database unreachable.")
    if st.button("♻️ Reset Session"): st.session_state.clear(); st.rerun()

# --- 6. INTERFACE & GAME LOGIC ---
st.title("🧬 Anatomy: Who Am I?")
if not raw_id: st.info("👋 Please enter your ID to begin."); st.stop()

if st.session_state.game_stage != "finished":
    if not st.session_state.messages:
        with st.spinner("Selecting structure..."):
            full_res = call_professor("start")
            if "[ANSWER:" in full_res:
                st.session_state.current_structure = full_res.split("[ANSWER:")[1].split("]")[0].strip()
                st.session_state.messages.append({"role": "assistant", "content": full_res.split("[ANSWER:")[0].strip()})
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

# --- 7. PLAYING LOGIC & CLOUD LOGGING ---
if st.session_state.game_stage == "playing":
    if prompt := st.chat_input("Enter your anatomical guess..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            is_correct_raw = call_professor("verify", user_input=prompt, structure=st.session_state.current_structure)
            
            if "YES" in is_correct_raw.upper() and "NO" not in is_correct_raw.upper():
                marks_earned = [30, 20, 10][st.session_state.attempts]
                round_time = int(time.time() - st.session_state.round_start_time)
                log_to_cloud({"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Student_ID": display_id, "Level": st.session_state.difficulty, "Structure": st.session_state.current_structure, "Result": "Correct", "Attempts": st.session_state.attempts + 1, "Marks": marks_earned, "Time_Seconds": round_time, "Session_ID": st.session_state.session_id})
                st.session_state.total_marks += marks_earned
                st.success(f"✅ CORRECT! ({marks_earned} marks)")
                st.balloons()
                explanation = call_professor("reveal", structure=st.session_state.current_structure)
                st.markdown(explanation)
                st.session_state.messages.append({"role": "assistant", "content": f"✅ CORRECT! {explanation}"})
                st.session_state.game_stage = "summary"; st.rerun()
            elif "NO" in is_correct_raw.upper():
                if st.session_state.attempts >= 2:
                    round_time = int(time.time() - st.session_state.round_start_time)
                    log_to_cloud({"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Student_ID": display_id, "Level": st.session_state.difficulty, "Structure": st.session_state.current_structure, "Result": "Failed", "Attempts": 3, "Marks": 0, "Time_Seconds": round_time, "Session_ID": st.session_state.session_id})
                    st.error(f"❌ Failed. Target: {st.session_state.current_structure}")
                    explanation = call_professor("reveal", structure=st.session_state.current_structure)
                    st.markdown(explanation)
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ FAILED. {explanation}"})
                    st.session_state.game_stage = "summary"; st.rerun()
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
            st.session_state.messages = []; st.session_state.attempts = 0
            st.session_state.game_stage = "playing"; st.session_state.round_start_time = time.time(); st.rerun()
    with col2:
        if st.button("🛑 End Game"):
            st.session_state.game_stage = "finished"; st.rerun()

elif st.session_state.game_stage == "finished":
    v_hash = generate_verification_hash(display_id, st.session_state.total_marks)
    st.success("Session Completed!"); st.subheader("🏁 Performance Record")
    st.code(f"ID: {display_id} | Total Marks: {st.session_state.total_marks} | Hash: {v_hash}")
    st.info("📸 Please take a screenshot for your submission record.")
    if st.button("Start New Session"): st.session_state.clear(); st.rerun()
