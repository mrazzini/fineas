# Data Model — Fineas

> **Read this file when working on:** database schema, SQLAlchemy models, Alembic migrations, seed data.

---

## Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐
│   assets     │       │   snapshots      │
├──────────────┤       ├──────────────────┤
│ id (PK)      │──┐    │ id (PK)          │
│ name         │  │    │ asset_id (FK)  ──┼──→ assets.id
│ asset_type   │  │    │ date             │
│ platform     │  │    │ amount           │
│ expected_    │  │    │ source           │
│   return     │  │    │ created_at       │
│ is_active    │  └───>│                  │
│ metadata     │       └──────────────────┘
│ created_at   │
│ updated_at   │       ┌──────────────────┐
└──────────────┘       │   goals          │
                       ├──────────────────┤
                       │ id (PK)          │
                       │ name             │
                       │ description      │
                       │ target_amount    │
                       │ target_date      │
                       │ goal_type        │
                       │ asset_scope      │
                       │ is_active        │
                       │ created_at       │
                       │ updated_at       │
                       └────────┬─────────┘
                                │
                       ┌────────▼─────────┐
                       │  projections     │
                       ├──────────────────┤
                       │ id (PK)          │
                       │ goal_id (FK)     │
                       │ computed_at      │
                       │ method           │
                       │ params (JSONB)   │
                       │ results (JSONB)  │
                       └──────────────────┘

┌──────────────────────┐
│  conversations       │
├──────────────────────┤
│ id (PK)              │
│ started_at           │
│ messages (JSONB[])   │
│ agent_type           │
│ actions_taken (JSONB)│
└──────────────────────┘
```

---

## Table Definitions

### `assets`

Represents a tracked financial instrument or account.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK, default gen_random_uuid() | Unique identifier |
| `name` | `VARCHAR(255)` | NOT NULL, UNIQUE | Display name (e.g., "Vanguard FTSE All-World") |
| `asset_type` | `VARCHAR(50)` | NOT NULL | Enum: `cash`, `stocks`, `bonds`, `p2p_lending`, `pension`, `money_market` |
| `platform` | `VARCHAR(100)` | | Source platform (e.g., "Scalable Capital", "Esketit") |
| `expected_annual_return` | `DECIMAL(8,5)` | | Nominal annualized return (e.g., 0.08500 for 8.5%) |
| `is_active` | `BOOLEAN` | DEFAULT true | Whether this asset is currently held |
| `metadata` | `JSONB` | DEFAULT '{}' | Flexible field for ISIN, currency, notes, etc. |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() | Auto-updated via trigger |

### `snapshots`

A point-in-time value for a specific asset. One row per asset per update.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK | |
| `asset_id` | `UUID` | FK → assets.id, NOT NULL | |
| `date` | `DATE` | NOT NULL | Snapshot date |
| `amount` | `DECIMAL(12,2)` | NOT NULL | Value in EUR |
| `source` | `VARCHAR(50)` | DEFAULT 'manual' | How this entered: `manual`, `nl_agent`, `csv_import`, `pdf_import` |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | |

**Composite unique constraint:** `(asset_id, date)` — one snapshot per asset per date.

**Key query patterns:**
```sql
-- Latest snapshot per asset
SELECT DISTINCT ON (asset_id) * FROM snapshots ORDER BY asset_id, date DESC;

-- Net worth at each date
SELECT date, SUM(amount) FROM snapshots GROUP BY date ORDER BY date;

-- Asset history
SELECT * FROM snapshots WHERE asset_id = ? ORDER BY date;
```

### `goals`

A financial target the user is working toward.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK | |
| `name` | `VARCHAR(255)` | NOT NULL | e.g., "Home down payment" |
| `description` | `TEXT` | | Free-text context |
| `target_amount` | `DECIMAL(12,2)` | NOT NULL | Target in EUR |
| `target_date` | `DATE` | | Optional deadline |
| `goal_type` | `VARCHAR(50)` | NOT NULL | Enum: `fire`, `milestone`, `emergency_fund`, `purchase` |
| `asset_scope` | `JSONB` | DEFAULT '"all"' | Which assets count: `"all"`, `["cash", "stocks"]`, or specific asset IDs |
| `is_active` | `BOOLEAN` | DEFAULT true | |
| `created_at` | `TIMESTAMPTZ` | | |
| `updated_at` | `TIMESTAMPTZ` | | |

### `projections`

Cached results of projection computations, tied to goals.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK | |
| `goal_id` | `UUID` | FK → goals.id | |
| `computed_at` | `TIMESTAMPTZ` | NOT NULL | When this projection was run |
| `method` | `VARCHAR(50)` | NOT NULL | `compound`, `monte_carlo`, `scenario` |
| `params` | `JSONB` | NOT NULL | Input parameters |
| `results` | `JSONB` | NOT NULL | Output (see schemas below) |

**`results` JSONB schema for `monte_carlo` method:**
```json
{
  "simulations": 10000,
  "target_hit_probability": 0.74,
  "median_years_to_target": 8.3,
  "percentiles": {
    "p10": { "years": 12.1, "final_value": 89200 },
    "p25": { "years": 9.8, "final_value": 112400 },
    "p50": { "years": 8.3, "final_value": 143800 },
    "p75": { "years": 6.9, "final_value": 189600 },
    "p90": { "years": 5.8, "final_value": 251300 }
  },
  "yearly_trajectory": [
    { "year": 2026, "p10": 28500, "p25": 30200, "p50": 32100, "p75": 34500, "p90": 37200 }
  ]
}
```

**`results` JSONB schema for `compound` method:**
```json
{
  "yearly_trajectory": [
    { "year": 2026, "projected_value": 38846, "cumulative_contributions": 9000, "cumulative_returns": 3100 }
  ],
  "target_hit_year": 2034,
  "final_value_at_horizon": 135573
}
```

### `conversations`

Stores chat history for context and audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | PK | |
| `started_at` | `TIMESTAMPTZ` | DEFAULT now() | |
| `messages` | `JSONB[]` | | Array of `{role, content, timestamp}` |
| `agent_type` | `VARCHAR(50)` | | Which agent handled this |
| `actions_taken` | `JSONB` | DEFAULT '[]' | Audit log of DB writes |

---

## Seed Data (from Excel)

### Assets

```
Name                              | Type         | Platform          | Expected Return | Active
----------------------------------|--------------|-------------------|-----------------|-------
Pure Cash Liquidity               | cash         | isyBank           | 0.00000         | true
Long-Term Stocks                  | stocks       | Scalable Capital  | 0.08500         | true
iBonds                            | bonds        | Scalable Capital  | -0.02620        | true
Xtrackers EUR Overnight           | money_market | Scalable Capital  | 0.03985         | true
Lyxor SMART                       | money_market | Scalable Capital  | 0.03900         | true
Esketit                           | p2p_lending  | Esketit           | 0.12800         | true
Estateguru                        | p2p_lending  | Estateguru        | 0.10000         | true
Robocash                          | p2p_lending  | Robocash          | 0.01027         | false
Fonchim                           | pension      | Fonchim           | 0.04200         | true
```

**Notes:**
- "Long-Term Stocks" is a composite of VWCE (Vanguard FTSE All-World), IWDA (iShares MSCI World), and EIMI (iShares MSCI EM) — tracked as a single position
- Robocash balance is €0 as of Feb 2026, marked `is_active = false`
- Fonchim (€12,099) is tracked on Dashboard but NOT in Historical_amounts — it has its own update cadence

### Pre-seeded Goals

```
Name               | Type           | Target   | Scope              | Notes
-------------------|----------------|----------|--------------------|------
Emergency Fund     | emergency_fund | 7,500    | ["cash"]           | ALREADY MET (€7,519 in cash + money_market)
Home Purchase Fund | purchase       | 10,000   | ["cash", "money_market"] | Dashboard row A15
FIRE Target        | fire           | computed | "all"              | 25x annual expenses or user-defined
```