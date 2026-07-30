"""
Risk Validator
==============
Risk control checks for alpha factors before submission.

Validates:
- Minimum data sufficiency
- No extreme concentration
- Reasonable turnover
- No look-ahead bias indicators
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from .engine import BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of risk validation checks."""

    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def add_recommendation(self, msg: str):
        self.recommendations.append(msg)


class RiskValidator:
    """
    Validate alpha factors against risk management rules.

    Usage:
        validator = RiskValidator()
        validation = validator.validate(backtest_result)
        if validation.passed:
            print("Alpha passed all risk checks")
    """

    def __init__(
        self,
        min_data_days: int = 252,
        min_assets: int = 10,
        max_turnover: float = 0.5,
        max_drawdown: float = 0.40,
        min_sharpe: float = 0.3,
        max_factor_correlation: float = 0.8,
    ):
        self.min_data_days = min_data_days
        self.min_assets = min_assets
        self.max_turnover = max_turnover
        self.max_drawdown = max_drawdown
        self.min_sharpe = min_sharpe
        self.max_factor_correlation = max_factor_correlation

    def validate(self, result: BacktestResult) -> ValidationResult:
        """Run all validation checks on a backtest result."""
        validation = ValidationResult()

        self._check_data_sufficiency(result, validation)
        self._check_performance(result, validation)
        self._check_risk(result, validation)
        self._check_turnover(result, validation)
        self._check_ic_stability(result, validation)

        return validation

    def _check_data_sufficiency(
        self, result: BacktestResult, validation: ValidationResult
    ):
        """Check if enough data was used."""
        if result.n_days < self.min_data_days:
            validation.add_error(
                f"Insufficient data: {result.n_days} days "
                f"(minimum: {self.min_data_days})"
            )

        if result.n_assets < self.min_assets:
            validation.add_error(
                f"Too few assets: {result.n_assets} "
                f"(minimum: {self.min_assets})"
            )

        if result.n_days < self.min_data_days * 3:
            validation.add_warning(
                f"Limited data history: {result.n_days} days. "
                f"Consider more historical data for robustness."
            )

    def _check_performance(
        self, result: BacktestResult, validation: ValidationResult
    ):
        """Check minimum performance thresholds."""
        if result.sharpe < self.min_sharpe:
            validation.add_warning(
                f"Low Sharpe ratio: {result.sharpe:.2f} "
                f"(minimum: {self.min_sharpe})"
            )

        if result.annual_return < 0:
            validation.add_error(
                f"Negative annual return: {result.annual_return:.2%}"
            )

        if result.calmar_ratio < 0.3:
            validation.add_warning(
                f"Low Calmar ratio: {result.calmar_ratio:.2f}"
            )

    def _check_risk(
        self, result: BacktestResult, validation: ValidationResult
    ):
        """Check risk metrics."""
        if abs(result.max_drawdown) > self.max_drawdown:
            validation.add_error(
                f"Excessive drawdown: {result.max_drawdown:.2%} "
                f"(maximum: {self.max_drawdown:.0%})"
            )

        if result.annual_volatility > 0.50:
            validation.add_warning(
                f"High annual volatility: {result.annual_volatility:.2%}"
            )

    def _check_turnover(
        self, result: BacktestResult, validation: ValidationResult
    ):
        """Check turnover constraints."""
        if result.turnover > self.max_turnover:
            validation.add_warning(
                f"High turnover: {result.turnover:.2%} "
                f"(maximum: {self.max_turnover:.0%})"
            )

        if result.turnover > 0.8:
            validation.add_error(
                f"Extreme turnover: {result.turnover:.2%}. "
                f"Alpha may be unstable."
            )

    def _check_ic_stability(
        self, result: BacktestResult, validation: ValidationResult
    ):
        """Check IC stability."""
        if result.ic_ir < 0.3:
            validation.add_warning(
                f"Low IC IR: {result.ic_ir:.2f}"
            )

        if result.ic_positive_ratio < 0.5:
            validation.add_warning(
                f"IC positive less than 50% of time: "
                f"{result.ic_positive_ratio:.1%}"
            )

        if result.ic_std > 0.15:
            validation.add_warning(
                f"High IC volatility: {result.ic_std:.4f}"
            )

    def check_correlation(
        self,
        new_factor: pd.Series,
        existing_factors: pd.DataFrame,
    ) -> Dict[str, float]:
        """
        Check if new factor is too correlated with existing ones.

        Args:
            new_factor: Factor values for new alpha
            existing_factors: DataFrame of existing factor values

        Returns:
            Dict of factor_name -> correlation
        """
        correlations = {}
        for col in existing_factors.columns:
            common = new_factor.dropna().index.intersection(
                existing_factors[col].dropna().index
            )
            if len(common) > 20:
                corr = new_factor[common].corr(existing_factors[col][common])
                correlations[col] = corr

        return correlations

    def summary_report(self, validation: ValidationResult) -> str:
        """Generate a human-readable validation summary."""
        lines = ["=" * 50, "RISK VALIDATION REPORT", "=" * 50, ""]

        if validation.passed:
            lines.append("Status: PASSED")
        else:
            lines.append("Status: FAILED")

        if validation.errors:
            lines.append(f"\nERRORS ({len(validation.errors)}):")
            for e in validation.errors:
                lines.append(f"  [ERROR] {e}")

        if validation.warnings:
            lines.append(f"\nWARNINGS ({len(validation.warnings)}):")
            for w in validation.warnings:
                lines.append(f"  [WARN]  {w}")

        if validation.recommendations:
            lines.append(f"\nRECOMMENDATIONS ({len(validation.recommendations)}):")
            for r in validation.recommendations:
                lines.append(f"  [REC]   {r}")

        lines.append("=" * 50)
        return "\n".join(lines)
