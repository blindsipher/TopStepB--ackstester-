"""
Config-Driven Strategy Schema System
Enables dynamic parameter configuration for frontend integration

This module provides a JSON-compatible schema system for strategy parameters,
search spaces, and portfolio configuration. Designed for TopstepX GUI integration
and dynamic strategy management.

Key Features:
- JSON-serializable parameter definitions
- Optuna search space auto-generation
- Validation and constraint handling
- Frontend-friendly metadata
- Database storage compatibility
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
import json
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("strategy_schema")


class ParameterType(str, Enum):
    """Parameter types for optimization"""
    INT = "int"
    FLOAT = "float"
    CATEGORICAL = "categorical"
    BOOL = "bool"


class ConstraintType(str, Enum):
    """Constraint types for parameter relationships"""
    COMPARISON = "comparison"  # e.g., param1 < param2
    CONDITIONAL = "conditional"  # e.g., param1 only if flag=True
    MUTUALLY_EXCLUSIVE = "mutually_exclusive"  # e.g., use_a excludes use_b


@dataclass
class ParameterDef:
    """
    Parameter definition for strategy optimization.

    Defines a single parameter's properties, bounds, and metadata.
    """
    name: str
    param_type: ParameterType
    default: Union[int, float, str, bool]

    # For numeric parameters (INT, FLOAT)
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None

    # For categorical parameters
    choices: Optional[List[Union[str, int, float]]] = None

    # Optuna-specific
    log_scale: bool = False  # Use log scale for sampling

    # Metadata for frontend
    display_name: Optional[str] = None
    description: Optional[str] = None
    group: Optional[str] = None  # Group related parameters

    def validate(self) -> bool:
        """Validate parameter definition."""
        if self.param_type in [ParameterType.INT, ParameterType.FLOAT]:
            if self.min_value is None or self.max_value is None:
                raise ValueError(f"Parameter '{self.name}': min_value and max_value required for numeric types")

            if self.min_value >= self.max_value:
                raise ValueError(f"Parameter '{self.name}': min_value must be < max_value")

        elif self.param_type == ParameterType.CATEGORICAL:
            if not self.choices or len(self.choices) == 0:
                raise ValueError(f"Parameter '{self.name}': choices required for categorical type")

        return True

    def suggest_from_trial(self, trial):
        """
        Sample parameter value from Optuna trial.

        Args:
            trial: Optuna trial object

        Returns:
            Sampled parameter value
        """
        if self.param_type == ParameterType.INT:
            return trial.suggest_int(
                self.name,
                self.min_value,
                self.max_value,
                step=self.step or 1,
                log=self.log_scale
            )

        elif self.param_type == ParameterType.FLOAT:
            return trial.suggest_float(
                self.name,
                self.min_value,
                self.max_value,
                step=self.step,
                log=self.log_scale
            )

        elif self.param_type == ParameterType.CATEGORICAL:
            return trial.suggest_categorical(self.name, self.choices)

        elif self.param_type == ParameterType.BOOL:
            return trial.suggest_categorical(self.name, [True, False])

        else:
            raise ValueError(f"Unknown parameter type: {self.param_type}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterDef':
        """Create from dictionary."""
        # Convert param_type string to enum
        if isinstance(data.get('param_type'), str):
            data['param_type'] = ParameterType(data['param_type'])

        return cls(**data)


@dataclass
class Constraint:
    """
    Parameter constraint definition.

    Defines relationships between parameters that must be enforced
    during optimization.
    """
    constraint_type: ConstraintType
    params: List[str]  # Parameters involved
    operator: Optional[str] = None  # For comparison: '<', '>', '<=', '>=', '=='
    value: Optional[Any] = None  # For conditional constraints

    def validate_params(self, params_dict: Dict[str, Any]) -> bool:
        """
        Validate parameter values against this constraint.

        Args:
            params_dict: Dictionary of parameter values

        Returns:
            True if constraint is satisfied
        """
        if self.constraint_type == ConstraintType.COMPARISON:
            # Format: [param1, operator, param2]
            # Example: ['exit_period', '<', 'entry_period']
            if len(self.params) != 2:
                return True  # Skip invalid constraints

            param1_val = params_dict.get(self.params[0])
            param2_val = params_dict.get(self.params[1])

            if param1_val is None or param2_val is None:
                return True  # Skip if params not present

            # Evaluate comparison
            if self.operator == '<':
                return param1_val < param2_val
            elif self.operator == '>':
                return param1_val > param2_val
            elif self.operator == '<=':
                return param1_val <= param2_val
            elif self.operator == '>=':
                return param1_val >= param2_val
            elif self.operator == '==':
                return param1_val == param2_val
            else:
                return True

        elif self.constraint_type == ConstraintType.CONDITIONAL:
            # Format: [dependent_param, 'requires', condition_param, expected_value]
            # Example: ['stop_loss_atr', 'requires', 'use_stop_loss', True]
            if len(self.params) < 2:
                return True

            condition_param = self.params[1]
            condition_val = params_dict.get(condition_param)

            if condition_val != self.value:
                # Condition not met, dependent param should not be used
                # This is handled by not suggesting the param in the first place
                return True

            return True

        elif self.constraint_type == ConstraintType.MUTUALLY_EXCLUSIVE:
            # Format: [param1, 'excludes', param2]
            # Only one of the params should be True/enabled
            if len(self.params) != 2:
                return True

            param1_val = params_dict.get(self.params[0])
            param2_val = params_dict.get(self.params[1])

            # If both are True, constraint violated
            if param1_val and param2_val:
                return False

            return True

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Constraint':
        """Create from dictionary."""
        if isinstance(data.get('constraint_type'), str):
            data['constraint_type'] = ConstraintType(data['constraint_type'])

        return cls(**data)


@dataclass
class PortfolioConfig:
    """
    Portfolio and execution configuration.

    Defines how the strategy should be executed in the backtest.
    """
    # Position sizing
    contracts_per_trade: int = 1
    use_dynamic_sizing: bool = False
    size_as_percentage_of_equity: Optional[float] = None  # If dynamic sizing

    # Execution costs
    commission_per_trade: float = 0.62  # $ per side
    slippage_ticks: int = 1  # Ticks of slippage

    # Risk management (applied at portfolio level)
    max_position_size: Optional[int] = None
    daily_loss_limit: Optional[float] = None  # $
    max_drawdown_limit: Optional[float] = None  # $

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PortfolioConfig':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class StrategySchema:
    """
    Complete strategy schema with parameters, constraints, and metadata.

    This is the top-level schema object that defines everything needed
    to configure, optimize, and execute a strategy.
    """
    strategy_name: str
    strategy_class: str  # Python class name (e.g., 'BollingerBandsStrategy')
    description: str
    category: str  # 'trend', 'mean_reversion', 'momentum', etc.

    # Parameters and constraints
    parameters: List[ParameterDef] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)

    # Portfolio configuration
    portfolio_config: PortfolioConfig = field(default_factory=PortfolioConfig)

    # Metadata
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Frontend hints
    display_order: Optional[List[str]] = None  # Order to display parameters
    parameter_groups: Optional[Dict[str, List[str]]] = None  # Group params in UI

    def add_parameter(self, param_def: ParameterDef):
        """Add a parameter to the schema."""
        param_def.validate()
        self.parameters.append(param_def)

    def add_constraint(self, constraint: Constraint):
        """Add a constraint to the schema."""
        self.constraints.append(constraint)

    def get_parameter(self, name: str) -> Optional[ParameterDef]:
        """Get parameter definition by name."""
        for param in self.parameters:
            if param.name == name:
                return param
        return None

    def sample_from_trial(self, trial) -> Dict[str, Any]:
        """
        Sample all parameters from an Optuna trial.

        Args:
            trial: Optuna trial object

        Returns:
            Dict of parameter names to sampled values
        """
        params = {}

        for param_def in self.parameters:
            # Check conditional constraints before sampling
            should_sample = True

            for constraint in self.constraints:
                if constraint.constraint_type == ConstraintType.CONDITIONAL:
                    if param_def.name == constraint.params[0]:
                        # This is a conditional parameter
                        condition_param = constraint.params[1]
                        required_value = constraint.value

                        # Check if condition is met
                        if condition_param in params:
                            if params[condition_param] != required_value:
                                should_sample = False
                                break

            if should_sample:
                params[param_def.name] = param_def.suggest_from_trial(trial)

        # Validate constraints
        for constraint in self.constraints:
            if not constraint.validate_params(params):
                logger.warning(f"Constraint validation failed: {constraint}")
                # Optuna will prune this trial
                raise ValueError(f"Constraint violated: {constraint.constraint_type.value}")

        return params

    def get_default_params(self) -> Dict[str, Any]:
        """Get dictionary of default parameter values."""
        return {param.name: param.default for param in self.parameters}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'strategy_name': self.strategy_name,
            'strategy_class': self.strategy_class,
            'description': self.description,
            'category': self.category,
            'parameters': [p.to_dict() for p in self.parameters],
            'constraints': [c.to_dict() for c in self.constraints],
            'portfolio_config': self.portfolio_config.to_dict(),
            'version': self.version,
            'author': self.author,
            'tags': self.tags,
            'display_order': self.display_order,
            'parameter_groups': self.parameter_groups,
        }

    def to_json(self, filepath: Optional[Path] = None) -> str:
        """
        Export schema to JSON.

        Args:
            filepath: Optional file path to save JSON

        Returns:
            JSON string
        """
        json_str = json.dumps(self.to_dict(), indent=2)

        if filepath:
            Path(filepath).write_text(json_str)
            logger.info(f"Schema saved to {filepath}")

        return json_str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategySchema':
        """Create schema from dictionary."""
        # Convert nested objects
        parameters = [ParameterDef.from_dict(p) for p in data.get('parameters', [])]
        constraints = [Constraint.from_dict(c) for c in data.get('constraints', [])]
        portfolio_config = PortfolioConfig.from_dict(data.get('portfolio_config', {}))

        return cls(
            strategy_name=data['strategy_name'],
            strategy_class=data['strategy_class'],
            description=data['description'],
            category=data['category'],
            parameters=parameters,
            constraints=constraints,
            portfolio_config=portfolio_config,
            version=data.get('version', '1.0.0'),
            author=data.get('author'),
            tags=data.get('tags', []),
            display_order=data.get('display_order'),
            parameter_groups=data.get('parameter_groups'),
        )

    @classmethod
    def from_json(cls, filepath: Path) -> 'StrategySchema':
        """Load schema from JSON file."""
        data = json.loads(Path(filepath).read_text())
        return cls.from_dict(data)


# ==============================================================================
# EXAMPLE SCHEMA BUILDERS
# ==============================================================================

def create_bollinger_bands_schema() -> StrategySchema:
    """
    Example: Create schema for Bollinger Bands strategy.

    This demonstrates how to build a complete strategy schema.
    """
    schema = StrategySchema(
        strategy_name="bollinger_bands_mean_reversion",
        strategy_class="BollingerBandsStrategy",
        description="Mean reversion strategy using Bollinger Bands",
        category="mean_reversion",
        tags=["bollinger", "mean_reversion", "volatility"]
    )

    # Add parameters
    schema.add_parameter(ParameterDef(
        name="bb_period",
        param_type=ParameterType.INT,
        default=20,
        min_value=5,
        max_value=100,
        step=1,
        display_name="BB Period",
        description="Lookback period for Bollinger Bands",
        group="indicators"
    ))

    schema.add_parameter(ParameterDef(
        name="bb_std",
        param_type=ParameterType.FLOAT,
        default=2.0,
        min_value=1.0,
        max_value=3.0,
        step=0.1,
        display_name="BB Standard Deviations",
        description="Number of standard deviations for bands",
        group="indicators"
    ))

    schema.add_parameter(ParameterDef(
        name="use_stop_loss",
        param_type=ParameterType.BOOL,
        default=True,
        display_name="Use Stop Loss",
        description="Enable stop loss protection",
        group="risk"
    ))

    schema.add_parameter(ParameterDef(
        name="stop_loss_pct",
        param_type=ParameterType.FLOAT,
        default=2.0,
        min_value=0.5,
        max_value=5.0,
        step=0.1,
        display_name="Stop Loss %",
        description="Stop loss percentage",
        group="risk"
    ))

    # Add constraint: stop_loss_pct only relevant if use_stop_loss=True
    schema.add_constraint(Constraint(
        constraint_type=ConstraintType.CONDITIONAL,
        params=["stop_loss_pct", "use_stop_loss"],
        value=True
    ))

    # Set display order and grouping
    schema.display_order = ["bb_period", "bb_std", "use_stop_loss", "stop_loss_pct"]
    schema.parameter_groups = {
        "Indicator Settings": ["bb_period", "bb_std"],
        "Risk Management": ["use_stop_loss", "stop_loss_pct"]
    }

    return schema


def create_ema_cross_schema() -> StrategySchema:
    """Example: EMA crossover strategy schema."""
    schema = StrategySchema(
        strategy_name="ema_crossover",
        strategy_class="EMACrossStrategy",
        description="Trend following using EMA crossover",
        category="trend",
        tags=["ema", "crossover", "trend"]
    )

    schema.add_parameter(ParameterDef(
        name="fast_period",
        param_type=ParameterType.INT,
        default=10,
        min_value=5,
        max_value=50,
        step=1,
        display_name="Fast EMA Period",
        group="indicators"
    ))

    schema.add_parameter(ParameterDef(
        name="slow_period",
        param_type=ParameterType.INT,
        default=30,
        min_value=10,
        max_value=200,
        step=5,
        display_name="Slow EMA Period",
        group="indicators"
    ))

    # Add constraint: fast_period must be < slow_period
    schema.add_constraint(Constraint(
        constraint_type=ConstraintType.COMPARISON,
        params=["fast_period", "slow_period"],
        operator="<"
    ))

    schema.display_order = ["fast_period", "slow_period"]

    return schema
