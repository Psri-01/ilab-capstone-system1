# Data Dictionary

## Synthetic Dataset for UTS Innovation Lab Coherence Engine

This document provides complete field definitions for all tables in the dataset.

---

## Table of Contents

1. [periods.csv](#periodscsv)
2. [projections.csv](#projectionscsv)
3. [buckets.csv](#bucketscsv)
4. [goals.csv](#goalscsv)
5. [allocations.csv](#allocationscsv)
6. [outputs.csv](#outputscsv)
7. [metrics.csv](#metricscsv)
8. [derived_fields.csv](#derived_fieldscsv)
9. [analytical_flat.csv](#analytical_flatcsv)

---

## periods.csv

**Description**: Monthly time periods with budget information.

**Row Count**: 24

| Field | Type | Description | Value Range | Example |
|-------|------|-------------|-------------|---------|
| `period_id` | int | Unique period identifier | 1-24 | 1 |
| `start_date` | date | First day of month | 2024-01-01 to 2025-12-01 | 2024-01-01 |
| `end_date` | date | Last day of month | 2024-01-31 to 2025-12-31 | 2024-01-31 |
| `total_budget_available` | float | Total budget for this period (dollars) | 800,000 or 1,000,000 | 1000000.00 |
| `total_time_hours_available` | float | Total staff hours available | Always 2000 | 2000.0 |

**Special Cases**:
- Periods 10-12 have `total_budget_available` = $800,000 (20% shock reduction)
- All other periods have $1,000,000

---

## projections.csv

**Description**: Single operational projection spanning all periods.

**Row Count**: 1

| Field | Type | Description | Value Range | Example |
|-------|------|-------------|-------------|---------|
| `projection_id` | int | Unique projection identifier | Always 1 | 1 |
| `name` | string | Projection name | "Operational" | Operational |
| `start_period` | int | First period of projection | Always 1 | 1 |
| `end_period` | int | Last period of projection | Always 24 | 24 |

---

## buckets.csv

**Description**: 3-level budget hierarchy (L1 → L2 → L3).

**Row Count**: 53 (4 L1 + 14 L2 + 35 L3)

| Field | Type | Description | Value Range | Example |
|-------|------|-------------|-------------|---------|
| `bucket_id` | int | Unique bucket identifier | 1-53 | 5 |
| `parent_bucket_id` | int | ID of parent bucket | 1-53 or NULL (for L1) | 1 |
| `projection_id` | int | Reference to projection | Always 1 | 1 |
| `bucket_name` | string | Human-readable bucket name | Various | Google Ads - Search |
| `bucket_level` | int | Hierarchy level | 1, 2, or 3 | 3 |
| `allocation_percentage_of_parent` | float | % of parent bucket's allocation | 0.0-1.0 | 0.40 |
| `allocation_percentage_of_total` | float | % of total budget | 0.0-1.0 | 0.056 |
| `is_leaf` | boolean | True if leaf bucket (L3 only) | True/False | True |

**Relationships**:
- L1 buckets: `parent_bucket_id` is NULL, `allocation_percentage_of_parent` = 1.0
- L2 buckets: `parent_bucket_id` references L1
- L3 buckets: `parent_bucket_id` references L2, `is_leaf` = True

**Hierarchy Example**:
```
Marketing (L1, 40% of total)
  └─ Paid Acquisition (L2, 35% of Marketing = 14% of total)
      └─ Google Ads - Search (L3, 40% of Paid Acq = 5.6% of total)
```

---

## goals.csv

**Description**: SMARTeR goals with symmetric range bands, one per leaf bucket.

**Row Count**: 35

| Field | Type | Description | Value Range | Example |
|-------|------|-------------|-------------|---------|
| `goal_id` | int | Unique goal identifier | 1-35 | 1 |
| `bucket_id` | int | Reference to leaf bucket | Leaf bucket IDs only | 9 |
| `metric_name` | string | Name of performance metric | Various | CAC - Search |
| `metric_unit` | string | Unit of measurement | Various | dollars |
| `start_period` | int | First period of goal | Always 1 | 1 |
| `end_period` | int | Last period of goal | Always 24 | 24 |
| `target_value_final_period` | float | Goal target by period 24 | Varies by metric | 45.0 |
| `initial_value` | float | Starting metric value (period 1) | Varies by metric | 75.0 |
| `minimum_viable_allocation` | float | Minimum % of total budget needed | 0.0-1.0 | 0.045 |
| `optimal_allocation_min` | float | Lower bound of green band | 0.0-1.0 | 0.052 |
| `optimal_allocation_max` | float | Upper bound of green band | 0.0-1.0 | 0.062 |
| `red_low_max` | float | Severely underfunded threshold | 0.0-1.0 | 0.035 |
| `orange_low_max` | float | Moderately underfunded threshold | 0.0-1.0 | 0.045 |
| `green_min` | float | Entering optimal zone (= optimal_allocation_min) | 0.0-1.0 | 0.052 |
| `green_max` | float | Exiting optimal zone (= optimal_allocation_max) | 0.0-1.0 | 0.062 |
| `orange_high_min` | float | Moderately overfunded threshold | 0.0-1.0 | 0.070 |
| `red_high_min` | float | Severely overfunded threshold | 0.0-1.0 | 0.080 |
| `scenario_story` | string | Embedded scenario pattern | underfunded, overfunded, optimal, dynamic | underfunded |

**Symmetric Range Bands**:
```
red_low_max < orange_low_max < green_min < green_max < orange_high_min < red_high_min
    ↓             ↓              ↓           ↓            ↓                ↓
Severely      Moderately      OPTIMAL     OPTIMAL    Moderately      Severely
Under         Under           START       END        Over            Over
```

**Scenario Stories**:
- `underfunded` (8 goals): Consistently below minimum_viable in periods 1-18
- `overfunded` (8 goals): Consistently above optimal_max in periods 8-24
- `optimal` (10 goals): Near green band center throughout
- `dynamic` (9 goals): Shift between categories in periods 12-14

---

## allocations.csv

**Description**: Per-period budget allocations for each leaf bucket.

**Row Count**: 840 (35 leaf buckets × 24 periods)

| Field | Type | Description | Value Range | Example |
|-------|------|-------------|-------------|---------|
| `allocation_id` | int | Unique allocation record ID | 1-840 | 1 |
| `bucket_id` | int | Reference to leaf bucket | Leaf bucket IDs | 9 |
| `period_id` | int | Reference to period | 1-24 | 1 |
| `allocated_amount` | float | Budget allocated (dollars) | 0.0+ | 42000.00 |
| `allocated_time_hours` | float | Staff hours allocated | 0.0+ | 84.0 |
| `allocation_percentage_of_total` | float | % of total period budget | 0.0-1.0 | 0.042 |
| `allocation_percentage_of_parent` | float | % of parent bucket allocation | 0.0-1.0 | 0.30 |

**Key Constraints**:
- For each period, all `allocation_percentage_of_total` sum to 1.0 (100%)
- `allocated_amount` = `allocation_percentage_of_total` × period `total_budget_available`
- Budget shock applied: periods 10-12 have lower `allocated_amount` values

---

## outputs.csv

**Description**: Delivered outputs with quality scores, includes lag effects.

**Row Count**: 840

| Field | Type | Description | Value Range | Example |
|-------|------|-------------|-------------|---------|
| `output_id` | int | Unique output record ID | 1-840 | 1 |
| `bucket_id` | int | Reference to leaf bucket | Leaf bucket IDs | 9 |
| `period_id` | int | Reference to period | 1-24 | 1 |
| `delivered_output_quantity` | float | Units of output delivered | 0.0+ | 850.0 |
| `delivered_output_quality_score` | float | Output quality measure | 0.0-1.0 | 0.78 |
| `output_cost_per_unit` | float | Cost efficiency ($/unit) | 0.0+ | 49.41 |
| `total_cost` | float | Total cost (= allocated_amount) | 0.0+ | 42000.00 |

**Key Relationships**:
- Output quantity responds to allocations with 2-3 period lag
- Diminishing returns: ratio > 1.5 of optimal reduces marginal output
- Quality score peaks in green band, declines when under/overfunded
- Cost per unit = `allocated_amount` / `delivered_output_quantity`

---

## metrics.csv

**Description**: Goal performance metrics with trajectories and statistics.

**Row Count**: 840

| Field | Type | Description | Value Range | Example |
|-------|------|-------------|-------------|---------|
| `metric_id` | int | Unique metric record ID | 1-840 | 1 |
| `goal_id` | int | Reference to goal | 1-35 | 1 |
| `period_id` | int | Reference to period | 1-24 | 1 |
| `observed_value` | float | Actual metric reading | Varies by metric | 72.5 |
| `expected_value` | float | Target trajectory value | Varies by metric | 70.0 |
| `variance_from_target` | float | Distance to final target | Varies by metric | 27.5 |
| `trailing_3_period_avg` | float | Rolling 3-period average | Varies by metric | 72.5 |
| `trailing_6_period_slope` | float | Linear regression slope over 6 periods | Any | 0.0 |
| `volatility_measure` | float | Standard deviation over 6 periods | 0.0+ | 0.0 |

**Key Patterns**:
- Underfunded goals: Slow improvement, plateau by period 18
- Overfunded goals: Fast initial growth, plateau/decline by period 20
- Optimal goals: Steady linear improvement to target
- Market shock: -15% to growth metrics in periods 14-17

---

## derived_fields.csv

**Description**: Pre-computed derived metrics for coherence analysis.

**Row Count**: 840

| Field | Type | Description | Value Range | Example |
|-------|------|-------------|-------------|---------|
| `derived_id` | int | Unique derived record ID | 1-840 | 1 |
| `goal_id` | int | Reference to goal | 1-35 | 1 |
| `period_id` | int | Reference to period | 1-24 | 1 |
| `range_position_score` | float | Continuous position in range bands | 0.0-1.0 | 0.28 |
| `status_band` | string | Categorical band assignment | red_low, orange_low, green, orange_high, red_high | orange_low |
| `underfunded_flag` | boolean | True if below minimum viable | True/False | True |
| `overfunded_flag` | boolean | True if above optimal max | True/False | False |
| `allocation_efficiency_ratio` | float | Current vs. avg efficiency | 0.0+ | 0.87 |
| `probability_of_hitting_target` | float | Heuristic attainability score | 0.0-1.0 | 0.35 |
| `time_to_green_estimate` | int | Estimated periods until green band | 0+ or -1 | 12 |
| `weighted_goal_status_score` | float | Used for parent bucket rollup | 0.0-1.0 | 0.28 |
| `allocation_fitness_score` | float | 1.0 if green, 0.0 otherwise | 0.0 or 1.0 | 0.0 |

**Range Position Score Mapping**:
- 0.0-0.1: red_low (severely underfunded)
- 0.1-0.35: orange_low (moderately underfunded)
- 0.35-0.65: green (OPTIMAL)
- 0.65-0.9: orange_high (moderately overfunded)
- 0.9-1.0: red_high (severely overfunded)

---

## analytical_flat.csv

**Description**: Denormalized view with all tables joined for easy analysis.

**Row Count**: 840

Contains all fields from all tables above, joined on foreign keys. Use this file for:
- Quick exploratory analysis
- Avoiding complex joins
- Pandas/R analysis workflows

**Join Logic**:
```
allocations (base)
  ← buckets (on bucket_id)
  ← periods (on period_id)
  ← goals (on bucket_id)
  ← outputs (on bucket_id, period_id)
  ← metrics (on goal_id, period_id)
  ← derived_fields (on goal_id, period_id)
```

---

## Relationships Diagram

```
projection (1)
    ↓
buckets (53)
    ↓
goals (35) ────┬──── periods (24)
               │          ↓
          allocations (840)
                    ↓
              outputs (840)
                    ↓
              metrics (840)
                    ↓
          derived_fields (840)
```

---

## Data Generation Details

- **Random Seed**: 42 (reproducible)
- **Normalization**: All allocations per period sum to exactly 100%
- **Lag Implementation**: Weighted moving average with exponential decay
- **Diminishing Returns**: Logarithmic scaling above optimal ratio
- **Noise Levels**: ±10-15% for outputs, ±10-20% for metrics

---

## Common Queries

### Find Goals by Scenario

```sql
SELECT goal_id, metric_name, scenario_story
FROM goals
WHERE scenario_story = 'underfunded';
```

### Calculate Period Coherence

```sql
SELECT period_id,
       AVG(CASE WHEN status_band = 'green' THEN 1.0 ELSE 0.0 END) as coherence_score
FROM derived_fields
GROUP BY period_id
ORDER BY period_id;
```

### Identify Diminishing Returns

```sql
SELECT g.goal_id, g.metric_name,
       AVG(CASE WHEN p.period_id <= 12 THEN o.output_cost_per_unit END) as early_cost,
       AVG(CASE WHEN p.period_id > 12 THEN o.output_cost_per_unit END) as late_cost
FROM goals g
JOIN outputs o ON g.bucket_id = o.bucket_id
WHERE g.scenario_story = 'overfunded'
GROUP BY g.goal_id, g.metric_name
HAVING late_cost > early_cost * 1.2;
```

---

## Data Quality Guarantees

✅ No null values in required fields
✅ All foreign keys resolve
✅ All percentages sum to 100% where expected
✅ All range bands properly ordered
✅ All quality scores between 0-1
✅ All probability values between 0-1
✅ Budget shock visible in data
✅ Scenario patterns validated

---

**Last Updated**: 2026-02-20
**Version**: 1.0.0
