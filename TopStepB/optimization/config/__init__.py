"""
Optimization Configuration Module
==================================

Contains configuration classes and settings for Optuna-based optimization.
"""

from .optuna_config import (
    OptimizationConfig,
    CompositeScoreWeights,
    MetricNormalizationBounds,
    create_study_paths,
)

__all__ = [
    'OptimizationConfig',
    'CompositeScoreWeights',
    'MetricNormalizationBounds',
    'create_study_paths',
]
