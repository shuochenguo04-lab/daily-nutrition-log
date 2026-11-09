# Daily Nutrition Log

A local-first Python prototype for recording meals and seeing how much of each daily nutrition target remains. It tracks energy, protein, fat, and carbohydrates. The first version covers the meal-logging workflow with SQLite and a command-line interface.

## Run the demo

Use Python 3.13. The project has no third-party dependencies or API keys.

```sh
python3 tracker.py demo
```

```text
Nutrition summary · 2026-01-15
Metric            Target   Logged  Remaining
Energy (kcal)       2000     1000       1000
Protein (g)          130       72         58
Fat (g)               60       28         32
Carbs (g)            235      115        120

Meals
  #1  Yogurt and oats · 380 kcal
  #2  Chicken rice bowl · 620 kcal
```

The demo uses fictional records in an in-memory database and can be run without affecting any saved meals.

## Log a meal

```sh
python3 tracker.py goal --kcal 2000 --protein 130 --fat 60 --carbs 235
python3 tracker.py add 'Chicken rice bowl' --kcal 620 --protein 46 --fat 16 --carbs 73
python3 tracker.py summary
```

The summary lists meal IDs. Use the ID printed by `add` or `summary` when editing or deleting an entry. For example, on a new database:

```sh
python3 tracker.py edit 1 'Half a chicken rice bowl' --kcal 310 --protein 23 --fat 8 --carbs 37
python3 tracker.py summary
python3 tracker.py delete 1
```

`goal`, `add`, and `summary` use the device's local date by default. Pass `--date YYYY-MM-DD` to select a different day. Targets are set per day. Use whole kilocalories and grams. A negative remaining amount shows the amount over the entered target. The default database is `nutrition.sqlite3` in the working directory. It is ignored by Git.

## Design and verification

- `tracker.py` handles command-line input, validation, and display.
- `nutrition.py` stores daily targets and individual meals. The summary derives totals from meal records, so corrections and deletions do not leave a stale running total.
- `tests/test_tracker.py` exercises the CLI with temporary databases, including persistence, edits, deletions, date boundaries, and invalid input.

```sh
python3 -m unittest discover -s tests -v
```

The GitHub Actions workflow runs the same test suite on pushes and pull requests. See [GitHub's Python CI guide](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

## Project status

This is the manual logging prototype. Planned work includes photo-based estimates with a review step, weight tracking, and a mobile lock-screen widget. The demo targets are examples. Development was assisted by Codex.
