"""
Input Validation Utilities
Validates user inputs and configuration parameters
"""
from typing import Tuple, List, Dict, Any
import re
from pathlib import Path

class ConfigurationValidator:
    """Validate optimization configuration parameters"""

    VALID_SYMBOLS = ['ES', 'MES', 'NQ', 'MNQ', 'YM', 'MYM', 'RTY', 'M2K', 'CL', 'MCL', 'GC', 'MGC', 'SI']
    VALID_TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
    VALID_ACCOUNT_TYPES = ['topstep_50k', 'topstep_100k', 'topstep_150k']
    VALID_SPLIT_TYPES = ['chronological', 'walk_forward']

    @staticmethod
    def validate(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate complete configuration

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # Required fields
        required_fields = [
            'strategy', 'symbol', 'timeframe', 'account_type',
            'slippage', 'commission', 'contracts_per_trade', 'split_type'
        ]

        for field in required_fields:
            if field not in config or config[field] is None or config[field] == '':
                errors.append(f"Missing required field: {field}")

        # Validate strategy
        if 'strategy' in config and config['strategy']:
            if not ConfigurationValidator.validate_strategy(config['strategy']):
                errors.append(f"Invalid strategy name: {config['strategy']}")

        # Validate symbol
        if 'symbol' in config and config['symbol']:
            if config['symbol'] not in ConfigurationValidator.VALID_SYMBOLS:
                errors.append(f"Invalid symbol: {config['symbol']}. Must be one of {ConfigurationValidator.VALID_SYMBOLS}")

        # Validate timeframe
        if 'timeframe' in config and config['timeframe']:
            if config['timeframe'] not in ConfigurationValidator.VALID_TIMEFRAMES:
                errors.append(f"Invalid timeframe: {config['timeframe']}. Must be one of {ConfigurationValidator.VALID_TIMEFRAMES}")

        # Validate account type
        if 'account_type' in config and config['account_type']:
            if config['account_type'] not in ConfigurationValidator.VALID_ACCOUNT_TYPES:
                errors.append(f"Invalid account type: {config['account_type']}. Must be one of {ConfigurationValidator.VALID_ACCOUNT_TYPES}")

        # Validate numeric fields
        numeric_validations = [
            ('slippage', 0, 10, "Slippage must be between 0 and 10 ticks"),
            ('commission', 0, 50, "Commission must be between $0 and $50"),
            ('contracts_per_trade', 1, 100, "Contracts per trade must be between 1 and 100"),
            ('max_trials', 1, 100000, "Max trials must be between 1 and 100,000"),
            ('max_workers', 1, 64, "Max workers must be between 1 and 64"),
        ]

        for field, min_val, max_val, error_msg in numeric_validations:
            if field in config and config[field] is not None:
                try:
                    value = float(config[field])
                    if value < min_val or value > max_val:
                        errors.append(error_msg)
                except (ValueError, TypeError):
                    errors.append(f"{field} must be a valid number")

        # Validate split type
        if 'split_type' in config and config['split_type']:
            if config['split_type'] not in ConfigurationValidator.VALID_SPLIT_TYPES:
                errors.append(f"Invalid split type: {config['split_type']}. Must be one of {ConfigurationValidator.VALID_SPLIT_TYPES}")

        # Validate split ratios if provided
        if 'split_ratios' in config and config['split_ratios']:
            is_valid, ratio_errors = ConfigurationValidator.validate_split_ratios(config['split_ratios'])
            errors.extend(ratio_errors)

        # Validate data source (must have either data_file or synthetic_bars)
        has_data_file = 'data_file' in config and config['data_file']
        has_synthetic = 'synthetic_bars' in config and config['synthetic_bars']

        if not has_data_file and not has_synthetic:
            errors.append("Must specify either data_file or synthetic_bars")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_strategy(strategy_name: str) -> bool:
        """Validate strategy name format"""
        # Strategy names should be lowercase, underscore-separated
        pattern = r'^[a-z][a-z0-9_]*$'
        return bool(re.match(pattern, strategy_name))

    @staticmethod
    def validate_split_ratios(ratios_str: str) -> Tuple[bool, List[str]]:
        """Validate split ratios string (e.g., '0.6,0.2,0.2')"""
        errors = []

        try:
            ratios = [float(x.strip()) for x in ratios_str.split(',')]

            if len(ratios) != 3:
                errors.append("Split ratios must have exactly 3 values (train, validate, test)")

            for ratio in ratios:
                if ratio < 0 or ratio > 1:
                    errors.append("Each split ratio must be between 0 and 1")

            if abs(sum(ratios) - 1.0) > 0.001:
                errors.append(f"Split ratios must sum to 1.0 (currently: {sum(ratios)})")

        except ValueError:
            errors.append("Split ratios must be valid decimal numbers")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_data_file(file_path: str) -> Tuple[bool, List[str]]:
        """Validate data file path and format"""
        errors = []

        path = Path(file_path)

        if not path.exists():
            errors.append(f"File does not exist: {file_path}")
            return (False, errors)

        if not path.is_file():
            errors.append(f"Path is not a file: {file_path}")
            return (False, errors)

        # Check extension
        valid_extensions = ['.csv', '.parquet']
        if path.suffix.lower() not in valid_extensions:
            errors.append(f"Invalid file extension: {path.suffix}. Must be .csv or .parquet")

        return (len(errors) == 0, errors)

class DataValidator:
    """Validate data file contents"""

    REQUIRED_COLUMNS = ['datetime', 'open', 'high', 'low', 'close', 'volume']

    @staticmethod
    def validate_dataframe(df) -> Tuple[bool, List[str]]:
        """Validate pandas DataFrame structure"""
        errors = []

        # Check for required columns (case-insensitive)
        df_columns_lower = [col.lower() for col in df.columns]

        for required_col in DataValidator.REQUIRED_COLUMNS:
            if required_col not in df_columns_lower:
                errors.append(f"Missing required column: {required_col}")

        # Check for empty dataframe
        if len(df) == 0:
            errors.append("DataFrame is empty")

        # Check for sufficient data
        if len(df) < 100:
            errors.append(f"Insufficient data: {len(df)} rows. Need at least 100 rows")

        # Validate OHLC logic (if columns exist)
        if all(col in df_columns_lower for col in ['open', 'high', 'low', 'close']):
            # Check if high >= low
            if 'high' in df.columns and 'low' in df.columns:
                if not (df['high'] >= df['low']).all():
                    errors.append("Data validation failed: High must be >= Low")

        return (len(errors) == 0, errors)
