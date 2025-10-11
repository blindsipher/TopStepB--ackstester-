from __future__ import annotations

import base64
import io
from typing import List

try:
    import matplotlib
    matplotlib.use("Agg")  # Headless backend for CI/servers
    import matplotlib.pyplot as plt
except Exception:  # Matplotlib may be unavailable; degrade gracefully
    matplotlib = None  # type: ignore
    plt = None  # type: ignore
import pandas as pd


def _to_series(returns: List[float], freq: str = "D") -> pd.Series:
    if not returns:
        return pd.Series(dtype=float)
    idx = pd.date_range("2000-01-01", periods=len(returns), freq=freq)
    return pd.Series(returns, index=idx)


def _fig_to_b64img() -> str:
    if plt is None:
        return ""
    buf = io.BytesIO()
    try:
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=120)
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")
    except Exception:
        try:
            plt.close()
        except Exception:
            pass
        return ""


def cumulative_return_image(returns: List[float], freq: str = "D") -> str:
    if plt is None:
        return ""
    s = _to_series(returns, freq)
    if s.empty:
        return ""
    eq = (1 + s).cumprod()
    plt.figure(figsize=(5, 2.0))
    plt.plot(eq.index, eq.values, color="#1f77b4", linewidth=1.2)
    plt.title("Cumulative Return")
    plt.grid(True, alpha=0.2)
    return _fig_to_b64img()


def drawdown_image(returns: List[float], freq: str = "D") -> str:
    if plt is None:
        return ""
    s = _to_series(returns, freq)
    if s.empty:
        return ""
    eq = (1 + s).cumprod()
    peak = eq.cummax()
    dd = (eq / peak) - 1.0
    plt.figure(figsize=(5, 2.0))
    plt.fill_between(dd.index, dd.values, 0.0, color="#d62728", alpha=0.35)
    plt.title("Drawdown")
    plt.grid(True, alpha=0.2)
    return _fig_to_b64img()
