# Overleaf Assembly Guide

## Title
**Governing Agentic AI in Service Systems: Design Principles for Autonomous Agent Oversight**

## How to Assemble in Overleaf

1. Use the official ICIS 2026 template
2. Copy content from each .tex file into the corresponding section of your Overleaf document
3. **DO NOT** include author names anywhere (double-blind review)

## File Order (copy-paste into Overleaf)

| File | Section | Approx Pages |
|---|---|---|
| `00-title.tex` | Title (in template header) | — |
| `00-abstract.tex` | Abstract (149 words, under 150 limit) | — |
| `00-keywords.tex` | Keywords | — |
| `01-introduction.tex` | Section 1: Introduction | ~2.5 pages |
| `02-theoretical-background.tex` | Section 2: Theoretical Background | ~3 pages |
| `03-research-method.tex` | Section 3: Research Method | ~3 pages |
| `04-results.tex` | Section 4: Results | ~4 pages |
| `05-discussion.tex` | Section 5: Discussion | ~3 pages |
| `06-conclusion.tex` | Section 6: Conclusion | ~0.5 pages |
| `07-references.tex` | References (excluded from page count) | ~2 pages |

**Estimated total: ~16 pages** (within ICIS limit)

## Tables in the Paper (6 total)

| Table | Label | In Section |
|---|---|---|
| Table 1 | `tab:theoretical_foundations` | Section 2 (Theoretical Background) |
| Table 2 | `tab:evaluation_setup` | Section 3 (Research Method) |
| Table 3 | `tab:mode_comparison` | Section 4.1 (Three-Mode Comparison) |
| Table 4 | `tab:tier_breakdown` | Section 4.2 (Per-Tier Analysis) |
| Table 5 | `tab:failure_analysis` | Section 4.3 (Failure Classification) |
| (Expert Assessment table) | TBD | Section 4.4 (TO BE COMPLETED) |

## Figures to Include (from paper_assets/figures/)

| Figure | File | In Section |
|---|---|---|
| Architecture diagram | Create in draw.io/Mermaid | Section 3 |
| Per-tier accuracy bars | `fig2_tier_accuracy.html` → export as PDF | Section 4.2 |
| Failure type pie chart | `fig3_failure_types.html` → export as PDF | Section 4.3 |
| Confidence distribution | `fig4_confidence_distribution.html` → export as PDF | Section 4.3 |
| Radar chart | `fig1_radar_chart.html` → export as PDF | Section 5 or Appendix |

**To export Plotly figures as static images:**
Open each .html file in a browser, use the camera icon (top-right of chart) to download as PNG,
then include in Overleaf with `\includegraphics`.

## Sections TO BE COMPLETED by Co-Author

1. **Section 4.4: Expert Assessment** — structured evaluation with practitioners
2. **Section 4.5: Interactive HITL Study** — participants reviewing traces via Streamlit
3. **Remove all [TO BE COMPLETED] placeholders** before submission
4. **Anonymize the "Anonymous, 2026" reference** — this is the AMCIS paper

## Pre-Submission Checklist

- [ ] Under 16 pages (title, abstract, keywords, references excluded)
- [ ] No author names in body, abstract, headers, or PDF metadata
- [ ] All [TO BE COMPLETED] sections filled in
- [ ] Self-citations anonymized ("Anonymous, 2026")
- [ ] Official ICIS 2026 template used
- [ ] PDF format only
- [ ] Abstract under 150 words (currently 149)
