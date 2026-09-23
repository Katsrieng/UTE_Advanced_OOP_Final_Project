"""Create the configured database and tables, then explicitly seed development data."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database.common import create_schema, settings
from database.seed import seed_database
import mysql.connector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema-only', action='store_true', help='Create database/tables without sample records')
    args = parser.parse_args()
    try:
        config = settings()
        name = create_schema(config)
        print(f'Database and schema ready: {name}')
        if not args.schema_only:
            seed_database(config)
            print('Development seed data ready (existing records preserved).')
    except ValueError as exc:
        print(f'Setup failed: {exc}', file=sys.stderr)
        return 1
    except mysql.connector.Error as exc:
        # Avoid printing connection credentials or SQL statement contents.
        print(f'Setup failed: {type(exc).__name__}. Check server availability, .env and CREATE/table privileges.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
