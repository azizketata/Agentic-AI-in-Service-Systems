# Theoretical Grounding: Design Principles to IS Theory

This document maps each design principle to established IS/management theory, providing the theoretical foundation for the ICIS paper's contribution.

---

## Principle 1: Prospective Intent Contracts → Principal-Agent Theory

**Theory:** Principal-Agent Theory (Jensen & Meckling, 1976; Eisenhardt, 1989)

**Connection:** Intent contracts function as formal agreements between the human principal and the AI agent. They reduce agency costs by specifying acceptable actions, constraints, and escalation triggers *before* execution begins. Just as principal-agent theory prescribes contract design to align agent incentives with principal goals under information asymmetry, prospective intent contracts align the AI agent's autonomous reasoning with organizational objectives.

**Key insight for the paper:** The contract is created *before* execution, making governance prospective rather than retrospective — directly addressing the accountability gap identified in agentic BPM. Traditional RPA didn't need contracts because bots follow scripts; agentic systems need contracts because they reason autonomously.

**Prototype evidence:** IntentContract dataclass (goal, constraints, acceptable_actions, forbidden_actions, escalation_triggers). 0 contract violations in governed mode across 101 cases.

**Citations:** Jensen & Meckling (1976), Eisenhardt (1989), Lacity & Willcocks (2017)

---

## Principle 2: Graduated Autonomy → Levels of Automation

**Theory:** Levels of Automation framework (Parasuraman, Sheridan, & Wickens, 2000)

**Connection:** Rather than binary full-automation or full-human-control, graduated autonomy implements Parasuraman et al.'s LOA framework. The three tiers (full_auto, supervised, restricted) correspond to different points on the automation continuum, dynamically determined by decision risk factors.

**Key insight for the paper:** A single automation level cannot accommodate the variance inherent in service systems. Low-risk cases benefit from full automation; high-risk cases require multi-point human involvement. The graduated approach concentrates human effort where it has the highest impact — this is a resource allocation argument, not just a safety argument.

**Prototype evidence:** full_auto tier had 7 errors (no HITL); supervised tier had 0 errors (HITL at final decision); restricted tier had 0 errors (HITL at every step). The graduated approach correctly concentrates human effort.

**Citations:** Parasuraman et al. (2000), Sheridan & Verplank (1978), Endsley & Kiris (1995), Vagia et al. (2016)

---

## Principle 3: Reasoning Trace Transparency → Accountability Theory

**Theory:** Accountability Theory (Bovens, 2007; Bovens, Schillemans, & Weert, 2014)

**Connection:** Bovens defines accountability as the obligation to explain and justify conduct to an accountability forum. Trace transparency satisfies the *information condition* of accountability: without sufficient information about the agent's reasoning process, the forum cannot meaningfully assess its conduct. In agentic systems where processes are generated at runtime, reasoning traces become the primary accountability artifact, replacing pre-approved BPMN models.

**Key insight for the paper:** This is the strongest theoretical link. The AMCIS paper identified the "accountability gap" — governed mode's traces close it. The ungoverned agent makes decisions that are opaque; the governed agent's reasoning is fully auditable. This shifts governance from prospective (approving what the system *will* do) to transparent (understanding what the system *did* and *why*).

**Prototype evidence:** 274 audit log entries across 101 governed cases. Tagged reasoning traces ([ASSESS], [TOOL], [DECIDE], [GOV], [GUARDRAIL], [HITL]) create complete audit trails. AuditLog class supports structured querying.

**Citations:** Bovens (2007), Bovens et al. (2014), Wieringa (2020), Cobbe et al. (2021)

---

## Principle 4: Procedural Literacy Preservation → Meaningful Human Control

**Theory:** Meaningful Human Control (Santoni de Sio & van den Hoven, 2018)

**Connection:** MHC requires both relevant information *and* the competence to act on it. The automation-augmentation paradox (Raisch & Krakowski, 2021) warns that automation erodes procedural knowledge needed for oversight. HITL checkpoints combat "out-of-the-loop unfamiliarity" (Endsley, 2017) by requiring humans to engage with reasoning details — not merely rubber-stamp decisions.

**Key insight for the paper:** This connects directly to the AMCIS paper's "deskilling paradox." Our trace analysis shows the agent is wrong with 85% average confidence — these are *plausible* failures that only a procedurally literate human could catch. 31 of 33 errors had confidence >= 80%. Without HITL forcing engagement, humans would have no reason to question the agent.

**Prototype evidence:** 72 HITL events; 26 agent errors corrected by human review. The HITL experiment measures whether trace engagement actually preserves decision quality.

**Citations:** Santoni de Sio & van den Hoven (2018), Raisch & Krakowski (2021), Endsley (2017), Parasuraman & Manzey (2010)

---

## How to Use in the Paper

### In Theoretical Background (Section 2):
- Add a subsection "Theoretical Foundations for Governed Agentic Automation"
- Introduce each theory briefly and explain why it applies to agentic governance
- Cite the key papers and connect to the lifecycle collapse / accountability gap / deskilling paradox

### In Results (Section 4):
- For each design principle, present the prototype evidence
- Use the metrics as empirical grounding for the theoretical claims

### In Discussion (Section 5):
- Argue that the 4 principles are *theoretically necessary* — each addresses a specific governance tension grounded in established theory
- Discuss what happens when principles are absent (ungoverned mode results)
- Connect to the responsible AI discourse
