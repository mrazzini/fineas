# FIRE Projection Engine — Fineas

> **Read this file when working on:** `services/projection.py`, Monte Carlo simulations, compound growth, scenario comparisons.

This is the heart of the product. Implement as a standalone service that agents call via tools but that API endpoints can also invoke directly.

---

## Method 1: Deterministic Compound Growth

Replicates and improves the existing Excel projection logic.

### Formula (reverse-engineered from spreadsheet)

```
FV(t) = PV × (1 + r_weighted)^t + C × [((1 + r_weighted)^t - 1) / r_weighted]
```

Where:
- `PV` = current total portfolio value (sum of all assets)
- `r_weighted` = weighted average annual real return, calculated as:
  - Stocks weight × 0.06 (inflation-adjusted)
  - Bonds/Cash weight × 0.015 (inflation-adjusted)
  - P2P Lending weight × 0.08 (inflation-adjusted)
  - Pension weight × 0.042 (inflation-adjusted)
- `C` = annual contribution (currently €9,000/year or €750/month)
- `t` = time horizon in years

### Improvement over Excel

Compute `r_weighted` dynamically from the actual current allocation percentages rather than fixed weights. This means the projection automatically adjusts as the portfolio composition evolves.

### Excel Reference Values (for validation)

From the Dashboard projection table (age 31 = year 0, current value €38,846 including Fonchim):

| Years | Projected Value | % Increase | Age |
|-------|----------------|------------|-----|
| 0     | 38,846         | 0%         | 31  |
| 5     | 46,515         | 19.7%      | 36  |
| 10    | 56,332         | 45.0%      | 41  |
| 15    | 68,947         | 77.5%      | 46  |
| 20    | 85,214         | 119.4%     | 51  |
| 25    | 106,261        | 173.5%     | 56  |
| 30    | 133,574        | 243.9%     | 61  |
| 50    | 355,706        | 815.7%     | 81  |

Use these to validate the compound projection implementation.

---

## Method 2: Monte Carlo Simulation

For probabilistic projections and answering questions with confidence intervals.

### Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `n_simulations` | 10,000 | |
| `time_horizon_years` | User-specified or computed from goal | |
| `inflation_rate` | 0.02 | ECB target, applied for real returns |
| `monthly_contribution` | 750 | With optional annual increase rate |

### Per-Asset-Class Return Distributions (log-normal)

| Asset Class | μ (mean nominal) | σ (std dev) | Source / Rationale |
|-------------|-------------------|-------------|-------------------|
| Stocks | 0.085 | 0.18 | MSCI World historical |
| Bonds | 0.03 | 0.06 | |
| Money Market | 0.035 | 0.005 | Near-deterministic |
| P2P Lending | 0.10 | 0.15 | High variance, default risk |
| Pension | 0.042 | 0.08 | |

### Simulation Logic

For each simulation:
1. Start with current portfolio value, broken down by asset class
2. For each month in the horizon:
   a. Draw a random annual return for each asset class from its log-normal distribution
   b. Convert to monthly return: `r_monthly = (1 + r_annual)^(1/12) - 1`
   c. Apply return to each asset class's current value
   d. Add monthly contribution (distributed proportionally to current allocation or target allocation)
   e. Sum for total portfolio value
3. Record yearly snapshots for trajectory plotting

### Output

Percentile bands (p10, p25, p50, p75, p90) at each year, probability of reaching target amount, median time to target.

---

## Method 3: Scenario Comparison

For answering "What if?" questions.

### Supported Scenario Modifications

- Change monthly contribution amount
- Change contribution growth rate (annual % increase)
- Override return assumptions for specific asset classes
- Reallocate between asset classes (e.g., "stop P2P, redirect to stocks")
- Change time horizon
- Add/remove lump sum events (e.g., "I expect a €5k bonus in June")

### Implementation

Run Method 1 or 2 with modified parameters and return side-by-side results. Each scenario gets a label, a parameter diff, and a full projection result.

```python
class Scenario(BaseModel):
    label: str                    # "Current pace", "Aggressive savings", etc.
    contribution_monthly: float
    contribution_growth_rate: float  # Annual % increase in contributions
    return_overrides: dict[str, float] | None  # Override specific asset class returns
    allocation_overrides: dict[str, float] | None  # Override target allocation
    lump_sums: list[LumpSum] | None  # One-time additions/withdrawals

class ScenarioComparison(BaseModel):
    scenarios: list[Scenario]
    method: Literal["compound", "monte_carlo"]
    results: list[ProjectionResult]
    summary: str  # LLM-generated natural language comparison
```