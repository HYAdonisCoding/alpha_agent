#!/usr/bin/env python3
"""
Alpha Submission Tracker
=========================
Mark alphas as submitted to WorldQuant BRAIN after manual submission.

Usage:
    # List unsubmitted alphas (ready to submit)
    python scripts/submit_alpha.py --list

    # Mark alpha by database ID as submitted
    python scripts/submit_alpha.py --id 5

    # Mark by name with BRAIN alpha ID
    python scripts/submit_alpha.py --name volume_price_trend_n40 --brain-id ABC123

    # Add notes
    python scripts/submit_alpha.py --id 5 --notes "Submitted via BRAIN web, Sharpe 1.96"

    # Show submission history
    python scripts/submit_alpha.py --history
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("submit_alpha")


def parse_args():
    import argparse

    p = argparse.ArgumentParser(
        description="Mark alphas as submitted to WorldQuant BRAIN"
    )
    p.add_argument("--list", action="store_true",
                   help="List unsubmitted alphas with BRAIN-ready properties")
    p.add_argument("--history", action="store_true",
                   help="Show submission history")
    p.add_argument("--id", type=int,
                   help="Alpha database ID to mark as submitted")
    p.add_argument("--name", type=str,
                   help="Alpha name to mark as submitted")
    p.add_argument("--brain-id", type=str, default="",
                   help="BRAIN alpha ID assigned after submission")
    p.add_argument("--notes", type=str, default="",
                   help="Submission notes (e.g. BRAIN simulation results)")
    p.add_argument("--status", type=str, default="submitted",
                   choices=["submitted", "accepted", "rejected"],
                   help="Submission status (default: submitted)")
    return p.parse_args()


def _format_brain_props(brain_props_str: str) -> dict:
    """Parse brain_props JSON, return empty dict on failure."""
    if not brain_props_str:
        return {}
    try:
        return json.loads(brain_props_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def cmd_list(db):
    """List unsubmitted alphas with their BRAIN-ready properties."""
    alphas = db.get_unsubmitted(min_score=0.0, limit=100)

    if not alphas:
        print("\n  No unsubmitted alphas in database.\n")
        return

    print(f"\n  {'ID':<4} {'Name':<38} {'Score':>7} {'Sharpe':>8} {'BRAIN Name':<35}")
    print(f"  {'-'*4} {'-'*38} {'-'*7} {'-'*8} {'-'*35}")

    for a in alphas:
        props = _format_brain_props(a.get("brain_props"))
        brain_name = props.get("brain_name", a["name"])
        score = a.get("score") or 0
        sharpe = a.get("sharpe") or 0

        print(
            f"  {a['id']:<4} {a['name']:<38} {score:>7.2f} {sharpe:>8.2f} "
            f"{brain_name:<35}"
        )

    print(f"\n  Total: {len(alphas)} unsubmitted\n")

    # Show detailed BRAIN props for the best one
    best = alphas[0] if alphas else None
    if best:
        props = _format_brain_props(best.get("brain_props"))
        if props:
            print("  --- Best Alpha BRAIN Properties ---")
            print(f"  ID:           {best['id']}")
            print(f"  BRAIN Name:   {props.get('brain_name', 'N/A')}")
            print(f"  Tags:         {props.get('tags', 'N/A')}")
            print(f"  Color:        {props.get('color', 'N/A')}")
            print(f"  Description:  {props.get('description', 'N/A')[:120]}...")
            print(f"  Expression:   {best['expression']}")
            print()


def cmd_history(db):
    """Show submission history."""
    submitted = db.get_submitted(limit=50)

    if not submitted:
        print("\n  No submissions recorded yet.\n")
        return

    print(f"\n  {'ID':<4} {'Name':<38} {'Status':>10} {'BRAIN ID':>12} {'Submitted':<20}")
    print(f"  {'-'*4} {'-'*38} {'-'*10} {'-'*12} {'-'*20}")

    for s in submitted:
        status = s.get("submission_status", "?")
        brain_id = (s.get("brain_alpha_id") or "")[:12]
        submitted_at = (s.get("submitted_at") or "")[:19]

        print(
            f"  {s['id']:<4} {s['name']:<38} {status:>10} "
            f"{brain_id:>12} {submitted_at:<20}"
        )

    print(f"\n  Total: {len(submitted)} submitted\n")


def cmd_submit(db, args):
    """Mark an alpha as submitted."""
    from storage.database import Database

    # Find alpha by ID or name
    if args.id:
        alpha = db.get_alpha(args.id)
        if not alpha:
            logger.error(f"No alpha found with ID={args.id}")
            return 1
    elif args.name:
        alpha = db.get_alpha_by_name(args.name)
        if not alpha:
            logger.error(f"No alpha found with name='{args.name}'")
            return 1
    else:
        logger.error("Must specify --id or --name")
        return 1

    alpha_id = alpha["id"]
    alpha_name = alpha["name"]

    submission_id = db.mark_submitted(
        alpha_id=alpha_id,
        brain_alpha_id=args.brain_id,
        notes=args.notes,
    )

    if submission_id:
        logger.info(f"  Marked '{alpha_name}' (ID={alpha_id}) as submitted")
        if args.brain_id:
            logger.info(f"  BRAIN Alpha ID: {args.brain_id}")
    else:
        logger.error(f"  Failed to mark '{alpha_name}' as submitted")
        return 1

    return 0


def main():
    args = parse_args()
    from storage.database import Database

    db = Database()

    try:
        if args.list:
            cmd_list(db)
        elif args.history:
            cmd_history(db)
        elif args.id or args.name:
            return cmd_submit(db, args)
        else:
            # Default: show summary
            unsubmitted = db.get_unsubmitted(limit=100)
            submitted = db.get_submitted(limit=50)

            print(f"\n  Alpha Database Summary")
            print(f"  {'-'*40}")
            print(f"  Unsubmitted:  {len(unsubmitted)}")
            print(f"  Submitted:    {len(submitted)}")
            print(f"\n  Use --list to see unsubmitted alphas")
            print(f"  Use --history to see submission history")
            print(f"  Use --id <N> to mark an alpha as submitted\n")
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
