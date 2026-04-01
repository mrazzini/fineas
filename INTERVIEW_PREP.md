# Fineas — Interview Prep: Frontend & DevOps

This document covers the two areas flagged during interview prep as needing deeper understanding:
the **frontend architecture** and the **ops/deployment stack**. Each section explains
*what* exists in the code and *why* the decision was made — the "why" is what interviewers care about.

---

## Part 1 — Frontend Architecture

### The Big Picture

The frontend is a **Next.js 14** application with four pages:

| Route | File | Purpose |
|---|---|---|
| `/` | `app/page.tsx` | Dashboard (net worth, FIRE projection chart) |
| `/assets` | `app/assets/page.tsx` | CRUD for assets and snapshots |
| `/fire-calculator` | `app/fire-calculator/page.tsx` | FIRE scenario planner |
| `/import` | `app/import/page.tsx` | Smart import (AI ingestion UI) |

The app is **dark-mode only** and uses a Material 3 colour system defined in `tailwind.config.ts`.
Google Fonts (Inter, Space Grotesk, JetBrains Mono) are loaded in `app/layout.tsx`.

---

### React Query — The Core Concept

**File:** `apps/frontend/lib/providers.tsx`

React Query is a **server state management library**. Before understanding why it was chosen,
you need to understand the distinction between two kinds of state:

- **Client state** — UI things like "is this modal open?" or "what tab is active?".
  Lives entirely in the browser. `useState` handles this perfectly.

- **Server state** — data that lives on the backend (your assets, snapshots, projection).
  It can go stale, needs to be fetched, cached, and refreshed. This is where React Query shines.

#### What React Query does automatically (that you'd have to write manually otherwise):

```
Without React Query:
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  useEffect(() => {
    setLoading(true)
    fetch('/api/assets')
      .then(r => r.json())
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])
  // No caching. Refetches on every mount. Race condition bugs possible.

With React Query:
  const { data, isLoading, error } = useQuery({
    queryKey: ['assets'],
    queryFn: getAssets,
  })
  // Cached for 30s. Shared across components. Background sync. Retry on failure.
```

#### Why not Redux?
Redux is designed for client state (UI state machine). Using it for API data means writing
actions, reducers, and selectors just to cache a list of assets. React Query solves that
entire problem out of the box.

#### Configuration in the project:
```typescript
// apps/frontend/lib/providers.tsx
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,  // data is "fresh" for 30 seconds — no refetch within that window
      retry: 1,           // if a request fails, try once more before showing an error
    },
  },
})
```

**Interview answer:** "React Query handles server state — caching, background sync, loading and
error states — without boilerplate. Redux is for client/UI state. Plain useEffect+fetch has
no caching and is easy to get wrong with race conditions."

---

### API Client Pattern

**File:** `apps/frontend/lib/api.ts`

All API calls go through a single typed `request<T>()` function:

```typescript
// Simplified version of what's in the file
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(await res.text())
  if (res.status === 204) return undefined as T
  return res.json()
}

// Then typed wrappers per domain:
export const getAssets = () => request<Asset[]>('/assets')
export const createAsset = (body) => request<Asset>('/assets', { method: 'POST', body: JSON.stringify(body) })
```

**Why this pattern?**
- One place to change base URL, auth headers, or error handling
- TypeScript generics give you type safety on every call — `getAssets()` returns `Asset[]`, not `any`
- Clean to use inside React Query: `queryFn: getAssets`

The `/api` prefix is handled by Next.js rewrites in `next.config.mjs`:
```javascript
// In development: /api/* → http://localhost:8000/*
// In production: Caddy handles this routing (see DevOps section)
rewrites: () => [{ source: '/api/:path*', destination: 'http://localhost:8000/:path*' }]
```

---

### The Import Page — useMutation Pattern

**File:** `apps/frontend/app/import/page.tsx`

The import page demonstrates **two-phase mutation** with user confirmation:

```
Phase 1 (parse):
  useMutation → POST /ingest → returns validated preview (no DB writes)
  User reviews: sees errors, ambiguous matches, selects what to import

Phase 2 (apply):
  useMutation → POST /ingest/apply → writes selected items to DB
  Triggers query invalidation → assets list refreshes automatically
```

`useMutation` is the React Query equivalent of `useQuery` but for write operations:
```typescript
const parseMutation = useMutation({
  mutationFn: (text: string) => ingestText(text),
  onSuccess: (data) => setParseResult(data),
})

// In JSX:
<button onClick={() => parseMutation.mutate(inputText)}>
  {parseMutation.isPending ? 'Parsing...' : 'Parse'}
</button>
```

After a successful apply, the cache is invalidated so the dashboard refreshes:
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['assets'] })
  queryClient.invalidateQueries({ queryKey: ['latestBalances'] })
}
```

---

### Next.js App Router — Why It Was Chosen

Next.js 14 uses the **App Router** (introduced in Next.js 13). The key capability:

- **Server Components** — render on the server, send HTML to browser. Good for SEO and initial load.
- **Client Components** — `'use client'` directive. Needed for interactivity (useState, useEffect, onClick).

In this project, components that use React Query hooks are client components.
Static layout pieces (navbar, page wrappers) can be server components.

**Interview answer for "why Next.js?":**
"It gives me the ability to split server and client rendering. Static parts of the UI
render on the server for faster initial load. Interactive parts like the import wizard and
charts are client components. It also gives me file-based routing and built-in API proxying
for local development."

---

### TypeScript Types — The Contract Layer

**File:** `apps/frontend/lib/types.ts`

These interfaces mirror the Pydantic schemas from the backend. They are the
**frontend's contract** with the API.

Key things to note:
```typescript
// balance is a string, not a number — preserves decimal precision from backend Numeric(15,2)
balance: string

// asset_type uses a discriminated union matching the backend enum
asset_type: 'CASH' | 'STOCKS' | 'BONDS' | 'REAL_ESTATE' | 'CRYPTO' | 'PENSION_FUND' | 'OTHER'

// nullable fields match optional backend columns
ticker: string | null
annualized_return_pct: string | null
```

**Why string for balance?** JavaScript's `number` type is a 64-bit float. For large balances
with precise decimals, you can get rounding errors. Keeping it as a string and only converting
for display (in `lib/format.ts`) avoids that.

---

## Part 2 — DevOps & Deployment

### Docker Compose — Local Development

**File:** `docker-compose.yml`

Three services:

```
db (PostgreSQL 16)
  └── stores all data in a named volume (pgdata)
  └── health check: pg_isready before api starts

api (FastAPI backend)
  └── depends_on db (with health condition)
  └── port 8000 exposed to host
  └── env vars: DATABASE_URL, CORS_ORIGINS

frontend (Next.js)
  └── depends_on api
  └── port 3000 exposed to host
```

**Health checks** are critical — without them, the API might start before PostgreSQL is ready
to accept connections, causing startup failures. The `condition: service_healthy` line
makes Docker wait until the health check passes before starting dependent services.

**Named volume (`pgdata`)** persists the database between `docker compose down` and `docker compose up`.
Without it, your data disappears every restart.

---

### Production vs Development — What Changes

**File:** `docker-compose.prod.yml`

| Concern | Dev | Prod |
|---|---|---|
| Passwords | Hardcoded `fineas` | `${DB_PASSWORD}` from environment |
| Ports | 8000 and 3000 exposed | Only 80/443 exposed (via Caddy) |
| API URL | `http://localhost:8000` | Empty string (same-domain routing) |
| Restart | No policy | `restart: unless-stopped` |
| SSL/TLS | None | Caddy handles it automatically |
| Caddy service | Not present | Added as fourth service |

In production the frontend and API are **not directly accessible by port**. All traffic
enters through Caddy on ports 80 and 443.

---

### Caddy — Why Not Nginx?

**File:** `Caddyfile`

```caddyfile
{$DOMAIN:localhost} {
    handle /api/* {
        uri strip_prefix /api
        reverse_proxy api:8000
    }
    handle {
        reverse_proxy frontend:3000
    }
}
```

**What Caddy does:**
1. Receives all incoming traffic on ports 80 and 443
2. Routes `/api/*` → strips the `/api` prefix → forwards to FastAPI on port 8000
3. Routes everything else → forwards to Next.js on port 3000
4. **Automatically provisions and renews TLS certificates** via Let's Encrypt

**Why Caddy over Nginx?**

| | Nginx | Caddy |
|---|---|---|
| TLS setup | Manual (certbot + cron jobs) | Automatic |
| Config syntax | Verbose | Minimal |
| Certificate renewal | You manage it | Caddy manages it |
| Risk | Cert expires at 3am | Near-zero |

The single biggest reason: with Nginx you need to run certbot separately, configure renewal
cron jobs, and handle certificate rotation yourself. Caddy handles the full TLS lifecycle
from a single config file. For a project like this, that's the right trade-off.

**Interview answer:** "Caddy gives me automatic TLS. With Nginx I'd need to configure
certbot and renewal cron jobs manually. Caddy provisions and renews certificates automatically.
It also has a minimal config syntax — the whole routing config is six lines."

---

### GitHub Actions — CI Pipeline

**File:** `.github/workflows/ci.yml`

Triggers on: every pull request to `main`

```
1. Checkout code
2. Set up Python 3.12 + pip cache (faster subsequent runs)
3. Install requirements.txt + requirements-dev.txt
4. Spin up PostgreSQL 16 as a service (with health checks)
5. Create fineas_test database
6. Run pytest
```

**Why is ANTHROPIC_API_KEY intentionally absent?**

The tests mock the LLM. If the key were present, CI would make real API calls:
- Costs money on every PR
- Slow (LLM latency in CI = slow feedback)
- Flaky (non-deterministic LLM output can fail tests randomly)
- Security risk (API key in CI logs)

The `@pytest.mark.llm` tests only run when you explicitly opt in locally.

**Pip caching:** The `cache: pip` line tells GitHub Actions to cache the pip download
cache between runs. If requirements haven't changed, packages are restored from cache
instead of re-downloaded. Saves ~30-60 seconds per CI run.

---

### CD Pipeline — Deployment

**File:** `.github/workflows/deploy.yml`

Triggers on: push to `main` (or manual trigger)

```
SSH into EC2 instance →
  cd ~/fineas →
  git pull origin main →
  docker compose -f docker-compose.prod.yml build →
  docker compose -f docker-compose.prod.yml up -d
```

This is a **simple SSH-based deployment**. The production server pulls the latest code
and rebuilds Docker images in place. The `-d` flag runs containers in detached (background) mode.

Secrets stored in GitHub repository secrets:
- `EC2_HOST` — the EC2 instance IP/hostname
- `EC2_SSH_KEY` — private SSH key to authenticate

**Interview answer:** "CI runs pytest on every PR with a real PostgreSQL service but mocked
LLMs. On merge to main, the deploy pipeline SSHes into EC2, pulls the latest code, and
restarts the Docker Compose stack with the production config."

---

### Alembic — Database Migrations

**Files:** `apps/backend/alembic/`, `apps/backend/alembic.ini`

Alembic is to PostgreSQL what Git is to code — it version-controls your schema.

**Why this matters:** If you just run `CREATE TABLE` manually, your production database
and your local database can get out of sync. With Alembic, every schema change is a
versioned migration file. Running `alembic upgrade head` applies all pending migrations
in order.

**Two migrations in this project:**

```
1d023848bf9b  →  Creates assets + asset_snapshots tables (initial schema)
a3f9c1e2b4d5  →  Adds is_archived column to assets (soft-delete feature)
```

**Async engine:** The `alembic/env.py` uses `create_async_engine` to match the rest of
the app. This is a non-trivial setup — the default Alembic template is synchronous.

**Interview answer:** "Alembic version-controls the database schema. Every change is a
migration file checked into git, so dev, CI, and production all run the same schema
by running `alembic upgrade head`. It also gives you rollback capability with `downgrade`."

---

## Quick-Reference Cheat Sheet

| Question | One-sentence answer |
|---|---|
| Why React Query? | Server state management — handles caching, loading states, and background sync without boilerplate |
| Why not Redux? | Redux is for UI/client state, not server data from an API |
| Why Caddy over Nginx? | Automatic TLS certificate provisioning and renewal — no certbot, no cron jobs |
| Why mock LLMs in CI? | Real calls are slow, expensive, non-deterministic, and need API keys |
| Why two Docker Compose files? | Dev exposes ports and uses hardcoded passwords; prod uses env vars, restart policies, and Caddy |
| Why Alembic? | Version-controlled schema changes — same as git but for database structure |
| Why Next.js? | Server/client component split, file-based routing, built-in API proxy for dev |
| Why standalone Next.js build? | Enables Docker containerization without a full Node.js server |
| What does Caddy route? | `/api/*` → FastAPI on 8000, everything else → Next.js on 3000 |
| What does the CI pipeline test? | Backend pytest with real PostgreSQL, mocked LLM, no frontend tests |
