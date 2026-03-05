# Agent Specifications — Fineas

> **Read this file when working on:** LangGraph agents, agent tools, orchestrator, chat endpoint.

---

## 5.1 Agent Orchestrator (`agents/orchestrator.py`)

A LangGraph router that classifies incoming user messages and delegates to the appropriate agent.

**Classification categories:**
- `update` → NL Update Agent (Phase 1)
- `projection` → Projection Agent (Phase 2)
- `goal` → Projection Agent (Phase 2) — goal sub-workflow
- `monitor` → Monitoring Agent (Phase 3)
- `ingest` → Ingestion Agent (Phase 4)
- `general` → Direct LLM response (portfolio Q&A without tool use)

**Implementation:** Single LLM call with structured output to classify intent before routing.

```python
class IntentClassification(BaseModel):
    agent: Literal["update", "projection", "goal", "monitor", "ingest", "general"]
    confidence: float
    extracted_entities: dict  # e.g., {"assets": ["stocks"], "amount": 13200, "date": "2026-03"}
```

---

## 5.2 NL Update Agent (Phase 1)

**Purpose:** Parse natural language portfolio updates and write to the database with human confirmation.

### LangGraph State

```python
class UpdateAgentState(TypedDict):
    messages: list[BaseMessage]
    parsed_updates: list[AssetUpdate]      # Extracted from NL
    current_holdings: dict[str, float]     # Fetched from DB
    deltas: list[AssetDelta]               # Computed differences
    anomalies: list[str]                   # Flagged unusual changes
    user_confirmed: bool                   # Human-in-the-loop gate
    write_results: list[WriteResult]       # DB write outcomes
```

### Workflow Graph

```
[START]
   │
   ▼
[parse_input] ──→ LLM extracts structured updates from NL
   │                Output: list of {asset_name, new_amount, date}
   ▼
[fetch_current] ──→ Tool: get_current_holdings()
   │                 Retrieves latest snapshot for each mentioned asset
   ▼
[compute_deltas] ──→ Pure function: computes changes and flags anomalies
   │                  Anomaly thresholds:
   │                  - Single asset changed > 25% in one month → flag
   │                  - Total portfolio changed > 15% in one month → flag
   │                  - Negative values → flag
   │                  - Asset not recognized → ask for clarification
   ▼
[present_confirmation] ──→ Returns structured response to user:
   │                        "Here's what I'll update:
   │                         • Stocks: €12,578 → €13,200 (+€622, +4.9%)
   │                         • Xtrackers: €4,699 → €4,750 (+€51, +1.1%)
   │                         Confirm?"
   │
   ▼
[await_confirmation] ──→ HUMAN-IN-THE-LOOP INTERRUPT
   │                      User confirms, edits, or cancels
   │
   ├── confirmed ──→ [write_updates] ──→ Tool: batch_update_snapshots()
   │                        │
   │                        ▼
   │                 [recalculate_projections] ──→ Triggers projection refresh
   │                        │
   │                        ▼
   │                    [respond] ──→ "Updated. Your net worth is now €27,950.
   │                                   FIRE projection: on track for 2039."
   │
   ├── edited ──→ loop back to [compute_deltas] with corrections
   │
   └── cancelled ──→ [respond] ──→ "No changes made."
```

### Tools

| Tool | Signature | Description |
|------|-----------|-------------|
| `get_current_holdings` | `() → dict[str, HoldingInfo]` | Latest snapshot for all active assets |
| `get_asset_by_name` | `(fuzzy_name: str) → Asset` | Fuzzy-matches user input to asset names |
| `batch_update_snapshots` | `(updates: list[SnapshotCreate]) → list[Snapshot]` | Writes confirmed snapshots to DB |
| `get_net_worth_summary` | `() → NetWorthSummary` | Total net worth, breakdown by type, change since last |

### Fuzzy Matching Strategy

Users will say "stocks", "my ETFs", "the Xtrackers", "P2P", "esketit", "pension", "cash", "liquidity". Resolution:
1. First pass: LLM-based extraction with asset list in system prompt
2. Fallback: Levenshtein distance matching against asset names
3. Ambiguity: If "stocks" could mean composite position or specific ETF, ask

### Example Interactions

```
User: "Updated February numbers. Stocks at 13,200, Xtrackers 4,750,
       Lyxor 2,830, cash still 6,500. Esketit at 102, Estateguru 50."
Agent: Here's what I'll record for February 2026:
       • Long-Term Stocks: €12,578 → €13,200 (+€622, +4.9%)
       • Xtrackers EUR O/N: €4,699 → €4,750 (+€51, +1.1%)
       • Lyxor SMART: €2,820 → €2,830 (+€10, +0.4%)
       • Pure Cash: €6,500 → €6,500 (no change)
       • Esketit: €100 → €102 (+€2, +2.0%)
       • Estateguru: €50 → €50 (no change)
       Total net worth: €27,432 → €27,832 (+€400, +1.5%)
       Shall I save these?

User: "Actually stocks should be 13,100"
Agent: Got it, correcting:
       • Long-Term Stocks: €12,578 → €13,100 (+€522, +4.1%)
       Updated total: €27,732 (+€300, +1.1%)
       Confirm?

User: "Yes"
Agent: Saved. Your net worth is €27,732.
       FIRE projection updated — you're tracking toward €135k by 2039.
```

---

## 5.3 FIRE Projection Agent (Phase 2)

**Purpose:** Answer forward-looking financial questions and manage goals.

### LangGraph State

```python
class ProjectionAgentState(TypedDict):
    messages: list[BaseMessage]
    query_type: Literal["when_can_i", "what_if", "set_goal", "goal_progress"]
    current_portfolio: PortfolioSummary
    projection_params: ProjectionParams
    projection_results: ProjectionResults | None
    comparison_results: list[ProjectionResults] | None
```

### Workflow Branches

**"When can I afford X?"**
```
[parse_query] → extract target amount, optional constraints
[fetch_portfolio] → current state + contribution rate
[run_projection] → Tool: monte_carlo(target=X)
[format_response] → "At your current pace, you'll reach €X by [year] with [%] confidence."
```

**"What if...?"**
```
[parse_scenarios] → extract parameter changes
[run_base_projection] → Tool: monte_carlo(params=current)
[run_alt_projections] → Tool: monte_carlo(params=modified) for each scenario
[compare_and_respond] → Side-by-side comparison with delta analysis
```

**"Set a goal"**
```
[parse_goal] → extract name, amount, deadline, scope
[create_goal] → Tool: set_goal()
[run_initial_projection] → immediate feasibility check
[respond] → "Goal set. At current pace, you'll hit this [before/after] deadline."
```

### Tools

| Tool | Signature | Description |
|------|-----------|-------------|
| `get_portfolio_summary` | `() → PortfolioSummary` | Current holdings, allocation, contribution rate |
| `run_compound_projection` | `(params: CompoundParams) → CompoundResult` | Deterministic projection |
| `run_monte_carlo` | `(params: MonteCarloParams) → MonteCarloResult` | Probabilistic projection |
| `compare_scenarios` | `(scenarios: list[ScenarioParams]) → ComparisonResult` | Multi-scenario comparison |
| `set_goal` | `(goal: GoalCreate) → Goal` | Create a new goal |
| `list_goals` | `() → list[Goal]` | All active goals |
| `check_goal_progress` | `(goal_id: UUID) → GoalProgress` | Progress toward a specific goal |

### Example Interactions

```
User: "When can I afford a €50,000 down payment for a home?"
Agent: Based on your portfolio (€26,747) and contributions (€750/mo):
       • Deterministic: March 2028 (2.1 years)
       • Monte Carlo (10,000 sims):
         - 75% chance by June 2028
         - 50% chance by February 2028
         - 25% chance by October 2027
       Want me to set this as a tracked goal?

User: "What if I bump contributions to €1,000/month?"
Agent: Comparison:
       │ Scenario          │ 50% target date │ Months saved │
       │ Current (€750/mo) │ Feb 2028        │ —            │
       │ €1,000/mo         │ Sept 2027       │ 5 months     │
       The extra €250/mo accelerates by ~5 months.

User: "Set a goal: €50k home fund by end of 2028"
Agent: Goal created: "Home Fund"
       Target: €50,000 by December 2028
       Progress: €26,747 (53.5%)
       Projection: likely by Feb 2028 — 10 months early.
```

---

## 5.4 Monitoring Agent (Phase 3)

**Purpose:** Autonomous agent that runs on a schedule and surfaces insights. NOT triggered by user messages.

**Execution triggers:**
1. Scheduled background task (APScheduler or Celery beat)
2. On-demand when user opens the dashboard (lightweight check)

### Monitoring Checks

| Check | Logic | Alert Threshold |
|-------|-------|-----------------|
| Allocation drift | Current allocation % vs target | > 5% drift in any category |
| Contribution pace | YTD contributions vs annual target | > 10% behind pace |
| Goal progress | Actual vs projected trajectory | > 15% behind projected value |
| Milestone alerts | Net worth crossed round number | Every €5,000 milestone |
| Stale data | Days since last snapshot | > 45 days without update |

### Output Format

```python
class MonitoringReport(BaseModel):
    generated_at: datetime
    alerts: list[Alert]
    insights: list[Insight]
    milestones: list[Milestone]

class Alert(BaseModel):
    severity: Literal["info", "warning", "action_needed"]
    category: str
    title: str
    detail: str
    suggested_action: str | None
```

---

## 5.5 Document Ingestion Agent (Phase 4)

**Purpose:** Parse uploaded files (CSV, PDF, screenshots) and propose portfolio updates.

**Deferred to Phase 4. Design notes for future:**
- CSV: LLM-based column matching to known assets
- PDF: Vision models for table extraction from platform statements
- Screenshots: Claude vision API for dashboard number extraction
- All paths converge to the same confirmation flow as NL Update Agent (human-in-the-loop)