# ilab-capstone-system1

System 1 acts as the **'ears and mouth'** of the Decidr Coherence Engine — responsible for input parsing (converting natural language queries into structured JSON) and output translation (converting System 2's scores back into natural language explanations). This is part of the UTS iLab Capstone project for MDSI.

## Architecture Overview
```
User (English query)
        ↓
   System 1 (Input)
   ├── query_extractor.py  →  extracts params from NL query
   ├── output.json         →  received from System 3 (time-series records)
   └── goals_config.json   →  received from System 3 (static goal configs)
        ↓
   combined_payload_*.json (NL params + matched records)
        ↓
   combine.py
   ├── output_updated.json       →  sent back to System 3
   └── goals_config_updated.json →  sent back to System 3
        ↓
   System 3 → System 2 (scoring/predictions)
        ↓
   System 3 returns scored JSONs to System 1
        ↓
   System 1 (Output) ← explainer.py [Phase 2 - pending]
        ↓
   User (English explanation + dashboard)
```

## Phase 1: Input Pipeline Completed

**Objective:** Parse natural language user queries, combine extracted parameters with System 3's JSON files, and return annotated combined JSONs ready for System 2.

### What Was Built

**`models.py`** — Pydantic schema definitions
- `GoalConfig`: static goal thresholds (green/orange/red bands, target value)
- `PeriodRecord`: time-series allocation and performance data per goal per period
- Resolved data drift during initial run (column name mismatches, type coercion on `bucket_id`)

**`loader.py`** — ETL validation pipeline
- Ingests `goals.csv` and `analytical_flat.csv` via Pandas
- Validates every row through Pydantic models
- Ran with **0 errors**, producing two clean JSON files:
  - `output.json` — 840 validated period records (Option A)
  - `goals_config.json` — 35 static goal configurations (Option B)

**`query_extractor.py`** — Natural language → structured JSON
- Extracts `goal_id`, `period_id`, `underfunded_flag`, `overfunded_flag` from plain English queries
- Looks up matching records from `output.json` and `goals_config.json`
- Outputs `combined_payload_{n}.json` per query — envelope containing:
  - `user_query`: original English string
  - `extracted_params`: parsed fields
  - `goal_config`: matched static config from System 3
  - `period_records`: matched time-series records from System 3

**`combine.py`** — Merge payloads back into annotated JSON files
- Annotates records and goal configs with `queried_by` field (which user query triggered them)
- Outputs:
  - `output_updated.json` — full 840-record dataset with query provenance
  - `goals_config_updated.json` — full 35-goal config with query provenance
- These are the files sent back to System 3

### Sample Queries Tested
```
"How is Goal 1 doing in Period 3?"
"Which goals are underfunded right now?"
"What is the probability of Goal 17 hitting its target by Period 24?"
```

## Phase 1b: LLM Output POC Completed (partial)

**`explainer.py`** — Ollama + qwen2.5:3b explanation generation
- Takes a period record + goal config → generates plain English explanation
- Prompt includes XAI confidence hedging ("The data suggests..." framing)
- Tested on worst-performing, specific, and overfunded goals

**`run.py`** — End-to-end test runner
- Test 1: Worst performing goal by `range_position_score`
- Test 2: Specific goal/period query (Goal 17, Period 18)
- Test 3: Overfunded goal

> **Note:** `explainer.py` is the output-half prototype. Full output translation (System 2 scores → NL explanations → dashboard) is Phase 2, pending System 2's scored JSON output from System 3.

## Phase 2: Output Translation 🔜 Pending

Waiting on System 3 to return scored JSONs from System 2. Once received, System 1 will:
- Translate coherence scores (R, I, A + overall CS) into audience-specific NL explanations
- Generate executive summary and analyst drill-down views
- Produce interactive dashboard with downloadable reports (joint deliverable with System 3)

## How to Run

```bash
# Step 1: Generate clean JSON files from CSVs (run once)
python loader.py

# Step 2: Extract query params + build combined payloads
python query_extractor.py

# Step 3: Merge payloads into annotated output files for System 3
python combine.py

# Step 4: Test LLM explanation output (requires Ollama running locally)
ollama serve
python run.py
```

## File Reference

| File | Purpose | Status |
|---|---|---|
| `models.py` | Pydantic schema definitions | Final |
| `loader.py` | CSV → validated JSON | Final |
| `query_extractor.py` | NL query → combined payload JSON | Final |
| `combine.py` | Payloads + originals → annotated output files | Final |
| `explainer.py` | Score → NL explanation via Ollama | 🔜 Phase 2 |
| `run.py` | End-to-end test runner | 🔜 Phase 2 |
| `output.json` | 840 validated period records | Generated |
| `goals_config.json` | 35 static goal configs | Generated |
| `output_updated.json` | Annotated records → for System 3 | Generated |
| `goals_config_updated.json` | Annotated goal configs → for System 3 | Generated |

## Dependencies

```
pandas
pydantic
requests
```

Ollama (local): https://ollama.com — pull `qwen2.5:7b-instruct` or `qwen2.5:3b`