# Decidr Coherence Engine — System 1 v2: Conversation Layer

Revised per client meeting (2026-04-03) and lead guidance.

## What Changed from v1

| Aspect | v1 | v2 |
|--------|----|----|
| NL parsing | Extract ALL fields from NL | Extract **goal title only** from NL |
| Other fields | Also parsed from NL | **Structured form inputs** (dropdowns, text fields) |
| Schema | Generic metrics | **Mapped to actual v4 dataset** (goals.csv, buckets.csv) |
| Output | Not implemented | **Confidence-hedged score presentation** from System 2 |
| Scope | Full NLP pipeline | **Achievable in 1 month** per lead |

## Flow

```
INPUT:
  Structured Form (bucket cascade, metric, targets, scenario)
  + NL Textbox → [NLP extracts goal title only]
  → User confirms editable fields
  → JSON to System 3

OUTPUT:
  System 2 score payload (via System 3)
  → Confidence-hedged NL summary
  → 4 dimension cards with reasoning
  → Downloadable report
```

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit app — input form + score output page |
| `schemas.py` | Pydantic models mapped to v4 schema + confidence hedging helpers |
| `goal_extractor.py` | NL → goal title extraction (Ollama + heuristic fallback) |

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## System 2 Interface

System 2's `07_score_goal.py` returns a JSON payload containing:
- 4 dimension scores (coherence, attainability, relevance, integrity)
- Composite overall score
- GP uncertainty (gp_std, uncertain flag)
- Reasoning strings per dimension (from LLMs)
- Ensemble metadata (blend weights, variance)

System 1 does NOT re-call LLMs — it presents System 2's reasoning with confidence hedging:
- `uncertain=True` → "Elevated Uncertainty" badge, directional language
- `uncertain=False` → "High Confidence" badge
- `composite < 0.35` → "At Risk" flag
- `composite < 0.20` → "Critical" flag

## Dimension Labels (client-confirmed)

| Dimension | Weight | Question |
|-----------|--------|----------|
| Coherence | 35% | Are decisions consistent across levels, goals, and time? |
| Attainability | 25% | Is the goal realistically achievable? |
| Relevance | 20% | Is the allocation justified against stated goals? |
| Integrity | 20% | Are assumptions transparent & auditable? |
