from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import os
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from .config import ValidationConfig, ValidationTestConfig
from .runner import ScriptRunner
from .metrics import compute_core, compute_overall
from .tests import TEST_FUNCTIONS


class ValidationEngine:
    """Run configured validation tests over parameter sets."""

    def __init__(
        self,
        config: ValidationConfig | None = None,
        max_workers: int | None = None,
        orchestrator: Optional[Any] = None,
        trading_config: Optional[Any] = None,
        execution_config: Optional[Dict[str, Any]] = None,
        loader_mode: str = "importlib",
    ) -> None:
        self.config = config or ValidationConfig()
        self.max_workers = max_workers or min(32, os.cpu_count() or 1)
        # Optional context for deployed-file validation
        self.orchestrator = orchestrator
        self.trading_config = trading_config
        self.execution_config = execution_config or {}
        self.loader_mode = loader_mode
        self.logger = logging.getLogger(__name__)

    # ------------------------- legacy param-set path ------------------------- #

    def _run_single(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Derive a deterministic seed from the parameter set for reproducibility
        seed = int(abs(hash(str(sorted(params.items())))) % (2**32))
        rng = np.random.default_rng(seed)

        results: Dict[str, Dict[str, Any]] = {}
        executed: List[str] = []
        total_score = 0.0
        passed_all = True

        informational = {"noise_injection", "regime_testing"}

        for name, cfg in self.config.__dict__.items():
            if not isinstance(cfg, ValidationTestConfig) or not cfg.enabled:
                continue

            test_fn = TEST_FUNCTIONS[name]
            metric, passed = test_fn(params, rng=rng, **cfg.params)
            results[name] = {"metric": metric, "passed": passed}
            executed.append(name)

            if name not in informational:
                total_score += metric
                passed_all = passed_all and passed

        return {
            "params": params,
            "score": total_score,
            "tests": executed,
            "results": results,
            "passed": passed_all,
        }

    def run(self, parameter_sets: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        params_list = list(parameter_sets)

        # Deployed-file mode: items contain 'file_path'
        if params_list and isinstance(params_list[0], dict) and "file_path" in params_list[0]:
            return self._run_deployed_files(params_list)

        # Legacy parameter-dict mode
        workers = min(self.max_workers, len(params_list)) or 1
        with ThreadPoolExecutor(max_workers=workers) as exe:
            return list(exe.map(self._run_single, params_list))

    # ------------------------ deployed-file validation ----------------------- #
    def _run_deployed_files(self, deployed_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.orchestrator or not self.trading_config:
            # Without context, we cannot execute deployed scripts; mark as failed
            return [
                {
                    "params": {**item, "error": "Missing orchestrator/trading_config for deployed-file validation"},
                    "score": 0.0,
                    "tests": [],
                    "results": {},
                    "passed": False,
                }
                for item in deployed_files
            ]

        # Acquire data splits via orchestrator with proper access control
        # In-sample = train + validation; use analytics phase to obtain both
        analytics_access = self.orchestrator.get_authorized_data("analytics", phase="analytics")
        validation_access = self.orchestrator.get_authorized_data("validation", phase="validation")

        train_df = getattr(analytics_access, "train_data", None)
        val_df = getattr(analytics_access, "validation_data", None)
        test_df = getattr(validation_access, "test_data", None)

        # Log data sizes for verification
        try:
            self.logger.info(
                f"Validation data sizes: train={len(train_df) if train_df is not None else 0}, "
                f"validation={len(val_df) if val_df is not None else 0}, "
                f"test={len(test_df) if test_df is not None else 0}"
            )
        except Exception:
            pass

        runner = ScriptRunner(
            trading_config=self.trading_config,
            execution_config=self.execution_config,
            loader_mode=self.loader_mode,
        )

        results: List[Dict[str, Any]] = []
        for item in deployed_files:
            try:
                script_path = item["file_path"]

                in_sample_returns: List[float] = []
                out_of_sample_returns: List[float] = []
                in_sample_trades = 0
                out_of_sample_trades = 0

                if train_df is not None and val_df is not None and len(train_df) and len(val_df):
                    ins = runner.run_in_sample(script_path, train_df, val_df)
                    in_sample_returns = ins.get("returns", [])
                    in_sample_trades = int(ins.get("trade_count", 0))
                if test_df is not None and len(test_df):
                    oos = runner.run_out_of_sample(script_path, test_df)
                    out_of_sample_returns = oos.get("returns", [])
                    out_of_sample_trades = int(oos.get("trade_count", 0))

                # Compute basic metrics on normalized returns
                metrics_in = compute_core(in_sample_returns) if in_sample_returns else {}
                metrics_oos = compute_core(out_of_sample_returns) if out_of_sample_returns else {}

                # Overall (cumulative) metrics using the same equity base used for normalization
                equity_base = None
                try:
                    equity_base = ins.get('equity_base') if 'ins' in locals() else None
                    if not equity_base:
                        equity_base = oos.get('equity_base') if 'oos' in locals() else None
                except Exception:
                    equity_base = None
                metrics_in_overall = compute_overall(in_sample_returns, equity_base) if in_sample_returns else {}
                metrics_oos_overall = compute_overall(out_of_sample_returns, equity_base) if out_of_sample_returns else {}


                enhanced = {
                    **item,
                    "in_sample_returns": in_sample_returns,
                    "out_of_sample_returns": out_of_sample_returns,
                    "in_sample_trade_count": in_sample_trades,
                    "out_of_sample_trade_count": out_of_sample_trades,
                    "metrics": {
                        "in": metrics_in,
                        "oos": metrics_oos,
                        "in_overall": metrics_in_overall,
                        "oos_overall": metrics_oos_overall,
                    },
                    "meta": {
                        "symbol": getattr(self.trading_config, "symbol", None),
                        "timeframe": getattr(self.trading_config, "timeframe", None),
                        "equity_base": equity_base,
                    }
                }

                # Reuse existing test machinery
                run_res = self._run_single(enhanced)

                # Enforce minimum trades baseline
                min_in = getattr(self.config, "min_trades_in_sample", 0)
                min_oos = getattr(self.config, "min_trades_out_of_sample", 0)
                baseline_ok = (in_sample_trades >= min_in) and (out_of_sample_trades >= min_oos)

                if not baseline_ok:
                    # Add baseline result into results map
                    tests_map = run_res.get("results", {})
                    tests_map["min_trades_baseline"] = {
                        "metric": {
                            "in_sample_trades": in_sample_trades,
                            "out_of_sample_trades": out_of_sample_trades,
                            "min_required_in": min_in,
                            "min_required_out": min_oos,
                        },
                        "passed": False,
                    }
                    run_res["results"] = tests_map
                    executed = run_res.get("tests", [])
                    executed.append("min_trades_baseline")
                    run_res["tests"] = executed
                    run_res["passed"] = False

                results.append(run_res)
            except Exception as e:
                results.append(
                    {
                        "params": {**item, "error": str(e)},
                        "score": 0.0,
                        "tests": [],
                        "results": {},
                        "passed": False,
                    }
                )

        return results


