"""
LangGraph Node Functions

Each node is a function that takes AgentState and returns partial state updates.
"""

import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agent.prompts import ASSESSMENT_PROMPT_TEMPLATE, SYSTEM_PROMPT
from src.agent.state import AgentState
from src.agent.tools import ALL_TOOLS
from src.common.llm import get_llm


def _get_llm_with_tools():
    llm = get_llm()
    return llm.bind_tools(ALL_TOOLS)


def assess_application(state: AgentState) -> dict:
    """
    LLM reasoning node. On first call, sends the case prompt.
    On subsequent calls (after tools), continues the conversation.
    """
    llm = _get_llm_with_tools()

    if not state.get("messages"):
        # First call — build initial prompt
        prompt = ASSESSMENT_PROMPT_TEMPLATE.format(
            case_id=state["case_id"],
            amount_requested=state["amount_requested"],
            risk_tier=state["risk_tier"],
            num_events=state["num_events"],
            num_offers=state["num_offers"],
            case_duration_hours=state["case_duration_hours"],
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        trace_entry = f"[ASSESS] Sent case {state['case_id']} to LLM for evaluation"
        new_user_msg = [HumanMessage(content=prompt)]
    else:
        # Subsequent call — continue with full conversation history
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        trace_entry = f"[ASSESS] LLM processing tool results (step {len(state.get('steps_taken', []))+1})"
        new_user_msg = []

    response = llm.invoke(messages)

    return {
        "messages": new_user_msg + [response],
        "current_step": "assessed",
        "reasoning_trace": state.get("reasoning_trace", []) + [trace_entry],
        "steps_taken": state.get("steps_taken", []) + [{"step": "assess", "node": "assess_application"}],
    }


def call_tools(state: AgentState) -> dict:
    """Execute tool calls requested by the LLM."""
    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {}

    tool_map = {t.name: t for t in ALL_TOOLS}
    tool_messages = []
    trace_entries = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if tool_name in tool_map:
            result = tool_map[tool_name].invoke(tool_args)
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )
            trace_entries.append(f"[TOOL] {tool_name}({tool_args}) -> {str(result)[:200]}")

    return {
        "messages": tool_messages,
        "reasoning_trace": state.get("reasoning_trace", []) + trace_entries,
        "steps_taken": state.get("steps_taken", []) + [
            {"step": "tool_call", "tools": [tc["name"] for tc in last_message.tool_calls]}
        ],
    }


def make_decision(state: AgentState) -> dict:
    """Parse the decision from the last LLM message (no extra LLM call needed)."""
    last_message = state["messages"][-1]
    content = last_message.content if isinstance(last_message.content, str) else str(last_message.content)

    decision = _parse_decision(content)
    confidence = _parse_confidence(content)

    trace_entry = f"[DECIDE] Decision: {decision}, Confidence: {confidence}"

    return {
        "decision": decision,
        "confidence": confidence,
        "decision_reasoning": content,
        "current_step": "decided",
        "reasoning_trace": state.get("reasoning_trace", []) + [trace_entry],
        "steps_taken": state.get("steps_taken", []) + [{"step": "decision", "node": "make_decision"}],
    }


def _parse_decision(content: str) -> str:
    """Extract decision from LLM response text."""
    content_upper = content.upper()
    if "DECISION: APPROVED" in content_upper or "DECISION:APPROVED" in content_upper:
        return "approved"
    elif "DECISION: DECLINED" in content_upper or "DECISION:DECLINED" in content_upper:
        return "declined"
    elif "APPROVED" in content_upper and "DECLINED" not in content_upper:
        return "approved"
    elif "DECLINED" in content_upper:
        return "declined"
    return "declined"  # Default to decline if unclear (conservative)


def _parse_confidence(content: str) -> float:
    """Extract confidence score from LLM response text."""
    match = re.search(r"CONFIDENCE:\s*([\d.]+)", content, re.IGNORECASE)
    if match:
        try:
            val = float(match.group(1))
            return min(1.0, max(0.0, val))
        except ValueError:
            pass
    return 0.5  # Default confidence


def should_continue(state: AgentState) -> str:
    """Routing function: continue tool calling or go to decision."""
    last_message = state["messages"][-1]

    # If LLM wants to call tools, continue the loop
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "call_tools"

    # If we already have a decision, end
    if state.get("decision"):
        return "end"

    # LLM responded with text (no tool calls) — parse as decision
    return "make_decision"
