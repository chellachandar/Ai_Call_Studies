import json
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core import exceptions
from protection_engine import (
    check_ct_adequacy,
    ref_areva_calc,
    bus_diff_check
)

# Retry logic to handle 429 Resource Exhausted errors
@retry(
    retry=retry_if_exception_type(exceptions.ResourceExhausted),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(3)
)
def call_gemini(model, prompt):
    return model.generate_content(prompt)

def clean_json_response(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return text.strip()

def normalize_params(params):
    """Map flexible naming to engine requirements and ensure numeric types."""
    mapping = {
        "mva_transformer": "mva", "transformer_mva": "mva", "rated_mva": "mva",
        "voltage": "voltage_kv", "kv": "voltage_kv",
        "fault_level": "fault_ka", "fault_current": "fault_ka"
    }
    normalized = {}
    for key, value in params.items():
        norm_key = mapping.get(key, key)
        # Convert string numbers to float/int for the math engine
        if isinstance(value, str) and value.replace('.', '', 1).isdigit():
            normalized[norm_key] = float(value) if '.' in value else int(value)
        else:
            normalized[norm_key] = value
    return normalized

def run_protection_assistant(user_input, api_key):
    genai.configure(api_key=api_key)
    # Using Gemini 2.0 Flash for speed and efficiency
    model = genai.GenerativeModel("gemini-2.0-flash") 

    # Consolidated Prompt: One call for extraction and initial engineering thoughts
    orchestration_prompt = f"""
    You are a Senior Protection Engineer. 
    1. Extract parameters from: "{user_input}"
    2. Provide a brief (2-sentence) professional overview of this protection type.

    Return ONLY a JSON object with this structure:
    {{
      "check_type": "ct" | "ref" | "bus",
      "parameters": {{ ... }},
      "overview": "Your engineering insight here"
    }}
    """

    try:
        response = call_gemini(model, orchestration_prompt)
        raw_data = json.loads(clean_json_response(response.text))
    except exceptions.ResourceExhausted:
        return {{"ERROR": "Quota Exceeded"}}, "The API rate limit was hit. Please try again in 30 seconds."
    except Exception as e:
        return {{"ERROR": "Extraction Failed"}}, f"Failed to parse request: {str(e)}"

    check_type = raw_data.get("check_type")
    params = normalize_params(raw_data.get("parameters", {}))
    overview = raw_data.get("overview", "Processing protection calculation...")

    # --- Deterministic Engine Execution ---
    try:
        if check_type == "ct":
            result = check_ct_adequacy(**params)
            status_text = "Adequate" if result['adequate'] else "Inadequate - Risk of Saturation"
        elif check_type == "ref":
            result = ref_areva_calc(**params)
            status_text = "Stable" if result['stable'] else "Unstable - Requires Higher Knee Point Voltage"
        elif check_type == "bus":
            result = bus_diff_check(**params)
            status_text = "Operate (Trip)" if result['operate'] else "Restrain (Normal)"
        else:
            return {{"ERROR": "Unknown Check"}}, "Unsupported protection type."
    except Exception as e:
        return {{"ERROR": "Calculation Error"}}, f"The engine failed: {str(e)}"

    # Final Interpretation
    final_explanation = f"**Engineering Overview:** {overview}\n\n**Status:** {status_text}"
    
    return result, final_explanation
