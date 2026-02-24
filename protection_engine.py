import math


def check_ct_adequacy(ct_ratio, mva, voltage_kv, fault_ka, accuracy_class="5P20"):
    primary, secondary = map(int, ct_ratio.split("/"))

    I_fl = (mva * 1e6) / (math.sqrt(3) * voltage_kv * 1e3)
    I_fault = fault_ka * 1000
    I_sec_fault = I_fault / (primary / secondary)

    if "5P" in accuracy_class:
        ALF = int(accuracy_class.replace("5P", ""))
    else:
        ALF = 10

    I_limit = ALF * secondary
    adequate = I_sec_fault <= I_limit

    return {
        "ifl": round(I_fl, 2),
        "if_sec": round(I_sec_fault, 2),
        "limit": I_limit,
        "adequate": adequate
    }


def ref_areva_calc(ct_ratio, earth_fault_ka, r_ct, r_lead, r_relay, vk_available):
    primary, secondary = map(int, ct_ratio.split("/"))
    I_fault_sec = (earth_fault_ka * 1000) / (primary / secondary)

    R_total = r_ct + r_lead + r_relay
    Vk_required = 2 * I_fault_sec * R_total

    return {
        "if_sec": round(I_fault_sec, 2),
        "vk_required": round(Vk_required, 2),
        "stable": vk_available >= Vk_required
    }


def bus_diff_check(i_diff, i_restraint, pickup, slope):
    threshold = pickup + (slope / 100) * i_restraint
    operate = i_diff > threshold

    return {
        "threshold": round(threshold, 2),
        "operate": operate
    }
