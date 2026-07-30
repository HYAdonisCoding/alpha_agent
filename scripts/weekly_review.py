#!/usr/bin/env python3
"""
Weekly Review Script
====================
Reviews the past week's alpha research activity and generates insights.

Usage:
    python scripts/weekly_review.py
    python scripts/weekly_review.py --weeks 4
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("weekly_review")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Alpha Agent Weekly Review")
    parser.add_argument("--weeks", type=int, default=1, help="Number of weeks to review")
    args = parser.parse_args()

    logger.info(f"Alpha Agent Weekly Review - {datetime.now().isoformat()}")

    from storage.database import Database
    from ai.memory import AlphaMemory

    db = Database()
    memory = AlphaMemory()

    # Get recent runs
    runs = db.get_recent_runs(n=args.weeks * 7)

    if not runs:
        logger.info("No runs found for this period.")
        return 0

    # Platform stats
    stats = db.get_stats()
    memory_stats = memory.get_stats()

    # Top alphas
    top_alphas = db.get_top_alphas(min_score=0.5, limit=10)

    # Top patterns from memory
    top_patterns = memory.get_top_patterns(n=5)

    # Build summary
    print("\n" + "=" * 60)
    print("ALPHA AGENT - WEEKLY RESEARCH REVIEW")
    print("=" * 60)
    print(f"Period: Last {args.weeks} week(s)")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print()
    print("PLATFORM STATS")
    print(f"  Total active alphas: {stats.get('total_alphas', 0)}")
    print(f"  Total backtests: {stats.get('total_backtests', 0)}")
    print(f"  Success rate (memory): {memory_stats.get('success_rate', 0):.1%}")
    print(f"  Avg Sharpe (success): {memory_stats.get('avg_sharpe', 0):.2f}")
    print()
    print("CATEGORY BREAKDOWN")
    for cat, count in stats.get("by_category", {}).items():
        print(f"  {cat}: {count}")
    print()

    if top_patterns:
        print("TOP PATTERNS (by avg Sharpe)")
        for i, p in enumerate(top_patterns, 1):
            print(
                f"  {i}. {p['category']}: avg Sharpe={p['avg_sharpe']:.2f} "
                f"(n={p['count']}, best: {p['best_name']} @ {p['best_sharpe']:.2f})"
            )
        print()

    if top_alphas:
        print(f"TOP ALPHAS (score >= 0.5)")
        for i, a in enumerate(top_alphas[:10], 1):
            print(
                f"  {i}. {a.get('name', 'N/A'):30s} "
                f"Score={a.get('score', 0):.2f} | "
                f"Sharpe={a.get('sharpe', 0):.2f} | "
                f"IC IR={a.get('ic_ir', 0):.2f}"
            )
        print()

    # Lessons learned this week
    lessons = memory.get_lessons()
    if lessons:
        print(f"LESSONS LEARNED ({len(lessons)} entries)")
        for lesson in lessons[-10:]:  # Last 10
            print(f"  - {lesson}")
        print()

    # Weekly activity
    print("DAILY ACTIVITY")
    for run in runs[:7]:  # Last 7 days
        date = run.get("run_date", "unknown")
        gen = run.get("alphas_generated", 0)
        app = run.get("alphas_approved", 0)
        sub = run.get("alphas_submitted", 0)
        best = run.get("best_alpha_name", "-")
        best_score = run.get("best_alpha_score", 0)
        notes = run.get("notes", "")
        print(
            f"  {date}: Generated={gen}, Approved={app}, Submitted={sub}, "
            f"Best={best} ({best_score:.2f})"
        )
    print()

    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
