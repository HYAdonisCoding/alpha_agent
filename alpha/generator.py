"""
Alpha Generator
===============
Core alpha generation engine. Combines template-based generation
with market context to produce novel alpha candidates.

The generator can work in two modes:
1. Template-based: systematically explore parameter combinations
2. AI-assisted: use LLM to propose novel combinations (future)
"""

import logging
import random
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

import pandas as pd

from .templates import AlphaTemplates, AlphaTemplate

logger = logging.getLogger(__name__)


@dataclass
class AlphaCandidate:
    """A generated alpha candidate ready for backtesting."""

    name: str
    category: str
    description: str
    expression: str
    template_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    market_context: Optional[Dict] = None


class AlphaGenerator:
    """
    Alpha generation engine.

    Generates alpha candidates through systematic template exploration
    and (optionally) AI-assisted hypothesis generation.

    Usage:
        gen = AlphaGenerator()
        candidates = gen.generate(n=10, market_state={"regime": "bullish"})
    """

    def __init__(
        self,
        mode: str = "template",  # "template", "ai", "hybrid"
        random_seed: Optional[int] = None,
    ):
        self.mode = mode
        self.templates = AlphaTemplates()
        if random_seed:
            random.seed(random_seed)

    def generate(
        self,
        n: int = 10,
        market_state: Optional[Dict] = None,
        categories: Optional[List[str]] = None,
        prefer_categories: Optional[List[str]] = None,
        exclude_templates: Optional[List[str]] = None,
        exclude_expressions: Optional[set] = None,
        brain_template_weights: Optional[Dict[str, float]] = None,
        brain_category_weights: Optional[Dict[str, float]] = None,
    ) -> List[AlphaCandidate]:
        """
        Generate n alpha candidates.

        Args:
            n: Number of candidates to generate
            market_state: Current market conditions (regime, vol, trend, etc.)
            categories: Specific categories to use (default: all)
            prefer_categories: Categories to prefer (weighted higher)
            exclude_templates: Template names to skip
            exclude_expressions: Known-failed expressions to avoid regenerating
            brain_template_weights: Template weights from BRAIN feedback learning
                                     (e.g. {'volume_price_trend': 2.5, 'price_momentum': 0.3})
            brain_category_weights: Category weights from BRAIN feedback learning

        Returns:
            List of AlphaCandidate objects
        """
        if self.mode == "template":
            return self._generate_from_templates(
                n, market_state, categories, prefer_categories,
                exclude_templates, exclude_expressions,
                brain_template_weights, brain_category_weights,
            )
        elif self.mode == "ai":
            return self._generate_with_ai(n, market_state)
        else:  # hybrid
            n_template = n // 2
            n_ai = n - n_template
            candidates = self._generate_from_templates(
                n_template, market_state, categories, prefer_categories,
                exclude_templates, exclude_expressions,
                brain_template_weights, brain_category_weights,
            )
            # AI generation would go here
            return candidates

    def _generate_from_templates(
        self,
        n: int,
        market_state: Optional[Dict] = None,
        categories: Optional[List[str]] = None,
        prefer_categories: Optional[List[str]] = None,
        exclude_templates: Optional[List[str]] = None,
        exclude_expressions: Optional[set] = None,
        brain_template_weights: Optional[Dict[str, float]] = None,
        brain_category_weights: Optional[Dict[str, float]] = None,
    ) -> List[AlphaCandidate]:
        """Generate candidates by exploring template parameter space."""
        exclude_templates = exclude_templates or []
        exclude_expressions = exclude_expressions or set()
        brain_template_weights = brain_template_weights or {}
        brain_category_weights = brain_category_weights or {}

        # Get templates
        if categories:
            all_templates = []
            for cat in categories:
                all_templates.extend(self.templates.get_by_category(cat))
        else:
            all_templates = self.templates.get_all_templates()

        # Filter excluded
        all_templates = [t for t in all_templates if t.name not in exclude_templates]

        if not all_templates:
            logger.warning("No templates available for generation")
            return []

        # Determine which templates to use based on market state + BRAIN feedback
        if market_state and market_state.get("regime"):
            selected = self._market_aware_selection(
                all_templates, market_state, n,
                brain_template_weights=brain_template_weights,
                brain_category_weights=brain_category_weights,
            )
        else:
            # Still apply BRAIN feedback weights even without market state
            selected = self._weighted_selection(
                all_templates, n,
                brain_template_weights=brain_template_weights,
                brain_category_weights=brain_category_weights,
            )

        candidates = []
        max_attempts_per_template = 10  # Avoid infinite loops on exhausted param space
        for template in selected:
            param_combos = self.templates.get_parameter_combinations(template)
            if not param_combos:
                params = {}
                expression = self.templates.instantiate(template, params)
                if expression in exclude_expressions:
                    continue  # Skip exact duplicate of a known failure
            else:
                # Try random param combos, avoiding known-failed expressions
                expression = None
                for _ in range(max_attempts_per_template):
                    params = random.choice(param_combos)
                    candidate_expr = self.templates.instantiate(template, params)
                    if candidate_expr not in exclude_expressions:
                        expression = candidate_expr
                        break

                if expression is None:
                    # All param combos for this template have failed — skip
                    logger.debug(f"All param combos exhausted for template {template.name}, skipping")
                    continue

            candidate = AlphaCandidate(
                name=f"{template.name}_{self._params_suffix(params) if 'params' in dir() else 'base'}",
                category=template.category,
                description=template.description,
                expression=expression,
                template_name=template.name,
                parameters=params if 'params' in dir() else {},
                market_context=market_state,
            )
            candidates.append(candidate)

        return candidates

    def _market_aware_selection(
        self,
        templates: List[AlphaTemplate],
        market_state: Dict,
        n: int,
        brain_template_weights: Optional[Dict[str, float]] = None,
        brain_category_weights: Optional[Dict[str, float]] = None,
    ) -> List[AlphaTemplate]:
        """
        Select templates based on market regime AND BRAIN feedback.

        Market regime weights (base):
        - Bullish: prefer momentum templates (3.0x)
        - Bearish: prefer mean_reversion templates (3.0x)
        - High volatility: prefer volatility templates (2.5x)
        - Low volatility: prefer cross_sectional templates (2.0x)

        BRAIN feedback weights (blended in):
        - Templates with BRAIN acceptances get boosted (up to 3.0x)
        - Templates with only BRAIN rejections get penalized (0.3x)
        - Templates with no BRAIN data keep their market weight

        The final weight = market_weight * brain_weight (multiplicative blend)
        """
        brain_template_weights = brain_template_weights or {}
        brain_category_weights = brain_category_weights or {}

        regime = market_state.get("regime", "neutral")

        # Log brain feedback influence
        if brain_template_weights or brain_category_weights:
            n_influenced = sum(
                1 for t in templates
                if t.name in brain_template_weights or t.category in brain_category_weights
            )
            if n_influenced > 0:
                logger.info(
                    f"  BRAIN feedback influencing {n_influenced}/{len(templates)} templates"
                )

        weights = {}
        for t in templates:
            # 1. Market regime weight
            market_w = 1.0
            if regime == "bullish" and t.category == "momentum":
                market_w = 3.0
            elif regime == "bearish" and t.category == "mean_reversion":
                market_w = 3.0
            elif regime == "high_volatility" and t.category == "volatility":
                market_w = 2.5
            elif regime == "low_volatility" and t.category == "cross_sectional":
                market_w = 2.0

            # 2. BRAIN feedback weight (template-level takes precedence over category-level)
            brain_w = 1.0
            if t.name in brain_template_weights:
                brain_w = brain_template_weights[t.name]
            elif t.category in brain_category_weights:
                brain_w = brain_category_weights[t.category]

            # 3. Blend: multiplicative so both factors matter
            weights[t.name] = market_w * brain_w

            if brain_w != 1.0:
                logger.debug(
                    f"  Template {t.name}: market_w={market_w}, brain_w={brain_w:.2f}, final={weights[t.name]:.2f}"
                )

        # Weighted random selection
        weighted = []
        for t in templates:
            w = max(weights.get(t.name, 1.0), 0.1)  # Minimum weight to avoid zero chance
            count = max(int(w), 1)  # Integer counts for selection
            weighted.extend([t] * count)

        return random.choices(weighted, k=n) if weighted else random.choices(templates, k=n)

    def _weighted_selection(
        self,
        templates: List[AlphaTemplate],
        n: int,
        brain_template_weights: Optional[Dict[str, float]] = None,
        brain_category_weights: Optional[Dict[str, float]] = None,
    ) -> List[AlphaTemplate]:
        """
        Select templates using only BRAIN feedback weights (no market context).

        Used when there's no market regime data but we still want to
        prefer/avoid templates based on BRAIN feedback.
        """
        brain_template_weights = brain_template_weights or {}
        brain_category_weights = brain_category_weights or {}

        if not brain_template_weights and not brain_category_weights:
            return random.choices(templates, k=n)

        weights = {}
        for t in templates:
            w = 1.0
            if t.name in brain_template_weights:
                w = brain_template_weights[t.name]
            elif t.category in brain_category_weights:
                w = brain_category_weights[t.category]
            weights[t.name] = max(w, 0.1)

        weighted = []
        for t in templates:
            count = max(int(weights.get(t.name, 1.0)), 1)
            weighted.extend([t] * count)

        return random.choices(weighted, k=n) if weighted else random.choices(templates, k=n)

    def _generate_with_ai(
        self, n: int, market_state: Optional[Dict] = None
    ) -> List[AlphaCandidate]:
        """
        Use LLM to generate novel alpha ideas.

        This is a placeholder. Requires OpenAI API or similar.
        """
        logger.warning(
            "AI generation mode requires LLM integration. "
            "Set OPENAI_API_KEY and configure ai/ module."
        )
        # Fall back to template generation
        return self._generate_from_templates(n, market_state)

    @staticmethod
    def _params_suffix(params: Dict) -> str:
        """Create a concise suffix from parameter values."""
        if not params:
            return "base"
        return "_".join(f"{k}{v}" for k, v in sorted(params.items()))

    def generate_from_idea(
        self,
        idea: str,
        expression: str,
        category: str = "custom",
    ) -> AlphaCandidate:
        """
        Generate a single alpha from a manual idea/expression.

        Args:
            idea: Natural language description of the alpha idea
            expression: The factor expression
            category: Category tag
        """
        name = idea.lower().replace(" ", "_")[:50]
        return AlphaCandidate(
            name=name,
            category=category,
            description=idea,
            expression=expression,
            template_name="manual",
        )
