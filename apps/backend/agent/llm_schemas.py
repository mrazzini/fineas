"""
Pydantic schemas used exclusively for LLM structured output.

These are NOT FastAPI request/response schemas — they live here so the LLM
knows exactly what JSON shape to produce.  `.with_structured_output()` from
LangChain serialises these models into the tool/function spec that the model
receives, and then deserialises the model's response back into typed objects.

Keeping them separate from `schemas.py` (the HTTP layer) avoids coupling the
AI contract to the REST API contract.
"""
from typing import Optional

from pydantic import BaseModel, Field


class ParsedAsset(BaseModel):
    """One financial asset the LLM found in the input text."""
    name: str = Field(
        description=(
            "The asset name. If this clearly matches one of the existing portfolio assets "
            "listed in the prompt, use that asset's exact name. Otherwise use a concise "
            "descriptive label, e.g. 'Vanguard FTSE All-World ETF'."
        )
    )
    asset_type: str = Field(
        description=(
            "Category of the asset. Must be one of: CASH, STOCKS, BONDS, "
            "REAL_ESTATE, CRYPTO, PENSION_FUND, OTHER. Infer from context."
        )
    )
    ticker: Optional[str] = Field(
        default=None,
        description="Market ticker symbol if mentioned, e.g. 'VWCE.DE'. Omit if not stated."
    )
    annualized_return_pct: Optional[float] = Field(
        default=None,
        description=(
            "Expected annual return as a decimal fraction, e.g. 0.085 for 8.5%. "
            "Include only if explicitly stated in the text."
        )
    )
    match_candidates: Optional[list[str]] = Field(
        default=None,
        description=(
            "Only populate when you cannot determine which existing portfolio asset "
            "the user is referring to. List the exact names of 2–4 candidate assets "
            "from the EXISTING PORTFOLIO ASSETS section. Omit this field entirely "
            "when you are confident about the match or when the asset is clearly new."
        )
    )


class ParsedSnapshot(BaseModel):
    """One balance reading the LLM found in the input text."""
    asset_name: str = Field(
        description="Must exactly match the `name` field of a ParsedAsset in this response."
    )
    snapshot_date: str = Field(
        description=(
            "Date of the balance in ISO 8601 format (YYYY-MM-DD). "
            "Infer the day as the 1st of the month when only a month/year is given."
        )
    )
    balance: float = Field(description="Balance amount as a plain number (no currency symbols).")


class ParsedPortfolioUpdate(BaseModel):
    """Top-level output schema — everything the LLM extracted from one input."""
    assets: list[ParsedAsset] = Field(
        default_factory=list,
        description="All unique financial assets mentioned in the text."
    )
    snapshots: list[ParsedSnapshot] = Field(
        default_factory=list,
        description="All balance/value readings mentioned in the text."
    )
