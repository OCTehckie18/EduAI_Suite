#!/usr/bin/env python3
"""
Migrate chain_answer_games table to add missing columns
"""
from sqlalchemy import inspect, text
from app.database import engine
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))


def migrate():
    """Run migrations for chain_answer_games table"""

    with engine.begin() as connection:
        inspector = inspect(connection)

        print(" Checking chain_answer_games table...")
        try:
            columns = {col['name']
                       for col in inspector.get_columns('chain_answer_games')}
            print(f"   Current columns: {columns}")

            # Add subject column
            if 'subject' not in columns:
                print("    Adding 'subject' column...")
                connection.execute(
                    text("ALTER TABLE chain_answer_games ADD COLUMN subject VARCHAR")
                )
                print("    'subject' column added")
            else:
                print("    'subject' column already exists")

            # Add ollama_suggestions column
            if 'ollama_suggestions' not in columns:
                print("    Adding 'ollama_suggestions' column...")
                connection.execute(
                    text(
                        "ALTER TABLE chain_answer_games ADD COLUMN ollama_suggestions VARCHAR")
                )
                print("    'ollama_suggestions' column added")
            else:
                print("    'ollama_suggestions' column already exists")

            # Add time_per_turn column if missing
            if 'time_per_turn' not in columns:
                print("    Adding 'time_per_turn' column...")
                connection.execute(
                    text(
                        "ALTER TABLE chain_answer_games ADD COLUMN time_per_turn INTEGER DEFAULT 30")
                )
                print("    'time_per_turn' column added")
            else:
                print("    'time_per_turn' column already exists")

        except Exception as e:
            print(f"    Error: {e}")
            return 1

    print("\n Migration completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(migrate())
