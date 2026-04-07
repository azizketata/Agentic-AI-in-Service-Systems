"""Tests for the governance layer."""

import pytest

from src.common.types import AutonomyTier, GovernanceEventType
from src.governance.intent_contract import create_intent_contract, IntentContract
from src.governance.autonomy_tiers import classify_autonomy_tier, get_hitl_points, get_tier_description
from src.governance.guardrails import (
    check_action_allowlist,
    check_step_limit,
    check_confidence_gate,
    check_amount_ceiling,
    run_all_guardrails,
    any_guardrail_blocked,
    get_blocked_reasons,
)
from src.governance.audit_logger import AuditLog, AuditEntry
from src.governance.hitl import should_trigger_hitl, create_hitl_request, simulate_hitl_response


class TestAutonomyTiers:
    def test_low_amount_low_risk_is_full_auto(self):
        tier = classify_autonomy_tier(3000, "low")
        assert tier == AutonomyTier.FULL_AUTO

    def test_medium_amount_is_supervised(self):
        tier = classify_autonomy_tier(15000, "medium")
        assert tier == AutonomyTier.SUPERVISED

    def test_high_amount_is_restricted(self):
        tier = classify_autonomy_tier(30000, "high")
        assert tier == AutonomyTier.RESTRICTED

    def test_high_risk_overrides_low_amount(self):
        tier = classify_autonomy_tier(3000, "high")
        assert tier == AutonomyTier.RESTRICTED

    def test_hitl_points_full_auto_empty(self):
        points = get_hitl_points(AutonomyTier.FULL_AUTO)
        assert points == []

    def test_hitl_points_supervised_has_final_decision(self):
        points = get_hitl_points(AutonomyTier.SUPERVISED)
        assert "final_decision" in points

    def test_hitl_points_restricted_has_multiple(self):
        points = get_hitl_points(AutonomyTier.RESTRICTED)
        assert len(points) >= 2

    def test_tier_descriptions_not_empty(self):
        for tier in AutonomyTier:
            desc = get_tier_description(tier)
            assert desc, f"Description for {tier.value} should not be empty"


class TestIntentContracts:
    def test_create_contract(self):
        contract = create_intent_contract("CASE_1", 15000.0, "supervised")
        assert contract.case_id == "CASE_1"
        assert contract.autonomy_tier == "supervised"
        assert contract.goal != ""
        assert len(contract.acceptable_actions) > 0
        assert len(contract.forbidden_actions) > 0

    def test_contract_action_allowed(self):
        contract = create_intent_contract("CASE_1", 15000.0, "supervised")
        assert contract.is_action_allowed("assess_application") is True
        assert contract.is_action_allowed("make_decision") is True

    def test_contract_action_forbidden(self):
        contract = create_intent_contract("CASE_1", 15000.0, "supervised")
        assert contract.is_action_allowed("modify_loan_amount") is False
        assert contract.is_action_allowed("override_policy") is False

    def test_contract_step_limit(self):
        contract = create_intent_contract("CASE_1", 15000.0, "supervised")
        assert contract.is_within_step_limit(0) is True
        assert contract.is_within_step_limit(contract.max_steps - 1) is True
        assert contract.is_within_step_limit(contract.max_steps) is False

    def test_contract_serialization_roundtrip(self):
        contract = create_intent_contract("CASE_1", 15000.0, "supervised")
        data = contract.to_dict()
        restored = IntentContract.from_dict(data)
        assert restored.case_id == contract.case_id
        assert restored.autonomy_tier == contract.autonomy_tier
        assert restored.acceptable_actions == contract.acceptable_actions

    def test_high_value_contract_has_extra_constraints(self):
        contract = create_intent_contract("CASE_1", 30000.0, "restricted")
        constraint_text = " ".join(contract.constraints)
        assert "high-value" in constraint_text.lower() or "senior" in constraint_text.lower()


class TestGuardrails:
    @pytest.fixture
    def contract(self):
        return create_intent_contract("CASE_1", 15000.0, "supervised")

    def test_action_allowlist_pass(self, contract):
        result = check_action_allowlist(contract, "make_decision")
        assert result.allowed is True

    def test_action_allowlist_block(self, contract):
        result = check_action_allowlist(contract, "override_policy")
        assert result.allowed is False
        assert result.reason != ""

    def test_step_limit_pass(self, contract):
        result = check_step_limit(contract, 3)
        assert result.allowed is True

    def test_step_limit_block(self, contract):
        result = check_step_limit(contract, 100)
        assert result.allowed is False

    def test_confidence_gate_pass(self):
        result = check_confidence_gate(0.85, threshold=0.7)
        assert result.allowed is True

    def test_confidence_gate_block(self):
        result = check_confidence_gate(0.5, threshold=0.7)
        assert result.allowed is False

    def test_confidence_gate_none(self):
        result = check_confidence_gate(None)
        assert result.allowed is False

    def test_amount_ceiling_pass(self):
        result = check_amount_ceiling(3000, max_auto_approve=5000)
        assert result.allowed is True

    def test_amount_ceiling_block(self):
        result = check_amount_ceiling(10000, max_auto_approve=5000)
        assert result.allowed is False

    def test_run_all_guardrails_returns_results(self, contract):
        results = run_all_guardrails(contract, "make_decision", 3, confidence=0.9, amount=15000)
        assert len(results) >= 3, "Should run at least 3 guardrails"
        assert all(hasattr(r, "allowed") for r in results)
        assert all(hasattr(r, "reason") for r in results)
        assert all(r.reason != "" for r in results), "All guardrails should have a reason"

    def test_blocked_reasons_helper(self):
        from src.governance.guardrails import GuardrailResult
        results = [
            GuardrailResult(allowed=True, guardrail_name="a", reason="ok"),
            GuardrailResult(allowed=False, guardrail_name="b", reason="blocked!"),
        ]
        assert any_guardrail_blocked(results) is True
        reasons = get_blocked_reasons(results)
        assert reasons == ["blocked!"]


class TestAuditLogger:
    def test_log_entry(self):
        log = AuditLog()
        entry = log.log(
            case_id="C1", mode="governed",
            event_type=GovernanceEventType.STEP,
            step_number=1, action="assess",
            reasoning="Evaluating application",
        )
        assert len(log.entries) == 1
        assert entry.case_id == "C1"
        assert entry.reasoning == "Evaluating application"

    def test_log_multiple_entries(self):
        log = AuditLog()
        log.log("C1", "governed", GovernanceEventType.STEP, 1, "assess", "Step 1")
        log.log("C1", "governed", GovernanceEventType.VIOLATION, 2, "decide", "Blocked")
        log.log("C2", "governed", GovernanceEventType.STEP, 1, "assess", "Step 1")
        assert len(log.entries) == 3
        assert len(log.get_entries_for_case("C1")) == 2
        assert len(log.get_violations()) == 1

    def test_summary(self):
        log = AuditLog()
        log.log("C1", "governed", GovernanceEventType.STEP, 1, "a", "r")
        log.log("C1", "governed", GovernanceEventType.VIOLATION, 2, "b", "r")
        log.log("C1", "governed", GovernanceEventType.ESCALATION, 3, "c", "r")
        summary = log.summary()
        assert summary["total_entries"] == 3
        assert summary["violations"] == 1
        assert summary["escalations"] == 1

    def test_to_json_not_empty(self):
        log = AuditLog()
        log.log("C1", "governed", GovernanceEventType.STEP, 1, "a", "r")
        json_str = log.to_json()
        assert len(json_str) > 10

    def test_to_dataframe(self):
        log = AuditLog()
        log.log("C1", "governed", GovernanceEventType.STEP, 1, "a", "r")
        log.log("C2", "governed", GovernanceEventType.STEP, 1, "a", "r")
        df = log.to_dataframe()
        assert len(df) == 2
        assert "case_id" in df.columns


class TestHITL:
    def test_full_auto_never_triggers(self):
        assert should_trigger_hitl("full_auto", "final_decision", []) is False

    def test_supervised_triggers_at_decision(self):
        assert should_trigger_hitl("supervised", "final_decision", ["final_decision"]) is True

    def test_supervised_no_trigger_at_assessment(self):
        assert should_trigger_hitl("supervised", "assessment", ["final_decision"]) is False

    def test_restricted_triggers_at_all_points(self):
        hitl_points = ["assessment", "action_selection", "final_decision"]
        assert should_trigger_hitl("restricted", "assessment", hitl_points) is True
        assert should_trigger_hitl("restricted", "final_decision", hitl_points) is True

    def test_create_hitl_request(self):
        req = create_hitl_request("C1", "final_decision", "approved", ["step1"], 0.8, "supervised")
        assert req.case_id == "C1"
        assert req.agent_proposal == "approved"
        assert req.requires_approval is True

    def test_simulate_hitl_correct_approves(self):
        req = create_hitl_request("C1", "final_decision", "approved", [], 0.9, "supervised")
        resp = simulate_hitl_response(req, "approved")
        assert resp.approved is True
        assert resp.human_decision == "approve"

    def test_simulate_hitl_wrong_overrides(self):
        req = create_hitl_request("C1", "final_decision", "approved", [], 0.9, "supervised")
        resp = simulate_hitl_response(req, "declined")
        assert resp.approved is False
        assert resp.human_decision == "modify"
        assert resp.modified_action == "declined"
