# Phase 1 Verification Checklist

Use this checklist to verify the Phase 1 API layer is working correctly before moving to Phase 2 (The Math — Deterministic Projection Engine).

---

## Prerequisites

Start the database if it isn't already running:

```bash
docker compose up -d db
```

Ensure the test database exists:

```bash
docker compose exec db psql -U fineas -c "\l" | grep fineas_test
```

If missing, create it:

```bash
docker compose exec db psql -U fineas -c "CREATE DATABASE fineas_test TEMPLATE template0;"
```

---

## 1. Automated Tests

```bash
cd apps/backend && pytest -v
```

- [ ] **13 tests pass, 0 failures**
  - 8 asset tests (CRUD + edge cases)
  - 5 snapshot tests (CRUD + edge cases)

---

## 2. Alembic Migrations

```bash
cd apps/backend
DATABASE_URL=postgresql+asyncpg://fineas:fineas@localhost:5432/fineas alembic upgrade head
```

- [ ] Migration runs without errors
- [ ] Verify tables exist:

```bash
docker compose exec db psql -U fineas -c "\dt"
```

Expected: `assets`, `asset_snapshots`, `alembic_version` tables present.

- [ ] Verify schema matches models:

```bash
docker compose exec db psql -U fineas -c "\d assets"
docker compose exec db psql -U fineas -c "\d asset_snapshots"
```

Expected columns and constraints:
- `assets`: id (uuid PK), name (varchar 100, UNIQUE), asset_type (asset_type_enum), annualized_return_pct (numeric 6,4), ticker (varchar 20), created_at (timestamptz)
- `asset_snapshots`: id (uuid PK), asset_id (uuid FK→assets CASCADE), snapshot_date (date), balance (numeric 15,2), created_at (timestamptz), UNIQUE(asset_id, snapshot_date)

---

## 3. API Server Smoke Test

```bash
cd apps/backend && uvicorn main:app --reload
```

- [ ] Server starts without errors on http://localhost:8000

### Health endpoint

```bash
curl http://localhost:8000/health
```

- [ ] Returns `{"status":"ok"}`

### Swagger UI

- [ ] http://localhost:8000/docs loads and shows all endpoints

---

## 4. Manual API Walkthrough

With the server running, test the full CRUD lifecycle:

### Create an asset

```bash
curl -s -X POST http://localhost:8000/assets \
  -H "Content-Type: application/json" \
  -d '{"name":"Vanguard FTSE All-World","asset_type":"STOCKS","ticker":"VWCE.DE","annualized_return_pct":"0.0850"}' | python3 -m json.tool
```

- [ ] Returns 201 with id, name, asset_type, ticker, annualized_return_pct, created_at

### List assets

```bash
curl -s http://localhost:8000/assets | python3 -m json.tool
```

- [ ] Returns 200 with array containing the created asset

### Get asset by ID

```bash
curl -s http://localhost:8000/assets/<ASSET_ID> | python3 -m json.tool
```

- [ ] Returns 200 with the asset

### Update asset (PATCH)

```bash
curl -s -X PATCH http://localhost:8000/assets/<ASSET_ID> \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name"}' | python3 -m json.tool
```

- [ ] Returns 200 with updated name, other fields unchanged

### Create a snapshot

```bash
curl -s -X POST http://localhost:8000/assets/<ASSET_ID>/snapshots \
  -H "Content-Type: application/json" \
  -d '{"snapshot_date":"2025-12-31","balance":"50000.00"}' | python3 -m json.tool
```

- [ ] Returns 201 with id, asset_id, snapshot_date, balance, created_at

### List snapshots

```bash
curl -s http://localhost:8000/assets/<ASSET_ID>/snapshots | python3 -m json.tool
```

- [ ] Returns 200 with array of snapshots ordered by date

### Delete asset (cascade)

```bash
curl -s -X DELETE http://localhost:8000/assets/<ASSET_ID> -w "\n%{http_code}\n"
```

- [ ] Returns 204
- [ ] Subsequent GET returns 404
- [ ] Snapshots for that asset are also deleted (CASCADE)

---

## 5. Edge Cases

- [ ] **Duplicate asset name** → POST /assets with same name twice returns 409
- [ ] **Duplicate snapshot date** → POST same (asset_id, snapshot_date) twice returns 409
- [ ] **Asset not found** → GET /assets/00000000-0000-0000-0000-000000000000 returns 404
- [ ] **Snapshot on missing asset** → POST /assets/00000000-.../snapshots returns 404

---

## 6. Docker Compose Full Stack

```bash
docker compose up --build
```

- [ ] Both `db` and `api` services start
- [ ] `api` waits for `db` healthcheck before starting
- [ ] http://localhost:8000/health returns `{"status":"ok"}`

---

## Ready for Phase 2

All boxes checked above means Phase 1 is complete. Phase 2 (Deterministic Projection Engine) can begin — it will add pure-math projection functions on top of the asset/snapshot data layer built here.
