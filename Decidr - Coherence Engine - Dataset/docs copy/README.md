# Synthetic Dataset for UTS Innovation Lab

## Coherence Engine for Goal-Aligned Decision Making

This dataset simulates a complete organizational decision-making system across 24 monthly periods, designed to enable students to build and test coherence scoring models for evaluating resource allocation decisions.

---

## Dataset Overview

### Purpose

This synthetic dataset allows students to explore four key evaluation dimensions:

1. **Relevance** - Is a given allocation justified based on requirements and goals?
2. **Coherence** - Is the set of allocations internally consistent and aligned with objectives?
3. **Integrity** - Do actual outcomes align with intended allocations?
4. **Attainability** - What's the likelihood of achieving a goal given current allocation and historical evidence?

### Key Features

- **24 monthly periods** (Jan 2024 - Dec 2025)
- **3-level budget hierarchy**: 4 L1 → 14 L2 → 35 L3 leaf buckets
- **35 SMARTeR goals** with symmetric range bands
- **Embedded scenario patterns**: 8 underfunded, 8 overfunded, 10 optimal, 9 dynamic
- **Budget shock**: 20% reduction in periods 10-12
- **Market shock**: 15% reduction to growth metrics in period 14
- **Lag effects**: Allocation → output → metric with 2-3 period delays
- **Diminishing returns**: Overfunding doesn't proportionally increase output

---

## Critical Innovation: Symmetric Range Bands

Unlike traditional models that only penalize underfunding, this dataset implements **symmetric range bands** where BOTH low and high allocations are suboptimal:

```
red_low < orange_low < green_min < GREEN < green_max < orange_high < red_high
    ↓          ↓           ↓        ↓        ↓           ↓           ↓
Severely  Moderately  Approaching OPTIMAL Approaching Moderately  Severely
Under     Under       Optimal    RANGE   Over      Over        Over
```

- **Underfunding** (red/orange low): Insufficient resources, slow progress
- **Optimal** (green band): Right level of investment, efficient returns
- **Overfunding** (orange/red high): Diminishing returns, wasted resources

---

## Dataset Structure

### Output Files

#### Normalized Tables (`output/normalized/`)

- `periods.csv` - 24 monthly periods with budget information
- `projections.csv` - Single "Operational" projection
- `buckets.csv` - 53 total buckets (4 L1, 14 L2, 35 L3 leaf)
- `goals.csv` - 35 SMARTeR goals with symmetric range bands
- `allocations.csv` - 840 allocation records (35 buckets × 24 periods)
- `outputs.csv` - 840 output records with quality scores
- `metrics.csv` - 840 metric readings with trajectories
- `derived_fields.csv` - 840 pre-computed derived fields

#### Flattened Analytical Table (`output/analytical/`)

- `analytical_flat.csv` - All data joined into one wide table for immediate analysis

---

## Three Embedded Scenario Stories

The dataset contains three deliberately embedded patterns for testing detection models:

### Story 1: Underfunded High Potential (8 goals)

**Characteristics**:
- Consistently below `minimum_viable_allocation` in periods 1-18
- Good output efficiency but insufficient scale
- Slow improvement that plateaus by period 18
- Eventually misses target by period 24

**Example goals**: Early-stage initiatives, under-resourced teams

**Detection signal**: High allocation efficiency ratio but low absolute output

### Story 2: Overfunded Inefficiency (8 goals)

**Characteristics**:
- In green band periods 1-7, then above `optimal_max` in periods 8-24
- Diminishing returns visible in rising cost-per-unit
- Fast initial growth, then plateau/decline by period 20
- Moves into orange/red high bands

**Example goals**: Over-invested mature products, bloated teams

**Detection signal**: Declining output quality score, increasing cost per unit

### Story 3: Optimally Tuned (10 goals)

**Characteristics**:
- Allocations near green band center throughout
- Stable trajectory with improving cost efficiency
- Steady linear improvement toward target
- Hits target by periods 22-24

**Example goals**: Well-managed initiatives with right resource levels

**Detection signal**: Stable efficiency ratio, consistent green band status

### Story 4: Dynamic Reallocation (9 goals)

**Characteristics**:
- Start in one allocation category (periods 1-12)
- Transition during periods 12-14 (budget shock period)
- End in different category (periods 15-24)

**Example goals**: Strategic pivots, responses to market changes

**Detection signal**: Clear transition in allocation levels and status bands

---

## Shock Events

### Budget Shock (Periods 10-12)

- **Type**: Internal constraint
- **Impact**: 20% reduction in total budget
- **Effect**: Forces rebalancing across all buckets
- **Observation**: Metric lag visible in periods 12-15

### Market Shock (Period 14+)

- **Type**: External market conditions
- **Impact**: 15% reduction to growth-related metrics
- **Affected metrics**: Traffic, revenue, leads, attendees, user counts
- **Recovery**: Gradual recovery over periods 15-17

---

## Getting Started

### Loading the Data

```python
import pandas as pd

# Option 1: Load normalized tables
periods = pd.read_csv('output/normalized/periods.csv')
buckets = pd.read_csv('output/normalized/buckets.csv')
goals = pd.read_csv('output/normalized/goals.csv')
allocations = pd.read_csv('output/normalized/allocations.csv')
outputs = pd.read_csv('output/normalized/outputs.csv')
metrics = pd.read_csv('output/normalized/metrics.csv')
derived = pd.read_csv('output/normalized/derived_fields.csv')

# Option 2: Load flattened table (easier to start with)
df = pd.read_csv('output/analytical/analytical_flat.csv')
```

### Example Queries

#### Identify Underfunded Goals

```python
# Find goals consistently below minimum viable allocation
underfunded = goals[goals['scenario_story'] == 'underfunded']

for _, goal in underfunded.iterrows():
    goal_allocs = allocations[allocations['bucket_id'] == goal['bucket_id']]
    below_min = (goal_allocs['allocation_percentage_of_total'] <
                 goal['minimum_viable_allocation']).sum()
    print(f"Goal {goal['goal_id']} ({goal['metric_name']}): "
          f"{below_min}/24 periods below minimum")
```

#### Analyze Budget Shock Impact

```python
# Compare pre-shock, during-shock, post-shock allocations
pre_shock = allocations[allocations['period_id'].isin([8, 9])]['allocated_amount'].mean()
during_shock = allocations[allocations['period_id'].isin([10, 11, 12])]['allocated_amount'].mean()
post_shock = allocations[allocations['period_id'].isin([13, 14])]['allocated_amount'].mean()

print(f"Budget shock impact: {(1 - during_shock/pre_shock)*100:.1f}% reduction")
print(f"Recovery: {(post_shock/during_shock - 1)*100:.1f}% increase post-shock")
```

#### Detect Diminishing Returns

```python
# Find overfunded goals with declining efficiency
overfunded = goals[goals['scenario_story'] == 'overfunded']

for _, goal in overfunded.iterrows():
    goal_outputs = outputs[outputs['bucket_id'] == goal['bucket_id']].sort_values('period_id')

    early_efficiency = goal_outputs.iloc[:8]['output_cost_per_unit'].mean()
    late_efficiency = goal_outputs.iloc[-8:]['output_cost_per_unit'].mean()

    if late_efficiency > early_efficiency * 1.2:  # 20% cost increase
        print(f"Goal {goal['goal_id']}: Declining efficiency detected")
        print(f"  Early cost/unit: ${early_efficiency:.2f}")
        print(f"  Late cost/unit: ${late_efficiency:.2f}")
```

#### Calculate Coherence Score

```python
# Simple coherence metric: % of goals in green band per period
def calculate_period_coherence(period_id):
    period_derived = derived[derived['period_id'] == period_id]
    green_count = (period_derived['status_band'] == 'green').sum()
    total_goals = len(period_derived)
    return green_count / total_goals

coherence_over_time = [calculate_period_coherence(p) for p in range(1, 25)]

import matplotlib.pyplot as plt
plt.plot(range(1, 25), coherence_over_time)
plt.xlabel('Period')
plt.ylabel('Coherence Score (% in Green Band)')
plt.title('Organizational Coherence Over Time')
plt.axvline(x=10, color='r', linestyle='--', label='Budget Shock Start')
plt.legend()
plt.show()
```

---

## Key Relationships

### Hierarchy

```
Projection (1)
  └─ L1 Buckets (4)
      └─ L2 Buckets (14)
          └─ L3 Leaf Buckets (35)
              └─ Goals (35, one per leaf)
```

### Causal Chain

```
Allocation (Period N)
  ↓ (2-3 period lag with diminishing returns)
Output Quantity & Quality (Period N+2)
  ↓ (1-2 period lag)
Metric Performance (Period N+3)
  ↓
Goal Attainment (Period 24)
```

### Derived Relationships

- `range_position_score` ← allocation vs. symmetric bands
- `status_band` ← categorical version of range score
- `underfunded_flag` ← allocation < minimum_viable
- `overfunded_flag` ← allocation > optimal_max
- `allocation_efficiency_ratio` ← current vs. rolling average efficiency
- `probability_of_hitting_target` ← trajectory projection

---

## Validation Checks Passed

✅ All L1 bucket percentages sum to 100%
✅ All L2/L3 child percentages sum to 100% of parent
✅ All allocation percentages per period sum to 100%
✅ 8 goals consistently underfunded (below minimum in 14+ / 18 early periods)
✅ 8 goals consistently overfunded (above optimal in 13+ / 17 late periods)
✅ Range bands properly ordered for all goals
✅ Budget shock visible (~20% reduction in periods 10-12)
✅ All foreign keys resolve correctly
✅ All data values within valid ranges

---

## Research Questions Students Can Explore

1. **Can you build a model to detect underfunded goals before they miss targets?**
   - Use early-period allocation patterns + efficiency ratios
   - Test sensitivity: how early can you detect?

2. **How do you quantify "coherence" across competing goals?**
   - Define coherence metrics (variance, balance, alignment)
   - Test under constraint (budget shock)

3. **Can you predict which overfunded goals have diminishing returns?**
   - Use cost-per-unit trajectories
   - Identify optimal allocation thresholds

4. **How should priorities change after a shock event?**
   - Model reallocation strategies
   - Optimize for resilience vs. performance

5. **What's the relationship between allocation consistency and goal success?**
   - Compare stable vs. volatile allocation patterns
   - Control for total allocation amount

---

## Limitations & Considerations

- **Fully synthetic**: No real organizational data, patterns are designed
- **Simplified model**: Real organizations have more complex dependencies
- **Fixed random seed (42)**: Same data every generation (reproducible)
- **Normalization effects**: Optimal goals may shift outside green bands due to 100% sum constraint
- **No external factors**: Beyond market shock, no seasonality or external events
- **Single projection**: No scenario comparison (this vs. that strategy)

---

## Technical Details

- **Random seed**: 42 (for reproducibility)
- **Generation time**: <1 minute on standard hardware
- **Total records**: 840 per table (35 goals × 24 periods)
- **File sizes**: ~500KB flattened, ~300KB normalized (total)
- **Dependencies**: pandas, numpy, python-dateutil

---

## Citation

If you use this dataset in your research, please cite:

```
Synthetic Dataset for Coherence Engine Evaluation
UTS Innovation Lab Project - 2024
Generated with claude-sonnet-4-5
Purpose: Goal-Aligned Decision Making Research
```

---

## Support

For questions about the dataset structure or generation process, refer to:
- `data_dictionary.md` - Complete field definitions
- Plan file in `.claude/plans/` - Implementation details
- Source code in `src/` - Generation logic

---

**Dataset generated**: 2026-02-20
**Version**: 1.0.0
**Random seed**: 42
