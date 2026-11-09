"""SQLite storage and daily totals for the nutrition log."""

import sqlite3
from dataclasses import astuple, dataclass


@dataclass(frozen=True)
class Nutrition:
    kcal: int
    protein: int
    fat: int
    carbs: int

    def remaining_after(self, intake: "Nutrition") -> "Nutrition":
        return Nutrition(
            self.kcal - intake.kcal,
            self.protein - intake.protein,
            self.fat - intake.fat,
            self.carbs - intake.carbs,
        )


class NutritionLog:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                day TEXT PRIMARY KEY NOT NULL,
                kcal INTEGER NOT NULL CHECK (kcal >= 0),
                protein INTEGER NOT NULL CHECK (protein >= 0),
                fat INTEGER NOT NULL CHECK (fat >= 0),
                carbs INTEGER NOT NULL CHECK (carbs >= 0)
            );
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                kcal INTEGER NOT NULL CHECK (kcal >= 0),
                protein INTEGER NOT NULL CHECK (protein >= 0),
                fat INTEGER NOT NULL CHECK (fat >= 0),
                carbs INTEGER NOT NULL CHECK (carbs >= 0)
            );
            CREATE INDEX IF NOT EXISTS meals_by_day ON meals (day);
        """)

    def set_goal(self, day: str, values: Nutrition) -> None:
        with self.connection:
            self.connection.execute("""
                INSERT INTO goals (day, kcal, protein, fat, carbs) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(day) DO UPDATE SET
                    kcal = excluded.kcal, protein = excluded.protein,
                    fat = excluded.fat, carbs = excluded.carbs
            """, (day, *astuple(values)))

    def add_meal(self, day: str, name: str, values: Nutrition) -> int:
        with self.connection:
            cursor = self.connection.execute("""
                INSERT INTO meals (day, name, kcal, protein, fat, carbs)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (day, name, *astuple(values)))
            return cursor.lastrowid

    def edit_meal(self, meal_id: int, name: str, values: Nutrition) -> None:
        with self.connection:
            cursor = self.connection.execute("""
                UPDATE meals SET name = ?, kcal = ?, protein = ?, fat = ?, carbs = ?
                WHERE id = ?
            """, (name, *astuple(values), meal_id))
            if cursor.rowcount == 0:
                raise ValueError(f"Meal #{meal_id} was not found.")

    def delete_meal(self, meal_id: int) -> None:
        with self.connection:
            cursor = self.connection.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
            if cursor.rowcount == 0:
                raise ValueError(f"Meal #{meal_id} was not found.")

    def daily_report(self, day: str) -> tuple[Nutrition | None, Nutrition, list[tuple[int, str, int]]]:
        # Read the goal and meals in one snapshot so the report stays consistent.
        with self.connection:
            self.connection.execute("BEGIN")
            goal_row = self.connection.execute(
                "SELECT kcal, protein, fat, carbs FROM goals WHERE day = ?", (day,)
            ).fetchone()
            meals = self.connection.execute("""
                SELECT id, name, kcal, protein, fat, carbs FROM meals WHERE day = ? ORDER BY id
            """, (day,)).fetchall()

        goal = Nutrition(*goal_row) if goal_row is not None else None
        intake = Nutrition(
            sum(meal[2] for meal in meals),
            sum(meal[3] for meal in meals),
            sum(meal[4] for meal in meals),
            sum(meal[5] for meal in meals),
        )
        return goal, intake, [(meal_id, name, kcal) for meal_id, name, kcal, *_ in meals]
