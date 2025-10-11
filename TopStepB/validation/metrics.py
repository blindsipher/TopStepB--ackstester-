"""
Core per-bar metrics for validation gating and recording.

We compute per-bar statistics without annualization so thresholds remain
symbol/timeframe agnostic after return normalization.
"""

from __future__ import annotations

from typing import Dict
import numpy as np
import pandas as pd


def _to_series(arr) -> pd.Series:
    if isinstance(arr, pd.Series):
        return arr.astype(float)
    return pd.Series(arr, dtype=float)


def compute_core(returns) -> Dict[str, float]:
    """Compute core per-bar metrics for a returns series.

    Metrics:
      - mean: average per-bar return
      - std: standard deviation of per-bar return
      - sharpe: mean/std (0 if std=0)
      - sortino: mean/downside_std (0 if downside_std=0)
      - max_drawdown: min(equity/peak - 1) on cumulative equity curve
      - calmar: mean / abs(max_drawdown) (0 if no drawdown)
      - cvar_5: Conditional VaR at 5% (average of worst 5% returns)
      - profit_factor: sum(positive) / abs(sum(negative)) (0 if no negatives)
      - win_rate: fraction of positive returns
      - risk_reward: avg_win / abs(avg_loss) (0 if no losses)
    """
    s = _to_series(returns)
    n = len(s)
    if n == 0:
        return {
            "mean": 0.0,
            "std": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "cvar_5": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "risk_reward": 0.0,
        }

    mean = float(s.mean())
    std = float(s.std(ddof=0))
    sharpe = float(mean / std) if std > 0 else 0.0

    # Downside std for Sortino
    downside = np.minimum(s.values, 0.0)
    downside_std = float(np.sqrt(np.mean(np.square(downside)))) if n > 0 else 0.0
    sortino = float(mean / downside_std) if downside_std > 0 else 0.0

    # Equity curve and drawdown
    equity = (1.0 + s).cumprod()
    peak = equity.cummax()
    drawdown = (equity / peak) - 1.0
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0
    calmar = float(mean / abs(max_drawdown)) if max_drawdown < 0 else 0.0

    # CVaR at 5%
    if n >= 20:
        var_5 = float(np.percentile(s, 5))
        cvar_5 = float(s[s <= var_5].mean()) if (s <= var_5).any() else var_5
    else:
        var_5 = float(np.percentile(s, 5))
        cvar_5 = var_5

    pos_sum = float(s[s > 0].sum())
    neg_sum = float(s[s < 0].sum())
    profit_factor = float(pos_sum / abs(neg_sum)) if neg_sum < 0 else (float("inf") if pos_sum > 0 else 0.0)

    win_rate = float((s > 0).mean())

    avg_win = float(s[s > 0].mean()) if (s > 0).any() else 0.0
    avg_loss = float(s[s < 0].mean()) if (s < 0).any() else 0.0
    risk_reward = float(avg_win / abs(avg_loss)) if avg_loss < 0 else 0.0

    return {
        "mean": mean,
        "std": std,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "calmar": calmar,
        "cvar_5": cvar_5,
        "profit_factor": profit_factor,
        "win_rate": win_rate,
        "risk_reward": risk_reward,
    }


def compute_overall(returns, equity_base: float | None = None) -> Dict[str, float]:
    """Compute overall (cumulative) metrics without per-bar averaging.

    Returns a minimal set focused on total outcome over the whole series:
      - total_return: (1 + r).prod() - 1
      - equity_final: equity_base * (1 + total_return) if equity_base provided
      - bars: number of bars
    """
    s = _to_series(returns)
    n = len(s)
    if n == 0:
        return {"total_return": 0.0, "equity_final": float(equity_base) if equity_base else 0.0, "bars": 0}
    total = float((1.0 + s).prod() - 1.0)
    eq_final = float(equity_base) * (1.0 + total) if equity_base else 0.0
    return {"total_return": total, "equity_final": eq_final, "bars": n}
