"""
Fixed Activity Routing Tables (RPA Baseline)

Defines the expected process paths for each decision outcome.
Used for conformance checking against the BPI 2012 event log.
"""

# Standard process paths derived from BPI 2012 process mining
PROCESS_ROUTES: dict[str, list[str]] = {
    "auto_approve": [
        "A_SUBMITTED",
        "A_PARTLYSUBMITTED",
        "A_PREACCEPTED",
        "A_ACCEPTED",
        "A_FINALIZED",
    ],
    "standard_review": [
        "A_SUBMITTED",
        "A_PARTLYSUBMITTED",
        "W_Completeren aanvraag",
        "A_PREACCEPTED",
        "O_CREATED",
        "O_SENT",
        "A_ACCEPTED",
        "A_FINALIZED",
    ],
    "senior_review": [
        "A_SUBMITTED",
        "A_PARTLYSUBMITTED",
        "W_Completeren aanvraag",
        "W_Nabellen offertes",
        "A_PREACCEPTED",
        "O_CREATED",
        "O_SENT",
        "O_ACCEPTED",
        "A_ACCEPTED",
        "A_FINALIZED",
    ],
    "decline": [
        "A_SUBMITTED",
        "A_PARTLYSUBMITTED",
        "A_DECLINED",
    ],
    "incomplete": [
        "A_SUBMITTED",
        "A_PARTLYSUBMITTED",
        "A_CANCELLED",
    ],
}

# Key activities that indicate major process milestones
MILESTONE_ACTIVITIES = {
    "A_SUBMITTED": "Application submitted",
    "A_PREACCEPTED": "Pre-acceptance",
    "A_ACCEPTED": "Final acceptance",
    "A_DECLINED": "Application declined",
    "A_CANCELLED": "Application cancelled",
    "A_FINALIZED": "Process finalized",
    "O_CREATED": "Offer created",
    "O_SENT": "Offer sent to customer",
    "O_ACCEPTED": "Offer accepted by customer",
}


def get_expected_route(outcome: str) -> list[str]:
    """Get the expected activity sequence for a given outcome."""
    return PROCESS_ROUTES.get(outcome, PROCESS_ROUTES["incomplete"])


def get_milestone_activities() -> dict[str, str]:
    """Get the milestone activities and their descriptions."""
    return MILESTONE_ACTIVITIES.copy()
