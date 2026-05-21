# Pulse Expense Tracker

Pulse is a compact, single-file personal expense tracker intended for technical assessments and quick demos. It provides fast, offline persistence using SQLite, a minimal, scriptable CLI for daily entry, and a lightweight analytics summary (monthly burn-rate and category breakdown) to help users understand spending velocity without external services.

Key qualities:

- Lightweight: no build step and no external dependencies beyond Python 3.
- Persistent: stores data locally in a single SQLite file (`data/pulse_expenses.sqlite3`).
- Practical analytics: month-to-date spend, recent daily average, projected month-end, and top category.
- Audit-friendly: storage and query logic is centralized in `db.py` for quick review.

## Features

- Add, list, update, and delete expenses from an interactive menu or direct subcommands.
- Summary analytics including burn-rate/pacing and top categories.
- Robust input validation and simple concurrency guards (SQLite busy timeout).

## Persistence

All data is stored locally in `data/pulse_expenses.sqlite3`. The database schema is created automatically on first run by the application.

## Run

1. Install Python 3.14 or newer.
2. Open a terminal in the project folder.
3. Run:

```bash
python app.py
```

That starts the interactive menu and stores data in `data/pulse_expenses.sqlite3`.

### Quick examples (non-interactive)

- Add an expense:

```bash
python app.py add 12.50 Food --note "Lunch"
```

- List recent expenses:

```bash
python app.py list --limit 10
```
