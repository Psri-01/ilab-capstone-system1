"""
Decidr Coherence Engine — System 1 Goal Extractor (v2)

Simplified per lead's guidance: ONLY extracts goal title from NL input.
All other fields (bucket, metric, target, scenario) are structured form inputs.

This is the one NLP operation in the input pipeline.
"""

import json
import re
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


EXTRACT_SYSTEM_PROMPT = """You are a goal title extractor. Given a natural language goal description, extract:
1. A concise goal title (max 8 words)  
2. If a metric name is mentioned, suggest it
3. If a unit type is detectable, suggest it

Respond ONLY with a JSON object (no markdown, no backticks):
{
  "goal_title": "concise title, max 8 words",
  "metric_suggestion": "suggested metric name if detectable, else empty string",
  "unit_suggestion": "one of: score, percentage, ratio, count, dollars, visitors, leads, attendees, ms, seconds, hours, days, projects — or empty string if not detectable"
}"""


class GoalExtractor:
    """Extract goal title from natural language. Minimal NLP — one field only."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        use_llm: bool = True,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.use_llm = use_llm

    def extract(self, nl_input: str) -> dict:
        """
        Extract goal title (and optional metric/unit suggestions) from NL.

        Returns:
            {"goal_title": str, "metric_suggestion": str, "unit_suggestion": str}
        """
        if self.use_llm:
            try:
                return self._extract_with_llm(nl_input)
            except Exception as e:
                logger.warning(f"LLM extraction failed, using fallback: {e}")

        return self._extract_with_heuristics(nl_input)

    def _extract_with_llm(self, nl_input: str) -> dict:
        """Call Ollama to extract goal title."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": nl_input},
            ],
            "stream": False,
            "format": "json",
        }

        resp = requests.post(
            f"{self.ollama_url}/api/chat",
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()

        content = resp.json()["message"]["content"]
        clean = content.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(clean)

        return {
            "goal_title": result.get("goal_title", "")[:80],
            "metric_suggestion": result.get("metric_suggestion", ""),
            "unit_suggestion": result.get("unit_suggestion", ""),
        }

    def _extract_with_heuristics(self, nl_input: str) -> dict:
        """Simple keyword-based extraction when LLM is unavailable."""
        # Take first clause as title
        for sep in [".", ",", " by ", " through ", " via "]:
            parts = nl_input.split(sep)
            if len(parts) > 1:
                title = parts[0].strip()
                break
        else:
            title = nl_input.strip()

        # Clean common prefixes
        for prefix in ["I want to ", "We need to ", "Our goal is to ", "I'd like to ",
                        "We want to ", "The goal is to ", "We aim to "]:
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix):]
                break

        # Truncate to ~8 words
        words = title.split()[:8]
        title = " ".join(words)

        # Detect metric/unit hints
        text_lower = nl_input.lower()
        unit = ""
        metric = ""

        unit_keywords = {
            "percentage": ["%", "percent", "rate"],
            "score": ["score", "rating"],
            "ratio": ["ratio", "roas", "roi"],
            "count": ["count", "number of"],
            "dollars": ["$", "dollar", "revenue", "budget"],
            "visitors": ["visitor", "traffic"],
            "days": ["days", "time to"],
            "hours": ["hours"],
        }
        for u, keywords in unit_keywords.items():
            if any(kw in text_lower for kw in keywords):
                unit = u
                break

        return {
            "goal_title": title.capitalize() if title else "",
            "metric_suggestion": metric,
            "unit_suggestion": unit,
        }
