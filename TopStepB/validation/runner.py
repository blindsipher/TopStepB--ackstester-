"""
Deployed Strategy Script Runner
===============================

Runs a deployed strategy script (Python module) over OHLCV dataframes in a
bar-by-bar manner, approximating live execution. Returns a simple per-bar PnL
series in dollars using position-based mark-to-market with basic cost model.

This runner is intentionally lightweight and in-process for speed. It relies on
the deployed script exposing a factory `create_live_strategy()` that returns an
object with a `process_new_bar(bar: dict, account_balance=...) -> dict` method
and a `get_current_position_info()` method.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import util as importlib_util
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import pandas as pd


@dataclass
class ExecutionConfig:
    """Execution parameters used to approximate trading costs."""
    slippage_ticks: float = 0.0
    commission_per_trade: float = 0.0
    contracts_per_trade: int = 1


class ScriptRunner:
    """Load a deployed script and run it over dataframes to produce PnL series."""

    def __init__(
        self,
        trading_config: Any,
        execution_config: Optional[Dict[str, Any]] = None,
        loader_mode: str = "importlib",
    ) -> None:
        self.trading_config = trading_config
        self.exec_cfg = ExecutionConfig(**(execution_config or {}))
        self.loader_mode = loader_mode

        # Derive point value from trading config (tick value per tick size)
        try:
            tick_size = float(getattr(trading_config.market_spec, "tick_size"))
            tick_value = float(getattr(trading_config.market_spec, "tick_value"))
            self.point_value = tick_value / tick_size if tick_size else 1.0
        except Exception:
            # Fallback if market_spec not available
            self.point_value = 1.0

        # Equity base for normalization (returns = pnl / equity_base)
        equity_base = None

        # 1) Caller override via execution_config
        try:
            if execution_config and "equity_base" in execution_config:
                equity_base = float(execution_config["equity_base"])
        except Exception:
            equity_base = None

        # 2) Prefer selected account's starting balance from TradingConfig
        if equity_base is None:
            try:
                account_cfg = getattr(self.trading_config, "account_config", None)
                if account_cfg is not None:
                    if hasattr(account_cfg, "starting_balance"):
                        equity_base = float(account_cfg.starting_balance)
                    elif hasattr(account_cfg, "account_size"):
                        equity_base = float(account_cfg.account_size)
            except Exception:
                equity_base = None

        # 3) Fallback to runtime configuration initial equity
        if equity_base is None:
            try:
                from config.system_config import RuntimeConfiguration
                equity_base = float(RuntimeConfiguration.get_runtime_config().initial_equity)
            except Exception:
                equity_base = 100000.0

        self.equity_base = equity_base

    # ----------------------------- Public API ----------------------------- #
    def run_in_sample(
        self,
        script_path: str,
        train_df: pd.DataFrame,
        validation_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        df = pd.concat([train_df, validation_df], ignore_index=True)
        df = df.sort_values("datetime")
        returns, trade_count = self._run_on_dataframe(script_path, df)
        return {"returns": returns, "trade_count": trade_count, "equity_base": self.equity_base}

    def run_out_of_sample(self, script_path: str, test_df: pd.DataFrame) -> Dict[str, Any]:
        df = test_df.sort_values("datetime")
        returns, trade_count = self._run_on_dataframe(script_path, df)
        return {"returns": returns, "trade_count": trade_count, "equity_base": self.equity_base}

    # --------------------------- Internal helpers ------------------------- #
    def _load_module(self, script_path: str):
        path = Path(script_path)
        if not path.exists():
            raise FileNotFoundError(f"Deployed script not found: {script_path}")

        # Fast, structured module loading
        spec = importlib_util.spec_from_file_location(path.stem, str(path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create import spec for: {script_path}")
        module = importlib_util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return module

    def _create_strategy(self, module) -> Any:
        if not hasattr(module, "create_live_strategy"):
            raise ValueError("Deployed script missing 'create_live_strategy' factory")
        strategy = module.create_live_strategy()
        return strategy

    def _extract_market_params(self, module) -> Tuple[float, float]:
        # Prefer script-level globals, fall back to trading_config-derived values
        tick_size = getattr(module, "tick_size", None)
        tick_value = getattr(module, "tick_value", None)
        try:
            if tick_size is not None and tick_value is not None:
                return float(tick_size), float(tick_value)
        except Exception:
            pass

        try:
            ts = float(getattr(self.trading_config.market_spec, "tick_size"))
            tv = float(getattr(self.trading_config.market_spec, "tick_value"))
            return ts, tv
        except Exception:
            # Reasonable defaults (ES-like) if neither available
            return 0.25, 12.50

    def _run_on_dataframe(self, script_path: str, df: pd.DataFrame) -> Tuple[List[float], int]:
        module = self._load_module(script_path)
        strategy = self._create_strategy(module)

        tick_size, tick_value = self._extract_market_params(module)
        point_value = tick_value / tick_size if tick_size else self.point_value

        # Basic cost model in dollars
        def trade_cost(transitions: int) -> float:
            # One side cost: slippage_ticks * tick_value + commission
            one_side = (self.exec_cfg.slippage_ticks * tick_value) + self.exec_cfg.commission_per_trade
            return transitions * one_side * self.exec_cfg.contracts_per_trade

        returns: List[float] = []
        prev_close: Optional[float] = None
        prev_position = 0
        trade_count = 0

        # Iterate bars in time order
        for row in df.sort_values("datetime").itertuples(index=False):
            close = float(getattr(row, "close"))
            open_ = float(getattr(row, "open"))
            high = float(getattr(row, "high"))
            low = float(getattr(row, "low"))
            volume = float(getattr(row, "volume")) if hasattr(row, "volume") else 0.0
            ts = getattr(row, "datetime")
            ts_str = str(ts)

            bar = {
                "timestamp": ts_str,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }

            decision = strategy.process_new_bar(bar, account_balance=100000)

            # Determine current position
            pos_info = None
            if isinstance(decision, dict):
                pos_info = decision.get("position_info")
            if pos_info is None and hasattr(strategy, "get_current_position_info"):
                pos_info = strategy.get_current_position_info()
            position = int(pos_info.get("position", 0)) if pos_info else 0

            # Per-bar PnL is mark-to-market from previous close using held position
            if prev_close is None:
                pnl = 0.0
            else:
                price_diff = (close - prev_close)
                pnl = price_diff * position * point_value * self.exec_cfg.contracts_per_trade

            # Apply transaction costs when position changes
            if position != prev_position:
                # Flat->pos or pos->flat: 1 transition; pos->other pos: 2 (exit+entry)
                transitions = 1 if (prev_position == 0 or position == 0) else 2
                pnl -= trade_cost(transitions)

                # Count entries as trades (flat->pos or sign flip implies new entry)
                if position != 0:
                    trade_count += 1

            # Normalize PnL to per-bar returns for stable metrics
            ret = float(pnl) / float(self.equity_base) if self.equity_base else float(pnl)
            returns.append(ret)
            prev_close = close
            prev_position = position

        return returns, trade_count

