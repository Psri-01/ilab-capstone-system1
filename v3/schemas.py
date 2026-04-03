"""
Decidr Coherence Engine — System 1 Schemas (v2)
Mapped to actual v4 dataset: goals.csv, buckets.csv, analytical_flat.csv

Key change from v1: Structured fields for everything EXCEPT goal title,
which is the only field extracted from NL input via NLP.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ── Bucket hierarchy from buckets.csv ──────────────────────────────────────

BUCKET_HIERARCHY: dict[str, dict[str, list[str]]] = {
    "Marketing": {
        "Paid Acquisition": ["Google Ads - Search", "Google Ads - Display", "Social Media Ads"],
        "Content & SEO": ["Blog Content Production", "SEO Optimization", "Video Content"],
        "Partnerships": ["Partner Acquisition", "Co-Marketing Campaigns", "Channel Partnerships"],
        "Events & Community": ["Virtual Events", "In-Person Events", "Community Management"],
    },
    "Product": {
        "Core Platform": ["Backend Services", "Frontend Development", "APIs & Integrations"],
        "New Features": ["Feature Development", "A/B Testing", "Feature Launch"],
        "Technical Debt": ["Code Refactoring", "Infrastructure Upgrades"],
        "Research & Innovation": ["Proof of Concepts", "Innovation Labs"],
    },
    "Operations": {
        "Customer Success": ["Onboarding", "Support Tickets", "Account Management"],
        "Infrastructure & DevOps": ["Cloud Infrastructure", "CI/CD Pipeline"],
        "Data & Analytics": ["Data Engineering", "Analytics & Reporting"],
    },
    "G&A": {
        "Finance & Legal": ["Financial Planning", "Legal & Compliance"],
        "HR & Recruiting": ["Talent Acquisition", "Employee Development"],
        "General Admin": ["Office Operations", "Vendor Management"],
    },
}

# ── Constants from goals.csv ───────────────────────────────────────────────

METRIC_UNITS = [
    "score", "percentage", "ratio", "count", "dollars",
    "visitors", "leads", "attendees", "ms", "seconds",
    "hours", "days", "projects",
]

SCENARIOS = ["optimal", "underfunded", "overfunded", "dynamic"]

# Dimension labels — aligned per client feedback
DIMENSIONS = ["coherence", "attainability", "relevance", "integrity"]

DIMENSION_WEIGHTS = {
    "coherence": 0.35,
    "attainability": 0.25,
    "relevance": 0.20,
    "integrity": 0.20,
}


# ── Models ─────────────────────────────────────────────────────────────────

class GoalInput(BaseModel):
    """
    Structured goal input for System 3.

    All fields are structured form inputs EXCEPT goal_title,
    which is extracted from NL via NLP.
    """
    goal_title: str = Field(description="Extracted from NL input via NLP")
    bucket_l1: str = Field(description="L1 division (Marketing, Product, Operations, G&A)")
    bucket_l2: str = Field(description="L2 department")
    bucket_l3: str = Field(description="L3 function (leaf bucket)")
    metric_name: str = Field(description="e.g. NPS Score, Organic Traffic")
    metric_unit: str = Field(description="One of METRIC_UNITS")
    target_value: Optional[float] = Field(default=None)
    initial_value: Optional[float] = Field(default=None)
    periods: int = Field(default=24, description="Number of periods (default 24)")
    scenario_story: str = Field(default="optimal", description="One of SCENARIOS")


class System3Payload(BaseModel):
    """
    Complete payload sent to System 3 (Ann's team).
    Contains raw NL input + structured goal.
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    goal: GoalInput
    raw_nl_input: str = Field(description="Original NL text — always preserved")
    metadata: dict = Field(default_factory=lambda: {
        "source": "system_1",
        "version": "0.2.0",
        "destination": "system_3",
    })

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


class System2ScoreResponse(BaseModel):
    """
    Score payload returned from System 2 via System 3.
    Used by System 1 to generate confidence-hedged output.

    Maps to: 07_score_goal.py return payload
    """
    goal_id: int
    attainability: float
    relevance: float
    coherence: float
    integrity: float
    overall: float
    gp_mean: float
    gp_std: float
    gp_weight: float
    llm_weight: float
    baseline: float
    uncertain: bool
    reasoning: dict[str, str] = Field(description="One sentence per dimension from LLMs")
    ensemble_meta: dict = Field(description="Per-dimension blend weights and variance")
    n_llm_ok: int
    status: str


# ── Confidence hedging helpers ─────────────────────────────────────────────

def confidence_label(score_response: System2ScoreResponse) -> str:
    """Generate confidence label for output display."""
    if score_response.uncertain:
        return f"Elevated Uncertainty (σ = {score_response.gp_std:.4f})"
    return f"High Confidence (σ = {score_response.gp_std:.4f})"


def risk_flag(composite: float) -> str:
    """Risk classification per 08_composite_score.py thresholds."""
    if composite < 0.20:
        return "critical"
    if composite < 0.35:
        return "at_risk"
    return "on_track"


def hedged_summary(score_response: System2ScoreResponse) -> str:
    """
    Generate a confidence-hedged NL summary for System 1 output.
    Uses reasoning strings from System 2 — does NOT re-call LLMs.
    """
    risk = risk_flag(score_response.overall)
    conf = "with high confidence" if not score_response.uncertain else "with elevated uncertainty"

    # Lead with composite
    summary = f"This goal scores {score_response.overall:.1%} overall coherence {conf}."

    # Strongest and weakest dimension
    dims = {
        "coherence": score_response.coherence,
        "attainability": score_response.attainability,
        "relevance": score_response.relevance,
        "integrity": score_response.integrity,
    }
    strongest = max(dims, key=dims.get)
    weakest = min(dims, key=dims.get)

    summary += (
        f" {strongest.capitalize()} is the strongest dimension at {dims[strongest]:.1%},"
        f" while {weakest} scores lowest at {dims[weakest]:.1%}."
    )

    if risk == "critical":
        summary += " ⚠ This goal is flagged as CRITICAL and requires immediate attention."
    elif risk == "at_risk":
        summary += " ⚠ This goal is AT RISK and should be reviewed."

    if score_response.uncertain:
        summary += (
            f" Note: GP uncertainty is elevated (σ = {score_response.gp_std:.4f}),"
            " so the attainability estimate should be treated as directional."
        )

    return summary
