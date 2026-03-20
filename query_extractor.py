import json

def extract_query_params(user_query: str) -> dict:
    query = user_query.lower()
    words = query.split()
    params = {}

    for i, word in enumerate(words):
        clean = word.strip("?.,")
        if clean.isdigit():
            prev = words[i-1] if i > 0 else ""
            if "goal" in prev:
                params["goal_id"] = int(clean)
            elif "period" in prev:
                params["period_id"] = int(clean)

    if "underfunded" in query:
        params["underfunded_flag"] = True
    if "overfunded" in query:
        params["overfunded_flag"] = True

    return params


def build_combined_payload(user_query: str, goal_configs: list, period_records: list) -> dict:
    """
    Takes English query + 2 JSON files from System 3.
    Returns one combined JSON ready to send back to System 3.
    """
    query_params = extract_query_params(user_query)

    goal_id   = query_params.get("goal_id")
    period_id = query_params.get("period_id")

    # Match goal config
    goal_config = next(
        (g for g in goal_configs if g["goal_id"] == goal_id), None
    ) if goal_id else None

    # Match period record(s)
    if goal_id and period_id:
        # Specific record
        matched_records = [
            r for r in period_records
            if r["goal_id"] == goal_id and r["period_id"] == period_id
        ]
    elif goal_id:
        # All periods for this goal
        matched_records = [r for r in period_records if r["goal_id"] == goal_id]
    elif query_params.get("underfunded_flag"):
        matched_records = [r for r in period_records if r.get("underfunded_flag") == True]
    elif query_params.get("overfunded_flag"):
        matched_records = [r for r in period_records if r.get("overfunded_flag") == True]
    else:
        matched_records = []

    return {
        "user_query": user_query,
        "extracted_params": query_params,
        "goal_config": goal_config,
        "period_records": matched_records   # list — System 3 handles filtering further
    }


if __name__ == "__main__":
    with open("output.json") as f:
        period_records = json.load(f)
    with open("goals_config.json") as f:
        goal_configs = list(json.load(f).values())

    queries = [
        "How is Goal 1 doing in Period 3?",
        "Which goals are underfunded right now?",
        "What is the probability of Goal 17 hitting its target by Period 24?"
    ]

    for i, q in enumerate(queries, 1):
        payload = build_combined_payload(q, goal_configs, period_records)
        filename = f"combined_payload_{i}.json"
        with open(filename, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"Query {i}: '{q}'")
        print(f"  → goal_id: {payload['extracted_params'].get('goal_id')} | "
              f"period_id: {payload['extracted_params'].get('period_id')} | "
              f"records matched: {len(payload['period_records'])}")
        print(f"  → saved to {filename}")