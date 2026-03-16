# ilab-capstone-system1
System 1 acts as the 'eyes and mouth', aka input and output of the Decidr Coherence Engine (of 3 systems as a whole). This is a part of the UTS iLab Capstone project for MDSI.

## Decidr Coherence Engine: System 1 POC Status
Phase 1: The Input Pipeline (Completed)
Objective: Establish a strict, schema-validated boundary between the raw CSV data and System 2, following the Brenndoerfer "Schema-First" architecture.

## What We Did:
Defined the Interface Contract: We mapped the exact column headers from goals.csv and analytical_flat.csv into two strict Pydantic models (GoalConfig and PeriodRecord).
Built the Gatekeeper: We wrote loader.py to ingest the CSVs via Pandas and pass every single row through the Pydantic models.
Resolved Data Drift: The initial run caught several schema mismatches (e.g., column name discrepancies like target_value_final_period vs target_value_period_24, and type coercion issues with bucket_id). These were corrected in the models.

Final Output: The pipeline successfully ran with 0 errors. It generated two mathematically clean, strictly-typed JSON files ready for the LLM and System 2:

output.json (Option A - Time-series period records)
goals_config.json (Option B - Static goal configurations/thresholds)

Current Architecture State:
models.py: Contains the finalized Pydantic schemas.
loader.py: The ETL script that validates and outputs the JSONs.

Handoff Note: Next Steps for Phase 2 (LLM Integration)
We now have a bulletproof Pydantic validation layer. The raw CSVs are successfully converting into clean, strictly-typed JSONs (output.json and goals_config.json). The data is ready for further analysis.

The goal for this phase is to prove the LLM connection works by generating one single explanation for a hardcoded goal (pick a poorly performing/underfunded one to make it interesting).

Here is a game plan for the explainer.py script:

1. Environment Setup
We are using Ollama locally for this POC to keep things fast and free.
Install Ollama on your machine.
Run ollama run qwen2.5:7b-instruct in your terminal to pull the model.

2. Build explainer.py
Write a script that does the following:
Loads the two JSON files generated (output.json and goals_config.json).
Finds a specific record (e.g., the record with the worst range_position_score).
Finds that record's matching static config using the goal_id.
Injects both JSON objects into a prompt string.
Uses the requests library or the official Python Ollama client to ping the local Qwen2.5 API.

3. The Prompt Template (Crucial)
When you build the prompt template, remember the two big takeaways from our literature review on Explainable AI (XAI):
Context is everything: You must feed the LLM both the period record (what happened) AND the goal config (what the thresholds are). Without the config, the LLM won't know if a score of "0.21" is a disaster or just slightly below average.

The Confidence Hedge: Research shows LLMs overstate confidence when explaining metrics. You need to explicitly instruct Qwen2.5 to look at the data (and any uncertainty metrics) and hedge its language. Add an instruction like: "If the score is low, use phrasing that reflects uncertainty (e.g., 'The data suggests...' or 'Potential factors include...') rather than stating it as absolute fact."

4. Tie it together in run.py
Once your explainer function works, create a quick run.py to act as the entry point:

Python
# run.py skeleton
from loader import load_and_validate
from explainer import explain_record

#### 1. Ensure data is fresh and valid
records, goals, errors = load_and_validate()

#### 2. Pick the worst performing record (just for the POC)
(Add your logic here to sort/filter records)
target_record = records[0] # Placeholder

#### 3. Get the matching config
target_config = goals[str(target_record['goal_id'])]

#### 4. Generate the narrative
explanation = explain_record(target_record, target_config)
print(explanation)