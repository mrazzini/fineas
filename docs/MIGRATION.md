# Excel Migration Script — Fineas

> **Read this file when working on:** `scripts/migrate_excel.py`, initial data seeding.

---

## Purpose

One-time script to populate the PostgreSQL database from the original `data/CA_HFLOW.xlsx` file.

## Requirements

1. Read `CA_HFLOW.xlsx` from `data/` directory
2. Parse `Asset_classes` sheet → insert into `assets` table
3. Parse `Dashboard` sheet → extract additional assets not in Asset_classes (Pure Cash Liquidity, Fonchim)
4. Parse `Historical_amounts` sheet → insert into `snapshots` table
5. Parse `Dashboard` projection table → insert initial goals (Emergency Fund, Home Purchase, FIRE)
6. Parse `Dashboard` net worth history (columns H-K) → verify against computed snapshots
7. **Must be idempotent** — running twice should not create duplicates

---

## Column-to-Asset Mapping for Historical_amounts

```
Column A → Date (snapshot date)
Column B → "Pure Cash Liquidity"
Column C → "Long-Term Stocks"
Column D → "iBonds"
Column E → "Xtrackers EUR Overnight"
Column F → "Lyxor SMART"
Column G → "Esketit"
Column H → "Estateguru"
Column I → "Robocash"
Column J → Total (COMPUTED — do not store as asset, use for verification)
```

**Data range:** Rows 2-23 (April 2024 through February 2026). Row 23 has no date in column A — use the sequence pattern to infer or pull from Dashboard.

---

## Fonchim Handling

Fonchim appears on the Dashboard (€12,099) but NOT in Historical_amounts. The migration script should:
1. Create the Fonchim asset record
2. Create a single snapshot with the Dashboard value and the latest update date
3. Log a warning that Fonchim historical data is not available

---

## Dashboard Net Worth History (Verification)

Columns H-K on the Dashboard sheet contain a separate net worth time series starting from April 2023 (before Historical_amounts begins in April 2024). This predates the per-asset tracking.

**For the migration:**
- Rows with dates before April 2024: Store as aggregate net worth snapshots only (no per-asset breakdown available). Consider a separate `net_worth_history` table or a special "total" snapshot.
- Rows with dates April 2024+: Verify that Dashboard net worth matches the sum of Historical_amounts for that date. Log discrepancies.

---

## Verification Checks

After migration, assert:
- Number of assets = 9 (including Fonchim, including inactive Robocash)
- Number of snapshots = (22 dates × ~8 active assets per date) — exact count depends on zero-value handling
- Latest net worth = €26,747 (from Dashboard, Feb 2026)
- Fonchim has exactly 1 snapshot (€12,099)
- Total with Fonchim = €38,846 (matches Dashboard E16)