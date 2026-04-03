import pandas as pd
import json
from pydantic import ValidationError
from models import GoalConfig, PeriodRecord

def load_and_validate():
    valid_records = []
    valid_goals = {}
    errors = []

    print("Loading CSV files...")
    try:
        goals_df = pd.read_csv('goals.csv')
        records_df = pd.read_csv('analytical_flat.csv')
    except FileNotFoundError as e:
        print(f"Error: Could not find CSV files. {e}")
        return [], {}, [{"error": "Missing CSV files"}]

    # 1. Validate the Static Goals (Option B)
    print(f"Validating {len(goals_df)} goal configs...")
    for idx, row in goals_df.iterrows():
        try:
            # .dropna().to_dict() prevents Pandas from passing 'NaN' for empty cells
            row_dict = row.dropna().to_dict() 
            goal = GoalConfig(**row_dict)
            # Store by goal_id so we can easily look it up for the LLM prompt later
            valid_goals[goal.goal_id] = goal.model_dump() 
        except ValidationError as e:
            errors.append({
                "source": "goals.csv", 
                "row_index": idx, 
                "goal_id": row.get("goal_id", "Unknown"),
                "error": e.errors() # Extracts the clean Pydantic error dictionary
            })

    # 2. Validate the Period Records (Option A)
    print(f"Validating {len(records_df)} period records...")
    for idx, row in records_df.iterrows():
        try:
            row_dict = row.dropna().to_dict()
            record = PeriodRecord(**row_dict)
            valid_records.append(record.model_dump())
        except ValidationError as e:
            errors.append({
                "source": "analytical_flat.csv", 
                "row_index": idx, 
                "period": row.get("period_id", "Unknown"),
                "goal_id": row.get("goal_id", "Unknown"),
                "error": e.errors()
            })

    return valid_records, valid_goals, errors

if __name__ == "__main__":
    # Execute the loader when running this script directly
    records, goals, errors = load_and_validate()
    
    # Export Option A (The Time-Series Data)
    with open("output.json", "w") as f:
        json.dump(records, f, indent=2)
        
    # Export Option B (The Static Configs)
    with open("goals_config.json", "w") as f:
        json.dump(goals, f, indent=2)

    # Export the Error Log
    with open("errors.json", "w") as f:
        json.dump(errors, f, indent=2)

    print("-" * 30)
    print(f"SUCCESS: Exported {len(records)} valid period records to output.json")
    print(f"SUCCESS: Exported {len(goals)} valid goal configs to goals_config.json")
    print(f"ERRORS: {len(errors)} rows failed validation (Logged in errors.json)")