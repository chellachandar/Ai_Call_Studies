import streamlit as st
from ai_orchestrator import run_protection_assistant

st.set_page_config(page_title="Gemini Protection Assistant", layout="wide")
st.title("⚡ Gemini Protection Engineering Assistant")

st.info("Calculations are performed deterministically; AI is used for parameter extraction and context.")

user_input = st.text_area(
    "Enter Protection Request",
    placeholder="Example: 40 MVA, 400kV transformer. 800/1 CT, 25kA fault level. Is the CT adequate?"
)

if st.button("Run Analysis"):
    if not user_input.strip():
        st.warning("Please provide technical details.")
        st.stop()

    with st.spinner("Analyzing with Gemini..."):
        result, explanation = run_protection_assistant(
            user_input,
            st.secrets["GEMINI_API_KEY"]
        )

    if "ERROR" in result:
        st.error(f"Error: {result['ERROR']}")
        st.write(explanation)
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔢 Calculated Data")
            st.json(result)
        with col2:
            st.subheader("🧠 Engineering Interpretation")
            st.write(explanation)
