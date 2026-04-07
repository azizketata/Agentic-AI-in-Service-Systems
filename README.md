# Governing Agentic AI in Service Systems

**Design Principles for Autonomous Agent Oversight**

A Design Science Research prototype that compares rule-based automation (RPA), ungoverned agentic AI, and governed agentic AI across two service domains — financial services and healthcare — demonstrating how governance mechanisms address the accountability gap, deskilling paradox, and lifecycle collapse in autonomous AI systems.

> **Paper:** *"Governing Agentic AI in Service Systems: Design Principles for Autonomous Agent Oversight"*
> Submitted to ICIS 2026 (47th International Conference on Information Systems), Track 1: Digital Collaboration and Coexistence

---

## What This Project Does

Agentic AI systems — autonomous agents capable of goal-directed planning, contextual reasoning, and tool orchestration — are replacing rule-based RPA in service operations. But governance frameworks designed for deterministic bots cannot accommodate systems that generate process paths at runtime.

This prototype addresses that gap by implementing and evaluating **four design principles** for governing agentic AI:

| Principle | What It Does | Grounded In |
|---|---|---|
| **Prospective Intent Contracts** | Machine-readable contracts created before agent execution specifying goals, constraints, and acceptable actions | Principal-Agent Theory (Jensen & Meckling, 1976) |
| **Graduated Autonomy** | Agent freedom varies by decision risk — full-auto, supervised, or restricted tiers with different HITL density | Levels of Automation (Parasuraman et al., 2000) |
| **Reasoning Trace Transparency** | Every agent reasoning step logged in structured, human-interpretable format | Accountability Theory (Bovens, 2007) |
| **Procedural Literacy Preservation** | HITL checkpoints require humans to engage with agent reasoning details before approving | Meaningful Human Control (Santoni de Sio & van den Hoven, 2018) |

---

## Key Findings

### Cross-Domain Results

| Metric | Rule-Based | Agentic | Governed |
|---|---|---|---|
| **Loan Processing** (BPI 2012, N=101) | 48.5% | 67.3% | **93.1%** |
| **Sepsis Triage** (Sepsis Cases, N=99) | 72.7% | 57.6% | **92.9%** |

### The Deskilling Paradox — Made Concrete

- The ungoverned agent fails with **85% average confidence** — errors are plausible, not obvious
- **31 of 33 errors** (94%) had confidence >= 80%
- The agent **never predicts "cancelled"** (customer withdrawal) — an entire outcome category is a systematic blind spot invisible without procedural knowledge

### The Governance-Efficiency Tradeoff (consistent across both domains)

| Autonomy Tier | Loans (Governed) | Sepsis (Governed) |
|---|---|---|
| **Supervised** (HITL at decision) | **100%** | **100%** |
| **Restricted** (HITL at every step) | **100%** | **100%** |
| **Full Auto** (no HITL) | 76% | 71% |
| Governed errors | 7 (all full-auto) | 7 (all full-auto) |

Governance achieves perfect accuracy where HITL is active — in both financial services and healthcare. All errors in both domains occur exclusively in the full-auto tier.

### Guardrail Effectiveness

- Governance mechanisms caught **79% of agent errors** (26/33)
- All 7 misses occurred in the full-auto tier where no HITL exists
- Intent contracts and guardrails enforce boundaries; HITL actually corrects errors

---

## Architecture

```
                    STREAMLIT DASHBOARD (6 pages + dataset toggle)
        +----------+----------+----------+----------+----------+
        | Process  |  Mode    |Reasoning | Govern.  | Metrics  | Trace
        | Overview |Comparison|  Trace   |Dashboard | Panel    | Analysis
        +----+-----+----+-----+----+-----+----+-----+----+-----+
             |          |          |          |          |
    +--------+----------+----------+----------+----------+------+
    |              THREE PROCESSING MODES                       |
    |  +----------+  +----------+  +--------------------+      |
    |  |Rule-Based|  | Agentic  |  |     Governed       |      |
    |  |(if/else) |  |(LangGraph|  | (LangGraph +       |      |
    |  |No LLM    |  | ReAct)   |  |  Intent Contracts  |      |
    |  |          |  |          |  |  Graduated Autonomy |      |
    |  |          |  |          |  |  Trace Transparency |      |
    |  |          |  |          |  |  HITL Checkpoints)  |      |
    |  +----------+  +----------+  +--------------------+      |
    +------------------------------+---------------------------+
                                   |
    +------------------------------+---------------------------+
    |              SHARED INFRASTRUCTURE                        |
    |  Data Layer     | Governance Layer  | Evaluation Engine   |
    |  (BPI 2012 +    | (Contracts,       | (Metrics, Trace     |
    |   Sepsis Cases) |  Guardrails,      |  Analysis,          |
    |                 |  Audit Logger)    |  Conformance)       |
    +------------------------------------------------------+
```

---

## Datasets

| Dataset | Domain | Cases | Events | Source |
|---|---|---|---|---|
| **BPI Challenge 2012** | Loan Applications (Dutch bank) | 13,087 | 262,200 | [4TU.ResearchData](https://data.4tu.nl/articles/dataset/BPI_Challenge_2012/12689204) |
| **Sepsis Cases** | Hospital Patient Pathways | 1,050 | 15,214 | [4TU.ResearchData](https://data.4tu.nl/articles/dataset/Sepsis_Cases_-_Event_Log/12707639) |

Both datasets are gold-standard benchmarks in the BPM and process mining research community.

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) (stateful graphs, native HITL via `interrupt_before`) |
| LLM | Configurable — Claude (Anthropic) or GPT-4o (OpenAI) |
| Dashboard | [Streamlit](https://streamlit.io) (6 pages, interactive HITL experiment) |
| Process Mining | [pm4py](https://pm4py.fit.fraunhofer.de/) (model discovery, conformance checking) |
| Data Validation | [Pydantic](https://docs.pydantic.dev/) |
| Charts | [Plotly](https://plotly.com/python/) |
| Testing | [pytest](https://pytest.org/) (98 tests) |

---

## Quick Start

### 1. Install dependencies

```bash
cd prototype
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env with your Anthropic and/or OpenAI API keys
```

### 3. Download datasets

- [BPI Challenge 2012](https://data.4tu.nl/articles/dataset/BPI_Challenge_2012/12689204) → `prototype/data/raw/BPI_Challenge_2012.xes`
- [Sepsis Cases](https://data.4tu.nl/articles/dataset/Sepsis_Cases_-_Event_Log/12707639) → `prototype/data/raw/Sepsis Cases - Event Log.xes`

### 4. Preprocess data

```bash
python -m src.data.preprocessor          # BPI 2012
python -m src.data.sepsis_preprocessor   # Sepsis Cases
```

### 5. Run the pipeline

```bash
python run_pipeline.py          # BPI 2012 (101 cases x 3 modes, ~35 min)
python run_sepsis_pipeline.py   # Sepsis (99 cases x 3 modes, ~35 min)
```

### 6. Launch the dashboard

```bash
streamlit run app/app.py
```

### 7. Run tests

```bash
pytest tests/ -v    # 98 tests
```

---

## Project Structure

```
prototype/
├── app/                           # Streamlit dashboard
│   ├── app.py                     # Entry point
│   ├── path_setup.py              # Centralized path resolution + dataset toggle
│   ├── pages/                     # 6 dashboard pages
│   │   ├── 1_process_overview.py  # Dataset exploration
│   │   ├── 2_mode_comparison.py   # Three-mode comparison with real data
│   │   ├── 3_reasoning_trace.py   # Trace viewer + HITL experiment
│   │   ├── 4_governance_dashboard.py
│   │   ├── 5_metrics_panel.py     # + process conformance analysis
│   │   └── 6_trace_analysis.py    # Failure classification + paper examples
│   └── components/                # Reusable widgets
├── src/
│   ├── data/                      # Data loading and preprocessing
│   ├── rule_engine/               # Deterministic decision logic (RPA baseline)
│   ├── agent/                     # LangGraph agents (ungoverned + governed)
│   │   ├── graph.py               # Ungoverned agent
│   │   ├── governed_graph.py      # Governed agent (DSR artifact core)
│   │   ├── tools.py               # Loan processing tools
│   │   ├── sepsis_tools.py        # Clinical triage tools
│   │   └── ...
│   ├── governance/                # Four design principles implementation
│   │   ├── intent_contract.py     # DP1: Prospective Intent Contracts
│   │   ├── autonomy_tiers.py      # DP2: Graduated Autonomy
│   │   ├── audit_logger.py        # DP3: Reasoning Trace Transparency
│   │   ├── guardrails.py          # Pre-execution policy checks
│   │   └── hitl.py                # DP4: Procedural Literacy Preservation
│   ├── evaluation/                # Analysis and metrics
│   │   ├── metrics.py             # Quantitative evaluation
│   │   ├── comparison.py          # Three-mode comparison tables
│   │   ├── trace_analysis.py      # Qualitative failure classification
│   │   ├── conformance.py         # Process conformance (pm4py)
│   │   ├── hitl_experiment.py     # Interactive HITL study data model
│   │   └── theoretical_mapping.py # Design principles → IS theory
│   └── common/
│       ├── llm.py                 # Configurable LLM factory (Anthropic/OpenAI)
│       └── types.py               # Shared enums
├── tests/                         # 98 tests covering all modules
├── config/
│   ├── settings.yaml              # LLM provider, thresholds, paths
│   └── governance_policies.yaml   # Autonomy tiers, guardrails, intent contracts
├── run_pipeline.py                # BPI 2012 pipeline runner
├── run_sepsis_pipeline.py         # Sepsis pipeline runner
├── generate_paper_assets.py       # Paper tables, figures, LaTeX, statistics
└── paper_assets/                  # Generated tables, figures, key statistics
```

---

## Related Work

This prototype builds on the conceptual analysis in:

> *Process Automation Revisited: From Rule-Based to Agentic AI in Service Systems* (AMCIS 2026)

Which identified the lifecycle collapse, accountability gap, and deskilling paradox as governance tensions in the shift from RPA to agentic AI. The present work provides empirically grounded design knowledge for addressing these tensions.

---

## Keywords

`agentic AI` `AI governance` `autonomous agents` `service systems` `design science research` `human-in-the-loop` `responsible AI` `business process management` `RPA` `LangGraph` `process mining` `human-AI collaboration` `accountability` `deskilling paradox` `lifecycle collapse` `meaningful human control`

---

## Citation

If you use this work, please cite:

```bibtex
@inproceedings{governing_agentic_ai_2026,
  title={Governing Agentic AI in Service Systems: Design Principles for Autonomous Agent Oversight},
  booktitle={Proceedings of the 47th International Conference on Information Systems (ICIS 2026)},
  year={2026},
  address={Lisbon, Portugal}
}
```

---

## License

This project is part of an academic research effort. Please contact the authors for reuse permissions.
