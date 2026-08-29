"""Apply every SQL migration in order using a direct Supabase PostgreSQL URI.

Migrations are written to be idempotent (create ... if not exists, add column if not
exists), so re-running this is safe.
"""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.environ.get("SUPABASE_DB_URL")
    if not database_url:
        print("SUPABASE_DB_URL is required. Copy the PostgreSQL URI from Supabase Dashboard > Connect.")
        return 2

    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migrations:
        print(f"No migrations found in {MIGRATIONS_DIR}")
        return 1

    with psycopg.connect(database_url) as connection:
        for migration in migrations:
            with connection.cursor() as cursor:
                cursor.execute(migration.read_text(encoding="utf-8"))
            connection.commit()
            print(f"Applied {migration.name}")

    print(f"{len(migrations)} migration(s) applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
