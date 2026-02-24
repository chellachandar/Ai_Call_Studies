import streamlit as st
import time
from ai_orchestrator import run_protection_assistant

st.set_page_config(page_title="Gemini Protection Assistant", layout="wide")
st.title("⚡ Protection Engineering Assistant")

# Check if we are in a cooldown period
if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0

user_input = st.text_area("Engineering Request", placeholder="Describe your CT, REF, or Bus Diff task...")

if st.button("Run Analysis"):
    current_time = time.time()
    
    # Simple rate limiting on the UI side (6 seconds between clicks)
    if current_time - st.session_state.last_request_time < 6:
        st.error("Slow down! Please wait a few seconds between requests to respect API limits.")
    else:
        st.session_state.last_request_time = current_time
        
        with st.spinner("Consulting Gemini AI..."):
            result, explanation = run_protection_assistant(
                user_input,
                st.secrets["GEMINI_API_KEY"]
            )

        if "ERROR" in result:
            st.error(f"System Busy: {result['ERROR']}")
            st.info(explanation)
        else:
            st.success("Analysis Complete")
            c1, c2 = st.columns(2)
            c1.json(result)
            c2.markdown(explanation)
