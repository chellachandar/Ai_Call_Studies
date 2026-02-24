import json
from openai import OpenAI
from protection_engine import (
    check_ct_adequacy,
    ref_areva_calc,
    bus_diff_check
)

def run_protection_assistant(user_input, api_key):

    client = OpenAI(api_key=api_key)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "check_ct_adequacy",
                "description": "CT adequacy check",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ct_ratio": {"type": "string"},
                        "mva": {"type": "number"},
                        "voltage_kv": {"type": "number"},
                        "fault_ka": {"type": "number"},
                        "accuracy_class": {"type": "string"}
                    },
                    "required": ["ct_ratio","mva","voltage_kv","fault_ka"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "ref_areva_calc",
                "description": "AREVA high impedance REF check",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ct_ratio": {"type": "string"},
                        "earth_fault_ka": {"type": "number"},
                        "r_ct": {"type": "number"},
                        "r_lead": {"type": "number"},
                        "r_relay": {"type": "number"},
                        "vk_available": {"type": "number"}
                    },
                    "required": ["ct_ratio","earth_fault_ka","r_ct","r_lead","r_relay","vk_available"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "bus_diff_check",
                "description": "Busbar differential bias check",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "i_diff": {"type": "number"},
                        "i_restraint": {"type": "number"},
                        "pickup": {"type": "number"},
                        "slope": {"type": "number"}
                    },
                    "required": ["i_diff","i_restraint","pickup","slope"]
                }
            }
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":user_input}],
        tools=tools,
        tool_choice="auto",
        temperature=0
    )

    message = response.choices[0].message

    if message.tool_calls:

        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        # Run deterministic function
        if function_name == "check_ct_adequacy":
            result = check_ct_adequacy(**arguments)

        elif function_name == "ref_areva_calc":
            result = ref_areva_calc(**arguments)

        elif function_name == "bus_diff_check":
            result = bus_diff_check(**arguments)

        # Send result back for explanation
        explanation = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You are a senior protection engineer. Interpret results. Do not recalculate."},
                {"role":"user","content":f"User Request: {user_input}"},
                {"role":"assistant","content":f"Deterministic Result: {result}"}
            ],
            temperature=0.2
        )

        return result, explanation.choices[0].message.content

    return None, "Could not determine required protection check."
