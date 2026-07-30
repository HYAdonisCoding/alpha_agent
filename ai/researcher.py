"""
AI Researcher
=============
AI-powered alpha hypothesis generation.

Analyzes market data and proposes novel alpha ideas using LLM reasoning.
Works alongside template-based generation for diversity.
"""

import logging
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import pandas as pd
import numpy as np

from alpha.generator import AlphaCandidate
from alpha.templates import AlphaTemplates

logger = logging.getLogger(__name__)


@dataclass
class MarketContext:
    """Summarized market state for AI reasoning."""

    regime: str  # "bullish", "bearish", "neutral", "volatile"
    trend_strength: float
    volatility: float
    volume_trend: str  # "increasing", "decreasing", "stable"
    sector_rotation: Optional[str] = None
    macro_notes: Optional[str] = None


class AIResearcher:
    """
    AI researcher that generates alpha hypotheses.

    Two modes:
    1. Rule-based: Uses market context to weight template selection
    2. LLM-based: (Future) Uses GPT/Claude to propose novel ideas

    Usage:
        researcher = AIResearcher()
        ideas = researcher.research(market_context)
    """

    def __init__(
        self,
        model: str = "rule-based",
        max_ideas: int = 10,
        temperature: float = 0.7,
    ):
        self.model = model
        self.max_ideas = max_ideas
        self.temperature = temperature
        self.templates = AlphaTemplates()
        self._research_history: List[Dict] = []

    def research(
        self,
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        market_context: Optional[MarketContext] = None,
        n_ideas: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate alpha research ideas.

        Args:
            market_data: Current market data
            market_context: Summarized market state
            n_ideas: Number of ideas to generate

        Returns:
            List of idea dicts with: name, category, description, expression
        """
        if self.model == "llm":
            return self._llm_research(market_data, market_context, n_ideas)
        else:
            return self._rule_based_research(market_context, n_ideas)

    def _rule_based_research(
        self,
        market_context: Optional[MarketContext] = None,
        n_ideas: int = 5,
    ) -> List[Dict[str, Any]]:
        """Rule-based idea generation using market context."""
        ideas = []

        # Determine which categories to focus on based on market state
        if market_context:
            regime = market_context.regime
            if regime == "bullish":
                focus = ["momentum", "volume"]
            elif regime == "bearish":
                focus = ["mean_reversion", "volatility"]
            elif regime == "volatile":
                focus = ["volatility", "cross_sectional"]
            else:
                focus = self.templates.get_categories()
        else:
            focus = self.templates.get_categories()

        # Generate ideas from focused categories
        for category in focus:
            templates = self.templates.get_by_category(category)
            if not templates:
                continue

            for template in templates[:2]:  # 2 per category
                param_combos = self.templates.get_parameter_combinations(template)
                if param_combos:
                    params = param_combos[0]  # Use first param combo as base
                    expression = self.templates.instantiate(template, params)
                else:
                    params = {}
                    expression = template.expression

                ideas.append(
                    {
                        "name": template.name,
                        "category": template.category,
                        "description": self._enrich_description(
                            template, market_context
                        ),
                        "expression": expression,
                        "template": template.name,
                        "parameters": params,
                    }
                )

                if len(ideas) >= n_ideas:
                    break

            if len(ideas) >= n_ideas:
                break

        self._research_history.extend(ideas)
        return ideas[:n_ideas]

    def _enrich_description(
        self,
        template,
        market_context: Optional[MarketContext] = None,
    ) -> str:
        """Enrich template description with market context."""
        desc = template.description
        if market_context:
            desc += f" (Market regime: {market_context.regime}, "
            desc += f"vol={market_context.volatility:.2f})"
        return desc

    def _llm_research(
        self,
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        market_context: Optional[MarketContext] = None,
        n_ideas: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        LLM-based research using OpenAI/Claude.

        Requires OPENAI_API_KEY environment variable.
        """
        logger.info("LLM research mode - attempting API call...")

        try:
            import openai

            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(market_data, market_context, n_ideas)

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=2000,
            )

            ideas = json.loads(response.choices[0].message.content)
            return ideas.get("ideas", [])[:n_ideas]

        except ImportError:
            logger.warning("openai package not installed, falling back to rule-based")
            return self._rule_based_research(market_context, n_ideas)
        except Exception as e:
            logger.error(f"LLM research failed: {e}, falling back to rule-based")
            return self._rule_based_research(market_context, n_ideas)

    def _build_system_prompt(self) -> str:
        """Build system prompt for LLM alpha research."""
        return """You are a quantitative research analyst specializing in
alpha factor discovery for WorldQuant BRAIN.

Your task is to propose alpha factor expressions based on market conditions.
Each alpha should be:

1. A valid BRAIN expression using operators like: rank, ts_delta, ts_mean,
   ts_std, ts_rank, ts_zscore, ts_corr, ts_sum, ts_min, ts_max,
   decay_linear, signed_power, scale
2. Theoretically grounded (explain the economic rationale)
3. Low correlation with standard factors

Available data fields: close, volume, open, high, low

Return JSON format:
{
  "ideas": [
    {
      "name": "descriptive_name",
      "category": "momentum|mean_reversion|volume|volatility|cross_sectional",
      "description": "Economic rationale for this alpha",
      "expression": "rank(ts_delta(close,20)) * rank(volume)"
    }
  ]
}"""

    def _build_user_prompt(
        self,
        market_data: Optional[Dict],
        market_context: Optional[MarketContext],
        n_ideas: int,
    ) -> str:
        """Build user prompt with market context."""
        prompt = f"Generate {n_ideas} alpha factor ideas"

        if market_context:
            prompt += f"\n\nMarket Context:\n"
            prompt += f"- Regime: {market_context.regime}\n"
            prompt += f"- Trend strength: {market_context.trend_strength:.2f}\n"
            prompt += f"- Volatility: {market_context.volatility:.2%}\n"
            prompt += f"- Volume trend: {market_context.volume_trend}\n"

        if market_data:
            # Summarize data shape (don't send raw data)
            for key, df in market_data.items():
                prompt += f"\nData '{key}': {df.shape[0]} rows x {df.shape[1]} cols"

        return prompt

    def analyze_market(
        self,
        prices: pd.DataFrame,
        volumes: Optional[pd.DataFrame] = None,
    ) -> MarketContext:
        """
        Analyze current market state from price/volume data.

        Returns a MarketContext with regime classification.
        """
        if prices.empty:
            return MarketContext(
                regime="neutral",
                trend_strength=0.0,
                volatility=0.0,
                volume_trend="stable",
            )

        # Use close prices or first available
        try:
            close = prices.xs("close", level="field", axis=1)
        except (KeyError, AttributeError):
            close = prices

        # Market returns (equal-weighted)
        mkt_returns = close.pct_change().mean(axis=1)

        # Recent trend (20-day)
        recent_ret = mkt_returns.iloc[-20:].mean() * 252
        trend_strength = (
            recent_ret / mkt_returns.iloc[-60:].std()
            if mkt_returns.iloc[-60:].std() > 0
            else 0
        )

        # Volatility (20-day)
        volatility = mkt_returns.iloc[-20:].std() * np.sqrt(252)

        # Volume trend
        if volumes is not None:
            vol_short = volumes.iloc[-10:].mean().mean()
            vol_long = volumes.iloc[-60:].mean().mean()
            if vol_short > vol_long * 1.3:
                volume_trend = "increasing"
            elif vol_short < vol_long * 0.7:
                volume_trend = "decreasing"
            else:
                volume_trend = "stable"
        else:
            volume_trend = "stable"

        # Regime classification
        if volatility > 0.35:
            regime = "volatile"
        elif recent_ret > 0.10:
            regime = "bullish"
        elif recent_ret < -0.10:
            regime = "bearish"
        else:
            regime = "neutral"

        return MarketContext(
            regime=regime,
            trend_strength=round(trend_strength, 3),
            volatility=round(volatility, 3),
            volume_trend=volume_trend,
        )

    def get_research_history(self, n: int = 10) -> List[Dict]:
        """Get recent research ideas."""
        return self._research_history[-n:]
