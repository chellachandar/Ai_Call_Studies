import json
import google.generativeai as genai
from protection_engine import (
    check_ct_adequacy,
    ref_areva_calc,
    bus_diff_check
)

def run_protection_assistant(user_input, api_key):

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("models/gemini-2.5-flash")

    # Step 1 — Ask Gemini to extract structured data
    extraction_prompt = f"""
You are a protection engineering assistant.

From the following user request, identify:
- which protection check is required (ct, ref, or bus)
- all numerical parameters needed

Return ONLY valid JSON in this format:

{{
  "check_type": "ct/ref/bus",
  "parameters": {{ ... }}
}}

User request:
{user_input}
"""

    extraction_response = model.generate_content(extraction_prompt)

    try:
        extracted = json.loads(extraction_response.text)
    except:
        return None, "Could not extract structured parameters."

    check_type = extracted["check_type"]
    params = extracted["parameters"]

    # Step 2 — Run deterministic engine
    if check_type == "ct":
        result = check_ct_adequacy(**params)

    elif check_type == "ref":
        result = ref_areva_calc(**params)

    elif check_type == "bus":
        result = bus_diff_check(**params)

    else:
        return None, "Unknown protection type."

    # Step 3 — Ask Gemini to explain deterministic result
    explanation_prompt = f"""
You are a senior protection engineer.

User request:
{user_input}

Deterministic result:
{result}

Interpret results.
Do NOT recalculate.
Do NOT modify values.
Only provide engineering explanation.
"""

    explanation = model.generate_content(explanation_prompt)

    return result, explanation.text
