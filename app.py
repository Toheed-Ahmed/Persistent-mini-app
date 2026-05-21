from __future__ import annotations

import argparse
from calendar import monthrange
from datetime import date

from db import (
    DEFAULT_DB_PATH,
    Expense,
    add_expense,
    category_totals,
    delete_expense,
    initialize_database,
    list_expenses,
    recent_daily_totals,
    total_spend_for_range,
    update_expense,
)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    initialize_database(DEFAULT_DB_PATH)

    if args.command is None:
        return _run_interactive_menu()

    if args.command == "add":
        return _handle_add(args.amount, args.category, args.date, args.note or "")

    if args.command == "list":
        return _handle_list(args.limit, args.category)

    if args.command == "update":
        return _handle_update(args.id, args.amount, args.category, args.date, args.note or "")

    if args.command == "delete":
        return _handle_delete(args.id)

    if args.command == "summary":
        return _handle_summary()

    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="Pulse Expense Tracker",
        description="Persistent expense logging with local SQLite storage.",
    )
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a new expense.")
    add_parser.add_argument("amount", type=float, help="Expense amount.")
    add_parser.add_argument("category", help="Expense category.")
    add_parser.add_argument("--date", dest="date", help="Expense date in YYYY-MM-DD format.")
    add_parser.add_argument("--note", default="", help="Optional note.")

    list_parser = subparsers.add_parser("list", help="List stored expenses.")
    list_parser.add_argument("--limit", type=int, default=20, help="Maximum rows to show.")
    list_parser.add_argument("--category", help="Filter by category.")

    update_parser = subparsers.add_parser("update", help="Update an existing expense.")
    update_parser.add_argument("id", type=int, help="Expense id.")
    update_parser.add_argument("amount", type=float, help="Expense amount.")
    update_parser.add_argument("category", help="Expense category.")
    update_parser.add_argument("date", help="Expense date in YYYY-MM-DD format.")
    update_parser.add_argument("--note", default="", help="Optional note.")

    delete_parser = subparsers.add_parser("delete", help="Delete an expense.")
    delete_parser.add_argument("id", type=int, help="Expense id.")

    subparsers.add_parser("summary", help="Show the burn-rate summary.")

    return parser


def _run_interactive_menu() -> int:
    menu = (
        "\nPulse Expense Tracker\n"
        "1) Add expense\n"
        "2) List expenses\n"
        "3) Update expense\n"
        "4) Delete expense\n"
        "5) Show summary\n"
        "6) Quit\n"
    )

    while True:
        print(menu)
        choice = input("Choose an action: ").strip()

        if choice == "1":
            try:
                amount = float(input("Amount: ").strip())
                category = input("Category: ").strip()
                expense_date = input("Date [YYYY-MM-DD, blank for today]: ").strip() or None
                note = input("Note [optional]: ").strip()
                print(_format_expense(add_expense(amount, category, expense_date, note)))
            except ValueError as exc:
                print(f"Error: {exc}")
        elif choice == "2":
            try:
                category = input("Filter category [optional]: ").strip() or None
                limit_text = input("Limit [default 20]: ").strip()
                limit = int(limit_text) if limit_text else 20
                print(_format_expense_table(list_expenses(limit=limit, category=category)))
            except ValueError as exc:
                print(f"Error: {exc}")
        elif choice == "3":
            try:
                expense_id = int(input("Expense id: ").strip())
                amount = float(input("Amount: ").strip())
                category = input("Category: ").strip()
                expense_date = input("Date [YYYY-MM-DD]: ").strip()
                note = input("Note [optional]: ").strip()
                print(_format_expense(update_expense(expense_id, amount, category, expense_date, note)))
            except (ValueError, LookupError) as exc:
                print(f"Error: {exc}")
        elif choice == "4":
            try:
                expense_id = int(input("Expense id: ").strip())
                confirmed = input("Type DELETE to confirm: ").strip().upper()
                if confirmed == "DELETE" and delete_expense(expense_id):
                    print("Deleted.")
                else:
                    print("Delete cancelled.")
            except ValueError as exc:
                print(f"Error: {exc}")
        elif choice == "5":
            print(_format_summary())
        elif choice == "6":
            return 0
        else:
            print("Invalid choice. Select 1-6.")


def _handle_add(amount: float, category: str, expense_date: str | None, note: str) -> int:
    expense = add_expense(amount=amount, category=category, expense_date=expense_date, note=note)
    print(_format_expense(expense))
    return 0


def _handle_list(limit: int | None, category: str | None) -> int:
    expenses = list_expenses(limit=limit, category=category)
    print(_format_expense_table(expenses))
    return 0


def _handle_update(expense_id: int, amount: float, category: str, expense_date: str, note: str) -> int:
    expense = update_expense(
        expense_id=expense_id,
        amount=amount,
        category=category,
        expense_date=expense_date,
        note=note,
    )
    print(_format_expense(expense))
    return 0


def _handle_delete(expense_id: int) -> int:
    deleted = delete_expense(expense_id)
    print("Deleted." if deleted else "Nothing deleted.")
    return 0 if deleted else 1


def _handle_summary() -> int:
    print(_format_summary())
    return 0


def _format_expense(expense: Expense) -> str:
    return (
        f"#{expense.id} | {expense.expense_date} | {expense.category} | "
        f"${expense.amount:.2f} | {expense.note or '-'}"
    )


def _format_expense_table(expenses: list[Expense]) -> str:
    if not expenses:
        return "No expenses recorded yet."

    rows = [
        ["ID", "Date", "Category", "Amount", "Note"],
        *[
            [
                str(expense.id),
                expense.expense_date,
                expense.category,
                f"${expense.amount:.2f}",
                expense.note or "-",
            ]
            for expense in expenses
        ],
    ]
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    rendered = []
    for index, row in enumerate(rows):
        rendered.append(" | ".join(value.ljust(widths[position]) for position, value in enumerate(row)))
        if index == 0:
            rendered.append("-+-".join("-" * width for width in widths))
    return "\n".join(rendered)


def _format_summary() -> str:
    today = date.today()
    month_start = today.replace(day=1)
    month_end = today.replace(day=monthrange(today.year, today.month)[1])
    days_passed = max((today - month_start).days + 1, 1)
    days_remaining = max((month_end - today).days, 0)

    month_spend = total_spend_for_range(start_date=month_start.isoformat(), end_date=today.isoformat())
    all_time_spend = total_spend_for_range()
    recent_days = recent_daily_totals(days=min(days_passed, 14))
    recent_average = _average_daily_spend(recent_days)
    projected_month_end = month_spend + (recent_average * days_remaining)
    pace_label = _pace_label(month_spend, recent_average, days_passed)

    lines = [
        f"Total spend: ${all_time_spend:.2f}",
        f"Month-to-date: ${month_spend:.2f}",
        f"Recent daily average: ${recent_average:.2f}",
        f"Projected month-end: ${projected_month_end:.2f}",
        f"Burn-rate status: {pace_label}",
    ]

    categories = category_totals()
    if categories:
        top_category, top_amount = categories[0]
        lines.append(f"Top category: {top_category} (${top_amount:.2f})")

    return "\n".join(lines)


def _average_daily_spend(rows: list[tuple[str, float]]) -> float:
    if not rows:
        return 0.0
    total = sum(amount for _, amount in rows)
    return total / len(rows)


def _pace_label(month_spend: float, average_daily_spend: float, days_passed: int) -> str:
    if average_daily_spend <= 0:
        return "No spending yet"

    month_average_pace = month_spend / max(days_passed, 1)

    if average_daily_spend <= month_average_pace * 0.9:
        return "Controlled"
    if average_daily_spend <= month_average_pace * 1.1:
        return "Steady"
    return "Accelerating"


if __name__ == "__main__":
    raise SystemExit(main())