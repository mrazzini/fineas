# API Contract — Fineas

> **Read this file when working on:** FastAPI routers, frontend API client, WebSocket chat, shared type definitions.

---

## REST Endpoints

```
# Assets
GET    /api/assets                    → list all assets
GET    /api/assets/{id}               → asset details + latest snapshot
POST   /api/assets                    → create new asset
PATCH  /api/assets/{id}               → update asset metadata

# Snapshots
GET    /api/snapshots                 → list snapshots (filter by asset, date range)
GET    /api/snapshots/latest          → latest snapshot per asset (dashboard view)
GET    /api/snapshots/history         → time series for net worth chart
POST   /api/snapshots                 → manual snapshot entry (non-agent path)

# Goals
GET    /api/goals                     → list all goals with current progress
POST   /api/goals                     → create goal
PATCH  /api/goals/{id}                → update goal
DELETE /api/goals/{id}                → soft-delete goal

# Projections
GET    /api/projections/{goal_id}     → latest projection for a goal
POST   /api/projections/run           → run new projection (compound or monte carlo)
POST   /api/projections/compare       → compare scenarios

# Monitoring
GET    /api/monitoring/report         → latest monitoring report
POST   /api/monitoring/run            → trigger a monitoring check

# Chat (WebSocket)
WS     /api/chat                      → agent interaction channel
```

---

## WebSocket Chat Protocol

### Client → Server

```typescript
interface ChatMessage {
  type: "user_message" | "confirmation_response";
  content: string;                    // For user_message
  confirmed?: boolean;                // For confirmation_response
  edits?: Record<string, number>;     // For confirmation_response with edits
}
```

### Server → Client

```typescript
interface AgentResponse {
  type: "thinking" | "response" | "confirmation_request" | "update_complete" | "error";
  content: string;                    // Display text
  data?: {
    updates?: AssetUpdate[];          // For confirmation_request
    net_worth?: number;               // For update_complete
    projection?: ProjectionResult;    // For projection responses
    chart_data?: ChartDataPoint[];    // For rendering charts
  };
}
```

---

## Shared Type Definitions

These types must stay in sync between frontend TypeScript and backend Pydantic models. **Source of truth: Pydantic models.** TypeScript types are derived.

### `packages/shared/schema.ts`

```typescript
type AssetType = "cash" | "stocks" | "bonds" | "p2p_lending" | "pension" | "money_market";

interface Asset {
  id: string;
  name: string;
  asset_type: AssetType;
  platform: string | null;
  expected_annual_return: number | null;
  is_active: boolean;
  metadata: Record<string, unknown>;
}

interface Snapshot {
  id: string;
  asset_id: string;
  date: string;          // ISO date
  amount: number;
  source: "manual" | "nl_agent" | "csv_import" | "pdf_import";
}

interface PortfolioSummary {
  total_net_worth: number;
  assets: Array<{
    asset: Asset;
    current_amount: number;
    allocation_pct: number;
    change_since_last: number;
    change_pct: number;
  }>;
  net_worth_history: Array<{
    date: string;
    total: number;
    by_type: Record<AssetType, number>;
  }>;
}

interface Goal {
  id: string;
  name: string;
  description: string | null;
  target_amount: number;
  target_date: string | null;
  goal_type: "fire" | "milestone" | "emergency_fund" | "purchase";
  current_progress: number;
  progress_pct: number;
  is_active: boolean;
}

interface MonteCarloResult {
  simulations: number;
  target_hit_probability: number;
  median_years_to_target: number;
  percentiles: Record<string, { years: number; final_value: number }>;
  yearly_trajectory: Array<{
    year: number;
    p10: number;
    p25: number;
    p50: number;
    p75: number;
    p90: number;
  }>;
}

interface Alert {
  severity: "info" | "warning" | "action_needed";
  category: string;
  title: string;
  detail: string;
  suggested_action: string | null;
}

interface MonitoringReport {
  generated_at: string;
  alerts: Alert[];
  insights: Array<{ title: string; detail: string }>;
  milestones: Array<{ title: string; detail: string; reached_at: string }>;
}
```