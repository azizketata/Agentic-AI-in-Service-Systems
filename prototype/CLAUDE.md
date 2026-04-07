# Agentic AI Governance Prototype

## What This Is
DSR artifact for ICIS 2026 paper. Three-mode loan processing system comparing
rule-based (RPA) vs ungoverned agentic vs governed agentic automation.
Uses BPI Challenge 2012 dataset (Dutch bank loan applications).

## Project Layout
- `src/data/` — BPI 2012 data loading (XES via pm4py) and preprocessing
- `src/rule_engine/` — Deterministic if/else loan processing (RPA baseline)
- `src/agent/` — LangGraph agents: `graph.py` (ungoverned), `governed_graph.py` (with guardrails)
- `src/governance/` — DSR artifact core: intent contracts, autonomy tiers, guardrails, audit logger, HITL
- `src/evaluation/` — Metrics computation and three-mode comparison
- `app/` — Streamlit dashboard (5 pages in `app/pages/`)
- `config/` — YAML configs for settings, governance policies
- `data/raw/` — BPI 2012 XES file (gitignored)
- `data/processed/` — Parquet after preprocessing
- `data/sample/` — ~100 stratified cases for demo/dev

## Build & Run
- Install: `pip install -r requirements.txt`
- Preprocess data: `python -m src.data.preprocessor`
- Run Streamlit: `streamlit run app/app.py`
- Run tests: `pytest tests/`

## LLM Configuration
- Provider configurable in `config/settings.yaml` (anthropic or openai)
- API keys in `.env` (never commit)
- LLM abstracted via factory in `src/common/llm.py` — change provider there

## Key Patterns
- All three modes process the same LoanApplication (Pydantic model in `src/data/schemas.py`)
- Agent state defined in `src/agent/state.py` (LangGraph TypedDict)
- Governance checks happen at graph nodes, not as middleware
- HITL uses LangGraph native `interrupt_before` — Streamlit polls graph state
- Audit entries are structured dataclasses in `src/governance/audit_logger.py`
- Tools in `src/agent/tools.py` are simulated (return preprocessed BPI data, no external APIs)

## Conventions
- Type hints on all functions
- Pydantic models for data schemas, dataclasses for internal structures
- YAML for configuration, not Python constants
- Keep Streamlit pages thin — business logic stays in `src/`

## Important
- Never commit `.env` or `data/raw/` (large files + secrets)
- temperature=0 for LLM calls (reproducibility)
- The governed_graph.py is the core DSR artifact — changes here must preserve
  the 4 design principles: intent contracts, graduated autonomy, trace transparency,
  procedural literacy preservation
