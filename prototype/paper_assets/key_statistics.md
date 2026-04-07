# Key Statistics for Paper Claims

Use these numbers directly in the paper text.

## Accuracy
- Rule-Based: 48.5%
- Agentic: 67.3%
- Governed: 93.1%

## Per-Tier (Governed Mode)
- Full Auto: 76%
- Supervised: 100%
- Restricted: 100%

## Failure Analysis
- total: 33
- cancelled_blind_spots: 25
- false_approvals: 6
- false_declines: 2
- avg_confidence_when_wrong: 0.8500000000000001
- high_confidence_errors: 31
- high_confidence_error_pct: 0.9393939393939394

## Governance
- guardrail_catches: 26
- guardrail_misses: 7
- catch_rate: 0.7878787878787878
- total_audit_entries: 274
- total_hitl_events: 72
- all_governed_errors_in_full_auto: True

## Key Claims (copy-paste ready)
- **claim_1**: The ungoverned agent achieves 67.3% accuracy but fails with 85% average confidence — errors are plausible, not obvious.
- **claim_2**: 31 of 33 agentic errors (94%) had confidence >= 80%, exemplifying the deskilling paradox.
- **claim_3**: Governed mode achieves 100% accuracy in supervised and restricted tiers, where HITL checkpoints are active.
- **claim_4**: All 7 governed mode errors occurred in the full_auto tier, demonstrating the governance-efficiency tradeoff.
- **claim_5**: Governance mechanisms caught 79% of agent errors (26/33), with all misses in the full_auto tier.
- **claim_6**: The agent never predicts 'cancelled' (customer withdrawal), missing an entire outcome category — a systematic blind spot invisible without procedural knowledge.
