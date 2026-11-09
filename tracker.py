"""Command-line interface for the daily nutrition log."""

import argparse
import sqlite3
import sys
from contextlib import closing
from dataclasses import astuple
from datetime import date

from nutrition import Nutrition, NutritionLog


def nonnegative_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("enter a whole number") from None
    if not 0 <= number <= 2**63 - 1:
        raise argparse.ArgumentTypeError("enter a nonnegative whole number within SQLite's integer range")
    return number


def meal_id(value: str) -> int:
    number = nonnegative_integer(value)
    if number == 0:
        raise argparse.ArgumentTypeError("meal IDs start at 1")
    return number


def meal_name(value: str) -> str:
    name = value.strip()
    if not name or not name.isprintable():
        raise argparse.ArgumentTypeError("enter a meal name on one line")
    return name


def iso_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() == value:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("use a valid date in YYYY-MM-DD format")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track daily calories and macronutrients locally.")
    parser.add_argument("--db", default="nutrition.sqlite3", help="path to the local SQLite database")
    commands = parser.add_subparsers(dest="command", required=True)
    goal = commands.add_parser("goal", help="set or replace a day's targets")
    add = commands.add_parser("add", help="log a meal")
    edit = commands.add_parser("edit", help="replace a meal's name and nutrition values")
    delete = commands.add_parser("delete", help="remove a meal by ID")
    summary = commands.add_parser("summary", help="show one day's intake and remaining amounts")
    commands.add_parser("demo", help="show an example using fictional data in memory")

    for command in (goal, add, summary):
        command.add_argument("--date", type=iso_date, default=date.today().isoformat(), help="local date, YYYY-MM-DD (default: today)")
    for command in (edit, delete):
        command.add_argument("id", type=meal_id)
    for command in (add, edit):
        command.add_argument("name", type=meal_name)
    for command in (goal, add, edit):
        command.add_argument("--kcal", type=nonnegative_integer, required=True)
        command.add_argument("--protein", type=nonnegative_integer, required=True, help="protein in grams")
        command.add_argument("--fat", type=nonnegative_integer, required=True, help="fat in grams")
        command.add_argument("--carbs", type=nonnegative_integer, required=True, help="carbohydrates in grams")
    return parser


def print_summary(log: NutritionLog, day: str) -> None:
    goal, intake, meals = log.daily_report(day)
    targets = astuple(goal) if goal is not None else ("—",) * 4
    remaining = astuple(goal.remaining_after(intake)) if goal is not None else ("—",) * 4
    print(f"Nutrition summary · {day}")
    print(f"{'Metric':<15} {'Target':>8} {'Logged':>8} {'Remaining':>10}")
    labels = ("Energy (kcal)", "Protein (g)", "Fat (g)", "Carbs (g)")
    for label, target, logged, balance in zip(labels, targets, astuple(intake), remaining):
        print(f"{label:<15} {target:>8} {logged:>8} {balance:>10}")

    if goal is None:
        print("\nSet a goal for this date to see remaining amounts.")
    print("\nMeals")
    if not meals:
        print("  No meals logged.")
    for entry_id, name, kcal in meals:
        print(f"  #{entry_id}  {name} · {kcal} kcal")


def main() -> int:
    args = build_parser().parse_args()
    database = ":memory:" if args.command == "demo" else args.db
    try:
        with closing(sqlite3.connect(database)) as connection:
            log = NutritionLog(connection)
            if args.command == "demo":
                day = "2026-01-15"
                log.set_goal(day, Nutrition(2000, 130, 60, 235))
                log.add_meal(day, "Yogurt and oats", Nutrition(380, 26, 12, 42))
                log.add_meal(day, "Chicken rice bowl", Nutrition(620, 46, 16, 73))
                print_summary(log, day)
            elif args.command == "summary":
                print_summary(log, args.date)
            elif args.command == "delete":
                log.delete_meal(args.id)
                print(f"Deleted meal #{args.id}.")
            else:
                values = Nutrition(args.kcal, args.protein, args.fat, args.carbs)
                if args.command == "goal":
                    log.set_goal(args.date, values)
                    print(f"Saved goals for {args.date}.")
                elif args.command == "add":
                    entry_id = log.add_meal(args.date, args.name, values)
                    print(f"Logged meal #{entry_id} for {args.date}.")
                else:
                    log.edit_meal(args.id, args.name, values)
                    print(f"Updated meal #{args.id}.")
    except (ValueError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
