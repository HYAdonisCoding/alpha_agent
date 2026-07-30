"""
Database Models
===============
SQLite schema for alpha research platform.

Tables:
- alphas: Alpha factor definitions
- backtests: Backtest results
- submissions: BRAIN submission records
- daily_runs: Daily research pipeline runs
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA = """
-- Alpha factor definitions
CREATE TABLE IF NOT EXISTS alphas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'unknown',
    description TEXT,
    expression TEXT NOT NULL,
    template_name TEXT,
    parameters TEXT,  -- JSON string
    brain_props TEXT,  -- JSON: {brain_name, tags, color, description}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',  -- active, archived, deleted
    UNIQUE(name, expression)
);

-- Backtest results (one per alpha per run)
CREATE TABLE IF NOT EXISTS backtests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alpha_id INTEGER NOT NULL,
    sharpe REAL DEFAULT 0,
    fitness REAL DEFAULT 0,
    turnover REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    annual_return REAL DEFAULT 0,
    annual_volatility REAL DEFAULT 0,
    calmar_ratio REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    ic_mean REAL DEFAULT 0,
    ic_ir REAL DEFAULT 0,
    ic_std REAL DEFAULT 0,
    ic_positive_ratio REAL DEFAULT 0,
    score REAL DEFAULT 0,
    grade TEXT,
    n_days INTEGER DEFAULT 0,
    n_assets INTEGER DEFAULT 0,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alpha_id) REFERENCES alphas(id)
);

-- BRAIN submission records
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alpha_id INTEGER NOT NULL,
    brain_alpha_id TEXT,
    status TEXT DEFAULT 'pending',  -- pending, submitted, accepted, rejected
    simulation_result TEXT,  -- JSON
    submitted_at TIMESTAMP,
    accepted_at TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (alpha_id) REFERENCES alphas(id)
);

-- BRAIN performance feedback records (detailed history)
CREATE TABLE IF NOT EXISTS brain_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alpha_id INTEGER NOT NULL,
    submission_id INTEGER,
    sharpe REAL NOT NULL,
    fitness REAL NOT NULL,
    turnover REAL NOT NULL,
    returns REAL NOT NULL,
    drawdown REAL NOT NULL,
    margin REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'rejected',  -- accepted, rejected
    notes TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alpha_id) REFERENCES alphas(id),
    FOREIGN KEY (submission_id) REFERENCES submissions(id)
);

-- Daily research pipeline runs
CREATE TABLE IF NOT EXISTS daily_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date DATE NOT NULL,
    alphas_generated INTEGER DEFAULT 0,
    alphas_backtested INTEGER DEFAULT 0,
    alphas_approved INTEGER DEFAULT 0,
    alphas_submitted INTEGER DEFAULT 0,
    best_alpha_name TEXT,
    best_alpha_score REAL,
    market_regime TEXT,
    notes TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(run_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_alphas_category ON alphas(category);
CREATE INDEX IF NOT EXISTS idx_alphas_status ON alphas(status);
CREATE INDEX IF NOT EXISTS idx_backtests_alpha_id ON backtests(alpha_id);
CREATE INDEX IF NOT EXISTS idx_backtests_score ON backtests(score DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_alpha_id ON submissions(alpha_id);
CREATE INDEX IF NOT EXISTS idx_daily_runs_date ON daily_runs(run_date);
"""

# Migrations: add columns that may not exist in older databases
# Each migration is run after SCHEMA and errors are silently ignored
# (SQLite doesn't support IF NOT EXISTS for ALTER TABLE)
MIGRATIONS = [
    # v0.2: Add BRAIN feedback columns to submissions
    "ALTER TABLE submissions ADD COLUMN brain_sharpe REAL",
    "ALTER TABLE submissions ADD COLUMN brain_fitness REAL",
    "ALTER TABLE submissions ADD COLUMN brain_turnover REAL",
    "ALTER TABLE submissions ADD COLUMN brain_returns REAL",
    "ALTER TABLE submissions ADD COLUMN brain_drawdown REAL",
    "ALTER TABLE submissions ADD COLUMN brain_margin REAL",
    "ALTER TABLE submissions ADD COLUMN brain_status TEXT",
    # v0.2: New brain_feedback table (for DBs created before v0.2)
    """CREATE TABLE IF NOT EXISTS brain_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alpha_id INTEGER NOT NULL,
        submission_id INTEGER,
        sharpe REAL NOT NULL,
        fitness REAL NOT NULL,
        turnover REAL NOT NULL,
        returns REAL NOT NULL,
        drawdown REAL NOT NULL,
        margin REAL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'rejected',
        notes TEXT,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (alpha_id) REFERENCES alphas(id),
        FOREIGN KEY (submission_id) REFERENCES submissions(id)
    )""",
    # v0.2: New indexes
    "CREATE INDEX IF NOT EXISTS idx_submissions_brain_status ON submissions(brain_status)",
    "CREATE INDEX IF NOT EXISTS idx_brain_feedback_alpha_id ON brain_feedback(alpha_id)",
]


def init_db(db_path: str = "storage/alpha.db") -> sqlite3.Connection:
    """
    Initialize database and create tables if they don't exist.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Database connection
    """
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Create tables
    conn.executescript(SCHEMA)

    # Run migrations (safe — errors on existing columns are ignored)
    for migration in MIGRATIONS:
        try:
            conn.execute(migration)
        except sqlite3.OperationalError:
            pass  # Column/index already exists

    conn.commit()

    logger.info(f"Database initialized at {db_path}")
    return conn
