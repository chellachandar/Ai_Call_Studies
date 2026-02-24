import json
import google.generativeai as genai
from protection_engine import (
    check_ct_adequacy,
    ref_areva_calc,
    bus_diff_check
)

def clean_json_response(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return text.strip()

def normalize_params(params):
    """Normalizes keys and ensures values are numeric where expected."""
    mapping = {
        "mva_transformer": "mva", "transformer_mva": "mva", "rated_mva": "mva",
        "voltage": "voltage_kv", "kv": "voltage_kv",
        "fault_level": "fault_ka", "fault_current": "fault_ka"
    }
    
    normalized = {}
    for key, value in params.items():
        norm_key = mapping.get(key, key)
        # Convert string numbers to float/int to avoid math errors in protection_engine
        if isinstance(value, str) and value.replace('.', '', 1).isdigit():
            normalized[norm_key] = float(value) if '.' in value else int(value)
        else:
            normalized[norm_key] = value
    return normalized

def run_protection_assistant(user_input, api_key):
    genai.configure(api_key=api_key)
    # FIX: Updated to a valid model name
    model = genai.GenerativeModel("gemini-2.0-flash") 

    extraction_prompt = f"""
    You are a protection engineering assistant. Extract structured data.
    Return ONLY valid JSON. 
    Allowed check_type: "ct", "ref", "bus"
    User request: {user_input}
    """

    extraction_response = model.generate_content(extraction_prompt)
    raw_text = clean_json_response(extraction_response.text)

    try:
        extracted = json.loads(raw_text)
    except Exception:
        return {"ERROR": "JSON extraction failed"}, "Could not parse parameters."

    check_type = extracted.get("check_type")
    # Normalize keys AND types
    params = normalize_params(extracted.get("parameters", {}))

    try:
        if check_type == "ct":
            required = ["ct_ratio", "mva", "voltage_kv", "fault_ka"]
            if not all(k in params for k in required):
                return {"ERROR": "Missing parameters"}, "Need: ct_ratio, mva, voltage_kv, fault_ka"
            result = check_ct_adequacy(**params)

        elif check_type == "ref":
            result = ref_areva_calc(**params)

        elif check_type == "bus":
            result = bus_diff_check(**params)
        else:
            return {"ERROR": "Unknown type"}, "Invalid protection type."

    except Exception as e:
        return {"ERROR": f"Engine Error: {str(e)}"}, "The math engine failed to process the extracted data."

    explanation_prompt = f"Senior Engineer: Interpret these results for a user. Result: {result}. Input: {user_input}. Do not change numbers."
    explanation_response = model.generate_content(explanation_prompt)

    return result, explanation_response.text
