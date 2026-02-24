import streamlit as st
from ai_orchestrator import run_protection_assistant

st.set_page_config(layout="wide")
st.title("⚡ LLM Protection Engineering Assistant")

user_input = st.text_area(
    "Enter Protection Check Request",
    placeholder="Example: Check CT adequacy for 40 MVA transformer, 400 kV, CT 800/1, fault 25 kA, 5P20"
)

if st.button("Run Protection Check"):

    result, explanation = run_protection_assistant(
        user_input,
        st.secrets["OPENAI_API_KEY"]
    )

    st.subheader("🔢 Deterministic Result")
    st.json(result)

    st.subheader("🧠 Engineering Interpretation")
    st.write(explanation)
