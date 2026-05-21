from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "pulse_expenses.sqlite3"


@dataclass(frozen=True)
class Expense:
    id: int
    expense_date: str
    category: str
    amount: float
    note: str
    created_at: str


def initialize_database(db_path: Path | str = DEFAULT_DB_PATH) -> Path:
    database_path = Path(db_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.execute("PRAGMA busy_timeout = 5000;")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date DESC);"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);"
        )

    return database_path


def add_expense(
    amount: float,
    category: str,
    expense_date: str | None = None,
    note: str = "",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Expense:
    normalized_date = _normalize_date(expense_date)
    normalized_category = _normalize_text(category, "category")
    normalized_note = note.strip()
    normalized_amount = _normalize_amount(amount)

    with _connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        cursor = connection.execute(
            """
            INSERT INTO expenses (expense_date, category, amount, note)
            VALUES (?, ?, ?, ?)
            """,
            (normalized_date, normalized_category, normalized_amount, normalized_note),
        )
        row = connection.execute(
            "SELECT id, expense_date, category, amount, note, created_at FROM expenses WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return _row_to_expense(row)


def list_expenses(
    db_path: Path | str = DEFAULT_DB_PATH,
    limit: int | None = None,
    category: str | None = None,
) -> list[Expense]:
    clauses: list[str] = []
    parameters: list[object] = []

    if category:
        clauses.append("category = ?")
        parameters.append(category.strip())

    query = "SELECT id, expense_date, category, amount, note, created_at FROM expenses"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY expense_date DESC, id DESC"
    if limit is not None:
        query += " LIMIT ?"
        parameters.append(int(limit))

    with _connect(db_path) as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [_row_to_expense(row) for row in rows]


def update_expense(
    expense_id: int,
    amount: float,
    category: str,
    expense_date: str,
    note: str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Expense:
    normalized_amount = _normalize_amount(amount)
    normalized_category = _normalize_text(category, "category")
    normalized_date = _normalize_date(expense_date)
    normalized_note = note.strip()

    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE expenses
            SET expense_date = ?, category = ?, amount = ?, note = ?
            WHERE id = ?
            """,
            (normalized_date, normalized_category, normalized_amount, normalized_note, int(expense_id)),
        )
        if cursor.rowcount == 0:
            raise LookupError(f"Expense {expense_id} was not found.")

        row = connection.execute(
            "SELECT id, expense_date, category, amount, note, created_at FROM expenses WHERE id = ?",
            (int(expense_id),),
        ).fetchone()

    return _row_to_expense(row)


def delete_expense(expense_id: int, db_path: Path | str = DEFAULT_DB_PATH) -> bool:
    with _connect(db_path) as connection:
        cursor = connection.execute("DELETE FROM expenses WHERE id = ?", (int(expense_id),))
        return cursor.rowcount > 0


def total_spend_for_range(
    db_path: Path | str = DEFAULT_DB_PATH,
    start_date: str | None = None,
    end_date: str | None = None,
) -> float:
    clauses: list[str] = []
    parameters: list[str] = []

    if start_date:
        clauses.append("expense_date >= ?")
        parameters.append(_normalize_date(start_date))
    if end_date:
        clauses.append("expense_date <= ?")
        parameters.append(_normalize_date(end_date))

    query = "SELECT COALESCE(SUM(amount), 0) FROM expenses"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    with _connect(db_path) as connection:
        value = connection.execute(query, parameters).fetchone()[0]

    return float(value or 0)


def category_totals(db_path: Path | str = DEFAULT_DB_PATH) -> list[tuple[str, float]]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) AS total
            FROM expenses
            GROUP BY category
            ORDER BY total DESC, category ASC
            """
        ).fetchall()

    return [(str(row[0]), float(row[1])) for row in rows]


def recent_daily_totals(db_path: Path | str = DEFAULT_DB_PATH, days: int = 14) -> list[tuple[str, float]]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT expense_date, COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE expense_date >= date('now', ?)
            GROUP BY expense_date
            ORDER BY expense_date ASC
            """,
            (f"-{int(days) - 1} day",),
        ).fetchall()

    return [(str(row[0]), float(row[1])) for row in rows]


@contextmanager
def _connect(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(Path(db_path))
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _normalize_amount(amount: float) -> float:
    try:
        normalized = float(amount)
    except (TypeError, ValueError) as exc:
        raise ValueError("amount must be a number") from exc

    if normalized <= 0:
        raise ValueError("amount must be greater than zero")

    return round(normalized, 2)


def _normalize_date(expense_date: str | None) -> str:
    if not expense_date:
        return date.today().isoformat()

    try:
        return datetime.strptime(str(expense_date).strip(), "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("expense_date must use YYYY-MM-DD format") from exc


def _normalize_text(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


def _row_to_expense(row: sqlite3.Row | None) -> Expense:
    if row is None:
        raise LookupError("Expense record was not found.")

    return Expense(
        id=int(row["id"]),
        expense_date=str(row["expense_date"]),
        category=str(row["category"]),
        amount=float(row["amount"]),
        note=str(row["note"]),
        created_at=str(row["created_at"]),
    )