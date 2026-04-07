"""
Theoretical Grounding (Enhancement E)

Maps each design principle to established IS theory with citations and evidence.
"""

THEORETICAL_MAPPING: list[dict] = [
    {
        "principle_number": 1,
        "principle_name": "Prospective Intent Contracts",
        "description": "Machine-readable contracts created before agent execution specifying goal, constraints, and acceptable actions",
        "theory": "Principal-Agent Theory",
        "key_citation": "Jensen & Meckling, 1976",
        "supporting_citations": [
            "Eisenhardt, 1989",
            "Lacity & Willcocks, 2017",
        ],
        "connection": (
            "Intent contracts function as formal agreements between the human principal "
            "and the AI agent, reducing agency costs by specifying acceptable actions, "
            "constraints, and escalation triggers before execution begins. Just as "
            "principal-agent theory prescribes contract design to align agent incentives "
            "with principal goals under information asymmetry (Jensen \\& Meckling, 1976), "
            "prospective intent contracts align the AI agent's autonomous reasoning with "
            "organizational objectives. The contract is created \\textit{before} execution, "
            "making governance prospective rather than retrospective — addressing the "
            "accountability gap identified in agentic BPM."
        ),
        "artifact_evidence": (
            "The IntentContract dataclass captures goal, constraints, acceptable\\_actions, "
            "forbidden\\_actions, and escalation\\_triggers. Guardrails validate contract "
            "compliance at every governance checkpoint. In the evaluation, 0 contract "
            "violations occurred in governed mode, demonstrating effective alignment."
        ),
        "prototype_metric": "contract_violations = 0 for governed mode",
    },
    {
        "principle_number": 2,
        "principle_name": "Graduated Autonomy",
        "description": "Agent freedom varies by decision risk level across three tiers",
        "theory": "Levels of Automation (LOA)",
        "key_citation": "Parasuraman, Sheridan, & Wickens, 2000",
        "supporting_citations": [
            "Sheridan & Verplank, 1978",
            "Endsley & Kiris, 1995",
            "Vagia, Fosch-Villaronga, & Kragic, 2016",
        ],
        "connection": (
            "Rather than binary full-automation or full-human-control, graduated "
            "autonomy implements Parasuraman et al.'s (2000) levels of automation "
            "framework. The three tiers — full\\_auto, supervised, restricted — "
            "correspond to different points on the automation continuum, with the "
            "level dynamically determined by decision risk factors (loan amount and "
            "risk tier). This addresses the finding that a single automation level "
            "cannot accommodate the variance inherent in service systems: low-risk "
            "cases benefit from full automation, while high-risk cases require human "
            "involvement at multiple decision points."
        ),
        "artifact_evidence": (
            "classify\\_autonomy\\_tier() maps (amount, risk\\_tier) to automation level. "
            "In the evaluation: full\\_auto tier had 7 errors (no HITL), supervised "
            "tier had 0 errors (HITL at final decision), restricted tier had 0 errors "
            "(HITL at every step). The graduated approach correctly concentrates human "
            "effort where it has the highest impact."
        ),
        "prototype_metric": "0 errors in supervised/restricted tiers vs 7 in full_auto",
    },
    {
        "principle_number": 3,
        "principle_name": "Reasoning Trace Transparency",
        "description": "Every agent reasoning step logged in human-interpretable, auditable format",
        "theory": "Accountability Theory",
        "key_citation": "Bovens, 2007",
        "supporting_citations": [
            "Bovens, Schillemans, & Weert, 2014",
            "Wieringa, 2020",
            "Cobbe, Lee, & Singh, 2021",
        ],
        "connection": (
            "Bovens (2007) defines accountability as the obligation to explain and "
            "justify conduct to an accountability forum. Trace transparency satisfies "
            "the \\textit{information condition} of accountability: without sufficient "
            "information about the agent's reasoning process, the forum (human reviewer, "
            "auditor, regulator) cannot meaningfully assess its conduct. In agentic "
            "systems where processes are generated at runtime, traditional design-time "
            "documentation no longer exists — reasoning traces become the primary "
            "accountability artifact, replacing the pre-approved BPMN models that "
            "traditional governance relies upon."
        ),
        "artifact_evidence": (
            "Tagged reasoning traces ([ASSESS], [TOOL], [DECIDE], [GOV], [GUARDRAIL], "
            "[HITL]) create a complete audit trail. The AuditLog stores 274 structured "
            "entries across 101 governed cases (avg 2.7 per case), enabling both "
            "real-time and retrospective review of agent conduct."
        ),
        "prototype_metric": "274 audit log entries, structured and queryable",
    },
    {
        "principle_number": 4,
        "principle_name": "Procedural Literacy Preservation",
        "description": "HITL checkpoints keep humans engaged with procedural details to maintain oversight competence",
        "theory": "Meaningful Human Control (MHC)",
        "key_citation": "Santoni de Sio & van den Hoven, 2018",
        "supporting_citations": [
            "Raisch & Krakowski, 2021",
            "Endsley, 2017",
            "Parasuraman & Manzey, 2010",
        ],
        "connection": (
            "Meaningful human control requires both relevant information \\textit{and} "
            "the competence to act on it (Santoni de Sio \\& van den Hoven, 2018). "
            "The automation-augmentation paradox (Raisch \\& Krakowski, 2021) warns that "
            "automation can erode the procedural knowledge needed for effective oversight. "
            "HITL checkpoints address this by requiring humans to engage with agent "
            "reasoning details — not merely rubber-stamp decisions. Endsley (2017) "
            "identifies 'out-of-the-loop unfamiliarity' as a key risk; procedural "
            "literacy preservation combats this by maintaining situation awareness "
            "through structured interaction with the agent's reasoning process."
        ),
        "artifact_evidence": (
            "72 HITL events across 101 governed cases. In supervised tier, humans "
            "review the full reasoning trace before approving the final decision. "
            "In restricted tier, humans engage at every significant action. The "
            "HITL experiment (Enhancement D) measures whether this engagement actually "
            "preserves decision quality over time."
        ),
        "prototype_metric": "72 HITL events; 26 agent errors corrected by human review",
    },
]


def get_mapping() -> list[dict]:
    """Return the full theoretical mapping."""
    return THEORETICAL_MAPPING


def get_mapping_for_principle(principle_number: int) -> dict | None:
    """Return mapping for a specific principle."""
    for m in THEORETICAL_MAPPING:
        if m["principle_number"] == principle_number:
            return m
    return None


def generate_latex_table() -> str:
    """Generate a LaTeX table for the paper."""
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Theoretical Grounding of Design Principles}",
        r"\label{tab:theoretical_mapping}",
        r"\begin{tabular}{p{3.5cm}p{3cm}p{3cm}p{5cm}}",
        r"\hline",
        r"\textbf{Design Principle} & \textbf{Theory} & \textbf{Key Citation} & \textbf{Connection} \\",
        r"\hline",
    ]

    for m in THEORETICAL_MAPPING:
        short_connection = m["connection"][:150].split(". ")[0] + "."
        lines.append(
            f"{m['principle_name']} & {m['theory']} & {m['key_citation']} & {short_connection} \\\\"
        )

    lines.extend([
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def generate_theory_section_notes() -> str:
    """Generate structured notes for the theoretical background section."""
    notes = []
    for m in THEORETICAL_MAPPING:
        cites = ", ".join(m["supporting_citations"])
        notes.append(
            f"### Principle {m['principle_number']}: {m['principle_name']}\n"
            f"**Theory:** {m['theory']} ({m['key_citation']}; see also {cites})\n\n"
            f"**Connection:** {m['connection']}\n\n"
            f"**Artifact Evidence:** {m['artifact_evidence']}\n\n"
            f"**Metric:** {m['prototype_metric']}\n"
        )
    return "\n---\n\n".join(notes)
