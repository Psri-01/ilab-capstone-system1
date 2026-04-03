"""
Decidr Coherence Engine — System 1 Goal Extractor (v2 - Groq API)

Simplified per lead's guidance: ONLY extracts goal title from NL input.
All other fields (bucket, metric, target, scenario) are structured form inputs.

This is the one NLP operation in the input pipeline.
Now using Groq API instead of local Ollama.
"""

import json
import os
import logging
from typing import Optional

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    """Extract goal title from natural language using Groq API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        use_llm: bool = True,
    ):
        """
        Initialize Goal Extractor with Groq API.
        
        Args:
            api_key: Groq API key (if None, reads from GROQ_API_KEY env var)
            model: Groq model to use (default: llama-3.3-70b-versatile)
            use_llm: Whether to use LLM or fall back to heuristics
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.use_llm = use_llm
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        
        if self.use_llm and not self.api_key:
            logger.warning("No Groq API key found. Set GROQ_API_KEY in .env file. Falling back to heuristics.")
            self.use_llm = False

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
        """Call Groq API to extract goal title."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": nl_input},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        resp = requests.post(
            self.groq_url,
            headers=headers,
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]
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
        title = nl_input.strip()
        for sep in [".", ",", " by ", " through ", " via "]:
            parts = nl_input.split(sep)
            if len(parts) > 1:
                title = parts[0].strip()
                break

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
