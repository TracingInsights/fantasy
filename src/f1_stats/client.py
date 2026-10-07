"""Fetch F1 Fantasy statistics from the f1fantasytools.com API."""

from __future__ import annotations

import logging

import httpx

BASE_URL = "https://f1fantasytools.com/api/statistics"

logger = logging.getLogger(__name__)

DEFAULT_YEARS = (2023, 2024, 2025, 2026)
DEFAULT_TIMEOUT = 60.0


class YearNotAvailableError(Exception):
    """Raised when the API rejects a year (e.g. outside the supported range)."""


def fetch_year(year: int, *, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Fetch the raw statistics payload for a season.

    Raises YearNotAvailableError if the API rejects the year, and httpx
    errors on transport failures / unexpected status codes.
    """
    url = f"{BASE_URL}/{year}"
    logger.info("Fetching %s", url)
    response = httpx.get(url, timeout=timeout, headers={"Accept": "application/json"})
    if response.status_code == 400:
        # API returns {"error": "Invalid year parameter"} for unsupported years.
        raise YearNotAvailableError(f"Year {year} not available: {response.text[:120]}")
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or "seasonResult" not in data:
        raise ValueError(f"Unexpected payload shape for {year}: {type(data)!r}")
    return data
