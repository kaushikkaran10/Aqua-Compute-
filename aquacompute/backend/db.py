import os
import sqlite3
from datetime import datetime, timezone


def _get_db_path() -> str:
    """Return database file path from environment variable or default."""
    return os.getenv("DB_PATH", "aquacompute.db")


def init_db() -> None:
    """Initialize the SQLite database and create the runs table if not exists."""
    with sqlite3.connect(_get_db_path()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                tier TEXT NOT NULL,
                model_name TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                reason TEXT NOT NULL,
                energy_kwh REAL NOT NULL,
                direct_water_l REAL NOT NULL,
                indirect_water_l REAL NOT NULL,
                water_l REAL NOT NULL,
                carbon_g REAL NOT NULL,
                baseline_water_l REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_run(record: dict) -> None:
    """Save an execution run record to the database."""
    created_at = record.get("created_at") or datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_get_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO runs (
                prompt, tier, model_name, input_tokens, output_tokens,
                reason, energy_kwh, direct_water_l, indirect_water_l,
                water_l, carbon_g, baseline_water_l, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["prompt"],
                record["tier"],
                record["model_name"],
                record["input_tokens"],
                record["output_tokens"],
                record["reason"],
                record["energy_kwh"],
                record["direct_water_l"],
                record["indirect_water_l"],
                record["water_l"],
                record["carbon_g"],
                record["baseline_water_l"],
                created_at,
            ),
        )


def list_runs() -> list[dict]:
    """Retrieve all saved runs ordered from oldest to newest."""
    with sqlite3.connect(_get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM runs ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]
