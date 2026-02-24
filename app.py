import streamlit as st
from ai_orchestrator import run_protection_assistant

st.set_page_config(layout="wide")
st.title("⚡ Gemini Protection Engineering Assistant")

st.write("One protection check per prompt.")

user_input = st.text_area(
    "Enter Protection Request",
    placeholder="Example: Check CT adequacy for 40 MVA transformer at 400 kV using 800/1 CT and 25 kA fault, 5P20 class."
)

if st.button("Run Protection Check"):

    if not user_input.strip():
        st.warning("Please enter a request.")
        st.stop()

    result, explanation = run_protection_assistant(
        user_input,
        st.secrets["GEMINI_API_KEY"]
    )

    st.subheader("🔢 Deterministic Result")
    st.json(result)

    st.subheader("🧠 Engineering Interpretation")
    st.write(explanation)
