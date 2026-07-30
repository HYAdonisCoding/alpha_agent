"""
Daily Report Generator
======================
Generates the daily alpha research report with:
- Executive summary
- Generated alphas table
- Performance metrics
- AI reviewer feedback
- Recommendations
"""

import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Any

from backtest.engine import BacktestResult
from backtest.metrics import AlphaScore

logger = logging.getLogger(__name__)


class DailyReport:
    """
    Generate daily alpha research reports.

    Supports Markdown and HTML output.

    Usage:
        report = DailyReport(output_dir="report/output")
        report.generate(market_state, results, scores)
    """

    def __init__(self, output_dir: str = "report/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        market_state: Dict,
        results: List[Dict[str, Any]],
        scores: Optional[List[AlphaScore]] = None,
        format: str = "markdown",
    ) -> str:
        """
        Generate the daily research report.

        Args:
            market_state: Market conditions dict
            results: List of {name, expression, result, review, ...}
            scores: List of AlphaScore objects
            format: "markdown" or "html"

        Returns:
            Report content as string, also saves to file
        """
        today = date.today().isoformat()

        if format == "html":
            content = self._build_html(today, market_state, results, scores)
            ext = ".html"
        else:
            content = self._build_markdown(today, market_state, results, scores)
            ext = ".md"

        # Save to file
        filename = f"alpha_daily_report_{today}{ext}"
        filepath = self.output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Report saved to {filepath}")

        return content

    def _build_markdown(
        self,
        today: str,
        market_state: Dict,
        results: List[Dict],
        scores: Optional[List[AlphaScore]],
    ) -> str:
        """Build markdown report."""
        lines = [
            f"# Alpha Research Daily Report",
            f"**Date:** {today}",
            f"**Generated at:** {datetime.now().strftime('%H:%M:%S')}",
            "",
            "---",
            "",
            "## Market Environment",
            "",
        ]

        # Market state
        regime = market_state.get("regime", "unknown")
        vol = market_state.get("volatility", 0)
        trend = market_state.get("trend_strength", 0)
        lines.extend([
            f"- **Regime:** {regime}",
            f"- **Volatility:** {vol:.2%}" if isinstance(vol, float) else f"- **Volatility:** {vol}",
            f"- **Trend Strength:** {trend:.3f}",
            "",
            "---",
            "",
        ])

        # Summary
        n_total = len(results)
        n_approved = sum(
            1 for r in results if r.get("review", {}).get("decision") == "APPROVED"
        )
        n_revise = sum(
            1 for r in results if r.get("review", {}).get("decision") == "REVISE"
        )
        n_rejected = sum(
            1 for r in results if r.get("review", {}).get("decision") == "REJECT"
        )

        lines.extend([
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Generated | {n_total} |",
            f"| Approved | {n_approved} |",
            f"| Needs Revision | {n_revise} |",
            f"| Rejected | {n_rejected} |",
            f"",
            "---",
            "",
        ])

        # Results table
        if results:
            lines.extend([
                "## Alpha Candidates",
                "",
                "| # | Name | Category | Sharpe | Fitness | Turnover | IC IR | Score | Decision |",
                "|---|------|----------|--------|---------|----------|-------|-------|----------|",
            ])

            for i, r in enumerate(results, 1):
                bt = r.get("backtest", {})
                review = r.get("review", {})

                name = r.get("name", f"Alpha_{i}")[:30]
                cat = r.get("category", "-")
                sharpe = f"{bt.get('sharpe', 0):.2f}"
                fitness = f"{bt.get('fitness', 0):.2f}"
                turnover = f"{bt.get('turnover', 0):.1%}"
                ic_ir = f"{bt.get('ic_ir', 0):.2f}"
                score_val = f"{r.get('score', 0):.2f}"
                decision = review.get("decision", "-")

                decision_icon = {
                    "APPROVED": "✅",
                    "REVISE": "🔄",
                    "REJECT": "❌",
                }.get(decision, "")

                lines.append(
                    f"| {i} | {name} | {cat} | {sharpe} | {fitness} | {turnover} | {ic_ir} | {score_val} | {decision_icon} {decision} |"
                )

            lines.extend(["", "---", ""])

        # Top alpha detail
        if results:
            best = max(results, key=lambda r: r.get("score", 0))
            lines.extend([
                "## Top Alpha Detail",
                "",
                f"**Name:** {best.get('name', 'N/A')}",
                f"**Category:** {best.get('category', 'N/A')}",
                f"**Expression:** `{best.get('expression', 'N/A')}`",
                f"**Description:** {best.get('description', 'N/A')}",
                "",
            ])

            bt = best.get("backtest", {})
            lines.extend([
                "### Performance",
                f"- Sharpe: {bt.get('sharpe', 0):.2f}",
                f"- Fitness: {bt.get('fitness', 0):.2f}",
                f"- Annual Return: {bt.get('annual_return', 0):.1%}",
                f"- Max Drawdown: {bt.get('max_drawdown', 0):.1%}",
                f"- Turnover: {bt.get('turnover', 0):.1%}",
                f"- IC IR: {bt.get('ic_ir', 0):.2f}",
                "",
            ])

            review = best.get("review", {})
            if review:
                lines.extend([
                    "### Review",
                    f"**Decision:** {review.get('decision', 'N/A')}",
                    f"**Feedback:** {review.get('feedback', 'N/A')}",
                    "",
                ])

        # Next steps
        lines.extend([
            "---",
            "",
            "## Recommended Actions",
            "",
        ])

        if n_approved > 0:
            lines.append(f"- [ ] Review {n_approved} approved alphas for BRAIN submission")
        if n_revise > 0:
            lines.append(f"- [ ] Optimize {n_revise} alphas needing revision")
        if n_rejected > 0:
            lines.append(f"- [ ] Archive {n_rejected} rejected alphas with lessons learned")

        lines.extend([
            "",
            "---",
            "",
            f"*Generated by Alpha Agent at {datetime.now().isoformat()}*",
            "",
        ])

        return "\n".join(lines)

    def _build_html(
        self,
        today: str,
        market_state: Dict,
        results: List[Dict],
        scores: Optional[List[AlphaScore]],
    ) -> str:
        """Build HTML report."""
        md_content = self._build_markdown(today, market_state, results, scores)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpha Research Daily Report - {today}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
        }}
        h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        h2 {{ color: #f0883e; margin-top: 30px; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #30363d;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{ background: #161b22; color: #58a6ff; }}
        tr:nth-child(even) {{ background: #161b22; }}
        code {{
            background: #161b22;
            padding: 2px 6px;
            border-radius: 4px;
            color: #7ee787;
        }}
        .approved {{ color: #7ee787; font-weight: bold; }}
        .revise {{ color: #d2991d; font-weight: bold; }}
        .reject {{ color: #f85149; font-weight: bold; }}
    </style>
</head>
<body>
    <pre style="white-space: pre-wrap; font-family: inherit;">{md_content}</pre>
</body>
</html>"""

        return html
