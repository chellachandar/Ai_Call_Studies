import json
import google.generativeai as genai
from protection_engine import (
    check_ct_adequacy,
    ref_areva_calc,
    bus_diff_check
)


# -------------------------
# JSON CLEANING
# -------------------------
def clean_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
    return text.strip()


# -------------------------
# PARAMETER NORMALIZATION
# -------------------------
def normalize_ct_params(params):
    mapping = {
        "mva_transformer": "mva",
        "transformer_mva": "mva",
        "rated_mva": "mva",
        "voltage": "voltage_kv",
        "kv": "voltage_kv",
        "fault_level": "fault_ka",
        "fault_current": "fault_ka"
    }

    normalized = {}
    for key, value in params.items():
        if key in mapping:
            normalized[mapping[key]] = value
        else:
            normalized[key] = value

    return normalized


def run_protection_assistant(user_input, api_key):

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    # -------------------------
    # STEP 1: STRUCTURED EXTRACTION
    # -------------------------
    extraction_prompt = f"""
You are a protection engineering assistant.

Extract structured data from the user request.

Return ONLY valid JSON.
No explanation.
No markdown.
No extra text.

Allowed check_type values:
- "ct"
- "ref"
- "bus"

Format:

{{
  "check_type": "ct",
  "parameters": {{ }}
}}

User request:
{user_input}
"""

    extraction_response = model.generate_content(extraction_prompt)
    raw_text = clean_json_response(extraction_response.text)

    try:
        extracted = json.loads(raw_text)
    except Exception:
        return {
            "ERROR": "JSON extraction failed",
            "model_output": raw_text
        }, "Could not extract structured parameters."

    check_type = extracted.get("check_type")
    params = extracted.get("parameters", {})

    # -------------------------
    # STEP 2: RUN ENGINE
    # -------------------------
    try:

        if check_type == "ct":

            params = normalize_ct_params(params)

            required = ["ct_ratio", "mva", "voltage_kv", "fault_ka"]
            for r in required:
                if r not in params:
                    return {"ERROR": f"Missing parameter: {r}"}, "Incomplete CT data."

            result = check_ct_adequacy(**params)

        elif check_type == "ref":

            required = ["ct_ratio", "earth_fault_ka", "r_ct", "r_lead", "r_relay", "vk_available"]
            for r in required:
                if r not in params:
                    return {"ERROR": f"Missing parameter: {r}"}, "Incomplete REF data."

            result = ref_areva_calc(**params)

        elif check_type == "bus":

            required = ["i_diff", "i_restraint", "pickup", "slope"]
            for r in required:
                if r not in params:
                    return {"ERROR": f"Missing parameter: {r}"}, "Incomplete Bus Diff data."

            result = bus_diff_check(**params)

        else:
            return {"ERROR": "Unknown protection type"}, "Invalid protection type."

    except Exception as e:
        return {"ERROR": str(e)}, "Deterministic engine failed."

    # -------------------------
    # STEP 3: ENGINEERING INTERPRETATION
    # -------------------------
    explanation_prompt = f"""
You are a senior protection engineer.

User request:
{user_input}

Deterministic result:
{result}

Interpret results professionally.
Do NOT recalculate.
Do NOT modify numeric values.
"""

    explanation_response = model.generate_content(explanation_prompt)

    return result, explanation_response.text
