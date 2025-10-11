from __future__ import annotations

"""
Frequency helpers for mapping pipeline timeframes to pandas freq strings and
annualization factors used by QuantStats. Defaults are conservative and can be
refined per instrument/session.
"""

from typing import Tuple


def timeframe_to_pandas_freq(timeframe: str) -> str:
    tf = (timeframe or "").strip().lower()
    mapping = {
        "1m": "1T", "5m": "5T", "10m": "10T", "15m": "15T", "20m": "20T",
        "30m": "30T", "45m": "45T", "1h": "1H", "4h": "4H", "1d": "1D"
    }
    return mapping.get(tf, "D")  # default daily


def annualization_for_timeframe(timeframe: str) -> float:
    """
    Approximate periods per year for the given timeframe.
    Assumptions (U.S. futures): ~252 trading days/year, ~6.5h/session.
    """
    tf = (timeframe or "").strip().lower()
    days = 252.0
    if tf == "1d":
        return days
    if tf == "4h":
        return days * (6.5 / 4.0)
    if tf == "1h":
        return days * 6.5
    if tf == "45m":
        return days * (6.5 * 60.0 / 45.0)
    if tf == "30m":
        return days * (6.5 * 2.0)
    if tf == "20m":
        return days * (6.5 * 3.0)
    if tf == "15m":
        return days * (6.5 * 4.0)
    if tf == "10m":
        return days * (6.5 * 6.0)
    if tf == "5m":
        return days * (6.5 * 12.0)
    if tf == "1m":
        return days * (6.5 * 60.0)
    return days  # default


def resolve_freq_and_annualization(timeframe: str) -> Tuple[str, float]:
    return timeframe_to_pandas_freq(timeframe), annualization_for_timeframe(timeframe)

