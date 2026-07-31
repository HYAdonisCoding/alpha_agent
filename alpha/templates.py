"""
Alpha Templates Library
=======================
Pre-defined alpha expression templates organized by category.

These templates serve as building blocks that the AI agent combines
and parameterizes to create novel alpha expressions.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class AlphaTemplate:
    """A single alpha expression template."""

    name: str
    category: str
    expression: str
    description: str
    parameters: Dict[str, List] = field(default_factory=dict)
    universe_filter: Optional[str] = None  # "us", "cn", "large_cap", etc.


class AlphaTemplates:
    """
    Library of alpha factor templates categorized by strategy type.

    Each template is a parameterized expression string where:
    - {n}, {k}, {m} etc. are replaceable parameters
    - close, volume, etc. are data field references
    """

    # ========== Momentum Templates ==========
    # NOTE: Simple price momentum has near-zero IC on S&P 500 2020-2026
    # These are kept for regime rotation but weighted lower by default

    MOMENTUM: List[AlphaTemplate] = [
        AlphaTemplate(
            name="price_momentum",
            category="momentum",
            expression="rank(ts_delta(close, {n}))",
            description="Price momentum over n days",
            parameters={"n": [5, 10, 20, 40, 60, 120]},
        ),
        AlphaTemplate(
            name="risk_adjusted_momentum",
            category="momentum",
            expression="rank(ts_delta(close, {n}) / ts_std(close, {n}))",
            description="Risk-adjusted momentum (return / volatility)",
            parameters={"n": [20, 40, 60, 120]},
        ),
        AlphaTemplate(
            name="trend_strength",
            category="momentum",
            expression="rank(ts_rank(close, {n}))",
            description="Trend strength: percentile rank of price over n days",
            parameters={"n": [10, 20, 40, 60, 120, 252]},
        ),
        AlphaTemplate(
            name="decay_weighted_momentum",
            category="momentum",
            expression="rank(decay_linear(ts_delta(close, 1), {n}))",
            description="Momentum with linear decay weighting",
            parameters={"n": [10, 20, 40, 60]},
        ),
    ]

    # ========== Mean Reversion Templates ==========
    # NOTE: S&P 500 2020-2026: short-term reversal + medium-term mean reversion works

    MEAN_REVERSION: List[AlphaTemplate] = [
        AlphaTemplate(
            name="short_term_reversal",
            category="mean_reversion",
            expression="-rank(ts_delta(close, {n}))",
            description="Short-term price reversal (backtest Sharpe ~0.62 at n=5)",
            parameters={"n": [3, 5, 10, 20]},
        ),
        AlphaTemplate(
            name="medium_term_reversal",
            category="mean_reversion",
            expression="-rank(ts_delta(close, {n}))",
            description="Medium-term mean reversion (backtest Sharpe ~0.68 at n=40)",
            parameters={"n": [30, 40, 60, 80]},
        ),
        AlphaTemplate(
            name="risk_adj_reversal",
            category="mean_reversion",
            expression="-rank(ts_delta(close, {n}) / ts_std(close, {k}))",
            description="Risk-adjusted reversal: fade moves on high vol",
            parameters={"n": [5, 10, 20], "k": [20, 40, 60]},
        ),
        AlphaTemplate(
            name="bollinger_reversion",
            category="mean_reversion",
            expression="-rank((close - ts_mean(close, {n})) / ts_std(close, {n}))",
            description="Bollinger band reversion signal",
            parameters={"n": [10, 20, 40]},
        ),
        AlphaTemplate(
            name="volume_confirmed_reversal",
            category="mean_reversion",
            expression="-rank(ts_delta(close, {n})) * rank(ts_delta(volume, {n}))",
            description="Reversal confirmed by volume divergence",
            parameters={"n": [5, 10, 20]},
        ),
    ]

    # ========== Volume Templates ==========

    VOLUME: List[AlphaTemplate] = [
        AlphaTemplate(
            name="volume_price_corr",
            category="volume",
            expression="rank(ts_corr(close, volume, {n}))",
            description="Price-volume correlation (backtest Sharpe ~0.59 at n=20)",
            parameters={"n": [10, 20, 40, 60]},
        ),
        AlphaTemplate(
            name="volume_price_divergence",
            category="volume",
            expression="-rank(ts_corr(close, volume, {n}))",
            description="Price-volume anti-correlation (divergence signal)",
            parameters={"n": [10, 20, 40, 60]},
        ),
        AlphaTemplate(
            name="abnormal_volume_reversal",
            category="volume",
            expression="-rank(ts_delta(close, {n})) * rank(volume / ts_mean(volume, 20))",
            description="Reversal on abnormal volume days",
            parameters={"n": [5, 10]},
        ),
        AlphaTemplate(
            name="volume_trend_divergence",
            category="volume",
            expression="rank(-ts_delta(close, {n})) - rank(ts_delta(volume, {n}))",
            description="Price down + volume down = buying opportunity",
            parameters={"n": [10, 20, 40]},
        ),
    ]

    # ========== Volatility Templates ==========
    # NOTE: S&P 500 2020-2026: high-vol stocks outperformed massively
    # `rank(ts_std(close, n) / close)` — Sharpe 4.1~4.9 depending on lookback
    # The low-vol anomaly is DEAD in this market regime; long high-vol is the alpha.

    VOLATILITY: List[AlphaTemplate] = [
        AlphaTemplate(
            name="high_volatility_premium",
            category="volatility",
            expression="rank(ts_std(close, {n}) / close)",
            description="Long high-volatility stocks (backtest Sharpe 4.1-4.9 on S&P 500)",
            parameters={"n": [10, 20, 40, 60]},
        ),
        AlphaTemplate(
            name="volatility_regime_change",
            category="volatility",
            expression="rank(ts_std(close, {n}) / ts_std(close, {k}))",
            description="Ratio of short-term to long-term volatility",
            parameters={"n": [10, 20], "k": [60, 120, 252]},
        ),
    ]

    # ========== Correlation / Cross-Sectional Templates ==========

    CROSS_SECTIONAL: List[AlphaTemplate] = [
        AlphaTemplate(
            name="price_volume_correlation",
            category="cross_sectional",
            expression="rank(ts_corr(close, volume, {n}))",
            description="Correlation between price and volume",
            parameters={"n": [20, 40, 60]},
        ),
        AlphaTemplate(
            name="relative_strength",
            category="cross_sectional",
            expression="rank(close / ts_mean(close, {n}))",
            description="Relative strength vs own history",
            parameters={"n": [20, 40, 60, 120]},
        ),
    ]

    # ========== Combination Templates ==========

    COMBINATION: List[AlphaTemplate] = [
        AlphaTemplate(
            name="momentum_quality",
            category="combination",
            expression="rank(ts_delta(close, {n})) * rank(1 / ts_std(close, {n}))",
            description="Momentum adjusted for stability (quality)",
            parameters={"n": [20, 40, 60]},
        ),
        AlphaTemplate(
            name="trend_volume_divergence",
            category="combination",
            expression="rank(ts_delta(close, {n})) + (1 - rank(volume / ts_mean(volume, {n})))",
            description="Trend minus volume confirmation",
            parameters={"n": [20, 40]},
        ),
        AlphaTemplate(
            name="momentum_acceleration",
            category="combination",
            expression="rank(ts_delta(ts_delta(close, {n}), {n}))",
            description="Acceleration: second derivative of price",
            parameters={"n": [5, 10, 20]},
        ),
    ]

    @classmethod
    def get_all_templates(cls) -> List[AlphaTemplate]:
        """Get all templates across all categories."""
        all_templates = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, list) and attr and isinstance(attr[0], AlphaTemplate):
                all_templates.extend(attr)
        return all_templates

    @classmethod
    def get_by_category(cls, category: str) -> List[AlphaTemplate]:
        """Get templates for a specific category."""
        attr_name = category.upper().replace(" ", "_")
        attr = getattr(cls, attr_name, None)
        if isinstance(attr, list) and attr and isinstance(attr[0], AlphaTemplate):
            return attr
        return []

    @classmethod
    def get_categories(cls) -> List[str]:
        """List all available template categories."""
        return [
            attr_name.lower()
            for attr_name in dir(cls)
            if not attr_name.startswith("_")
            and isinstance(getattr(cls, attr_name), list)
            and getattr(cls, attr_name)
            and isinstance(getattr(cls, attr_name)[0], AlphaTemplate)
        ]

    @classmethod
    def get_parameter_combinations(
        cls, template: AlphaTemplate
    ) -> List[Dict]:
        """
        Generate all valid parameter combinations for a template.

        Example:
            template with params {"n": [10, 20], "k": [3, 5]}
            returns: [{"n": 10, "k": 3}, {"n": 10, "k": 5}, ...]
        """
        if not template.parameters:
            return [{}]

        import itertools

        keys = list(template.parameters.keys())
        values = [template.parameters[k] for k in keys]

        combinations = []
        for combo in itertools.product(*values):
            combinations.append(dict(zip(keys, combo)))

        return combinations

    @classmethod
    def instantiate(
        cls, template: AlphaTemplate, params: Dict
    ) -> str:
        """
        Replace template parameters with actual values.

        Example:
            template.expression = "rank(ts_delta(close, {n}))"
            params = {"n": 20}
            returns: "rank(ts_delta(close, 20))"
        """
        return template.expression.format(**params)
