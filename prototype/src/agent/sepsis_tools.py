"""
Simulated Agent Tools for Sepsis Clinical Triage

Analogous to the loan tools but for clinical decisions.
"""

from langchain_core.tools import tool


@tool
def lookup_treatment_protocol(age: float, infection_suspected: bool) -> str:
    """Look up the applicable treatment protocol for a sepsis patient.

    Args:
        age: Patient age in years.
        infection_suspected: Whether infection is suspected.
    """
    if age >= 75 and infection_suspected:
        return (
            "PROTOCOL: High-risk elderly patient with suspected infection. "
            "Immediate IV antibiotics recommended. ICU admission threshold: low. "
            "Frequent lab monitoring (Leucocytes, CRP, LacticAcid) required. "
            "Expected stay: 5-14 days. Close monitoring for organ dysfunction."
        )
    elif infection_suspected:
        return (
            "PROTOCOL: Suspected infection. Standard sepsis pathway. "
            "IV antibiotics within 1 hour of triage. Lab work required. "
            "Monitor SIRS criteria. Escalate to ICU if organ dysfunction develops. "
            "Expected stay: 3-7 days."
        )
    elif age >= 75:
        return (
            "PROTOCOL: Elderly patient, no infection suspected. "
            "Standard observation protocol. Lab work as indicated. "
            "Monitor for secondary infection. "
            "Expected stay: 2-5 days."
        )
    else:
        return (
            "PROTOCOL: Standard assessment. Monitor vitals and lab values. "
            "Administer treatment as indicated by diagnosis. "
            "Expected stay: 1-3 days."
        )


@tool
def check_clinical_indicators(
    sirs_criteria: bool, hypotension: bool, organ_dysfunction: bool, lab_test_count: int
) -> str:
    """Check clinical severity indicators for a sepsis patient.

    Args:
        sirs_criteria: Whether patient meets 2 or more SIRS criteria.
        hypotension: Whether patient has hypotension.
        organ_dysfunction: Whether organ dysfunction is present.
        lab_test_count: Number of lab tests performed.
    """
    severity_flags = []
    if sirs_criteria:
        severity_flags.append("SIRS criteria met (2+)")
    if hypotension:
        severity_flags.append("HYPOTENSION detected — hemodynamic instability")
    if organ_dysfunction:
        severity_flags.append("ORGAN DYSFUNCTION — septic shock risk")

    if not severity_flags:
        status = "LOW SEVERITY: No critical flags. Standard care pathway appropriate."
    elif len(severity_flags) == 1:
        status = "MODERATE SEVERITY: One critical flag detected. Enhanced monitoring."
    else:
        status = "HIGH SEVERITY: Multiple critical flags. ICU assessment recommended."

    lab_status = f"Lab tests performed: {lab_test_count}. "
    if lab_test_count < 3:
        lab_status += "Insufficient lab data — additional tests recommended."
    elif lab_test_count > 10:
        lab_status += "Extensive testing performed — comprehensive data available."
    else:
        lab_status += "Adequate lab monitoring."

    return f"CLINICAL ASSESSMENT:\n{status}\nFlags: {', '.join(severity_flags) if severity_flags else 'None'}\n{lab_status}"


@tool
def calculate_patient_risk_score(
    age: float, num_events: int, has_antibiotics: bool,
    case_duration_hours: float, lab_test_count: int
) -> str:
    """Calculate a clinical risk score for the patient.

    Args:
        age: Patient age in years.
        num_events: Total number of clinical events.
        has_antibiotics: Whether IV antibiotics were administered.
        case_duration_hours: Total treatment duration in hours.
        lab_test_count: Number of lab tests performed.
    """
    score = 30  # Start baseline

    # Age factor
    if age >= 80:
        score += 25
    elif age >= 70:
        score += 15
    elif age >= 60:
        score += 10

    # Treatment intensity
    if has_antibiotics:
        score += 10  # Indicates serious infection
    if lab_test_count > 8:
        score += 10  # Many tests = complex case

    # Duration factor
    if case_duration_hours > 200:
        score += 15  # Long stay = complications
    elif case_duration_hours < 24:
        score -= 10  # Quick resolution

    # Event count
    if num_events > 20:
        score += 10

    score = max(0, min(100, score))
    risk_level = "LOW" if score < 35 else "MEDIUM" if score < 65 else "HIGH"

    return (
        f"RISK SCORE: {score}/100 ({risk_level})\n"
        f"Factors: age={age:.0f}, events={num_events}, antibiotics={'yes' if has_antibiotics else 'no'}, "
        f"duration={case_duration_hours:.0f}h, labs={lab_test_count}\n"
        f"Recommendation: {'Discharge likely appropriate' if score < 35 else 'Monitor closely before discharge' if score < 65 else 'Extended care / ICU evaluation recommended'}"
    )


ALL_SEPSIS_TOOLS = [lookup_treatment_protocol, check_clinical_indicators, calculate_patient_risk_score]
