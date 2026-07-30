"""
BRAIN Properties Generator
============================
Auto-generates WorldQuant BRAIN submission properties (name, tags, color,
description) from alpha candidates and their backtest results.

These properties are pre-filled at DB-save time so every quality alpha
in the database is submission-ready.
"""

import re
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# ---- Colour palette by category ----
CATEGORY_COLORS: Dict[str, str] = {
    "momentum":        "#3366CC",  # blue
    "mean_reversion":  "#DC3912",  # red
    "volume":          "#109618",  # green
    "volatility":      "#FF9900",  # orange
    "cross_sectional": "#990099",  # purple
    "combination":     "#0099C6",  # teal
}

# _DEFAULT_COLOR used for unknown categories
_DEFAULT_COLOR = "#666666"

# ---- Frequency / horizon tags based on dominant parameter ----
_HORIZON_TAGS: Dict[str, str] = {
    "short":  "short-term",       # n <= 10
    "mid":    "mid-frequency",    # 10 < n <= 60
    "long":   "long-term",        # n > 60
}

# ---- Expression operator → descriptive tag ----
_OPERATOR_TAGS: Dict[str, str] = {
    "ts_delta":   "trend",
    "ts_rank":    "rank-based",
    "ts_zscore":  "reversion",
    "ts_mean":    "mean-referenced",
    "ts_std":     "volatility-sensitive",
    "ts_corr":    "correlation-based",
    "volume":     "volume-weighted",
    "decay_linear": "time-decay",
}


def generate_brain_props(
    candidate: Any,
    backtest_result: Optional[Any] = None,
) -> Dict[str, str]:
    """
    Generate BRAIN submission properties for an alpha candidate.

    Args:
        candidate: AlphaCandidate with .name, .category, .expression,
                   .template_name, .parameters, .description
        backtest_result: BacktestResult (optional — enriches description with metrics)

    Returns:
        Dict with keys: brain_name, tags, color, description
    """
    category = getattr(candidate, "category", "unknown")
    expression = getattr(candidate, "expression", "")
    params = getattr(candidate, "parameters", {}) or {}
    internal_name = getattr(candidate, "name", "")
    internal_desc = getattr(candidate, "description", "")

    brain_name = _make_brain_name(internal_name, params, category)
    tags = _make_tags(category, expression, params)
    color = CATEGORY_COLORS.get(category, _DEFAULT_COLOR)
    description = _make_description(internal_name, internal_desc, expression,
                                    category, backtest_result)

    return {
        "brain_name": brain_name,
        "tags": tags,
        "color": color,
        "description": description,
    }


# ---- Internal helpers -------------------------------------------------

def _make_brain_name(internal_name: str, params: Dict, category: str) -> str:
    """Convert snake_case internal name to a readable BRAIN display name.

    volume_price_trend_n40  →  Volume Price Trend 40D
    trend_strength_n60      →  Trend Strength 60D
    gap_reversion_n20_k60   →  Gap Reversion 20D/60D
    """
    # Strip trailing _nXX param suffixes we added in generator.py
    # but keep them readable as "40D" etc
    base = re.sub(r'_n\d+.*$', '', internal_name)
    base = base.replace('_', ' ').strip()

    # Build readable param suffix
    param_parts = []
    for k, v in sorted(params.items()):
        if k == "n":
            param_parts.append(f"{v}D")
        else:
            param_parts.append(f"{k}{v}")

    if param_parts:
        return f"{base.title()} {'/'.join(param_parts)}"
    return base.title()


def _make_tags(category: str, expression: str, params: Dict) -> str:
    """Generate comma-separated tags: category, operator-derived, horizon, etc."""
    tags = [category.replace("_", "-")]

    # Operator-derived tags
    for op_key, op_tag in _OPERATOR_TAGS.items():
        if op_key in expression:
            if op_tag not in tags:
                tags.append(op_tag)

    # Horizon tag from dominant parameter
    n = params.get("n", 20)
    if isinstance(n, (int, float)):
        if n <= 10:
            tags.append(_HORIZON_TAGS["short"])
        elif n <= 60:
            tags.append(_HORIZON_TAGS["mid"])
        else:
            tags.append(_HORIZON_TAGS["long"])

    # Cross-sectional rank tag
    if "rank(" in expression:
        tags.append("cross-sectional")

    return ", ".join(tags)


def _make_description(
    name: str,
    internal_desc: str,
    expression: str,
    category: str,
    backtest: Optional[Any] = None,
) -> str:
    """Generate a BRAIN submission-ready description.

    Combines the internal template description with metric highlights
    when a backtest result is available.
    """
    parts = []

    # Core idea (from template description)
    if internal_desc:
        parts.append(internal_desc[0].upper() + internal_desc[1:].rstrip('.'))

    # Expression note
    parts.append(f"Expression: {expression}")

    # Category note
    category_labels = {
        "momentum": "Captures directional price momentum signals.",
        "mean_reversion": "Betting on price reversion to the mean after extremes.",
        "volume": "Uses trading volume to confirm or filter price signals.",
        "volatility": "Exploits volatility patterns and anomalies.",
        "cross_sectional": "Cross-sectional comparison across the universe.",
        "combination": "Combines multiple factor families for robustness.",
    }
    if category in category_labels:
        parts.append(category_labels[category])

    # Metric highlights (when available)
    if backtest is not None:
        sharpe = getattr(backtest, "sharpe", None)
        fitness = getattr(backtest, "fitness", None)
        ic_ir = getattr(backtest, "ic_ir", None)

        metric_notes = []
        if sharpe is not None:
            metric_notes.append(f"Sharpe={sharpe:.2f}")
        if fitness is not None:
            metric_notes.append(f"Fitness={fitness:.2f}")
        if ic_ir is not None:
            metric_notes.append(f"IC_IR={ic_ir:.2f}")

        if metric_notes:
            parts.append("Backtest: " + " | ".join(metric_notes) + ".")

    return " ".join(parts)
