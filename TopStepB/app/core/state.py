"""
Pipeline State Management
========================

Central dataclass for managing all pipeline state across modules.
Clean state container that flows through all phases.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime


@dataclass
class PipelineState:
    """
    Central state object for the entire trading pipeline
    
    Flows through all phases providing clean interfaces between modules.
    Contains all configurations, data, and metadata needed for processing.
    """
    
    # Core Configuration
    strategy_name: str
    symbol: str
    timeframe: str
    account_type: str
    
    # Execution Configuration  
    slippage_ticks: float
    commission_per_trade: float
    contracts_per_trade: int
    
    # Data Configuration
    split_type: str
    data_file_path: Optional[str] = None
    synthetic_bars: int = 5000
    
    # ARCHITECTURAL FIX: Replace constants.py values with configurable parameters
    split_ratios: tuple = (0.6, 0.2, 0.2)  # train, validation, test ratios
    gap_days: int = 1  # Days between splits to prevent data leakage
    
    # Optimization Configuration
    optimization_enabled: bool = True
    max_trials: int = 100
    max_workers: int = 2
    memory_per_worker_mb: int = 1500
    timeout_per_trial: int = 60
    results_top_n: int = 10

    # Validation Configuration - which tests to execute
    validation_tests: List[str] = field(
        default_factory=lambda: ["in_sample", "out_of_sample"]
    )

    # Validation Test Configuration Parameters
    validation_min_trades_in_sample: int = 10
    validation_min_trades_out_of_sample: int = 5

    # In-Sample Permutation Test
    validation_in_sample_permutation: bool = False
    validation_in_sample_permutation_count: int = 1000
    validation_in_sample_permutation_threshold: float = 0.05

    # Out-of-Sample Permutation Test
    validation_out_of_sample_permutation: bool = False
    validation_out_of_sample_permutation_count: int = 1000
    validation_out_of_sample_permutation_threshold: float = 0.05

    # Monte Carlo Simulation
    validation_monte_carlo: bool = False
    validation_monte_carlo_simulations: int = 100

    # Noise Injection Test
    validation_noise_injection: bool = False
    validation_noise_injection_simulations: int = 100
    validation_noise_injection_sigma: float = 0.01

    # Regime Testing
    validation_regime_testing: bool = False
    
    
    # Runtime State (populated during pipeline execution)
    full_data: Optional[pd.DataFrame] = None
    split_result: Optional[Dict[str, Any]] = None
    trading_config: Optional[Any] = None
    strategy_instance: Optional[Any] = None
    strategy_metadata: Optional[Dict[str, Any]] = None
    
    # Optimization State (populated during parameter optimization)
    optimization_result: Optional[Dict[str, Any]] = None
    best_parameters: Optional[List[Dict[str, Any]]] = None
    
    # PipelineOrchestrator State (secure data access control)
    walk_forward_splits: Optional[List[Any]] = None  # List of DataSplit objects for walk-forward
    secure_orchestrator: Optional[Any] = None  # PipelineOrchestrator instance for secure data access
    
    # Pipeline Metadata
    created_at: Optional[datetime] = None
    pipeline_phase: str = "initialized"
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    
    def __post_init__(self):
        """Initialize state after creation"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def add_error(self, error: str) -> None:
        """Add error to state"""
        self.errors.append(f"[{datetime.now().isoformat()}] {error}")
    
    def add_warning(self, warning: str) -> None:
        """Add warning to state"""
        self.warnings.append(f"[{datetime.now().isoformat()}] {warning}")
    
    def has_errors(self) -> bool:
        """Check if state has errors"""
        return len(self.errors) > 0
    
    def update_phase(self, phase: str) -> None:
        """Update current pipeline phase"""
        self.pipeline_phase = phase
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization"""
        result = {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'account_type': self.account_type,
            'slippage_ticks': self.slippage_ticks,
            'commission_per_trade': self.commission_per_trade,
            'contracts_per_trade': self.contracts_per_trade,
            'split_type': self.split_type,
            'data_file_path': self.data_file_path,
            'pipeline_phase': self.pipeline_phase,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'has_data': self.full_data is not None,
            'data_rows': len(self.full_data) if self.full_data is not None else 0,
            'has_errors': self.has_errors(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
        }
        
        # Include optimization results if available
        if self.optimization_result:
            # Convert optimization result to serializable format (exclude study object)
            opt_result = self.optimization_result.copy()
            if 'study' in opt_result:
                # Replace study object with summary
                study = opt_result.pop('study')
                opt_result['study_summary'] = {
                    'study_name': getattr(study, 'study_name', 'unknown'),
                    'best_value': getattr(study, 'best_value', None),
                    'total_trials': len(getattr(study, 'trials', []))
                }
            result['optimization_result'] = opt_result
        
        if self.best_parameters:
            result['best_parameters_count'] = len(self.best_parameters)
            result['has_optimization_results'] = True
        else:
            result['best_parameters_count'] = 0
            result['has_optimization_results'] = False
        
        return result
    
    def get_summary(self) -> str:
        """Get human-readable summary of state"""
        summary = f"""
Pipeline State Summary:
======================
Strategy: {self.strategy_name}
Market: {self.symbol} ({self.timeframe})
Account: {self.account_type}
Execution: {self.slippage_ticks} ticks slippage, ${self.commission_per_trade} commission, {self.contracts_per_trade} contracts
Split: {self.split_type}
Data: {len(self.full_data) if self.full_data is not None else 0} bars
Phase: {self.pipeline_phase}
Status: {'ERROR: Has Errors' if self.has_errors() else 'CLEAN'}"""
        
        # Add optimization summary if available
        if self.optimization_result:
            opt_summary = self.optimization_result.get('optimization_metadata', {})
            summary += f"""
Optimization: {opt_summary.get('total_trials', 0)} trials, """
            if 'best_score' in opt_summary:
                summary += f"best score: {opt_summary['best_score']:.4f}, "
            if 'optimization_time' in opt_summary:
                summary += f"time: {opt_summary['optimization_time']:.1f}s"
            
            if self.best_parameters:
                summary += f"""
Parameters: {len(self.best_parameters)} optimized sets ready for deployment"""
        
        return summary.strip()

    # ---------------- Memory management helpers ---------------- #
    def prune_heavy_state(self) -> None:
        """Release large, phase-specific objects to reduce memory footprint.

        Intended to be called near the end of pipeline execution or before
        serializing results. Removes references to large dataframes and
        objects that are no longer needed beyond reporting.
        """
        try:
            # Drop raw dataframes and split containers
            self.full_data = None
            self.walk_forward_splits = None
            # Orchestrator can hold large dataframes; drop it after validation/analytics
            self.secure_orchestrator = None
        except Exception:
            pass

        # Ensure heavyweight optimization internals are not retained
        try:
            if isinstance(self.optimization_result, dict):
                self.optimization_result.pop('study', None)
        except Exception:
            pass


@dataclass 
class ExecutionConfig:
    """Execution parameters for trading"""
    slippage_ticks: float
    commission_per_trade: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'slippage_ticks': self.slippage_ticks,
            'commission_per_trade': self.commission_per_trade
        }


@dataclass
class SplitConfig:
    """Data splitting configuration"""
    split_type: str
    train_ratio: float = 0.8
    window_months: int = 12
    step_months: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'split_type': self.split_type,
            'train_ratio': self.train_ratio,
            'window_months': self.window_months,
            'step_months': self.step_months
        }
