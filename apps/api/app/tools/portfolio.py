"""
Portfolio tools for the NL Update Agent.

Tools are plain functions (not async) — they receive the AsyncSession via
closure when the agent is instantiated. DB operations are run via asyncio.
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import Levenshtein
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.snapshot import Snapshot


# ---------------------------------------------------------------------------
# Data classes (no pydantic — keep it simple for tool return values)
# ---------------------------------------------------------------------------

class HoldingInfo:
    def __init__(
        self,
        asset_id: str,
        asset_name: str,
        asset_type: str,
        platform: str | None,
        current_amount: float,
        snapshot_date: date,
    ):
        self.asset_id = asset_id
        self.asset_name = asset_name
        self.asset_type = asset_type
        self.platform = platform
        self.current_amount = current_amount
        self.snapshot_date = snapshot_date

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "asset_type": self.asset_type,
            "platform": self.platform,
            "current_amount": self.current_amount,
            "snapshot_date": self.snapshot_date.isoformat(),
        }


class AssetDelta:
    def __init__(
        self,
        asset_name: str,
        asset_id: str,
        old_amount: float,
        new_amount: float,
    ):
        self.asset_name = asset_name
        self.asset_id = asset_id
        self.old_amount = old_amount
        self.new_amount = new_amount
        self.delta = new_amount - old_amount
        self.delta_pct = (self.delta / old_amount * 100) if old_amount else 0.0
        self.is_anomaly = (
            abs(self.delta_pct) > 25 or new_amount < 0
        )
        self.anomaly_reason = (
            f"{abs(self.delta_pct):.1f}% change exceeds 25% threshold"
            if abs(self.delta_pct) > 25 and new_amount >= 0
            else ("Negative value not allowed" if new_amount < 0 else None)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_name": self.asset_name,
            "asset_id": self.asset_id,
            "old_amount": self.old_amount,
            "new_amount": self.new_amount,
            "delta": round(self.delta, 2),
            "delta_pct": round(self.delta_pct, 2),
            "is_anomaly": self.is_anomaly,
            "anomaly_reason": self.anomaly_reason,
        }


class WriteResult:
    def __init__(self, asset_name: str, date: date, amount: float, success: bool, error: str | None = None):
        self.asset_name = asset_name
        self.date = date
        self.amount = amount
        self.success = success
        self.error = error


# ---------------------------------------------------------------------------
# Tool factory — injects session into closures
# ---------------------------------------------------------------------------

def make_portfolio_tools(session: AsyncSession):
    """Create tool functions bound to a specific DB session."""

    def _run_sync(coro):
        """Run a coroutine synchronously from within a sync tool."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context (LangGraph) — use nest_asyncio or run_until_complete
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    async def _get_latest_snapshots() -> dict[str, HoldingInfo]:
        stmt = (
            select(Snapshot)
            .join(Asset, Snapshot.asset_id == Asset.id)
            .where(Asset.is_active.is_(True))
            .distinct(Snapshot.asset_id)
            .order_by(Snapshot.asset_id, Snapshot.date.desc())
        )
        result = await session.execute(stmt)
        snapshots = list(result.scalars().all())

        holdings: dict[str, HoldingInfo] = {}
        for snap in snapshots:
            asset = await session.get(Asset, snap.asset_id)
            if asset:
                holdings[asset.name] = HoldingInfo(
                    asset_id=str(asset.id),
                    asset_name=asset.name,
                    asset_type=asset.asset_type,
                    platform=asset.platform,
                    current_amount=float(snap.amount),
                    snapshot_date=snap.date,
                )
        return holdings

    async def _get_all_active_asset_names() -> list[str]:
        stmt = select(Asset.name).where(Asset.is_active.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @tool
    def get_current_holdings() -> dict[str, dict]:
        """Get the latest snapshot for each active asset.
        Returns a dict mapping asset_name → {asset_id, asset_type, platform, current_amount, snapshot_date}.
        """
        holdings = _run_sync(_get_latest_snapshots())
        return {name: h.to_dict() for name, h in holdings.items()}

    @tool
    def get_asset_by_name(query: str) -> dict:
        """Find an asset by fuzzy-matching the user's text to known asset names.
        Returns {asset_id, asset_name, confidence} or raises if ambiguous.

        Args:
            query: User-provided asset name (e.g. "stocks", "xtrackers", "p2p")
        """
        names = _run_sync(_get_all_active_asset_names())
        q = query.lower().strip()

        # Exact match first
        for name in names:
            if name.lower() == q:
                return {"asset_name": name, "confidence": 1.0}

        # Substring match
        matches = [(name, 0.9) for name in names if q in name.lower() or name.lower() in q]
        if len(matches) == 1:
            return {"asset_name": matches[0][0], "confidence": matches[0][1]}

        # Levenshtein distance (normalized)
        scored = []
        for name in names:
            dist = Levenshtein.distance(q, name.lower())
            max_len = max(len(q), len(name))
            similarity = 1 - dist / max_len if max_len else 0
            scored.append((name, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_name, best_score = scored[0]

        if best_score >= 0.5:
            return {"asset_name": best_name, "confidence": round(best_score, 3)}

        return {
            "error": f"Could not match '{query}' to any asset. Available: {', '.join(names)}",
            "asset_name": None,
            "confidence": 0.0,
        }

    @tool
    def get_net_worth_summary() -> dict:
        """Get total net worth and per-asset breakdown.
        Returns {total, holdings: list[...], change_from_previous: float}
        """
        holdings = _run_sync(_get_latest_snapshots())
        total = sum(h.current_amount for h in holdings.values())
        return {
            "total_net_worth": round(total, 2),
            "holdings": [h.to_dict() for h in sorted(holdings.values(), key=lambda h: h.current_amount, reverse=True)],
        }

    async def _write_snapshots(updates: list[dict]) -> list[WriteResult]:
        """Write snapshots to the database."""
        results = []
        for upd in updates:
            asset_id = upd["asset_id"]
            snap_date = date.fromisoformat(upd["date"])
            amount = upd["amount"]

            try:
                # Upsert snapshot
                stmt = (
                    select(Snapshot)
                    .where(Snapshot.asset_id == asset_id)
                    .where(Snapshot.date == snap_date)
                )
                existing = (await session.execute(stmt)).scalar_one_or_none()

                if existing:
                    existing.amount = amount
                    existing.source = "nl_agent"
                else:
                    snap = Snapshot(
                        asset_id=asset_id,
                        date=snap_date,
                        amount=amount,
                        source="nl_agent",
                    )
                    session.add(snap)

                await session.commit()
                asset = await session.get(Asset, asset_id)
                results.append(WriteResult(
                    asset_name=asset.name if asset else asset_id,
                    date=snap_date,
                    amount=amount,
                    success=True,
                ))
            except Exception as e:
                await session.rollback()
                results.append(WriteResult(
                    asset_name=upd.get("asset_name", asset_id),
                    date=snap_date,
                    amount=amount,
                    success=False,
                    error=str(e),
                ))

        return results

    @tool
    def batch_update_snapshots(updates: list[dict]) -> list[dict]:
        """Write confirmed snapshot updates to the database.
        Only call this AFTER user confirmation.

        Args:
            updates: List of {asset_id: str, date: str (ISO), amount: float}
        """
        results = _run_sync(_write_snapshots(updates))
        return [
            {
                "asset_name": r.asset_name,
                "date": r.date.isoformat(),
                "amount": r.amount,
                "success": r.success,
                "error": r.error,
            }
            for r in results
        ]

    return [get_current_holdings, get_asset_by_name, get_net_worth_summary, batch_update_snapshots]
