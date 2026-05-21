# Pulse Expense Tracker Answers

## 1. How to run

Prerequisite: install Python 3.14+ and make sure `python` is available in the terminal.

Steps:

1. Clone or open the project folder.
2. Start the app with `python app.py`.
3. Use the interactive menu to add, view, update, delete, or summarize expenses.

If you prefer a direct command instead of the menu, the CLI also supports subcommands such as `python app.py add 12.50 Food --note Lunch`.

## 2. Stack choice

I selected plain Python 3 with the standard-library `sqlite3` module because it is the smallest reliable stack for a persistent mini-app.

Why this is the right fit:

- Zero build step: no bundler, transpiler, or asset pipeline.
- Zero third-party dependencies: nothing to install after Python itself.
- Local persistence: SQLite gives durable storage in a single file.
- Portable: the app runs the same on a fresh Windows machine, a laptop, or a CI runner.
- Easy to audit: the storage logic is concentrated in one small module, which is ideal for a technical assessment.

Why Next.js + Docker would be worse here:

- Next.js adds package management, build complexity, and multiple runtime layers that do not improve a local expense logger.
- Docker adds image management and filesystem indirection, which is unnecessary friction for a single-user desktop workflow.
- The assessment goal is fast, dependable delivery. A heavy full-stack framework would trade simplicity for tooling overhead without producing extra user value.

## 3. One real edge case

The code explicitly reduces SQLite write-lock failures by setting a busy timeout during initialization at [db.py](db.py#L33).

Failure state without it:
if another process briefly holds the database file, SQLite can fail immediately with a locked-database error instead of waiting a short period for the lock to clear. That would make normal usage feel flaky when two app actions overlap or the database is touched by another process.

The same storage layer also validates malformed or empty inputs before writing them, which prevents invalid rows from entering the database.

## 4. AI usage

| Tool                        | Prompt / purpose                  | Output used                                                                 |
| --------------------------- | --------------------------------- | --------------------------------------------------------------------------- |
| `apply_patch`               | Create the SQLite storage layer   | `db.py` with schema initialization, CRUD helpers, and summary query helpers |
| `mcp_pylance` syntax checks | Verify Python files parse cleanly | Confirmed `db.py` and `app.py` have no syntax errors                        |
| Terminal smoke test         | Validate persistence and queries  | Confirmed database init and query flow works against SQLite                 |
| `apply_patch`               | Build the CLI entrypoint          | `app.py` with add/list/update/delete/summary commands and interactive menu  |
| `apply_patch`               | Add documentation                 | `README.md` and this `ANSWERS.md` file                                      |

### Architectural change I forced

I forced the implementation away from a heavier web stack and into a Python CLI backed by SQLite. That change removed build tooling, removed frontend boilerplate, and made the whole app launch with a single command while still satisfying persistence and analytics requirements.

## 5. Honest gap

The current submission is intentionally lightweight, which means it does not yet have automated tests or a fully hardened transaction/retry layer around every write path.

24-hour roadmap:

1. Adding `pytest` coverage for storage validation, CRUD behavior, and summary calculations.
2. Adding CLI integration tests for the interactive menu and subcommands.
3. Wrap write operations in a small retry/transaction helper for stronger concurrency behavior.
4. Improve the summary output with trend comparison across recent time windows.
5. Optionally package the app as a single distributable entry point for easier handoff.
