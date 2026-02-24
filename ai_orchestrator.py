import json
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core import exceptions
from protection_engine import check_ct_adequacy, ref_areva_calc, bus_diff_check

@retry(
    retry=retry_if_exception_type(exceptions.ResourceExhausted),
    wait=wait_exponential(multiplier=2, min=5, max=15), # Increased wait time
    stop=stop_after_attempt(2) # Reduced attempts to fail faster and save quota
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
    mapping = {
        "mva_transformer": "mva", "transformer_mva": "mva", "rated_mva": "mva",
        "voltage": "voltage_kv", "kv": "voltage_kv",
        "fault_level": "fault_ka", "fault_current": "fault_ka"
    }
    normalized = {}
    for key, value in params.items():
        norm_key = mapping.get(key, key)
        if isinstance(value, str) and value.replace('.', '', 1).isdigit():
            normalized[norm_key] = float(value) if '.' in value else int(value)
        else:
            normalized[norm_key] = value
    return normalized

def run_protection_assistant(user_input, api_key):
    genai.configure(api_key=api_key)
    # Using 1.5-flash as it is more stable for high-volume free tier requests
    model = genai.GenerativeModel("gemini-1.5-flash") 

    orchestration_prompt = f"""
    Extract parameters for protection study.
    Request: "{user_input}"
    Return ONLY JSON:
    {{"check_type": "ct"|"ref"|"bus", "parameters": {{...}}, "overview": "short note"}}
    """

    try:
        response = call_gemini(model, orchestration_prompt)
        raw_data = json.loads(clean_json_response(response.text))
    except Exception as e:
        # Catching the RetryError specifically
        return {"ERROR": "Quota Limit"}, "The AI service is currently overloaded. Please wait 60 seconds."

    check_type = raw_data.get("check_type")
    params = normalize_params(raw_data.get("parameters", {}))
    overview = raw_data.get("overview", "Analysis complete.")

    try:
        if check_type == "ct":
            result = check_ct_adequacy(**params)
            status = "Adequate" if result['adequate'] else "Inadequate"
        elif check_type == "ref":
            result = ref_areva_calc(**params)
            status = "Stable" if result['stable'] else "Unstable"
        elif check_type == "bus":
            result = bus_diff_check(**params)
            status = "Operate" if result['operate'] else "Restrain"
        else:
            return {"ERROR": "Logic Error"}, "Unknown protection type extracted."
    except Exception as e:
        return {"ERROR": "Math Error"}, f"Missing or invalid parameters: {str(e)}"

    return result, f"**Overview:** {overview}\n\n**Result:** {status}"
