import requests
import json

def explain(user_query: str, period_record: dict, goal_config: dict) -> str:
    prompt = f"""You are an AI assistant for Decidr, a decision support system.

A user asked: "{user_query}"

Goal configuration:
- Goal ID: {goal_config['goal_id']}
- Target by final period: {goal_config['target_value_final_period']}
- Green band: {goal_config['green_min']} to {goal_config['green_max']}
- Current status band: {period_record['status_band']}

Current period data (Period {period_record['period_id']}):
- Allocation: ${period_record['allocation_amount']:,}
- Range position score: {period_record['range_position_score']} (0=worst, 1=best)
- Probability of hitting target: {period_record['probability_of_hitting_target']}
- Underfunded: {period_record['underfunded_flag']}
- Overfunded: {period_record['overfunded_flag']}

Respond in 3-4 plain English sentences. State the current status, 
why it is performing this way, and one concrete recommendation.
Do not use jargon or bullet points."""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "qwen2.5:3b", "prompt": prompt, "stream": False},
            timeout=120
        )
        # print("Status:", response.status_code)
        # print("Raw response:", response.text[:300])  # add this
        return response.json()["response"]
    except Exception as e:
        return f"[Ollama error: {e}]"