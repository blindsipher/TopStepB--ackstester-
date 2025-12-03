from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import re
import numpy as np

# QuantStats is OPTIONAL for enhanced analytics tear sheets only
# NOTE: Core validation and optimization use VectorBT's portfolio.stats() instead
# This is only used in analytics/engine.py for professional metric calculations
# and full HTML tear sheet generation. All optimization metrics come from VectorBT.
try:
    from quantstats import stats as qs  # type: ignore
    from quantstats import reports as qsr  # type: ignore
    _QS_AVAILABLE = True
except Exception:
    qs = None  # type: ignore
    qsr = None  # type: ignore
    _QS_AVAILABLE = False

from validation.metrics import compute_core
from .frequency import resolve_freq_and_annualization
from .plots import cumulative_return_image, drawdown_image


class AnalyticsEngine:
    """Generate professional two-page tear sheets per passed template.

    Page 1: In-sample + Out-of-sample quantstats metrics (curated), compact plots.
    Page 2: Tests summary (required + optional).
    """

    def __init__(self, max_size: int = 10, output_dir: str | os.PathLike[str] = "tear_sheets") -> None:
        self.max_size = max_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._cache: List[Dict[str, Any]] = []

    # --------------------------- core helpers --------------------------- #
    def _series(self, returns: List[float], freq: str) -> pd.Series:
        if not returns:
            return pd.Series(dtype=float)
        idx = pd.date_range("2000-01-01", periods=len(returns), freq=freq)
        return pd.Series(returns, index=idx)

    def _pro_metrics(self, returns: List[float], annualization: float | None) -> Dict[str, float]:
        if not returns:
            return {}
        s = self._series(returns, "D")  # index is uniform; annualization corrects scale

        def safe(fn, *args, **kwargs) -> float:
            try:
                val = fn(s, *args, **kwargs)
                return float(val) if val is not None else float("nan")
            except Exception:
                return float("nan")

        # Prefer QuantStats if available; otherwise compute basic fallbacks
        if _QS_AVAILABLE and qs is not None:
            periods = annualization if isinstance(annualization, (int, float)) and annualization else None
            sharpe = safe(qs.sharpe, rf=0.0, periods=periods)
            sortino = safe(qs.sortino, rf=0.0, periods=periods)
            cagr = safe(qs.cagr, rf=0.0, periods=periods)
            calmar = safe(qs.calmar)
            max_dd = safe(qs.max_drawdown)
            tail = safe(qs.tail_ratio)
            omega = safe(qs.omega, 0.0)
            var5 = safe(qs.value_at_risk, confidence=0.95)
            cvar5 = safe(qs.cvar, confidence=0.95)
        else:
            # Fallback computations
            m = float(s.mean()) if len(s) else 0.0
            v = float(s.std(ddof=0)) if len(s) else 0.0
            sharpe = float(m / v) if v > 0 else 0.0
            # Downside std for sortino
            downside = np.minimum(s.values, 0.0)
            dstd = float(np.sqrt(np.mean(np.square(downside)))) if len(s) else 0.0
            sortino = float(m / dstd) if dstd > 0 else 0.0
            # Equity/drawdown basics
            eq = (1.0 + s).cumprod()
            peak = eq.cummax()
            dd = (eq / peak) - 1.0
            max_dd = float(dd.min()) if len(dd) else 0.0
            calmar = float(m / abs(max_dd)) if max_dd < 0 else 0.0
            cagr = float(eq.iloc[-1] ** ( (annualization or 252.0) / max(len(s),1) ) - 1.0) if len(eq) else 0.0
            tail = float('nan')
            omega = float('nan')
            # VaR/CVaR (simple percentile-based)
            if len(s) >= 20:
                var_q = float(np.percentile(s, 5))
                cvar5 = float(s[s <= var_q].mean()) if (s <= var_q).any() else var_q
                var5 = var_q
            else:
                var5 = float(np.percentile(s, 5)) if len(s) else 0.0
                cvar5 = var5
        # Approximate stability: R^2 of cumulative equity vs time index
        try:
            eq = (1 + s).cumprod().values
            if len(eq) > 1:
                x = np.arange(len(eq), dtype=float)
                r = np.corrcoef(x, eq)[0, 1]
                stability = float(r * r) if r == r else float("nan")
            else:
                stability = float("nan")
        except Exception:
            stability = float("nan")
        core = compute_core(returns)
        return {
            "mean": core.get("mean", 0.0),
            "sharpe": sharpe,
            "sortino": sortino,
            "cagr": cagr,
            "calmar": calmar,
            "max_drawdown": max_dd,
            "tail_ratio": tail,
            "stability": stability,
            "omega": omega,
            "var_5": var5,
            "cvar_5": cvar5,
            "win_rate": core.get("win_rate", 0.0),
            "profit_factor": core.get("profit_factor", 0.0),
            "risk_reward": core.get("risk_reward", 0.0),
        }

    # --------------------------- page builders -------------------------- #
    def _extract_body(self, html_text: str) -> str:
        try:
            m = re.search(r'<body[^>]*>([\s\S]*?)</body>', html_text, re.IGNORECASE)
            return m.group(1) if m else html_text
        except Exception:
            return html_text

    def _build_metrics_page(self, result: Dict[str, Any]) -> Dict[str, Any]:
        params = result.get("params", {})
        rin = params.get("in_sample_returns", [])
        roos = params.get("out_of_sample_returns", [])
        meta = params.get("meta", {})
        timeframe = meta.get("timeframe") if isinstance(meta, dict) else None
        freq, annual = resolve_freq_and_annualization(timeframe or "1d")

        minfo = self._pro_metrics(rin, annual)
        ninfo = self._pro_metrics(roos, annual)

        fname = f"metrics_{uuid.uuid4().hex}.html"
        fpath = self.output_dir / fname

        # Small images for cumret & drawdown
        img_cum_in = cumulative_return_image(rin, freq)
        img_dd_in = drawdown_image(rin, freq)
        img_cum_oos = cumulative_return_image(roos, freq)
        img_dd_oos = drawdown_image(roos, freq)

        keys = [
            "mean","sharpe","sortino","cagr","calmar","max_drawdown",
            "tail_ratio","stability","omega","cvar_5","win_rate","profit_factor","risk_reward",
        ]

        def cell(v: Any) -> str:
            try:
                return f"{float(v):.6g}"
            except Exception:
                return str(v) if v is not None else ""

        with open(fpath, "w", encoding="utf-8") as fh:
            fh.write("<html><head><meta charset='utf-8'><title>Metrics</title>\n")
            fh.write("<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;background:#fafafa;color:#222;}h2{margin-top:0}table{border-collapse:collapse;margin-top:10px;border-radius:6px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);}th,td{border:1px solid #ddd;padding:8px 10px;text-align:right;background:#fff;}th{background:#f3f3f3;}th:first-child,td:first-child{text-align:left;}img{border:1px solid #ddd;margin:6px;border-radius:4px;background:#fff;}</style>")
            fh.write("</head><body>")
            fh.write("<h2>In-Sample & Out-of-Sample Metrics</h2>")
            fh.write("<table><tr><th>Set</th>" + "".join(f"<th>{k}</th>" for k in keys) + "</tr>")
            fh.write("<tr><td><b>In-Sample</b></td>" + "".join(f"<td>{cell(minfo.get(k))}</td>" for k in keys) + "</tr>")
            fh.write("<tr><td><b>Out-of-Sample</b></td>" + "".join(f"<td>{cell(ninfo.get(k))}</td>" for k in keys) + "</tr></table>")
            fh.write("<p><i>In-sample = train+validation; Out-of-sample = test only. Metrics are per-bar, annualized where applicable using timeframe.</i></p>")

            # Inline plots
            if img_cum_in:
                fh.write(f"<div><b>In-Sample</b> &nbsp; <img src='data:image/png;base64,{img_cum_in}' width='380'/> <img src='data:image/png;base64,{img_dd_in}' width='380'/></div>")
            if img_cum_oos:
                fh.write(f"<div><b>Out-of-Sample</b> &nbsp; <img src='data:image/png;base64,{img_cum_oos}' width='380'/> <img src='data:image/png;base64,{img_dd_oos}' width='380'/></div>")

            fh.write("</body></html>")

        combined = (rin or []) + (roos or [])
        summary = self._pro_metrics(combined, annual)
        summary["in"] = minfo
        summary["oos"] = ninfo
        return {"metrics": summary, "path": str(fpath)}

    def _build_tests_page(self, result: Dict[str, Any]) -> str:
        tests = result.get("results", {})
        fname = f"tests_{uuid.uuid4().hex}.html"
        fpath = self.output_dir / fname

        def stringify(obj: Any) -> str:
            if isinstance(obj, dict):
                return ", ".join(f"{k}={obj[k]}" for k in obj)
            return str(obj)

        with open(fpath, "w", encoding="utf-8") as fh:
            fh.write("<html><head><meta charset='utf-8'><title>Robustness Tests</title>")
            fh.write("<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px;}table{border-collapse:collapse;}th,td{border:1px solid #ccc;padding:6px 10px;text-align:left;}th:nth-child(2),td:nth-child(2){text-align:right;}</style>")
            fh.write("</head><body>")
            fh.write("<h2>Optional & Statistical Tests Summary</h2>")
            fh.write("<table><tr><th>Test</th><th>Metric</th><th>Status</th></tr>")
            for name, payload in tests.items():
                metric = payload.get("metric") if isinstance(payload, dict) else payload
                passed = payload.get("passed") if isinstance(payload, dict) else True
                fh.write(f"<tr><td>{name}</td><td>{stringify(metric)}</td><td>{'PASS' if passed else 'FAIL'}</td></tr>")
            fh.write("</table>")
            fh.write("</body></html>")

        return str(fpath)

    def _generate_tear_sheet(self, result: Dict[str, Any]) -> Dict[str, Any]:
        metrics_page = self._build_metrics_page(result)
        tests_page = self._build_tests_page(result)
        out: Dict[str, Any] = {
            "metrics": metrics_page.get("metrics", {}),
            "path": metrics_page.get("path", ""),
            "tests_path": tests_page,
        }
        # Optional: generate full QuantStats report for combined returns if available
        if _QS_AVAILABLE and qsr is not None:
            try:
                params = result.get("params", {})
                combined = (params.get("in_sample_returns") or []) + (params.get("out_of_sample_returns") or [])
                if combined:
                    s = self._series(combined, "D")
                    full_name = f"qs_report_{uuid.uuid4().hex}.html"
                    full_path = self.output_dir / full_name
                    # Generate full tear sheet without opening in browser
                    qsr.html(s, output=str(full_path), title="Strategy Report", download_filename=None)
                    out["qs_report_path"] = str(full_path)
            except Exception:
                pass
        return out

    # ------------------------------ API ------------------------------ #
    def ingest(self, validation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for res in validation_results:
            if not res.get("passed"):
                continue
            res["tear_sheet"] = self._generate_tear_sheet(res)
            self._cache.append(res)

        self._cache.sort(key=lambda r: r.get("score", 0), reverse=True)
        self._cache = self._cache[: self.max_size]
        return list(self._cache)

    def get_winners(self, top_n: int | None = None) -> List[Dict[str, Any]]:
        if top_n is None or top_n >= len(self._cache):
            return list(self._cache)
        return self._cache[:top_n]





