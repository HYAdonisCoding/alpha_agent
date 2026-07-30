"""
Chart Generator
===============
Visualization module for alpha research.

Generates:
- Cumulative return charts
- Drawdown charts
- IC decay charts
- Score comparison charts
- Correlation heatmaps
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generate charts for alpha research reports.

    Usage:
        charts = ChartGenerator(output_dir="report/output")
        charts.plot_cumulative_returns(result, save=True)
    """

    def __init__(self, output_dir: str = "report/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Lazy import matplotlib
        self._mpl_available = True
        try:
            import matplotlib
            matplotlib.use("Agg")  # Non-interactive backend
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            import seaborn as sns
            self.plt = plt
            self.sns = sns
            self.mdates = mdates
            self._setup_style()
        except ImportError:
            self._mpl_available = False
            logger.warning(
                "matplotlib/seaborn not installed. Charts disabled. "
                "Run: pip install matplotlib seaborn"
            )

    def _setup_style(self):
        """Configure matplotlib style for dark theme."""
        if not self._mpl_available:
            return
        self.plt.style.use("dark_background")
        self.sns.set_palette("viridis")

    def _check_available(self) -> bool:
        if not self._mpl_available:
            logger.warning("Charts unavailable - matplotlib not installed")
        return self._mpl_available

    # ---- Individual Charts ----

    def plot_cumulative_returns(
        self,
        result,
        title: str = "Cumulative Returns",
        save: bool = True,
        filename: str = "cumulative_returns.png",
    ) -> Optional[str]:
        """Plot cumulative returns with drawdown overlay."""
        if not self._check_available():
            return None

        if result.cumulative_returns is None or result.cumulative_returns.empty:
            return None

        fig, (ax1, ax2) = self.plt.subplots(
            2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]}
        )

        # Cumulative returns
        cum_ret = result.cumulative_returns
        ax1.plot(cum_ret.index, cum_ret.values, color="#4ecdc4", linewidth=1.5)
        ax1.fill_between(
            cum_ret.index, 1.0, cum_ret.values,
            where=(cum_ret.values >= 1.0),
            color="#4ecdc4", alpha=0.3,
        )
        ax1.fill_between(
            cum_ret.index, cum_ret.values, 1.0,
            where=(cum_ret.values < 1.0),
            color="#e74c3c", alpha=0.3,
        )
        ax1.axhline(y=1.0, color="white", linestyle="--", alpha=0.3, linewidth=0.8)
        ax1.set_title(f"{title}\nSharpe: {result.sharpe:.2f} | Return: {result.annual_return:.1%}", fontsize=13)
        ax1.set_ylabel("Cumulative Return")
        ax1.grid(True, alpha=0.2)

        # Drawdown
        if result.drawdown_series is not None and not result.drawdown_series.empty:
            dd = result.drawdown_series
            ax2.fill_between(dd.index, 0, dd.values, color="#e74c3c", alpha=0.5)
            ax2.plot(dd.index, dd.values, color="#e74c3c", linewidth=0.8)
            ax2.set_ylabel("Drawdown")
            ax2.set_xlabel("Date")
            ax2.grid(True, alpha=0.2)
            ax2.set_ylim(dd.min() * 1.1, 0.02)

        self.plt.tight_layout()

        if save:
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="#0d1117")
            self.plt.close(fig)
            return str(filepath)

        self.plt.close(fig)
        return None

    def plot_ic_series(
        self,
        result,
        title: str = "IC (Information Coefficient)",
        save: bool = True,
        filename: str = "ic_series.png",
    ) -> Optional[str]:
        """Plot IC series over time."""
        if not self._check_available():
            return None

        if result.ic_series is None or result.ic_series.empty:
            return None

        fig, ax = self.plt.subplots(figsize=(12, 5))

        ic = result.ic_series
        ax.plot(ic.index, ic.values, color="#58a6ff", linewidth=0.8, alpha=0.7)
        ax.axhline(y=0, color="white", linestyle="-", alpha=0.3, linewidth=0.8)

        # Rolling mean
        if len(ic) > 20:
            roll_mean = ic.rolling(20).mean()
            ax.plot(roll_mean.index, roll_mean.values, color="#f0883e", linewidth=2, label="20-period MA")

        ax.axhline(y=ic.mean(), color="#7ee787", linestyle="--", linewidth=1, label=f"Mean: {ic.mean():.4f}")
        ax.set_title(f"{title}\nIC Mean: {ic.mean():.4f} | IC IR: {result.ic_ir:.2f}", fontsize=13)
        ax.set_ylabel("IC")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.2)

        self.plt.tight_layout()

        if save:
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="#0d1117")
            self.plt.close(fig)
            return str(filepath)

        self.plt.close(fig)
        return None

    def plot_score_comparison(
        self,
        results: List[Dict],
        save: bool = True,
        filename: str = "score_comparison.png",
    ) -> Optional[str]:
        """Horizontal bar chart comparing alpha scores."""
        if not self._check_available() or not results:
            return None

        names = [r.get("name", f"Alpha_{i}")[:20] for i, r in enumerate(results)]
        scores = [r.get("score", 0) for r in results]

        # Sort descending
        sorted_idx = np.argsort(scores)
        names = [names[i] for i in sorted_idx]
        scores = [scores[i] for i in sorted_idx]

        fig, ax = self.plt.subplots(figsize=(10, max(6, len(results) * 0.4)))

        colors = []
        for s in scores:
            if s >= 1.5:
                colors.append("#7ee787")  # Green: recommend
            elif s >= 1.0:
                colors.append("#d2991d")  # Yellow: revise
            elif s >= 0.5:
                colors.append("#f0883e")  # Orange: archive
            else:
                colors.append("#f85149")  # Red: failure

        bars = ax.barh(names, scores, color=colors, alpha=0.8)

        # Add score labels
        for bar, score in zip(bars, scores):
            ax.text(
                bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                f"{score:.2f}", va="center", fontsize=9,
            )

        # Threshold lines
        ax.axvline(x=1.5, color="#7ee787", linestyle="--", alpha=0.5, label="Submit")
        ax.axvline(x=1.0, color="#d2991d", linestyle="--", alpha=0.5, label="Revise")

        ax.set_title("Alpha Score Comparison", fontsize=13)
        ax.set_xlabel("Score")
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.1, axis="x")

        self.plt.tight_layout()

        if save:
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="#0d1117")
            self.plt.close(fig)
            return str(filepath)

        self.plt.close(fig)
        return None

    def plot_correlation_heatmap(
        self,
        factor_values: pd.DataFrame,
        save: bool = True,
        filename: str = "correlation_heatmap.png",
    ) -> Optional[str]:
        """Plot correlation heatmap between factors."""
        if not self._check_available():
            return None

        if factor_values.empty or factor_values.shape[1] < 2:
            return None

        corr = factor_values.corr()

        fig, ax = self.plt.subplots(figsize=(10, 8))

        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
        self.sns.heatmap(
            corr,
            mask=mask,
            annot=True,
            fmt=".2f",
            cmap="RdBu_r",
            center=0,
            vmin=-1,
            vmax=1,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
            ax=ax,
        )

        ax.set_title("Factor Correlation Matrix", fontsize=13, pad=15)

        self.plt.tight_layout()

        if save:
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="#0d1117")
            self.plt.close(fig)
            return str(filepath)

        self.plt.close(fig)
        return None

    def plot_dashboard(
        self,
        result,
        ic_result=None,
        save: bool = True,
        filename: str = "alpha_dashboard.png",
    ) -> Optional[str]:
        """Generate a comprehensive alpha dashboard."""
        if not self._check_available():
            return None

        fig = self.plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # Top-left: Cumulative returns
        ax1 = fig.add_subplot(gs[0, :2])
        if result.cumulative_returns is not None and not result.cumulative_returns.empty:
            cr = result.cumulative_returns
            ax1.plot(cr.index, cr.values, color="#4ecdc4", linewidth=1.5)
            ax1.set_title(f"Cumulative Returns (Sharpe: {result.sharpe:.2f})", fontsize=11)
            ax1.grid(True, alpha=0.2)

        # Top-right: Key metrics
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.axis("off")
        metrics_text = "\n".join([
            f"Sharpe: {result.sharpe:.2f}",
            f"Fitness: {result.fitness:.2f}",
            f"Return: {result.annual_return:.1%}",
            f"Vol: {result.annual_volatility:.1%}",
            f"MaxDD: {result.max_drawdown:.1%}",
            f"Turnover: {result.turnover:.1%}",
            f"IC IR: {result.ic_ir:.2f}",
            f"Win Rate: {result.win_rate:.1%}",
        ])
        ax2.text(0.1, 0.9, metrics_text, transform=ax2.transAxes,
                 fontsize=10, verticalalignment="top", fontfamily="monospace",
                 bbox=dict(boxstyle="round", facecolor="#161b22", alpha=0.8))

        # Middle: IC series
        ax3 = fig.add_subplot(gs[1, :])
        ic = result.ic_series if result.ic_series is not None else (ic_result.ic_series if ic_result else None)
        if ic is not None and not ic.empty:
            ax3.plot(ic.index, ic.values, color="#58a6ff", linewidth=0.8, alpha=0.7)
            ax3.axhline(y=0, color="white", alpha=0.3)
            if len(ic) > 20:
                ax3.plot(ic.index, ic.rolling(20).mean(), color="#f0883e", linewidth=2)
            ax3.set_title(f"IC Series (Mean: {ic.mean():.4f})", fontsize=11)
            ax3.grid(True, alpha=0.2)

        # Bottom: Drawdown
        ax4 = fig.add_subplot(gs[2, :])
        if result.drawdown_series is not None and not result.drawdown_series.empty:
            dd = result.drawdown_series
            ax4.fill_between(dd.index, 0, dd.values, color="#e74c3c", alpha=0.5)
            ax4.set_title(f"Drawdown (Max: {result.max_drawdown:.1%})", fontsize=11)
            ax4.grid(True, alpha=0.2)

        self.plt.suptitle(f"Alpha Dashboard: {result.alpha_name}", fontsize=14, y=0.98)

        if save:
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="#0d1117")
            self.plt.close(fig)
            return str(filepath)

        self.plt.close(fig)
        return None
