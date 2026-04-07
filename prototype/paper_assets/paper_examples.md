### The Cancelled Blind Spot (Case 214064)

Case 214064 (EUR 5,000): The agent predicted 'approved' with 95% confidence, but the customer had cancelled their application. The agent's reasoning was logically sound — it evaluated creditworthiness and application completeness — but it cannot detect customer withdrawal intent from process metrics alone. This exemplifies the 'plausible failure' the deskilling paradox warns about.

---

### Governance Catches a False Approval (Case 200856)

Case 200856 (EUR 6,000): The ungoverned agent approved this loan, but the ground truth was 'declined'. In governed mode, the HITL checkpoint caught the error — the human reviewer corrected the decision. This demonstrates the accountability gap: without governance, the incorrect approval would have proceeded unchecked.

---

### Conservative Agent Declines a Valid Application (Case 202701)

Case 202701 (EUR 15,000): The agent declined this application, but it was actually approved. The agent's conservative bias — defaulting to decline under uncertainty — shows how agentic reasoning can be systematically wrong in ways that are hard to detect without procedural knowledge.

---

### Governance Limits: When Guardrails Are Not Enough (Case 211248)

Case 211248: Even with governance, the system produced an incorrect outcome. This case was in the full_auto tier (low risk), so no HITL checkpoint was triggered. It demonstrates the governance tradeoff: graduated autonomy reduces human burden but accepts some error in low-risk cases.

---

### Convergent Correctness: Three Modes, One Right Answer (Case 190824)

Case 190824 (EUR 25,000): All three modes correctly reached 'declined', but through different mechanisms. The rule engine applied threshold logic. The agent reasoned about policy and risk. The governed agent did the same with guardrail validation. This shows that governance adds transparency without sacrificing capability on straightforward cases.

---

