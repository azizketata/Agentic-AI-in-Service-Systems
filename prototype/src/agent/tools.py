"""
Simulated Agent Tools

These tools return preprocessed BPI 2012 data, simulating real service system
interactions (credit checks, policy lookups, etc.) without external API calls.
This makes results reproducible for the paper.
"""

from langchain_core.tools import tool


@tool
def lookup_credit_policy(amount: float) -> str:
    """Look up the applicable credit policy for a given loan amount.

    Args:
        amount: The requested loan amount in EUR.
    """
    if amount <= 0:
        return "POLICY: Invalid amount. Loan amounts must be positive."
    elif amount <= 5000:
        return (
            "POLICY: Small personal loan. "
            "Auto-approval eligible. Minimal documentation required. "
            "Standard interest rate applies. No collateral needed."
        )
    elif amount <= 25000:
        return (
            "POLICY: Standard personal loan. "
            "Requires income verification and credit check. "
            "Offer must be created and sent to applicant. "
            "Applicant must accept offer before approval. "
            "Processing time: 5-15 business days."
        )
    elif amount <= 50000:
        return (
            "POLICY: High-value personal loan. "
            "Requires comprehensive financial review. "
            "Senior credit officer must review. "
            "Collateral assessment may be required. "
            "Multiple offers may be generated for comparison. "
            "Processing time: 15-30 business days."
        )
    else:
        return (
            "POLICY: Amount exceeds personal loan ceiling of EUR 50,000. "
            "Application should be declined or redirected to commercial lending."
        )


@tool
def check_application_completeness(
    num_events: int, num_offers: int, amount: float
) -> str:
    """Check if the loan application has sufficient process completeness.

    Args:
        num_events: Total number of process events recorded for this case.
        num_offers: Number of loan offers generated.
        amount: The requested loan amount in EUR.
    """
    issues = []

    if num_events < 3:
        issues.append("Very few process events — application may be incomplete or abandoned.")
    if amount > 5000 and num_offers == 0:
        issues.append("No offers generated for a non-trivial loan — offer stage may have been skipped.")
    if num_events > 50:
        issues.append("Unusually high number of events — may indicate processing difficulties or rework.")

    if not issues:
        return (
            f"APPLICATION COMPLETE: {num_events} events recorded, "
            f"{num_offers} offers generated. Application appears well-processed."
        )
    else:
        return (
            f"APPLICATION ISSUES FOUND: {num_events} events, {num_offers} offers.\n"
            + "\n".join(f"- {issue}" for issue in issues)
        )


@tool
def calculate_risk_score(
    amount: float,
    num_events: int,
    num_offers: int,
    case_duration_hours: float,
) -> str:
    """Calculate a risk score for the loan application based on available data.

    Args:
        amount: The requested loan amount in EUR.
        num_events: Total number of process events.
        num_offers: Number of offers generated.
        case_duration_hours: Total case processing duration in hours.
    """
    score = 50  # Start neutral

    # Amount factor
    if amount <= 5000:
        score -= 15
    elif amount <= 25000:
        score += 5
    else:
        score += 20

    # Process completeness
    if num_offers > 0:
        score -= 10  # Offers present = good sign
    else:
        score += 10

    # Duration factor
    if 0 < case_duration_hours < 500:
        score -= 5  # Normal processing time
    elif case_duration_hours > 2000:
        score += 15  # Unusually long

    # Event count
    if 5 <= num_events <= 30:
        score -= 5
    elif num_events > 50:
        score += 10

    score = max(0, min(100, score))

    risk_level = "LOW" if score < 35 else "MEDIUM" if score < 65 else "HIGH"

    return (
        f"RISK ASSESSMENT: Score {score}/100 ({risk_level})\n"
        f"Factors: amount={amount:.0f} EUR, events={num_events}, "
        f"offers={num_offers}, duration={case_duration_hours:.0f}h\n"
        f"Recommendation: {'Proceed with caution' if score >= 65 else 'Standard processing' if score >= 35 else 'Low risk, eligible for fast-track'}"
    )


ALL_TOOLS = [lookup_credit_policy, check_application_completeness, calculate_risk_score]
