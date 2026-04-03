from pydantic import BaseModel, Field
from typing import Literal, Union

class UserIntent(BaseModel):
    query_type: Literal["metric_name_analysis", "compare_periods", "trend_analysis"]

class GoalConfig(BaseModel):
    """
    Option B — goals style (per goal, static config)
    Mapped exactly to goals.csv headers.
    """
    goal_id: int
    # metric_name: str
    bucket_id: Union[int, str]  # Accepts 19 or "L3-07"
    
    target_value_final_period: float
    
    # Range bands matching actual CSV columns
    red_low_max: float
    orange_low_max: float
    green_min: float
    green_max: float
    orange_high_min: float
    red_high_min: float

class PeriodRecord(BaseModel):
    """
    Option A — analytical_flat style (per row / per period)
    Mapped exactly to analytical_flat.csv headers.
    """
    period_id: int = Field(ge=1, le=24)
    bucket_id: Union[int, str]
    goal_id: int
    # metric_name: str
    scenario_story: str
    
    # Financial/Quantity metrics matching CSV
    allocated_amount: float 
    delivered_output_quantity: float 
    delivered_output_quality_score: float
    
    observed_value: float
    expected_value: float
    
    # Strictly bounded metrics
    range_position_score: float = Field(ge=0.0, le=1.0)
    probability_of_hitting_target: float = Field(ge=0.0, le=1.0)
    
    # Categorical / Enums
    status_band: Literal["red_low", "orange_low", "green", "orange_high", "red_high"]
    
    # Booleans
    underfunded_flag: bool
    overfunded_flag: bool
    
    # Ratios and Time Estimates
    allocation_efficiency_ratio: float
    time_to_green_estimate: int