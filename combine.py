import json

# Load originals
with open("output.json") as f:
    period_records = json.load(f)

with open("goals_config.json") as f:
    goal_configs_raw = json.load(f)
    goal_configs = list(goal_configs_raw.values())

# Load the 3 payloads
payloads = []
for i in range(1, 4):
    with open(f"combined_payload_{i}.json") as f:
        payloads.append(json.load(f))

# --- Build output_updated.json ---
# Annotate any period record that was referenced in a payload
# with which query triggered it

queried_records = {}  # key: (goal_id, period_id) → list of queries

for payload in payloads:
    for r in payload.get("period_records", []):
        key = (r["goal_id"], r["period_id"])
        if key not in queried_records:
            queried_records[key] = []
        queried_records[key].append(payload["user_query"])

output_updated = []
for r in period_records:
    record = r.copy()
    key = (r["goal_id"], r["period_id"])
    if key in queried_records:
        record["queried_by"] = queried_records[key]
    output_updated.append(record)

with open("output_updated.json", "w") as f:
    json.dump(output_updated, f, indent=2)

# --- Build goals_config_updated.json ---
# Annotate any goal config referenced in a payload

queried_goals = {}  # key: goal_id → list of queries

for payload in payloads:
    gc = payload.get("goal_config")
    if gc:
        gid = gc["goal_id"]
        if gid not in queried_goals:
            queried_goals[gid] = []
        queried_goals[gid].append(payload["user_query"])

goals_config_updated = {}
for key, g in goal_configs_raw.items():
    config = g.copy()
    if config["goal_id"] in queried_goals:
        config["queried_by"] = queried_goals[config["goal_id"]]
    goals_config_updated[key] = config

with open("goals_config_updated.json", "w") as f:
    json.dump(goals_config_updated, f, indent=2)

print(f"output_updated.json → {len(output_updated)} records "
      f"({len(queried_records)} annotated with query context)")
print(f"goals_config_updated.json → {len(goals_config_updated)} goals "
      f"({len(queried_goals)} annotated with query context)")