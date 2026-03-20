import json
from explainer import explain

# Load output.json (already a list)
with open("output.json") as f:
    period_records = json.load(f)

# Load goals_config.json (dict keyed by "1","2"... → convert to list)
with open("goals_config.json") as f:
    goal_configs = list(json.load(f).values())

# Fix field name to match your actual output.json
for r in period_records:
    if "allocated_amount" in r and "allocation_amount" not in r:
        r["allocation_amount"] = r["allocated_amount"]

# --- Test 1: worst performing goal (lowest range_position_score) ---
worst = min(period_records, key=lambda r: r["range_position_score"])
config = next(g for g in goal_configs if g["goal_id"] == worst["goal_id"])

print("=== TEST 1: Worst Performing Goal ===")
print(f"Goal {worst['goal_id']} | Period {worst['period_id']} | "
      f"Score: {worst['range_position_score']} | Band: {worst['status_band']}")

# --- Test 2: a specific goal/period you choose ---
TARGET_GOAL = 17
TARGET_PERIOD = 18

record = next(
    (r for r in period_records if r["goal_id"] == TARGET_GOAL and r["period_id"] == TARGET_PERIOD),
    None
)
config2 = next((g for g in goal_configs if g["goal_id"] == TARGET_GOAL), None)

print("\n=== TEST 2: Specific Goal Query ===")
if record and config2:
    print(f"Goal {TARGET_GOAL} | Period {TARGET_PERIOD}")
    print(explain("What would need to change for this goal to reach green?", record, config2))
else:
    print(f"Goal {TARGET_GOAL} / Period {TARGET_PERIOD} not found in data — check your goal_id values in output.json")

# --- Test 3: contrastive — overfunded goal ---
overfunded = next((r for r in period_records if r.get("overfunded_flag") == True), None)
if overfunded:
    config3 = next(g for g in goal_configs if g["goal_id"] == overfunded["goal_id"])
    print("\n=== TEST 3: Overfunded Goal ===")
    print(f"Goal {overfunded['goal_id']} | Period {overfunded['period_id']}")
    print(explain("This goal is receiving too much funding. What does that mean?", overfunded, config3))
else:
    print("\n=== TEST 3: No overfunded records found ===")